"""Application settings, read once from environment variables (and an optional .env file)."""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    database_url: str
    certificate_dir: Path
    cors_origins: list[str]
    max_recipients_per_job: int

    @classmethod
    def from_env(cls) -> "Settings":
        cert_dir = Path(os.getenv("CERTIFICATE_DIR", BASE_DIR / "generated_certificates"))
        if not cert_dir.is_absolute():
            cert_dir = BASE_DIR / cert_dir
        origins = os.getenv("CORS_ORIGINS", "http://localhost:5173")
        return cls(
            database_url=os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'bulk_certificates.db'}"),
            certificate_dir=cert_dir.resolve(),
            cors_origins=[o.strip() for o in origins.split(",") if o.strip()],
            max_recipients_per_job=int(os.getenv("MAX_RECIPIENTS_PER_JOB", "1000")),
        )


settings = Settings.from_env()
