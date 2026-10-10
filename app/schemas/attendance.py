"""
app/schemas/attendance.py
-------------------------
Pydantic schemas for attendance check-in, check-out, and retrieval.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class CheckInRequest(BaseModel):
    work_location: str = Field(..., description="OFFICE or WORK_FROM_HOME")

    @field_validator("work_location")
    @classmethod
    def validate_location(cls, v: str) -> str:
        if v not in ("OFFICE", "WORK_FROM_HOME"):
            raise ValueError("work_location must be 'OFFICE' or 'WORK_FROM_HOME'")
        return v


class CheckOutRequest(BaseModel):
    """
    Check-out timestamp is optional — when omitted, the server uses now().
    The attendance ID is resolved from the active session of the current user,
    so it is NOT supplied by the client (prevents spoofing).
    """
    pass


class AttendanceRecordResponse(BaseModel):
    id: int
    employee_id: int
    entry_time: datetime
    exit_time: Optional[datetime] = None
    work_location: str
    working_hours: float
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AttendanceSummaryResponse(BaseModel):
    employee_id: int
    total_records: int
    completed_sessions: int
    incomplete_sessions: int
    total_working_hours: float
    office_days: int
    wfh_days: int


class AttendanceListResponse(BaseModel):
    total: int
    records: list[AttendanceRecordResponse]
