"""
app/models/attendance.py
------------------------
SQLAlchemy ORM model for attendance records.

Design decisions
----------------
* ``working_minutes`` stores duration as an integer to avoid floating-point
  rounding errors.  Decimal hours are computed on the fly in services/schemas.
* ``status`` tracks the lifecycle: ACTIVE (checked-in), COMPLETED (checked-out),
  INCOMPLETE (no checkout recorded by EOD / scheduled job).
* Multiple sessions per day are allowed. Aggregation happens in the report
  service.
* ``work_location`` distinguishes OFFICE from WORK_FROM_HOME. Only OFFICE
  sessions count toward the physical-office-days requirement.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class WorkLocation(str, enum.Enum):
    OFFICE = "OFFICE"
    WORK_FROM_HOME = "WORK_FROM_HOME"


class AttendanceStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"          # checked-in, no exit recorded yet
    COMPLETED = "COMPLETED"    # normal completed session
    INCOMPLETE = "INCOMPLETE"  # no checkout by EOD; not counted as qualifying
    NOT_ATTENDED = "NOT_ATTENDED"  # placeholder used only in report output


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entry_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    exit_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    work_location: Mapped[str] = mapped_column(
        Enum(WorkLocation, name="work_location"), nullable=False
    )
    # Duration in minutes; NULL until checkout
    working_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum(AttendanceStatus, name="attendance_status"),
        nullable=False,
        default=AttendanceStatus.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    employee: Mapped["Employee"] = relationship("Employee", back_populates="attendance_records")

    __table_args__ = (
        # Speed up date-range queries per employee
        Index("ix_attendance_employee_entry", "employee_id", "entry_time"),
    )

    @property
    def working_hours(self) -> float:
        """Convenience: convert stored minutes to decimal hours."""
        if self.working_minutes is None:
            return 0.0
        return round(self.working_minutes / 60, 4)

    def __repr__(self) -> str:
        return (
            f"<AttendanceRecord id={self.id} employee_id={self.employee_id} "
            f"entry={self.entry_time} status={self.status}>"
        )
