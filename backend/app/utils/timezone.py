from datetime import datetime, timezone, timedelta
from typing import Annotated, Optional, Any
from pydantic import AfterValidator

# Machine standard: UTC
UTC = timezone.utc

# India Standard Time (IST, UTC+05:30), IANA: Asia/Kolkata
IST = timezone(timedelta(hours=5, minutes=30), name="Asia/Kolkata")


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensures a datetime object is timezone-aware in UTC.
    If the datetime is naive (as stored in SQLite/PostgreSQL), it is assigned UTC tzinfo.
    If it already has timezone information, it is converted to UTC.
    """
    if dt is None:
        return None
    if not isinstance(dt, datetime):
        return dt
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def utc_to_ist(dt: Optional[datetime]) -> Optional[datetime]:
    """Converts a UTC datetime (naive or aware) to Indian Standard Time (IST, UTC+5:30)."""
    if dt is None:
        return None
    if not isinstance(dt, datetime):
        return dt
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(IST)


def format_ist_datetime(dt: Optional[datetime], fmt: str = "%d %b %Y, %I:%M %p") -> str:
    """Formats a UTC datetime in IST with standard 12-hour AM/PM format.
    Example: '02 Oct 2026, 12:47 PM'
    """
    if dt is None:
        return "—"
    ist_dt = utc_to_ist(dt)
    return ist_dt.strftime(fmt)


# Pydantic v2 Type: Ensures all naive UTC datetimes from DB models are tagged as UTC
# and serialized to machine-readable ISO 8601 UTC strings ending with 'Z'
UtcDatetime = Annotated[datetime, AfterValidator(ensure_utc)]
