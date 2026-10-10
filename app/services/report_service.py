"""
app/services/report_service.py
--------------------------------
Unified report generation for daily, weekly, monthly, yearly, and custom
date ranges.  All five report types flow through one function family.

Key design principles
---------------------
* A single LEFT JOIN query starting from the employee table ensures that
  employees with zero attendance are included.
* ``daily_records`` for multi-day reports include every date in the range,
  even dates with no attendance (shown as NOT_ATTENDED).
* Weekly compliance is evaluated independently per calendar week; a monthly
  total is NEVER substituted for a weekly evaluation.
* Incomplete weeks are flagged as compliance_pending=True; is_compliant=None.
* Working minutes are summed per day (multiple sessions aggregated).
* Only COMPLETED records contribute to working hours; ACTIVE sessions are
  shown with their current partial hours but are not used in compliance.
"""

from __future__ import annotations

import logging
import zoneinfo
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.attendance import AttendanceRecord, AttendanceStatus, WorkLocation
from app.models.compliance import ComplianceRecord
from app.models.employee import Employee
from app.schemas.report import (
    AttendanceReportResponse,
    ReportDailyRecord,
    ReportEmployeeSummary,
    WeeklyComplianceSummary,
)
from app.utils.datetime_utils import (
    date_range,
    is_week_complete,
    minutes_to_hours,
    to_company_tz,
    week_bounds,
)

logger = logging.getLogger(__name__)
settings = get_settings()


# ── Period resolver ───────────────────────────────────────────────────────────

def resolve_period(
    period: str,
    date_param: Optional[date] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> tuple[date, date]:
    """
    Return (start_date, end_date) for the requested report period.
    Validates that all required query parameters for the period are provided.
    """
    if period == "daily":
        if not date_param:
            raise ValueError("'date' is required for period=daily")
        return date_param, date_param

    if period == "weekly":
        if not date_param:
            raise ValueError("'date' is required for period=weekly")
        return week_bounds(date_param)

    if period == "monthly":
        if not year or not month:
            raise ValueError("'year' and 'month' are required for period=monthly")
        if not (1 <= month <= 12):
            raise ValueError("'month' must be between 1 and 12")
        first = date(year, month, 1)
        # Last day of month
        if month == 12:
            last = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            last = date(year, month + 1, 1) - timedelta(days=1)
        return first, last

    if period == "yearly":
        if not year:
            raise ValueError("'year' is required for period=yearly")
        return date(year, 1, 1), date(year, 12, 31)

    if period == "custom":
        if not start_date or not end_date:
            raise ValueError("'start_date' and 'end_date' are required for period=custom")
        if start_date > end_date:
            raise ValueError("'start_date' must be on or before 'end_date'")
        return start_date, end_date

    raise ValueError(f"Invalid period '{period}'. Must be one of: daily, weekly, monthly, yearly, custom")


# ── Attendance data loader ────────────────────────────────────────────────────

def _load_attendance(
    db: Session,
    employee_ids: list[int],
    start: date,
    end: date,
) -> dict[int, list[AttendanceRecord]]:
    """
    Load all attendance records for the given employees in the date range.
    Returns a dict mapping employee_id → list[AttendanceRecord].
    Uses a single query to avoid per-employee round-trips.
    """
    tz = zoneinfo.ZoneInfo(settings.COMPANY_TIMEZONE)
    start_dt = datetime(start.year, start.month, start.day, tzinfo=tz)
    end_dt = datetime(end.year, end.month, end.day, 23, 59, 59, tzinfo=tz)

    records = db.scalars(
        select(AttendanceRecord).where(
            AttendanceRecord.employee_id.in_(employee_ids),
            AttendanceRecord.entry_time >= start_dt,
            AttendanceRecord.entry_time <= end_dt,
        ).order_by(AttendanceRecord.entry_time)
    ).all()

    result: dict[int, list[AttendanceRecord]] = defaultdict(list)
    for r in records:
        result[r.employee_id].append(r)
    return dict(result)


def _load_compliance(
    db: Session,
    employee_ids: list[int],
    start: date,
    end: date,
) -> dict[tuple[int, date], ComplianceRecord]:
    """
    Load stored compliance records for the weeks overlapping [start, end].
    Returns a dict mapping (employee_id, week_start) → ComplianceRecord.
    """
    records = db.scalars(
        select(ComplianceRecord).where(
            ComplianceRecord.employee_id.in_(employee_ids),
            ComplianceRecord.week_start >= start - timedelta(days=6),
            ComplianceRecord.week_end <= end + timedelta(days=6),
        )
    ).all()

    return {(r.employee_id, r.week_start): r for r in records}


# ── Per-employee aggregation ──────────────────────────────────────────────────

def _daily_records_for_employee(
    records: list[AttendanceRecord],
    all_dates: list[date],
) -> list[ReportDailyRecord]:
    """
    Group attendance records by calendar date (company TZ) and build
    ReportDailyRecord entries for every date in all_dates.
    Dates with no attendance are reported as NOT_ATTENDED.
    """
    tz = zoneinfo.ZoneInfo(settings.COMPANY_TIMEZONE)
    by_date: dict[date, list[AttendanceRecord]] = defaultdict(list)
    for r in records:
        day = to_company_tz(r.entry_time).date()
        by_date[day].append(r)

    result = []
    for d in all_dates:
        day_records = by_date.get(d, [])
        if not day_records:
            result.append(
                ReportDailyRecord(
                    date=d,
                    entry_time=None,
                    exit_time=None,
                    working_hours=0.0,
                    work_location=None,
                    status="NOT_ATTENDED",
                )
            )
            continue

        # Aggregate multiple sessions for the same day
        completed = [r for r in day_records if r.status == AttendanceStatus.COMPLETED]
        active = [r for r in day_records if r.status == AttendanceStatus.ACTIVE]
        incomplete = [r for r in day_records if r.status == AttendanceStatus.INCOMPLETE]

        # Earliest entry and latest exit
        earliest_entry = min(r.entry_time for r in day_records)
        latest_exit = max(
            (r.exit_time for r in day_records if r.exit_time), default=None
        )
        total_minutes = sum(r.working_minutes or 0 for r in completed)
        # Primary location (office takes priority; first record otherwise)
        locations = [r.work_location for r in day_records]
        location = WorkLocation.OFFICE if WorkLocation.OFFICE in locations else locations[0]

        if active:
            day_status = "ACTIVE"
        elif completed:
            day_status = "COMPLETED"
        else:
            day_status = "INCOMPLETE"

        result.append(
            ReportDailyRecord(
                date=d,
                entry_time=earliest_entry,
                exit_time=latest_exit,
                working_hours=minutes_to_hours(total_minutes),
                work_location=location,
                status=day_status,
            )
        )
    return result


def _weekly_summaries(
    employee_id: int,
    records: list[AttendanceRecord],
    start: date,
    end: date,
    compliance_map: dict[tuple[int, date], ComplianceRecord],
) -> list[WeeklyComplianceSummary]:
    """
    Build per-ISO-week compliance summaries for the date range.
    Uses stored ComplianceRecord when available; falls back to live calculation
    for incomplete or unevaluated weeks.
    """
    tz = zoneinfo.ZoneInfo(settings.COMPANY_TIMEZONE)
    summaries = []

    # Enumerate all ISO weeks that overlap [start, end]
    week_starts: list[date] = []
    cur = start - timedelta(days=start.weekday())  # Monday of the first week
    while cur <= end:
        week_starts.append(cur)
        cur += timedelta(days=7)

    for ws in week_starts:
        we = ws + timedelta(days=6)
        effective_start = max(ws, start)
        effective_end = min(we, end)

        stored = compliance_map.get((employee_id, ws))
        week_complete = is_week_complete(we)

        if stored:
            summaries.append(
                WeeklyComplianceSummary(
                    week_start=ws,
                    week_end=we,
                    office_days=stored.attendance_days,
                    total_working_hours=minutes_to_hours(stored.total_working_minutes),
                    average_hours_per_day=minutes_to_hours(
                        stored.average_working_minutes or 0
                    ),
                    is_compliant=stored.is_compliant,
                    compliance_pending=False,
                    violation_reasons=stored.violation_reasons or [],
                )
            )
        else:
            # Live computation for unevaluated or incomplete weeks
            week_records = [
                r
                for r in records
                if r.status == AttendanceStatus.COMPLETED
                and effective_start <= to_company_tz(r.entry_time).date() <= effective_end
            ]
            office_dates = {
                to_company_tz(r.entry_time).date()
                for r in week_records
                if r.work_location == WorkLocation.OFFICE
            }
            all_days = {to_company_tz(r.entry_time).date() for r in week_records}
            total_min = sum(r.working_minutes or 0 for r in week_records)
            avg_min = (total_min // len(all_days)) if all_days else 0
            total_hours = minutes_to_hours(total_min)
            avg_hours = minutes_to_hours(avg_min)

            if not week_complete:
                summaries.append(
                    WeeklyComplianceSummary(
                        week_start=ws,
                        week_end=we,
                        office_days=len(office_dates),
                        total_working_hours=total_hours,
                        average_hours_per_day=avg_hours,
                        is_compliant=None,
                        compliance_pending=True,
                        violation_reasons=[],
                    )
                )
            else:
                # Week is complete but not yet evaluated — compute on the fly
                violations = []
                if len(office_dates) < settings.MIN_OFFICE_DAYS_PER_WEEK:
                    violations.append(
                        f"Insufficient office days: {len(office_dates)}/{settings.MIN_OFFICE_DAYS_PER_WEEK}"
                    )
                if total_hours < settings.MIN_WEEKLY_WORKING_HOURS:
                    violations.append(
                        f"Insufficient total hours: {total_hours:.2f}/{settings.MIN_WEEKLY_WORKING_HOURS:.1f}"
                    )
                if avg_hours < settings.MIN_AVERAGE_HOURS_PER_DAY:
                    violations.append(
                        f"Average hours below threshold: {avg_hours:.2f}/{settings.MIN_AVERAGE_HOURS_PER_DAY:.1f}"
                    )
                summaries.append(
                    WeeklyComplianceSummary(
                        week_start=ws,
                        week_end=we,
                        office_days=len(office_dates),
                        total_working_hours=total_hours,
                        average_hours_per_day=avg_hours,
                        is_compliant=len(violations) == 0,
                        compliance_pending=False,
                        violation_reasons=violations,
                    )
                )

    return summaries


# ── Main report generator ─────────────────────────────────────────────────────

def generate_report(
    db: Session,
    period: str,
    start: date,
    end: date,
    department: Optional[str] = None,
    employee_id_filter: Optional[int] = None,
    page: int = 1,
    page_size: int = 100,
) -> AttendanceReportResponse:
    """
    Generate a unified attendance report.

    All active employees are returned, including those with no attendance.
    Uses a single query per entity type (no per-employee N+1 queries).
    """
    # 1. Load employees (filtered)
    emp_query = select(Employee).where(Employee.is_active == True)
    if department:
        emp_query = emp_query.where(Employee.department == department)
    if employee_id_filter:
        emp_query = emp_query.where(Employee.id == employee_id_filter)

    total_employees = db.scalar(
        select(func.count()).select_from(emp_query.subquery())
    ) or 0
    total_pages = max(1, (total_employees + page_size - 1) // page_size)

    employees = db.scalars(
        emp_query.order_by(Employee.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    if not employees:
        return AttendanceReportResponse(
            report_type=period,
            start_date=start,
            end_date=end,
            total_employees=total_employees,
            total_pages=total_pages,
            page=page,
            page_size=page_size,
            employees=[],
        )

    employee_ids = [e.id for e in employees]
    all_dates = date_range(start, end)

    # 2. Bulk-load attendance and compliance (2 queries)
    attendance_map = _load_attendance(db, employee_ids, start, end)
    compliance_map = _load_compliance(db, employee_ids, start, end)

    # 3. Build per-employee summaries
    tz = zoneinfo.ZoneInfo(settings.COMPANY_TIMEZONE)
    employee_summaries = []

    for emp in employees:
        emp_records = attendance_map.get(emp.id, [])
        daily = _daily_records_for_employee(emp_records, all_dates)
        weekly = _weekly_summaries(emp.id, emp_records, start, end, compliance_map)

        # Period-level aggregates (COMPLETED only)
        completed = [r for r in emp_records if r.status == AttendanceStatus.COMPLETED]
        total_min = sum(r.working_minutes or 0 for r in completed)
        office_dates = {
            to_company_tz(r.entry_time).date()
            for r in completed
            if r.work_location == WorkLocation.OFFICE
        }
        all_attended_dates = {
            to_company_tz(r.entry_time).date() for r in completed
        }

        att_days = len(all_attended_dates)
        total_hours = minutes_to_hours(total_min)
        avg_hours = (total_hours / att_days) if att_days else 0.0
        att_status = "ATTENDED" if att_days > 0 else "NOT_ATTENDED"

        # Overall compliance: only from complete weeks
        all_compliant = [w.is_compliant for w in weekly if w.is_compliant is not None]
        if not all_compliant:
            overall_compliant = None
        else:
            overall_compliant = all(all_compliant)

        employee_summaries.append(
            ReportEmployeeSummary(
                employee_id=emp.id,
                employee_name=emp.full_name,
                department=emp.department,
                attendance_days=att_days,
                total_working_hours=round(total_hours, 4),
                average_hours_per_day=round(avg_hours, 4),
                attendance_status=att_status,
                weekly_compliant=overall_compliant,
                weekly_summaries=weekly,
                daily_records=daily,
            )
        )

    return AttendanceReportResponse(
        report_type=period,
        start_date=start,
        end_date=end,
        total_employees=total_employees,
        total_pages=total_pages,
        page=page,
        page_size=page_size,
        employees=employee_summaries,
    )
