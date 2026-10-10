"""
app/schemas/compliance.py
-------------------------
Pydantic schemas for compliance records and violations.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class ComplianceRecordResponse(BaseModel):
    id: int
    employee_id: int
    week_start: date
    week_end: date
    attendance_days: int
    total_working_hours: float
    average_working_hours: Optional[float] = None
    is_compliant: bool
    violation_reasons: list[str]
    evaluated_at: datetime

    model_config = {"from_attributes": True}


class ComplianceViolationResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    employee_email: str
    week_start: date
    week_end: date
    attendance_days: int
    total_working_hours: float
    is_compliant: bool
    violation_reasons: list[str]
    evaluated_at: datetime

    model_config = {"from_attributes": True}


class ComplianceEvaluateRequest(BaseModel):
    """Manually trigger compliance evaluation for a specific week."""
    week_start: date  # Must be a Monday


class ComplianceEvaluateResponse(BaseModel):
    evaluated_employees: int
    compliant: int
    non_compliant: int
    notifications_queued: int


class ComplianceViolationListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    violations: list[ComplianceViolationResponse]
