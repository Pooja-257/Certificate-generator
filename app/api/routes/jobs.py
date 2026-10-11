from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.database import get_db
from app.db.models import GenerationJob
from app.schemas.certificate import CertificateResponse, JobCertificatesResponse
from app.schemas.job import JobCreate, JobCreated, JobStatusResponse
from app.services.job_processor import create_job, process_job

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def _get_job_or_404(db: Session, job_id: int) -> GenerationJob:
    job = db.get(GenerationJob, job_id)
    if job is None:
        raise AppError(404, "JOB_NOT_FOUND", f"Job {job_id} does not exist.")
    return job


@router.post(
    "",
    response_model=JobCreated,
    status_code=202,
    summary="Create a bulk certificate job",
    description="Validates the request, saves the job and returns immediately (202). "
    "Certificates are generated in the background; poll `GET /api/jobs/{job_id}` for progress.",
)
def create_generation_job(
    payload: JobCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
) -> JobCreated:
    job = create_job(db, payload)
    background_tasks.add_task(process_job, job.id)
    return JobCreated(job_id=job.id, status=job.status, total=job.total_count)


@router.get("", response_model=list[JobStatusResponse], summary="List recent jobs")
def list_jobs(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)) -> list[JobStatusResponse]:
    jobs = db.scalars(select(GenerationJob).order_by(GenerationJob.id.desc()).limit(limit)).all()
    return [JobStatusResponse.from_job(job) for job in jobs]


@router.get("/{job_id}", response_model=JobStatusResponse, summary="Get job status and progress")
def get_job(job_id: int, db: Session = Depends(get_db)) -> JobStatusResponse:
    return JobStatusResponse.from_job(_get_job_or_404(db, job_id))


@router.get(
    "/{job_id}/certificates",
    response_model=JobCertificatesResponse,
    summary="List every certificate in a job",
)
def list_job_certificates(job_id: int, db: Session = Depends(get_db)) -> JobCertificatesResponse:
    job = _get_job_or_404(db, job_id)
    return JobCertificatesResponse(
        job_id=job.id,
        status=job.status,
        total=job.total_count,
        certificates=[CertificateResponse.from_certificate(c) for c in job.certificates],
    )
