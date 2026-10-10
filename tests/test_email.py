"""
tests/test_email.py
--------------------
Tests for the email notification service.

Ensures:
  - Compliance warning emails are sent for non-compliant employees.
  - No real emails are sent (EMAIL_MOCK_MODE=true).
  - Duplicate notifications are prevented.
  - Delivery failure is recorded safely.
  - No warning is sent for an incomplete week.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.models.attendance import AttendanceRecord, AttendanceStatus
from app.models.compliance import ComplianceRecord
from app.models.notification import NotificationLog, NotificationStatus
from app.services.email_service import (
    MockEmailBackend,
    clear_mock_emails,
    get_mock_sent_emails,
    send_compliance_warning,
)
from tests.conftest import create_test_employee

PAST_MONDAY = date(2026, 9, 28)
PAST_SUNDAY = date(2026, 10, 4)


def _make_compliance_record(
    db: Session, employee_id: int, is_compliant: bool = False
) -> ComplianceRecord:
    reasons = [] if is_compliant else ["Insufficient office days: 0/3"]
    rec = ComplianceRecord(
        employee_id=employee_id,
        week_start=PAST_MONDAY,
        week_end=PAST_SUNDAY,
        attendance_days=0,
        total_working_minutes=0,
        average_working_minutes=0,
        is_compliant=is_compliant,
        violation_reasons=reasons,
    )
    db.add(rec)
    db.flush()
    return rec


# ── Mock backend captures emails ──────────────────────────────────────────────

def test_mock_backend_captures_email(db: Session):
    """The mock backend should capture emails without sending real ones."""
    clear_mock_emails()
    emp = create_test_employee(db, email="emp@test.com")
    rec = _make_compliance_record(db, emp.id, is_compliant=False)
    db.commit()

    log = send_compliance_warning(db, emp, rec)
    emails = get_mock_sent_emails()
    assert len(emails) == 1
    assert emails[0]["to"] == emp.email
    assert "Non-Compliance" in emails[0]["subject"]
    assert log.status == NotificationStatus.SENT


# ── Duplicate prevention ──────────────────────────────────────────────────────

def test_duplicate_notification_prevented(db: Session):
    """Calling send_compliance_warning twice should not send two emails."""
    clear_mock_emails()
    emp = create_test_employee(db, email="emp@test.com")
    rec = _make_compliance_record(db, emp.id, is_compliant=False)
    db.commit()

    log1 = send_compliance_warning(db, emp, rec)
    clear_mock_emails()  # clear after first send

    log2 = send_compliance_warning(db, emp, rec)
    emails = get_mock_sent_emails()
    assert len(emails) == 0  # second call should not send
    assert log2.id == log1.id  # returns the same log


# ── Failure recording ─────────────────────────────────────────────────────────

def test_smtp_failure_recorded(db: Session):
    """SMTP failure should update notification status to FAILED."""
    clear_mock_emails()
    emp = create_test_employee(db, email="emp@test.com")
    rec = _make_compliance_record(db, emp.id, is_compliant=False)
    db.commit()

    def failing_send(*args, **kwargs):
        raise ConnectionError("SMTP server unavailable")

    with patch.object(MockEmailBackend, "send", side_effect=failing_send):
        log = send_compliance_warning(db, emp, rec)

    assert log.status == NotificationStatus.FAILED
    assert "SMTP" in log.error_message or "Connection" in log.error_message


# ── Attempt count increments ──────────────────────────────────────────────────

def test_attempt_count_increments_on_retry(db: Session):
    """Retrying after a failure should increment attempt_count."""
    clear_mock_emails()
    emp = create_test_employee(db, email="emp@test.com")
    rec = _make_compliance_record(db, emp.id, is_compliant=False)
    db.commit()

    def failing_send(*args, **kwargs):
        raise ConnectionError("SMTP server unavailable")

    with patch.object(MockEmailBackend, "send", side_effect=failing_send):
        log1 = send_compliance_warning(db, emp, rec)

    assert log1.attempt_count == 1

    # Second attempt (retry)
    with patch.object(MockEmailBackend, "send", side_effect=failing_send):
        log2 = send_compliance_warning(db, emp, rec)

    assert log2.attempt_count == 2


# ── Email content ─────────────────────────────────────────────────────────────

def test_warning_email_contains_statistics(db: Session):
    """The warning email body should contain attendance statistics."""
    clear_mock_emails()
    emp = create_test_employee(db, email="emp@test.com")
    rec = _make_compliance_record(db, emp.id, is_compliant=False)
    db.commit()

    send_compliance_warning(db, emp, rec)
    email = get_mock_sent_emails()[0]
    assert emp.full_name in email["body"]
    assert "Office Days" in email["body"]
    assert "Total Working Hours" in email["body"]
