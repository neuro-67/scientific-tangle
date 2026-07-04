"""Single source of 'now' for the domain — testable time."""

from datetime import UTC, datetime


def now_utc() -> datetime:
    """Return the current time in UTC."""
    return datetime.now(UTC)
