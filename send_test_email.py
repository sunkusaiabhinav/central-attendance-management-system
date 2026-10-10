"""
send_test_email.py
------------------
Script to test real email delivery using configured Gmail SMTP credentials.

Dispatches a real compliance policy warning email to configured SMTP recipient.
"""

from __future__ import annotations

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.compliance import ComplianceRecord
from app.models.employee import Employee, EmployeeRole
from app.services.email_service import send_compliance_warning
from sqlalchemy import select


def run():
    # Clear settings cache so new .env values are reloaded
    get_settings.cache_clear()
    settings = get_settings()

    print(f"SMTP Host: {settings.SMTP_HOST}")
    print(f"SMTP Port: {settings.SMTP_PORT}")
    print(f"SMTP Username: {settings.SMTP_USERNAME}")
    print(f"SMTP From: {settings.SMTP_FROM_EMAIL}")
    print(f"Mock Mode: {settings.EMAIL_MOCK_MODE}")

    db = SessionLocal()
    try:
        email = os.getenv("TEST_RECIPIENT_EMAIL") or settings.SMTP_USERNAME or "employee@example.com"
        emp = db.scalar(select(Employee).where(Employee.email == email))
        if not emp:
            emp = Employee(
                full_name="Test Recipient",
                email=email,
                department="Engineering",
                hashed_password="TestPassword123",
                role=EmployeeRole.EMPLOYEE,
                is_active=True,
            )
            db.add(emp)
            db.commit()
            db.refresh(emp)

        # 2. Create or fetch sample non-compliant record for week 2026-10-05
        week_start = date(2026, 10, 5)
        rec = db.scalar(
            select(ComplianceRecord).where(
                ComplianceRecord.employee_id == emp.id,
                ComplianceRecord.week_start == week_start,
            )
        )
        if not rec:
            rec = ComplianceRecord(
                employee_id=emp.id,
                week_start=week_start,
                week_end=date(2026, 10, 11),
                attendance_days=1,  # Attended only 1 day in office (required 3)
                total_working_minutes=480,  # 8.0 hours total (required 15.0h)
                average_working_minutes=240,  # 4.0 hours average (required 5.0h)
                is_compliant=False,
                violation_reasons=[
                    "Insufficient office days: attended 1 day(s), required 3",
                    "Insufficient total working hours: 8.00 h, required 15.0 h",
                    "Average hours per attendance day too low: 4.00 h, required 5.0 h",
                ],
            )
            db.add(rec)
            db.commit()
            db.refresh(rec)

        print(f"\nSending real email to {emp.email}...")
        log = send_compliance_warning(db, emp, rec)

        print("\n--- RESULTS ---")
        print(f"Status: {log.status}")
        print(f"Recipient: {log.recipient_email}")
        print(f"Attempt Count: {log.attempt_count}")
        print(f"Sent At: {log.sent_at}")
        if log.error_message:
            print(f"Error Details: {log.error_message}")
        else:
            print("SUCCESS! Real email was dispatched to inbox via Gmail SMTP.")

    finally:
        db.close()


if __name__ == "__main__":
    run()
