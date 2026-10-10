"""
app/api/v1/employees.py
------------------------
Employee management endpoints (ADMIN only for mutations).
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_employee, require_admin
from app.db.session import get_db
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeListResponse,
    EmployeeResponse,
    EmployeeStatusUpdate,
    EmployeeUpdate,
)
from app.services import employee_service

router = APIRouter(prefix="/employees", tags=["Employees"])


@router.post(
    "",
    response_model=EmployeeResponse,
    status_code=201,
    summary="Create a new employee (ADMIN)",
)
def create_employee(
    data: EmployeeCreate,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    return employee_service.create_employee(db, data)


@router.get(
    "",
    response_model=EmployeeListResponse,
    summary="List employees with optional filters (ADMIN)",
)
def list_employees(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    department: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    total, employees = employee_service.list_employees(
        db, page=page, page_size=page_size, department=department, is_active=is_active
    )
    return EmployeeListResponse(
        total=total,
        page=page,
        page_size=page_size,
        employees=employees,
    )


@router.get(
    "/{employee_id}",
    response_model=EmployeeResponse,
    summary="Retrieve a single employee (ADMIN or self)",
)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current=Depends(get_current_employee),
):
    # Employees can view their own profile; admins can view anyone
    if current.role != "ADMIN" and current.id != employee_id:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return employee_service.get_employee(db, employee_id)


@router.patch(
    "/{employee_id}",
    response_model=EmployeeResponse,
    summary="Update employee details (ADMIN)",
)
def update_employee(
    employee_id: int,
    data: EmployeeUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    return employee_service.update_employee(db, employee_id, data)


@router.patch(
    "/{employee_id}/status",
    response_model=EmployeeResponse,
    summary="Activate or deactivate an employee (ADMIN)",
)
def update_employee_status(
    employee_id: int,
    data: EmployeeStatusUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    return employee_service.update_employee_status(db, employee_id, data.is_active)
