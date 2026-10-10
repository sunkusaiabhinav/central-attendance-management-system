"""
app/services/attendance_service.py
------------------------------------
Business logic for check-in, check-out, and working-hour calculations.

Policy / design decisions documented here
------------------------------------------
* An employee may have multiple attendance records per day (e.g. left for lunch
  and returned).  All COMPLETED sessions for a day are summed for daily totals.
* Only COMPLETED sessions are used in compliance calculations.  INCOMPLETE
  sessions (no checkout) are excluded from qualifying time.
* The employee identity used for check-in / check-out comes from the
  authenticated JWT, never from an untrusted client-supplied employee_id.
* ``working_minutes`` is stored as an integer (floor of total seconds / 60).
* Overlapping sessions are rejected with 409.
* Exit time must be strictly after entry time (>0 second gap).
* Only OFFICE sessions count toward the minimum office days requirement.
* WFH sessions count toward total working hours but NOT office-day count.
* Missing checkout: sessions left ACTIVE at EOD remain INCOMPLETE; a scheduled
  job (or manual admin action) can mark them.  Compliance ignores INCOMPLETE.
* Approved leave / holidays: outside scope of this system — the HR system
  should manage those.  Absence with no record is treated as NOT_ATTENDED.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models.attendance import AttendanceRecord, AttendanceStatus, WorkLocation
from app.models.employee import Employee
from app.utils.datetime_utils import ensure_utc, to_company_tz, utcnow

logger = logging.getLogger(__name__)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _active_session(db: Session, employee_id: int) -> Optional[AttendanceRecord]:
    """Return the current ACTIVE attendance session, or None."""
    return db.scalar(
        select(AttendanceRecord).where(
            AttendanceRecord.employee_id == employee_id,
            AttendanceRecord.status == AttendanceStatus.ACTIVE,
        )
    )


def _has_overlapping_session(
    db: Session, employee_id: int, start: datetime, end: datetime, exclude_id: int | None = None
) -> bool:
    """
    Return True if [start, end) overlaps any existing ACTIVE or COMPLETED session
    for the employee.
    """
    q = select(AttendanceRecord).where(
        AttendanceRecord.employee_id == employee_id,
        AttendanceRecord.status.in_(
            [AttendanceStatus.ACTIVE, AttendanceStatus.COMPLETED]
        ),
        or_(
            and_(
                AttendanceRecord.entry_time < end,
                or_(
                    AttendanceRecord.exit_time.is_(None),
                    AttendanceRecord.exit_time > start,
                ),
            )
        ),
    )
    if exclude_id is not None:
        q = q.where(AttendanceRecord.id != exclude_id)
    return db.scalar(select(func.count()).select_from(q.subquery())) > 0


# ── Public API ────────────────────────────────────────────────────────────────

def check_in(db: Session, employee: Employee, work_location: str) -> AttendanceRecord:
    """
    Record an attendance check-in.

    Raises
    ------
    409  if the employee already has an ACTIVE session.
    """
    if _active_session(db, employee.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have an active check-in session. Please check out first.",
        )

    now = utcnow()

    record = AttendanceRecord(
        employee_id=employee.id,
        entry_time=now,
        work_location=work_location,
        status=AttendanceStatus.ACTIVE,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    logger.info(
        "Check-in: employee_id=%d location=%s entry=%s",
        employee.id,
        work_location,
        now.isoformat(),
    )
    return record


def check_out(db: Session, employee: Employee) -> AttendanceRecord:
    """
    Record an attendance check-out for the employee's current active session.

    Raises
    ------
    404  if no active session exists.
    422  if exit_time <= entry_time (should not happen unless server clock skew).
    """
    record = _active_session(db, employee.id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active check-in session found. Please check in first.",
        )

    now = utcnow()
    entry_time = ensure_utc(record.entry_time)
    if now <= entry_time:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Exit time must be after entry time.",
        )

    duration_seconds = (now - entry_time).total_seconds()
    record.exit_time = now
    record.working_minutes = int(duration_seconds // 60)
    record.status = AttendanceStatus.COMPLETED

    db.commit()
    db.refresh(record)
    logger.info(
        "Check-out: employee_id=%d record_id=%d working_minutes=%d",
        employee.id,
        record.id,
        record.working_minutes,
    )
    return record


def get_employee_attendance(
    db: Session,
    employee_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[int, list[AttendanceRecord]]:
    """
    Retrieve paginated attendance records for an employee, optionally filtered
    by date range (inclusive, based on entry_time in UTC).
    """
    import zoneinfo
    from app.core.config import get_settings

    tz = zoneinfo.ZoneInfo(get_settings().COMPANY_TIMEZONE)

    q = select(AttendanceRecord).where(AttendanceRecord.employee_id == employee_id)

    if start_date:
        start_dt = datetime(start_date.year, start_date.month, start_date.day, tzinfo=tz)
        q = q.where(AttendanceRecord.entry_time >= start_dt)
    if end_date:
        from datetime import timedelta
        end_dt = datetime(
            end_date.year, end_date.month, end_date.day, 23, 59, 59, tzinfo=tz
        )
        q = q.where(AttendanceRecord.entry_time <= end_dt)

    total = db.scalar(select(func.count()).select_from(q.subquery()))
    records = db.scalars(
        q.order_by(AttendanceRecord.entry_time.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return total or 0, list(records)


def get_attendance_summary(
    db: Session,
    employee_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> dict:
    """Compute aggregated attendance statistics for an employee."""
    _, records = get_employee_attendance(
        db, employee_id, start_date, end_date, page=1, page_size=10000
    )
    completed = [r for r in records if r.status == AttendanceStatus.COMPLETED]
    incomplete = [r for r in records if r.status == AttendanceStatus.INCOMPLETE]
    active = [r for r in records if r.status == AttendanceStatus.ACTIVE]

    total_minutes = sum(r.working_minutes or 0 for r in completed)
    office_days = len(
        {
            to_company_tz(r.entry_time).date()
            for r in completed
            if r.work_location == WorkLocation.OFFICE
        }
    )
    wfh_days = len(
        {
            to_company_tz(r.entry_time).date()
            for r in completed
            if r.work_location == WorkLocation.WORK_FROM_HOME
        }
    )

    return {
        "employee_id": employee_id,
        "total_records": len(records),
        "completed_sessions": len(completed),
        "incomplete_sessions": len(incomplete) + len(active),
        "total_working_hours": round(total_minutes / 60, 4),
        "office_days": office_days,
        "wfh_days": wfh_days,
    }
