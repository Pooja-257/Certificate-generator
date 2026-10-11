"""Date helpers."""
from datetime import datetime, timezone


def as_utc(value: datetime | None) -> datetime | None:
    """SQLite drops timezone info; everything we store is UTC, so put it back before sending to clients."""
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
