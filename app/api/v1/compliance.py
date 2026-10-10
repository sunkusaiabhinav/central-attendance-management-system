"""
app/api/v1/compliance.py
-------------------------
Compliance information and policy evaluation endpoints.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import get_current_employee, require_admin
from app.db.session import get_db
from app.jobs.weekly_compliance import trigger_weekly_evaluation
from app.schemas.compliance import (
    ComplianceEvaluateRequest,
    ComplianceEvaluateResponse,
    ComplianceRecordResponse,
    ComplianceViolationListResponse,
    ComplianceViolationResponse,
)
from app.services import compliance_service
from app.services.employee_service import get_employee

router = APIRouter(prefix="/compliance", tags=["Compliance"])


@router.get(
    "/me",
    response_model=list[ComplianceRecordResponse],
    summary="View your own compliance history",
)
def get_my_compliance(
    week_start: Optional[date] = Query(None, description="Filter to a specific week (Monday)"),
    db: Session = Depends(get_db),
    current=Depends(get_current_employee),
):
    records = compliance_service.get_compliance_for_employee(db, current.id, week_start)
    return [_to_response(r) for r in records]


@router.get(
    "/violations",
    response_model=ComplianceViolationListResponse,
    summary="List all policy violations (ADMIN)",
)
def list_violations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    week_start: Optional[date] = Query(None, description="Filter to a specific week"),
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    total, records = compliance_service.get_violations(db, page, page_size, week_start)
    violations = []
    for r in records:
        emp = get_employee(db, r.employee_id)
        violations.append(
            ComplianceViolationResponse(
                id=r.id,
                employee_id=r.employee_id,
                employee_name=emp.full_name,
                employee_email=emp.email,
                week_start=r.week_start,
                week_end=r.week_end,
                attendance_days=r.attendance_days,
                total_working_hours=r.total_working_hours,
                is_compliant=r.is_compliant,
                violation_reasons=r.violation_reasons or [],
                evaluated_at=r.evaluated_at,
            )
        )
    return ComplianceViolationListResponse(
        total=total, page=page, page_size=page_size, violations=violations
    )


@router.get(
    "/{employee_id}",
    response_model=list[ComplianceRecordResponse],
    summary="View an employee's compliance history (ADMIN or self)",
)
def get_employee_compliance(
    employee_id: int,
    week_start: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current=Depends(get_current_employee),
):
    if current.role != "ADMIN" and current.id != employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own compliance records",
        )
    records = compliance_service.get_compliance_for_employee(db, employee_id, week_start)
    return [_to_response(r) for r in records]


@router.post(
    "/evaluate",
    response_model=ComplianceEvaluateResponse,
    summary="Manually trigger compliance evaluation for a week (ADMIN)",
    description=(
        "Evaluate all active employees for the specified week. "
        "The week_start must be a Monday. "
        "Sends violation warning emails for non-compliant employees."
    ),
)
def evaluate_compliance(
    data: ComplianceEvaluateRequest,
    force: bool = Query(False, description="Re-evaluate even if records already exist"),
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    if data.week_start.weekday() != 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"week_start must be a Monday; got {data.week_start} ({data.week_start.strftime('%A')})",
        )
    result = trigger_weekly_evaluation(data.week_start, force=force)
    return ComplianceEvaluateResponse(
        evaluated_employees=result.get("evaluated", 0),
        compliant=result.get("compliant", 0),
        non_compliant=result.get("non_compliant", 0),
        notifications_queued=result.get("notifications_queued", 0),
    )


@router.post(
    "/send-warning-emails",
    summary="Send warning emails to non-compliant employees for a week (ADMIN)",
    description=(
        "Finds all non-compliant employees for the given week (not meeting 3 office days, "
        "15 total hours, or 5h/day average) and sends/queues warning emails."
    ),
)
def send_warning_emails(
    week_start: date = Query(..., description="Target week (Monday)"),
    force: bool = Query(True, description="Force re-sending emails even if already sent for this week"),
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    from sqlalchemy import select
    from app.models.compliance import ComplianceRecord
    from app.models.employee import Employee
    from app.models.notification import NotificationStatus
    from app.services import email_service

    if week_start.weekday() != 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"week_start must be a Monday; got {week_start} ({week_start.strftime('%A')})",
        )

    non_compliant = db.scalars(
        select(ComplianceRecord).where(
            ComplianceRecord.week_start == week_start,
            ComplianceRecord.is_compliant == False,
        )
    ).all()

    sent = 0
    failed = 0
    for record in non_compliant:
        employee = db.get(Employee, record.employee_id)
        if not employee or not employee.is_active:
            continue
        try:
            log = email_service.send_compliance_warning(db, employee, record, force=force)
            if log.status == NotificationStatus.SENT:
                sent += 1
            else:
                failed += 1
        except Exception:
            failed += 1

    return {
        "week_start": week_start,
        "total_non_compliant": len(non_compliant),
        "emails_sent": sent,
        "emails_failed": failed,
    }


# ── Helper ────────────────────────────────────────────────────────────────────

def _to_response(record) -> ComplianceRecordResponse:
    return ComplianceRecordResponse(
        id=record.id,
        employee_id=record.employee_id,
        week_start=record.week_start,
        week_end=record.week_end,
        attendance_days=record.attendance_days,
        total_working_hours=record.total_working_hours,
        average_working_hours=record.average_working_hours,
        is_compliant=record.is_compliant,
        violation_reasons=record.violation_reasons or [],
        evaluated_at=record.evaluated_at,
    )
