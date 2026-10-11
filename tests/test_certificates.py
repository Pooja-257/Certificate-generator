from app.core.config import settings
from app.db import database
from app.db.models import Certificate, CertificateStatus
from tests.conftest import make_payload


def _create(client, *names):
    job_id = client.post("/api/jobs", json=make_payload(*names)).json()["job_id"]
    return job_id, client.get(f"/api/jobs/{job_id}/certificates").json()


def test_list_job_certificates(client, fake_pdf):
    job_id, body = _create(client, "Ann A", "Fail Me")
    assert body["job_id"] == job_id and body["total"] == 2
    ok, failed = body["certificates"]
    assert ok["status"] == "SUCCESS" and ok["download_url"] == f"/api/certificates/{ok['id']}"
    assert failed["status"] == "FAILED" and failed["download_url"] is None
    assert failed["error_message"] == "Simulated rendering failure."


def test_list_certificates_for_missing_job(client):
    assert client.get("/api/jobs/42/certificates").status_code == 404


def test_download_certificate(client, fake_pdf):
    _, body = _create(client, "Ann A")
    cert_id = body["certificates"][0]["id"]
    response = client.get(f"/api/certificates/{cert_id}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    assert f"Ann_A_certificate_{cert_id}.pdf" in response.headers["content-disposition"]


def test_certificate_not_found(client):
    response = client.get("/api/certificates/999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CERTIFICATE_NOT_FOUND"


def test_failed_certificate_cannot_be_downloaded(client, fake_pdf):
    _, body = _create(client, "Fail Me")
    response = client.get(f"/api/certificates/{body['certificates'][0]['id']}")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CERTIFICATE_FAILED"


def test_pending_certificate_cannot_be_downloaded(client, fake_pdf):
    _, body = _create(client, "Ann A")
    cert_id = body["certificates"][0]["id"]
    with database.SessionLocal() as db:
        db.get(Certificate, cert_id).status = CertificateStatus.PENDING.value
        db.commit()
    response = client.get(f"/api/certificates/{cert_id}")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CERTIFICATE_NOT_READY"


def test_missing_file_returns_404(client, fake_pdf):
    _, body = _create(client, "Ann A")
    cert_id = body["certificates"][0]["id"]
    (settings.certificate_dir / f"certificate_{cert_id}.pdf").unlink()
    assert client.get(f"/api/certificates/{cert_id}").status_code == 404


def test_path_traversal_in_stored_filename_is_blocked(client, fake_pdf):
    _, body = _create(client, "Ann A")
    cert_id = body["certificates"][0]["id"]
    with database.SessionLocal() as db:
        db.get(Certificate, cert_id).file_path = "../../etc/passwd"
        db.commit()
    assert client.get(f"/api/certificates/{cert_id}").status_code == 404
