"""
app/services/employee_service.py
---------------------------------
Business logic for employee management: create, list, get, update, status.
All database mutations use explicit transactions.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.employee import Employee, EmployeeRole
from app.schemas.employee import EmployeeCreate, EmployeeUpdate

logger = logging.getLogger(__name__)


def create_employee(db: Session, data: EmployeeCreate) -> Employee:
    """
    Create a new employee.  Raises 409 if the email is already registered.
    """
    existing = db.scalar(select(Employee).where(Employee.email == data.email))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Employee with email '{data.email}' already exists",
        )

    employee = Employee(
        full_name=data.full_name,
        email=data.email,
        department=data.department,
        hashed_password=hash_password(data.password),
        role=data.role,
        is_active=True,
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)
    logger.info("Created employee id=%d email=%s", employee.id, employee.email)
    return employee


def list_employees(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    department: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> tuple[int, list[Employee]]:
    """Return (total_count, employees) for the requested page."""
    query = select(Employee)
    if department:
        query = query.where(Employee.department == department)
    if is_active is not None:
        query = query.where(Employee.is_active == is_active)

    total = db.scalar(select(func.count()).select_from(query.subquery()))
    employees = db.scalars(
        query.order_by(Employee.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return total or 0, list(employees)


def get_employee(db: Session, employee_id: int) -> Employee:
    """Fetch employee by PK; raises 404 if not found."""
    employee = db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee {employee_id} not found",
        )
    return employee


def update_employee(db: Session, employee_id: int, data: EmployeeUpdate) -> Employee:
    """Partially update an employee's mutable fields."""
    employee = get_employee(db, employee_id)

    update_data = data.model_dump(exclude_unset=True)
    if "email" in update_data and update_data["email"] != employee.email:
        conflict = db.scalar(
            select(Employee).where(Employee.email == update_data["email"])
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Email '{update_data['email']}' is already in use",
            )

    for field, value in update_data.items():
        setattr(employee, field, value)

    db.commit()
    db.refresh(employee)
    logger.info("Updated employee id=%d fields=%s", employee_id, list(update_data))
    return employee


def update_employee_status(db: Session, employee_id: int, is_active: bool) -> Employee:
    """Activate or deactivate an employee."""
    employee = get_employee(db, employee_id)
    employee.is_active = is_active
    db.commit()
    db.refresh(employee)
    action = "activated" if is_active else "deactivated"
    logger.info("Employee id=%d %s", employee_id, action)
    return employee


def get_employee_by_email(db: Session, email: str) -> Optional[Employee]:
    """Fetch employee by email; returns None if not found."""
    return db.scalar(select(Employee).where(Employee.email == email))
