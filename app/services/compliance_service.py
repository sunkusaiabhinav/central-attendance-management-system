"""
app/services/compliance_service.py
------------------------------------
Reusable compliance evaluation engine.

Both the scheduled job (app/jobs/weekly_compliance.py) and the manual
trigger API endpoint call ``evaluate_week_compliance``.  The rules are
never duplicated in route handlers.

Policy
------
An employee's week is COMPLIANT if ALL three conditions are met:
  1. office_days  >= MIN_OFFICE_DAYS_PER_WEEK  (default 3)
  2. total_hours  >= MIN_WEEKLY_WORKING_HOURS   (default 15)
  3. avg_hours    >= MIN_AVERAGE_HOURS_PER_DAY  (default 5)

Only COMPLETED attendance records with work_location == OFFICE contribute
to office_days. Both OFFICE and WFH COMPLETED records contribute to
working-hour calculations.

WFH sessions count toward hours but NOT toward office-day headcount.

Edge cases
----------
* Incomplete week   → do NOT evaluate; no compliance record is created.
* No attendance     → all three conditions fail; employee is NON_COMPLIANT.
* ACTIVE session    → the session is in progress; it is excluded from
                      qualifying hours (no checkout recorded yet).
* INCOMPLETE session → excluded from qualifying hours.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.attendance import AttendanceRecord, AttendanceStatus, WorkLocation
from app.models.compliance import ComplianceRecord
from app.models.employee import Employee
from app.utils.datetime_utils import is_week_complete, minutes_to_hours, to_company_tz, week_bounds

logger = logging.getLogger(__name__)
settings = get_settings()


# ── Core evaluation ───────────────────────────────────────────────────────────

def _evaluate_employee_week(
    db: Session,
    employee_id: int,
    week_start: date,
    week_end: date,
) -> dict:
    """
    Compute compliance metrics for a single employee for one week.

    Returns a dict with keys:
      office_days, total_minutes, avg_minutes, is_compliant, violation_reasons
    """
    import zoneinfo

    tz = zoneinfo.ZoneInfo(settings.COMPANY_TIMEZONE)
    week_start_dt = datetime(week_start.year, week_start.month, week_start.day, tzinfo=tz)
    week_end_dt = datetime(week_end.year, week_end.month, week_end.day, 23, 59, 59, tzinfo=tz)

    records = db.scalars(
        select(AttendanceRecord).where(
            AttendanceRecord.employee_id == employee_id,
            AttendanceRecord.status == AttendanceStatus.COMPLETED,
            AttendanceRecord.entry_time >= week_start_dt,
            AttendanceRecord.entry_time <= week_end_dt,
        )
    ).all()

    # Unique OFFICE dates
    office_dates = {
        to_company_tz(r.entry_time).date()
        for r in records
        if r.work_location == WorkLocation.OFFICE
    }
    office_days = len(office_dates)

    # Total minutes from ALL completed sessions (OFFICE + WFH)
    total_minutes = sum(r.working_minutes or 0 for r in records)

    # Average hours per qualifying attendance day
    # Qualifying = days with at least one COMPLETED session (OFFICE or WFH)
    all_attendance_dates = {to_company_tz(r.entry_time).date() for r in records}
    qualifying_days = len(all_attendance_dates)

    if qualifying_days > 0:
        avg_minutes = total_minutes // qualifying_days
    else:
        avg_minutes = 0

    # ── Policy checks ─────────────────────────────────────────────────────────
    violation_reasons: list[str] = []
    min_office = settings.MIN_OFFICE_DAYS_PER_WEEK
    min_hours = settings.MIN_WEEKLY_WORKING_HOURS
    min_avg = settings.MIN_AVERAGE_HOURS_PER_DAY

    if office_days < min_office:
        violation_reasons.append(
            f"Insufficient office days: attended {office_days} day(s), "
            f"required {min_office}"
        )
    total_hours = minutes_to_hours(total_minutes)
    if total_hours < min_hours:
        violation_reasons.append(
            f"Insufficient total working hours: {total_hours:.2f} h, "
            f"required {min_hours:.1f} h"
        )
    avg_hours = minutes_to_hours(avg_minutes)
    if avg_hours < min_avg:
        violation_reasons.append(
            f"Average hours per attendance day too low: {avg_hours:.2f} h, "
            f"required {min_avg:.1f} h"
        )

    return {
        "office_days": office_days,
        "total_minutes": total_minutes,
        "avg_minutes": avg_minutes,
        "is_compliant": len(violation_reasons) == 0,
        "violation_reasons": violation_reasons,
    }


def evaluate_week_compliance(
    db: Session,
    week_start: date,
    force: bool = False,
) -> dict:
    """
    Evaluate all active employees for the week [week_start, week_start+6].

    Parameters
    ----------
    week_start:
        Must be a Monday.  Raises ValueError otherwise.
    force:
        When True, re-evaluates even if a record already exists (upserts).
        The scheduler should always pass force=False to avoid overwriting
        once-finalised results.

    Returns
    -------
    dict with keys: evaluated, compliant, non_compliant, skipped (already existed)
    """
    if week_start.weekday() != 0:
        raise ValueError(f"week_start must be a Monday, got {week_start} ({week_start.strftime('%A')})")

    week_end = week_start + __import__("datetime").timedelta(days=6)

    if not force and not is_week_complete(week_end):
        logger.info(
            "Skipping compliance evaluation: week %s–%s is not yet complete",
            week_start,
            week_end,
        )
        return {"evaluated": 0, "compliant": 0, "non_compliant": 0, "skipped_incomplete_week": True}

    employees = db.scalars(
        select(Employee).where(Employee.is_active == True)
    ).all()

    evaluated = compliant = non_compliant = skipped = 0

    for emp in employees:
        # Check for existing record
        existing = db.scalar(
            select(ComplianceRecord).where(
                ComplianceRecord.employee_id == emp.id,
                ComplianceRecord.week_start == week_start,
            )
        )
        if existing and not force:
            skipped += 1
            continue

        metrics = _evaluate_employee_week(db, emp.id, week_start, week_end)

        if existing and force:
            # Update existing record
            existing.attendance_days = metrics["office_days"]
            existing.total_working_minutes = metrics["total_minutes"]
            existing.average_working_minutes = metrics["avg_minutes"]
            existing.is_compliant = metrics["is_compliant"]
            existing.violation_reasons = metrics["violation_reasons"]
            existing.evaluated_at = datetime.now(timezone.utc)
            record = existing
        else:
            record = ComplianceRecord(
                employee_id=emp.id,
                week_start=week_start,
                week_end=week_end,
                attendance_days=metrics["office_days"],
                total_working_minutes=metrics["total_minutes"],
                average_working_minutes=metrics["avg_minutes"],
                is_compliant=metrics["is_compliant"],
                violation_reasons=metrics["violation_reasons"],
            )
            db.add(record)

        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            logger.warning(
                "Duplicate compliance record for employee_id=%d week=%s — skipping",
                emp.id,
                week_start,
            )
            skipped += 1
            continue

        evaluated += 1
        if metrics["is_compliant"]:
            compliant += 1
        else:
            non_compliant += 1

    db.commit()
    logger.info(
        "Compliance evaluation week=%s: evaluated=%d compliant=%d non_compliant=%d skipped=%d",
        week_start,
        evaluated,
        compliant,
        non_compliant,
        skipped,
    )
    return {
        "evaluated": evaluated,
        "compliant": compliant,
        "non_compliant": non_compliant,
        "skipped": skipped,
    }


def get_compliance_for_employee(
    db: Session,
    employee_id: int,
    week_start: Optional[date] = None,
) -> list[ComplianceRecord]:
    """Retrieve all or a specific week's compliance records for an employee."""
    q = select(ComplianceRecord).where(
        ComplianceRecord.employee_id == employee_id
    )
    if week_start:
        q = q.where(ComplianceRecord.week_start == week_start)
    return list(db.scalars(q.order_by(ComplianceRecord.week_start.desc())).all())


def get_violations(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    week_start: Optional[date] = None,
) -> tuple[int, list[ComplianceRecord]]:
    """Return paginated non-compliant records, optionally filtered by week."""
    q = (
        select(ComplianceRecord)
        .where(ComplianceRecord.is_compliant == False)
    )
    if week_start:
        q = q.where(ComplianceRecord.week_start == week_start)

    total = db.scalar(select(func.count()).select_from(q.subquery()))
    records = db.scalars(
        q.order_by(ComplianceRecord.week_start.desc(), ComplianceRecord.employee_id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return total or 0, list(records)
