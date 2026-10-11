from datetime import date

import pytest

from app.core.config import settings
from app.db.models import GenerationJob
from app.services import certificate_generator as gen
from app.utils.files import resolve_inside, sanitize_for_filename


def _data(name="John Doe", **overrides) -> gen.CertificateData:
    values = dict(
        certificate_id=1, job_id=1, recipient_name=name, course="Artificial Intelligence",
        certificate_title="Certificate of Participation", event_name="AI Workshop 2026",
        organization_name="ABC Organization", issue_date=date(2026, 10, 8),
    )
    values.update(overrides)
    return gen.CertificateData(**values)


def test_real_pdf_is_created(tmp_path):
    out = gen.generate_certificate_pdf(_data(), tmp_path / "certificate_1.pdf")
    assert out.read_bytes().startswith(b"%PDF")
    assert out.stat().st_size > 1000
    assert not list(tmp_path.glob("*.tmp"))


def test_very_long_name_still_renders(tmp_path):
    out = gen.generate_certificate_pdf(_data("A" * 100), tmp_path / "long.pdf")
    assert out.exists()


def test_unsupported_characters_raise_clear_error(tmp_path):
    with pytest.raises(gen.CertificateGenerationError, match="name"):
        gen.generate_certificate_pdf(_data("李雷"), tmp_path / "x.pdf")
    assert not (tmp_path / "x.pdf").exists()


def test_accented_latin_names_are_supported(tmp_path):
    assert gen.generate_certificate_pdf(_data("José Müller"), tmp_path / "a.pdf").exists()


def test_certificate_path_uses_only_the_id():
    path = gen.build_certificate_path(7)
    assert path == settings.certificate_dir / "certificate_7.pdf"


def test_date_format():
    assert gen.format_date(date(2026, 10, 8)) == "08 October 2026"


@pytest.mark.parametrize("raw,expected", [
    ("John Doe", "John_Doe"),
    ("../../etc/passwd", "etc_passwd"),
    ("Ana / ..\\Évora", "Ana_vora"),
    ("李雷", "recipient"),
])
def test_filename_sanitizing(raw, expected):
    assert sanitize_for_filename(raw) == expected


def test_resolve_inside_blocks_traversal(tmp_path):
    assert resolve_inside(tmp_path, "certificate_1.pdf") == (tmp_path / "certificate_1.pdf").resolve()
    assert resolve_inside(tmp_path, "../secret.txt") is None
    assert resolve_inside(tmp_path, "/etc/passwd") is None


@pytest.mark.parametrize("success,failed,total,expected", [(0, 0, 4, 0), (1, 0, 3, 33), (65, 2, 100, 67), (199, 0, 200, 99), (3, 0, 3, 100)])
def test_progress_percentage(success, failed, total, expected):
    job = GenerationJob(total_count=total, success_count=success, failure_count=failed)
    assert job.progress_percentage == expected


def test_end_to_end_with_real_pdfs(client):
    """No mocking: the whole flow, including an unrenderable name."""
    from tests.conftest import make_payload

    job_id = client.post("/api/jobs", json=make_payload("Ann A", "李雷")).json()["job_id"]
    status = client.get(f"/api/jobs/{job_id}").json()
    assert status["status"] == "COMPLETED_WITH_ERRORS"
    ok = client.get(f"/api/jobs/{job_id}/certificates").json()["certificates"][0]
    assert client.get(ok["download_url"]).content.startswith(b"%PDF")
