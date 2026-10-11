"""Request/response schemas for generation jobs."""
from datetime import date, datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, StringConstraints

from app.core.config import settings
from app.db.models import GenerationJob
from app.utils.dates import as_utc


def _normalize(value: str) -> str:
    """Collapse repeated whitespace and reject control characters."""
    value = " ".join(value.split())
    if not value.isprintable():
        raise ValueError("contains unsupported control characters")
    return value


def text_field(max_length: int):
    return Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=max_length),
        AfterValidator(_normalize),
    ]


class RecipientIn(BaseModel):
    name: text_field(100) = Field(description="Full name printed on the certificate.")
    email: EmailStr = Field(description="Recipient email address.")
    course: text_field(150) = Field(description="Course or programme the recipient completed.")


class JobCreate(BaseModel):
    certificate_title: text_field(100)
    event_name: text_field(150)
    organization_name: text_field(150)
    issue_date: date
    recipients: list[RecipientIn] = Field(min_length=1, max_length=settings.max_recipients_per_job)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "certificate_title": "Certificate of Participation",
                "event_name": "AI Workshop 2026",
                "organization_name": "ABC Organization",
                "issue_date": "2026-10-08",
                "recipients": [
                    {"name": "John Doe", "email": "john@example.com", "course": "Artificial Intelligence"},
                    {"name": "Jane Smith", "email": "jane@example.com", "course": "Artificial Intelligence"},
                ],
            }
        }
    )


class JobCreated(BaseModel):
    job_id: int
    status: str
    total: int


class JobStatusResponse(BaseModel):
    job_id: int
    status: str
    total: int
    successful: int
    failed: int
    completed: int
    progress_percentage: int
    certificate_title: str
    event_name: str
    organization_name: str
    issue_date: date
    created_at: datetime
    completed_at: datetime | None

    @classmethod
    def from_job(cls, job: GenerationJob) -> "JobStatusResponse":
        return cls(
            job_id=job.id,
            status=job.status,
            total=job.total_count,
            successful=job.success_count,
            failed=job.failure_count,
            completed=job.completed_count,
            progress_percentage=job.progress_percentage,
            certificate_title=job.certificate_title,
            event_name=job.event_name,
            organization_name=job.organization_name,
            issue_date=job.issue_date,
            created_at=as_utc(job.created_at),
            completed_at=as_utc(job.completed_at),
        )
