"""SQLAlchemy models: one GenerationJob has many Certificates."""
import enum
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_ERRORS = "COMPLETED_WITH_ERRORS"
    FAILED = "FAILED"


class CertificateStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    certificate_title: Mapped[str] = mapped_column(String(150))
    event_name: Mapped[str] = mapped_column(String(150))
    organization_name: Mapped[str] = mapped_column(String(150))
    issue_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default=JobStatus.PENDING.value, index=True)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    certificates: Mapped[list["Certificate"]] = relationship(
        back_populates="job", cascade="all, delete-orphan", order_by="Certificate.id"
    )

    @property
    def completed_count(self) -> int:
        return self.success_count + self.failure_count

    @property
    def progress_percentage(self) -> int:
        """Whole-number progress; rounds down so 99.5% never shows as 100% too early."""
        if self.total_count == 0:
            return 0
        return min(100, self.completed_count * 100 // self.total_count)


class Certificate(Base):
    __tablename__ = "certificates"
    __table_args__ = (Index("ix_certificates_job_id_status", "job_id", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("generation_jobs.id", ondelete="CASCADE"), index=True)
    recipient_name: Mapped[str] = mapped_column(String(100))
    recipient_email: Mapped[str] = mapped_column(String(254))
    course: Mapped[str] = mapped_column(String(150))
    status: Mapped[str] = mapped_column(String(20), default=CertificateStatus.PENDING.value)
    # Only the file NAME is stored (e.g. "certificate_7.pdf"), never an absolute path.
    file_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    job: Mapped[GenerationJob] = relationship(back_populates="certificates")
