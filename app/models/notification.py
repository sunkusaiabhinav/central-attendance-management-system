"""
app/models/notification.py
--------------------------
SQLAlchemy ORM model for email notification logs.

Design decisions
----------------
* ``status`` tracks the delivery lifecycle: PENDING → SENT | FAILED.
* ``attempt_count`` enables safe retry logic with exponential back-off.
* ``error_message`` is truncated to 1000 chars to avoid unbounded growth.
* A unique constraint on (employee_id, compliance_record_id, notification_type)
  prevents duplicate successful warnings for the same violation event.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class NotificationStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class NotificationType(str, enum.Enum):
    COMPLIANCE_WARNING = "COMPLIANCE_WARNING"


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    compliance_record_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("compliance_records.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    recipient_email: Mapped[str] = mapped_column(String(320), nullable=False)
    notification_type: Mapped[str] = mapped_column(
        Enum(NotificationType, name="notification_type"),
        nullable=False,
        default=NotificationType.COMPLIANCE_WARNING,
    )
    status: Mapped[str] = mapped_column(
        Enum(NotificationStatus, name="notification_status"),
        nullable=False,
        default=NotificationStatus.PENDING,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Sanitised – credentials and stack traces must never appear here
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    employee: Mapped["Employee"] = relationship("Employee", back_populates="notification_logs")
    compliance_record: Mapped["ComplianceRecord"] = relationship(
        "ComplianceRecord", back_populates="notification_logs"
    )

    __table_args__ = (
        UniqueConstraint(
            "employee_id",
            "compliance_record_id",
            "notification_type",
            name="uq_notification_employee_compliance_type",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<NotificationLog id={self.id} employee_id={self.employee_id} "
            f"status={self.status}>"
        )
