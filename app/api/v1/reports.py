"""
app/api/v1/reports.py
----------------------
Single unified reporting endpoint supporting five period types.
"""

from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import require_admin
from app.db.session import get_db
from app.schemas.report import AttendanceReportResponse
from app.services.report_service import generate_report, resolve_period

router = APIRouter(prefix="/reports", tags=["Reports"])

PERIOD_LITERAL = Literal["daily", "weekly", "monthly", "yearly", "custom"]


@router.get(
    "/attendance",
    response_model=AttendanceReportResponse,
    summary="Unified attendance report (ADMIN)",
    description="""
Returns attendance data for all active employees in one request.
Includes employees with zero attendance (NOT_ATTENDED).

## Period types

| period | Required params | Example |
|--------|----------------|---------|
| `daily` | `date` | `?period=daily&date=2026-10-09` |
| `weekly` | `date` | `?period=weekly&date=2026-10-09` |
| `monthly` | `year`, `month` | `?period=monthly&year=2026&month=10` |
| `yearly` | `year` | `?period=yearly&year=2026` |
| `custom` | `start_date`, `end_date` | `?period=custom&start_date=2026-10-01&end_date=2026-10-09` |

## Features

- All five report periods supported in one endpoint.
- Company-wide: returns **all** active employees in one request.
- Employees with no attendance are included (status = NOT_ATTENDED).
- Daily records show entry time, exit time, duration, work location, and status.
- Weekly compliance is evaluated per ISO week, not as an aggregate total.
- Incomplete weeks are marked `compliance_pending=true`.
- Optional department and employee_id filters for administrators.
- Paginated to support large employee counts.
""",
)
def get_attendance_report(
    # ── Period selector ───────────────────────────────────────────────────────
    period: PERIOD_LITERAL = Query(..., description="Report period type"),
    # ── daily / weekly ────────────────────────────────────────────────────────
    date: Optional[date] = Query(
        None, alias="date", description="Reference date for daily/weekly reports"
    ),
    # ── monthly ───────────────────────────────────────────────────────────────
    year: Optional[int] = Query(None, ge=2000, le=2100, description="Year for monthly/yearly reports"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Month number (1-12) for monthly report"),
    # ── custom ────────────────────────────────────────────────────────────────
    start_date: Optional[date] = Query(None, description="Start date for custom range"),
    end_date: Optional[date] = Query(None, description="End date for custom range"),
    # ── Filters ───────────────────────────────────────────────────────────────
    department: Optional[str] = Query(None, description="Filter by department name"),
    employee_id: Optional[int] = Query(None, description="Filter to a single employee"),
    # ── Pagination ────────────────────────────────────────────────────────────
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=200, description="Results per page"),
    # ── Auth ──────────────────────────────────────────────────────────────────
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    try:
        start, end = resolve_period(
            period=period,
            date_param=date,
            year=year,
            month=month,
            start_date=start_date,
            end_date=end_date,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return generate_report(
        db=db,
        period=period,
        start=start,
        end=end,
        department=department,
        employee_id_filter=employee_id,
        page=page,
        page_size=page_size,
    )
