"""
app/utils/datetime_utils.py
---------------------------
Timezone-aware datetime helpers used across services and jobs.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import zoneinfo

from app.core.config import get_settings


def get_company_tz() -> zoneinfo.ZoneInfo:
    """Return the company ZoneInfo object from settings."""
    return zoneinfo.ZoneInfo(get_settings().COMPANY_TIMEZONE)


def now_company() -> datetime:
    """Return the current datetime in the company's configured timezone."""
    return datetime.now(get_company_tz())


def utcnow() -> datetime:
    """Return the current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


def ensure_utc(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def to_company_tz(dt: datetime) -> datetime:
    """Convert any datetime to the company timezone safely."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(get_company_tz())


def week_bounds(ref: date) -> tuple[date, date]:
    """
    Return the Monday and Sunday of the ISO week containing *ref*.

    Monday = week_start, Sunday = week_end.
    """
    week_start = ref - timedelta(days=ref.weekday())
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def minutes_to_hours(minutes: int | None) -> float:
    """Convert integer minutes to decimal hours, rounded to 4 dp."""
    if minutes is None:
        return 0.0
    return round(minutes / 60, 4)


def date_range(start: date, end: date) -> list[date]:
    """Return every date from *start* to *end* inclusive."""
    days = []
    current = start
    while current <= end:
        days.append(current)
        current += timedelta(days=1)
    return days


def is_week_complete(week_end: date) -> bool:
    """
    Return True when the week (Monday-Sunday) has fully elapsed in the company
    timezone.  Compliance evaluation should only proceed for complete weeks.
    """
    today = now_company().date()
    return today > week_end
