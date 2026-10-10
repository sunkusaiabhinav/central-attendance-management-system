"""
app/models/compliance.py
------------------------
SQLAlchemy ORM model for weekly compliance evaluation results.

Design decisions
----------------
* ``week_start`` / ``week_end`` store the Monday and Sunday of the evaluated
  week (date-only, stored as DATE via DateTime with timezone=False).
* ``total_working_minutes`` and ``average_working_minutes`` use integers to
  avoid floating-point rounding during storage.
* ``violation_reasons`` stores a JSON array of human-readable reason strings.
* A unique constraint on (employee_id, week_start) prevents duplicate records
  for the same evaluation window.
* ``is_compliant`` is set once the week is fully evaluated. While a week is
  still in progress, no record is created.
"""

from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ComplianceRecord(Base):
    __tablename__ = "compliance_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    week_end: Mapped[date] = mapped_column(Date, nullable=False)

    # Qualifying office-day count for the week
    attendance_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_working_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # NULL until week is finalised
    average_working_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_compliant: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # List of violation reason strings; empty for compliant employees
    violation_reasons: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    employee: Mapped["Employee"] = relationship("Employee", back_populates="compliance_records")
    notification_logs: Mapped[list["NotificationLog"]] = relationship(
        "NotificationLog", back_populates="compliance_record", lazy="select"
    )

    __table_args__ = (
        UniqueConstraint("employee_id", "week_start", name="uq_compliance_employee_week"),
        Index("ix_compliance_week_start", "week_start"),
    )

    @property
    def total_working_hours(self) -> float:
        return round(self.total_working_minutes / 60, 4)

    @property
    def average_working_hours(self) -> float | None:
        if self.average_working_minutes is None:
            return None
        return round(self.average_working_minutes / 60, 4)

    def __repr__(self) -> str:
        return (
            f"<ComplianceRecord id={self.id} employee_id={self.employee_id} "
            f"week={self.week_start}–{self.week_end} compliant={self.is_compliant}>"
        )
