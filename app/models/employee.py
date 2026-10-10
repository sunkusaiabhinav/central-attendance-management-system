"""
app/models/employee.py
----------------------
SQLAlchemy ORM model for employees.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class EmployeeRole(str, enum.Enum):
    ADMIN = "ADMIN"
    EMPLOYEE = "EMPLOYEE"


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(
        String(320), unique=True, nullable=False, index=True
    )
    department: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        Enum(EmployeeRole, name="employee_role"), nullable=False, default=EmployeeRole.EMPLOYEE
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    attendance_records: Mapped[list["AttendanceRecord"]] = relationship(
        "AttendanceRecord", back_populates="employee", lazy="select"
    )
    compliance_records: Mapped[list["ComplianceRecord"]] = relationship(
        "ComplianceRecord", back_populates="employee", lazy="select"
    )
    notification_logs: Mapped[list["NotificationLog"]] = relationship(
        "NotificationLog", back_populates="employee", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Employee id={self.id} email={self.email!r} role={self.role}>"
