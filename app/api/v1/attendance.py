"""
app/api/v1/attendance.py
-------------------------
Attendance check-in, check-out, and retrieval endpoints.

The employee identity for check-in/check-out comes from the JWT token,
never from a client-supplied employee ID in the request body.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import get_current_employee, require_admin
from app.db.session import get_db
from app.schemas.attendance import (
    AttendanceListResponse,
    AttendanceRecordResponse,
    AttendanceSummaryResponse,
    CheckInRequest,
)
from app.services import attendance_service

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.post(
    "/check-in",
    response_model=AttendanceRecordResponse,
    status_code=201,
    summary="Check in (authenticated employee)",
)
def check_in(
    data: CheckInRequest,
    db: Session = Depends(get_db),
    current=Depends(get_current_employee),
):
    """Record the start of an attendance session for the authenticated employee."""
    record = attendance_service.check_in(db, current, data.work_location)
    return _to_response(record)


@router.post(
    "/check-out",
    response_model=AttendanceRecordResponse,
    summary="Check out (authenticated employee)",
)
def check_out(
    db: Session = Depends(get_db),
    current=Depends(get_current_employee),
):
    """Close the active attendance session for the authenticated employee."""
    record = attendance_service.check_out(db, current)
    return _to_response(record)


@router.get(
    "/me",
    response_model=AttendanceListResponse,
    summary="View your own attendance records",
)
def get_my_attendance(
    start_date: Optional[date] = Query(None, description="Filter from this date (inclusive)"),
    end_date: Optional[date] = Query(None, description="Filter to this date (inclusive)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current=Depends(get_current_employee),
):
    total, records = attendance_service.get_employee_attendance(
        db, current.id, start_date, end_date, page, page_size
    )
    return AttendanceListResponse(total=total, records=[_to_response(r) for r in records])


@router.get(
    "/{employee_id}",
    response_model=AttendanceListResponse,
    summary="View an employee's attendance (ADMIN or self)",
)
def get_employee_attendance(
    employee_id: int,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current=Depends(get_current_employee),
):
    if current.role != "ADMIN" and current.id != employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own attendance records",
        )
    total, records = attendance_service.get_employee_attendance(
        db, employee_id, start_date, end_date, page, page_size
    )
    return AttendanceListResponse(total=total, records=[_to_response(r) for r in records])


@router.get(
    "/{employee_id}/summary",
    response_model=AttendanceSummaryResponse,
    summary="Retrieve attendance totals and working hours (ADMIN or self)",
)
def get_attendance_summary(
    employee_id: int,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current=Depends(get_current_employee),
):
    if current.role != "ADMIN" and current.id != employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own attendance summary",
        )
    summary = attendance_service.get_attendance_summary(
        db, employee_id, start_date, end_date
    )
    return AttendanceSummaryResponse(**summary)


# ── Helper ────────────────────────────────────────────────────────────────────

def _to_response(record) -> AttendanceRecordResponse:
    return AttendanceRecordResponse(
        id=record.id,
        employee_id=record.employee_id,
        entry_time=record.entry_time,
        exit_time=record.exit_time,
        work_location=record.work_location,
        working_hours=record.working_hours,
        status=record.status,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )
