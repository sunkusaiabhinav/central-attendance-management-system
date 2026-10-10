"""
app/schemas/report.py
---------------------
Pydantic schemas for the unified attendance reporting endpoint.

The schema hierarchy:
  ReportDailyRecord       — a single day's attendance for one employee
  ReportEmployeeSummary   — one employee's data within a report period
  AttendanceReportResponse — top-level API response
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class ReportDailyRecord(BaseModel):
    """
    Single-day attendance slot.  ``status`` is one of:
      - COMPLETED      checked-in AND checked-out with valid duration
      - ACTIVE         checked-in, no checkout yet (still in session)
      - INCOMPLETE     checked-in, but no checkout by EOD; not qualifying
      - NOT_ATTENDED   no record for this date
    """
    date: date
    entry_time: Optional[datetime] = None
    exit_time: Optional[datetime] = None
    working_hours: float = 0.0
    work_location: Optional[str] = None
    status: str  # COMPLETED | ACTIVE | INCOMPLETE | NOT_ATTENDED


class WeeklyComplianceSummary(BaseModel):
    """Per-week compliance snapshot embedded in multi-day report responses."""
    week_start: date
    week_end: date
    office_days: int
    total_working_hours: float
    average_hours_per_day: float
    is_compliant: Optional[bool] = None   # None = incomplete week, not yet evaluated
    compliance_pending: bool = False       # True when week hasn't finished yet
    violation_reasons: list[str] = Field(default_factory=list)


class ReportEmployeeSummary(BaseModel):
    employee_id: int
    employee_name: str
    department: str
    attendance_days: int
    total_working_hours: float
    average_hours_per_day: float
    attendance_status: str  # ATTENDED | NOT_ATTENDED (period-level)
    weekly_compliant: Optional[bool] = None   # None when period spans incomplete weeks
    weekly_summaries: list[WeeklyComplianceSummary] = Field(default_factory=list)
    daily_records: list[ReportDailyRecord] = Field(default_factory=list)


class AttendanceReportResponse(BaseModel):
    report_type: str   # daily | weekly | monthly | yearly | custom
    start_date: date
    end_date: date
    total_employees: int
    total_pages: int = 1
    page: int = 1
    page_size: int = 100
    employees: list[ReportEmployeeSummary]
