"""Creating jobs and processing them in the background, one certificate at a time."""
import logging

from sqlalchemy.orm import Session

from app.db import database
from app.db.models import Certificate, CertificateStatus, GenerationJob, JobStatus, utcnow
from app.schemas.job import JobCreate
from app.services import certificate_generator
from app.services.certificate_generator import CertificateData, CertificateGenerationError

logger = logging.getLogger(__name__)


def create_job(db: Session, payload: JobCreate) -> GenerationJob:
    """Save the job and one PENDING certificate row per recipient."""
    job = GenerationJob(
        certificate_title=payload.certificate_title,
        event_name=payload.event_name,
        organization_name=payload.organization_name,
        issue_date=payload.issue_date,
        status=JobStatus.PENDING.value,
        total_count=len(payload.recipients),
        certificates=[
            Certificate(recipient_name=r.name, recipient_email=r.email, course=r.course)
            for r in payload.recipients
        ],
    )
    db.add(job)
    db.commit()
    return job


def _final_status(job: GenerationJob) -> JobStatus:
    if job.failure_count == 0:
        return JobStatus.COMPLETED
    if job.success_count == 0:
        return JobStatus.FAILED
    return JobStatus.COMPLETED_WITH_ERRORS


def _generate_one(db: Session, job: GenerationJob, cert: Certificate) -> None:
    """Generate a single certificate. Any error is recorded on that certificate only."""
    try:
        data = CertificateData(
            certificate_id=cert.id,
            job_id=job.id,
            recipient_name=cert.recipient_name,
            course=cert.course,
            certificate_title=job.certificate_title,
            event_name=job.event_name,
            organization_name=job.organization_name,
            issue_date=job.issue_date,
        )
        path = certificate_generator.build_certificate_path(cert.id)
        certificate_generator.generate_certificate_pdf(data, path)
        cert.status = CertificateStatus.SUCCESS.value
        cert.file_path = path.name
        cert.error_message = None
        job.success_count += 1
    except Exception as exc:  # noqa: BLE001 - one bad certificate must never stop the batch
        logger.exception("Certificate %s failed", cert.id)
        db.rollback()
        cert.status = CertificateStatus.FAILED.value
        cert.file_path = None
        cert.error_message = (
            str(exc) if isinstance(exc, CertificateGenerationError)
            else "Unexpected error while generating this certificate."
        )
        job.failure_count += 1
    db.commit()  # commit per certificate so the status endpoint shows live progress


def process_job(job_id: int) -> None:
    """Background task entry point. Opens its own session because the request's session is closed by then."""
    db = database.SessionLocal()
    try:
        job = db.get(GenerationJob, job_id)
        if job is None:
            logger.error("Job %s vanished before processing", job_id)
            return
        job.status = JobStatus.PROCESSING.value
        db.commit()

        for cert in list(job.certificates):
            if cert.status == CertificateStatus.PENDING.value:
                _generate_one(db, job, cert)

        job.status = _final_status(job).value
        job.completed_at = utcnow()
        db.commit()
    except Exception:  # noqa: BLE001 - last-resort guard so the job never stays PROCESSING forever
        logger.exception("Job %s crashed", job_id)
        db.rollback()
        job = db.get(GenerationJob, job_id)
        if job is not None:
            job.status = JobStatus.FAILED.value
            job.completed_at = utcnow()
            db.commit()
    finally:
        db.close()
