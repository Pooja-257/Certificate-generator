from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.db.database import get_db
from app.db.models import Certificate, CertificateStatus
from app.utils.files import resolve_inside, sanitize_for_filename

router = APIRouter(prefix="/certificates", tags=["Certificates"])


@router.get(
    "/{certificate_id}",
    summary="Download a generated certificate (PDF)",
    responses={404: {"description": "Certificate or file not found"}, 409: {"description": "Certificate not ready"}},
)
def download_certificate(certificate_id: int, db: Session = Depends(get_db)) -> FileResponse:
    cert = db.get(Certificate, certificate_id)
    if cert is None:
        raise AppError(404, "CERTIFICATE_NOT_FOUND", f"Certificate {certificate_id} does not exist.")
    if cert.status == CertificateStatus.PENDING.value:
        raise AppError(409, "CERTIFICATE_NOT_READY", "This certificate is still being generated.")
    if cert.status == CertificateStatus.FAILED.value or not cert.file_path:
        raise AppError(409, "CERTIFICATE_FAILED", "This certificate could not be generated, so there is nothing to download.")

    path = resolve_inside(settings.certificate_dir, cert.file_path)
    if path is None or not path.is_file():
        raise AppError(404, "CERTIFICATE_FILE_MISSING", "The certificate file is no longer available.")

    download_name = f"{sanitize_for_filename(cert.recipient_name)}_certificate_{cert.id}.pdf"
    return FileResponse(path, media_type="application/pdf", filename=download_name)
