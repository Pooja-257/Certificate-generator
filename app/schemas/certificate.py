"""Response schemas for certificates."""
from datetime import datetime

from pydantic import BaseModel

from app.db.models import Certificate, CertificateStatus
from app.utils.dates import as_utc


class CertificateResponse(BaseModel):
    id: int
    job_id: int
    recipient_name: str
    recipient_email: str
    course: str
    status: str
    download_url: str | None = None
    error_message: str | None = None
    created_at: datetime

    @classmethod
    def from_certificate(cls, cert: Certificate) -> "CertificateResponse":
        ready = cert.status == CertificateStatus.SUCCESS.value
        return cls(
            id=cert.id,
            job_id=cert.job_id,
            recipient_name=cert.recipient_name,
            recipient_email=cert.recipient_email,
            course=cert.course,
            status=cert.status,
            download_url=f"/api/certificates/{cert.id}" if ready else None,
            error_message=cert.error_message,
            created_at=as_utc(cert.created_at),
        )


class JobCertificatesResponse(BaseModel):
    job_id: int
    status: str
    total: int
    certificates: list[CertificateResponse]
