"""Test setup: an isolated SQLite file and certificate folder, created before the app is imported."""
import os
import shutil
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="certgen_tests_"))
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP / 'test.db'}"
os.environ["CERTIFICATE_DIR"] = str(_TMP / "certs")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.db.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services import certificate_generator  # noqa: E402


@pytest.fixture(autouse=True)
def clean_state():
    """Fresh tables and an empty certificate folder for every test."""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    shutil.rmtree(settings.certificate_dir, ignore_errors=True)
    settings.certificate_dir.mkdir(parents=True, exist_ok=True)
    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:  # BackgroundTasks finish before post() returns
        yield test_client


@pytest.fixture
def fake_pdf(monkeypatch):
    """Replace real PDF rendering with a tiny fake; recipients named 'Fail Me' raise an error."""

    def _fake(data, output_path):
        if data.recipient_name == "Fail Me":
            raise certificate_generator.CertificateGenerationError("Simulated rendering failure.")
        output_path.write_bytes(b"%PDF-1.4 fake")
        return output_path

    monkeypatch.setattr(certificate_generator, "generate_certificate_pdf", _fake)


def make_payload(*names: str) -> dict:
    names = names or ("John Doe", "Jane Smith")
    return {
        "certificate_title": "Certificate of Participation",
        "event_name": "AI Workshop 2026",
        "organization_name": "ABC Organization",
        "issue_date": "2026-10-08",
        "recipients": [
            {"name": n, "email": f"{n.split()[0].lower()}@example.com", "course": "Artificial Intelligence"}
            for n in names
        ],
    }
