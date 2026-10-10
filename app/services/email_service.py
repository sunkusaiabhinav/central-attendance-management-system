"""
app/services/email_service.py
------------------------------
Email notification service for compliance violation warnings.

Two backends are supported:
  1. SMTPEmailBackend  — sends real emails via configured SMTP server.
  2. MockEmailBackend  — captures emails in memory; used for testing.

The active backend is selected by the EMAIL_MOCK_MODE setting.

All sending logic is isolated here.  Route handlers and the scheduler call
``send_compliance_warning`` which records the attempt result in
NotificationLog regardless of success or failure.

Retry safety
------------
The service checks for an existing SENT notification before sending to
prevent duplicate warnings for the same (employee, compliance_record) pair.
Temporary SMTP failures are caught; the NotificationLog is updated with
FAILED status and error details.  The scheduler or a retry job can re-invoke
this function and the check will prevent re-sending if the first attempt
succeeded.
"""

from __future__ import annotations

import logging
import smtplib
import ssl
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.compliance import ComplianceRecord
from app.models.employee import Employee
from app.models.notification import NotificationLog, NotificationStatus, NotificationType
from app.utils.datetime_utils import minutes_to_hours

logger = logging.getLogger(__name__)
settings = get_settings()

# Shared in-memory store for the mock backend (accessible from tests)
_mock_sent_emails: list[dict] = []


def get_mock_sent_emails() -> list[dict]:
    """Return emails captured by MockEmailBackend (for test assertions)."""
    return _mock_sent_emails


def clear_mock_emails() -> None:
    """Clear the mock email store between tests."""
    _mock_sent_emails.clear()


# ── Email backends ────────────────────────────────────────────────────────────

class EmailBackend(Protocol):
    def send(self, to: str, subject: str, text_body: str, html_body: str) -> None: ...


class SMTPEmailBackend:
    def send(self, to: str, subject: str, text_body: str, html_body: str) -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        from_addr = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME
        msg["From"] = from_addr
        msg["To"] = to
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        context = ssl.create_default_context()
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(from_addr, [to], msg.as_string())


class MockEmailBackend:
    def send(self, to: str, subject: str, text_body: str, html_body: str) -> None:
        _mock_sent_emails.append({"to": to, "subject": subject, "body": html_body})
        logger.info("[MOCK EMAIL] To=%s Subject=%s", to, subject)


def _get_backend() -> EmailBackend:
    if settings.EMAIL_MOCK_MODE:
        return MockEmailBackend()
    return SMTPEmailBackend()


# ── Email composition ─────────────────────────────────────────────────────────

def _build_warning_email(employee: Employee, record: ComplianceRecord) -> tuple[str, str, str]:
    """Return (subject, text_body, html_body) for a compliance violation warning."""
    total_hours = minutes_to_hours(record.total_working_minutes)
    avg_hours = minutes_to_hours(record.average_working_minutes or 0)
    reasons_text = "\n".join(f"- {r}" for r in record.violation_reasons)
    reasons_html = "".join(f"<li>{r}</li>" for r in record.violation_reasons)

    subject = (
        f"Attendance Policy Non-Compliance Warning — "
        f"Week of {record.week_start.strftime('%B %d, %Y')}"
    )

    text_body = f"""Dear {employee.full_name},

This is an automated notice from the Attendance Management System.
Our records indicate that your attendance for the week of {record.week_start.strftime('%B %d, %Y')} to {record.week_end.strftime('%B %d, %Y')} did not meet the company's attendance policy requirements.

Attendance Statistics:
- Office Days: {record.attendance_days} (Required: >= {settings.MIN_OFFICE_DAYS_PER_WEEK})
- Total Working Hours: {total_hours:.2f} h (Required: >= {settings.MIN_WEEKLY_WORKING_HOURS:.1f} h)
- Average Hours / Day: {avg_hours:.2f} h (Required: >= {settings.MIN_AVERAGE_HOURS_PER_DAY:.1f} h)

Violation Reasons:
{reasons_text}

Please discuss this with your manager.

This message was sent automatically.
"""

    html_body = f"""
<html><body style="font-family:Arial,sans-serif;line-height:1.6;color:#333;">
<h2 style="color:#c0392b;">Attendance Policy Non-Compliance Warning</h2>
<p>Dear <strong>{employee.full_name}</strong>,</p>
<p>
  This is an automated notice from the Attendance Management System.
  Our records indicate that your attendance for the week of
  <strong>{record.week_start.strftime('%B %d, %Y')}</strong> to
  <strong>{record.week_end.strftime('%B %d, %Y')}</strong>
  did not meet the company's attendance policy requirements.
</p>
<h3>Your Attendance Statistics</h3>
<table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse;">
  <tr><th>Metric</th><th>Your Value</th><th>Required</th></tr>
  <tr>
    <td>Office Days</td>
    <td>{record.attendance_days}</td>
    <td>≥ {settings.MIN_OFFICE_DAYS_PER_WEEK}</td>
  </tr>
  <tr>
    <td>Total Working Hours</td>
    <td>{total_hours:.2f} h</td>
    <td>≥ {settings.MIN_WEEKLY_WORKING_HOURS:.1f} h</td>
  </tr>
  <tr>
    <td>Average Hours / Day</td>
    <td>{avg_hours:.2f} h</td>
    <td>≥ {settings.MIN_AVERAGE_HOURS_PER_DAY:.1f} h</td>
  </tr>
</table>
<h3>Violation Reasons</h3>
<ul>{reasons_html}</ul>
<p>
  Please discuss this with your manager. Repeated non-compliance may result
  in a formal HR review.
</p>
<p style="color:#888;font-size:0.85em;">
  This message was sent automatically. Please do not reply.
</p>
</body></html>
"""
    return subject, text_body, html_body


# ── Public API ────────────────────────────────────────────────────────────────

def send_compliance_warning(
    db: Session,
    employee: Employee,
    compliance_record: ComplianceRecord,
    force: bool = False,
) -> NotificationLog:
    """
    Send a compliance violation warning email and record the attempt.

    If a SENT notification already exists for this (employee, compliance_record)
    pair, the function returns that record without re-sending unless force=True.
    """
    # ── Idempotency check ─────────────────────────────────────────────────────
    if not force:
        existing = db.scalar(
            select(NotificationLog).where(
                NotificationLog.employee_id == employee.id,
                NotificationLog.compliance_record_id == compliance_record.id,
                NotificationLog.notification_type == NotificationType.COMPLIANCE_WARNING,
                NotificationLog.status == NotificationStatus.SENT,
            )
        )
        if existing:
            logger.info(
                "Notification already sent: employee_id=%d compliance_id=%d",
                employee.id,
                compliance_record.id,
            )
            return existing

    # ── Create / retrieve pending log ─────────────────────────────────────────
    log = db.scalar(
        select(NotificationLog).where(
            NotificationLog.employee_id == employee.id,
            NotificationLog.compliance_record_id == compliance_record.id,
            NotificationLog.notification_type == NotificationType.COMPLIANCE_WARNING,
            NotificationLog.status != NotificationStatus.SENT,
        )
    )
    if not log:
        log = NotificationLog(
            employee_id=employee.id,
            compliance_record_id=compliance_record.id,
            recipient_email=employee.email,
            notification_type=NotificationType.COMPLIANCE_WARNING,
            status=NotificationStatus.PENDING,
        )
        db.add(log)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            # Another process created the log concurrently — re-fetch
            log = db.scalar(
                select(NotificationLog).where(
                    NotificationLog.employee_id == employee.id,
                    NotificationLog.compliance_record_id == compliance_record.id,
                    NotificationLog.notification_type == NotificationType.COMPLIANCE_WARNING,
                )
            )
            if log and log.status == NotificationStatus.SENT:
                return log

    now = datetime.now(timezone.utc)
    log.attempt_count += 1
    log.last_attempt_at = now
    db.commit()

    # ── Send ─────────────────────────────────────────────────────────────────
    subject, text_body, html_body = _build_warning_email(employee, compliance_record)
    backend = _get_backend()
    try:
        backend.send(employee.email, subject, text_body, html_body)
        log.status = NotificationStatus.SENT
        log.sent_at = now
        log.error_message = None
        logger.info(
            "Compliance warning sent: employee_id=%d compliance_id=%d",
            employee.id,
            compliance_record.id,
        )
    except Exception as exc:  # noqa: BLE001
        # Sanitise: do not log SMTP credentials or full stack to the DB field
        safe_error = f"{type(exc).__name__}: {str(exc)[:800]}"
        log.status = NotificationStatus.FAILED
        log.error_message = safe_error
        logger.exception(
            "Failed to send compliance warning: employee_id=%d compliance_id=%d",
            employee.id,
            compliance_record.id,
        )

    db.commit()
    db.refresh(log)
    return log
