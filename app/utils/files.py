"""Helpers for building safe file names and safely resolving files inside the certificate folder."""
import re
from pathlib import Path


def sanitize_for_filename(text: str, max_length: int = 40) -> str:
    """Turn arbitrary text into a safe ASCII slug: 'Ana / ../Évora' -> 'Ana_vora'."""
    slug = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")
    return slug[:max_length] or "recipient"


def resolve_inside(base_dir: Path, filename: str) -> Path | None:
    """Return base_dir/filename only if it stays inside base_dir (blocks '../' tricks)."""
    base = base_dir.resolve()
    candidate = (base / filename).resolve()
    if candidate.parent != base:
        return None
    return candidate
