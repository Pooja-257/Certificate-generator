import pytest

from tests.conftest import make_payload


def test_create_job_returns_id_and_total(client, fake_pdf):
    response = client.post("/api/jobs", json=make_payload())
    assert response.status_code == 202
    body = response.json()
    assert body["job_id"] == 1
    assert body["total"] == 2
    assert body["status"] == "PENDING"


def test_empty_recipient_list_is_rejected(client):
    payload = make_payload()
    payload["recipients"] = []
    response = client.post("/api/jobs", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize(
    "recipient",
    [
        {"name": "   ", "email": "a@example.com", "course": "AI"},
        {"name": "Ann", "email": "not-an-email", "course": "AI"},
        {"name": "Ann", "email": "a@example.com", "course": ""},
        {"name": "Ann", "email": "a@example.com"},
    ],
)
def test_invalid_recipient_is_rejected(client, recipient):
    payload = make_payload()
    payload["recipients"] = [recipient]
    response = client.post("/api/jobs", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["details"]


def test_invalid_certificate_fields_are_rejected(client):
    payload = make_payload()
    payload["event_name"] = ""
    payload["issue_date"] = "not-a-date"
    response = client.post("/api/jobs", json=payload)
    assert response.status_code == 422
    fields = {d["field"] for d in response.json()["error"]["details"]}
    assert {"event_name", "issue_date"} <= fields


def test_job_status_after_successful_bulk_generation(client, fake_pdf):
    job_id = client.post("/api/jobs", json=make_payload("Ann A", "Bob B", "Cy C")).json()["job_id"]
    body = client.get(f"/api/jobs/{job_id}").json()
    assert body["status"] == "COMPLETED"
    assert (body["total"], body["successful"], body["failed"], body["completed"]) == (3, 3, 0, 3)
    assert body["progress_percentage"] == 100
    assert body["completed_at"] is not None


def test_individual_failure_does_not_stop_the_batch(client, fake_pdf):
    job_id = client.post("/api/jobs", json=make_payload("Ann A", "Fail Me", "Cy C")).json()["job_id"]
    body = client.get(f"/api/jobs/{job_id}").json()
    assert body["status"] == "COMPLETED_WITH_ERRORS"
    assert (body["successful"], body["failed"]) == (2, 1)
    assert body["progress_percentage"] == 100


def test_job_fails_when_every_certificate_fails(client, fake_pdf):
    job_id = client.post("/api/jobs", json=make_payload("Fail Me")).json()["job_id"]
    assert client.get(f"/api/jobs/{job_id}").json()["status"] == "FAILED"


def test_unexpected_exception_is_recorded_and_batch_continues(client, monkeypatch):
    from app.services import certificate_generator

    def boom(data, output_path):
        if data.recipient_name == "Ann A":
            raise RuntimeError("disk exploded at /secret/path")
        output_path.write_bytes(b"%PDF")

    monkeypatch.setattr(certificate_generator, "generate_certificate_pdf", boom)
    job_id = client.post("/api/jobs", json=make_payload("Ann A", "Bob B")).json()["job_id"]
    certs = client.get(f"/api/jobs/{job_id}/certificates").json()["certificates"]
    assert [c["status"] for c in certs] == ["FAILED", "SUCCESS"]
    assert "/secret/path" not in certs[0]["error_message"]  # internals are not leaked


def test_job_not_found(client):
    response = client.get("/api/jobs/999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "JOB_NOT_FOUND"


def test_list_jobs_returns_newest_first(client, fake_pdf):
    client.post("/api/jobs", json=make_payload())
    client.post("/api/jobs", json=make_payload("Zed Z"))
    ids = [j["job_id"] for j in client.get("/api/jobs").json()]
    assert ids == [2, 1]


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}
