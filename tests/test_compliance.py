"""
tests/test_compliance.py
------------------------
Tests for the compliance evaluation engine.

Covers all policy cases from the specification:
  A: 3 office days, 5+5+5 hours = COMPLIANT
  B: 2 office days, 8+8 hours = NON_COMPLIANT (office days)
  C: 3 office days, 4+4+4 hours = NON_COMPLIANT (hours + average)
  D: 4 office days, 4+4+4+4 hours = NON_COMPLIANT (average)
  E: No attendance = NON_COMPLIANT (all three reasons)
  F: Incomplete week = skipped / pending
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from app.models.attendance import AttendanceRecord, AttendanceStatus, WorkLocation
from app.models.compliance import ComplianceRecord
from app.services.compliance_service import evaluate_week_compliance
from tests.conftest import create_test_employee

# Monday of a firmly past week (ensures is_week_complete returns True)
PAST_MONDAY = date(2026, 9, 28)  # Monday 28 Sep 2026
PAST_SUNDAY = date(2026, 10, 4)   # Sunday  04 Oct 2026


def _add_completed_session(
    db: Session,
    employee_id: int,
    day: date,
    hours: float,
    location: str = "OFFICE",
):
    """Insert a completed attendance record for the given day and duration."""
    entry = datetime(day.year, day.month, day.day, 9, 0, 0, tzinfo=timezone.utc)
    exit_dt = entry + timedelta(hours=hours)
    minutes = int(hours * 60)
    record = AttendanceRecord(
        employee_id=employee_id,
        entry_time=entry,
        exit_time=exit_dt,
        work_location=location,
        working_minutes=minutes,
        status=AttendanceStatus.COMPLETED,
    )
    db.add(record)
    db.flush()
    return record


# ── Case A: Compliant ─────────────────────────────────────────────────────────

def test_case_a_compliant(db: Session):
    """3 office days × 5 h = 15 h total, avg 5 h → COMPLIANT."""
    emp = create_test_employee(db, email="a@test.com")
    for i in range(3):
        _add_completed_session(db, emp.id, PAST_MONDAY + timedelta(days=i), 5.0, "OFFICE")
    db.commit()

    result = evaluate_week_compliance(db, PAST_MONDAY, force=True)
    rec = db.query(ComplianceRecord).filter_by(employee_id=emp.id).first()
    assert rec is not None
    assert rec.is_compliant is True
    assert rec.violation_reasons == []


# ── Case B: Insufficient office days ─────────────────────────────────────────

def test_case_b_insufficient_office_days(db: Session):
    """2 office days, 16 total hours → NON_COMPLIANT (office days)."""
    emp = create_test_employee(db, email="b@test.com")
    for i in range(2):
        _add_completed_session(db, emp.id, PAST_MONDAY + timedelta(days=i), 8.0, "OFFICE")
    db.commit()

    evaluate_week_compliance(db, PAST_MONDAY, force=True)
    rec = db.query(ComplianceRecord).filter_by(employee_id=emp.id).first()
    assert rec.is_compliant is False
    assert any("office day" in r.lower() for r in rec.violation_reasons)


# ── Case C: Insufficient working hours ───────────────────────────────────────

def test_case_c_insufficient_hours(db: Session):
    """3 office days × 4 h = 12 h → NON_COMPLIANT (hours + average)."""
    emp = create_test_employee(db, email="c@test.com")
    for i in range(3):
        _add_completed_session(db, emp.id, PAST_MONDAY + timedelta(days=i), 4.0, "OFFICE")
    db.commit()

    evaluate_week_compliance(db, PAST_MONDAY, force=True)
    rec = db.query(ComplianceRecord).filter_by(employee_id=emp.id).first()
    assert rec.is_compliant is False
    violation_text = " ".join(rec.violation_reasons).lower()
    assert "hour" in violation_text


# ── Case D: Average below threshold ──────────────────────────────────────────

def test_case_d_average_below_threshold(db: Session):
    """4 office days × 4 h = 16 h but avg 4 h < 5 → NON_COMPLIANT."""
    emp = create_test_employee(db, email="d@test.com")
    for i in range(4):
        _add_completed_session(db, emp.id, PAST_MONDAY + timedelta(days=i), 4.0, "OFFICE")
    db.commit()

    evaluate_week_compliance(db, PAST_MONDAY, force=True)
    rec = db.query(ComplianceRecord).filter_by(employee_id=emp.id).first()
    assert rec.is_compliant is False
    assert any("average" in r.lower() for r in rec.violation_reasons)


# ── Case E: No attendance ─────────────────────────────────────────────────────

def test_case_e_no_attendance(db: Session):
    """No attendance → all three conditions fail → NON_COMPLIANT."""
    emp = create_test_employee(db, email="e@test.com")
    db.commit()

    evaluate_week_compliance(db, PAST_MONDAY, force=True)
    rec = db.query(ComplianceRecord).filter_by(employee_id=emp.id).first()
    assert rec.is_compliant is False
    assert len(rec.violation_reasons) == 3


# ── Case F: Incomplete week ───────────────────────────────────────────────────

def test_case_f_incomplete_week_skipped(db: Session):
    """An incomplete (future) week should not produce a compliance record."""
    emp = create_test_employee(db, email="f@test.com")
    db.commit()

    # Use a future Monday
    from app.utils.datetime_utils import now_company
    today = now_company().date()
    next_monday = today - timedelta(days=today.weekday()) + timedelta(days=7)

    result = evaluate_week_compliance(db, next_monday, force=False)
    assert result.get("skipped_incomplete_week") is True
    rec = db.query(ComplianceRecord).filter_by(employee_id=emp.id).first()
    assert rec is None


# ── WFH hours count toward total but not office days ─────────────────────────

def test_wfh_hours_count_but_not_office_days(db: Session):
    """WFH sessions count toward total hours but not office days."""
    emp = create_test_employee(db, email="wfh@test.com")
    # 2 office days (10 h) + 3 WFH days (15 h) = 25 h total, but only 2 office days
    for i in range(2):
        _add_completed_session(db, emp.id, PAST_MONDAY + timedelta(days=i), 5.0, "OFFICE")
    for i in range(2, 5):
        _add_completed_session(db, emp.id, PAST_MONDAY + timedelta(days=i), 5.0, "WORK_FROM_HOME")
    db.commit()

    evaluate_week_compliance(db, PAST_MONDAY, force=True)
    rec = db.query(ComplianceRecord).filter_by(employee_id=emp.id).first()
    assert rec.is_compliant is False
    assert any("office day" in r.lower() for r in rec.violation_reasons)
    assert rec.attendance_days == 2  # Only office days counted


# ── No duplicate records on re-evaluation ────────────────────────────────────

def test_no_duplicate_compliance_records(db: Session):
    """Re-evaluating without force should not create duplicate records."""
    emp = create_test_employee(db, email="dup@test.com")
    db.commit()

    evaluate_week_compliance(db, PAST_MONDAY, force=True)
    evaluate_week_compliance(db, PAST_MONDAY, force=False)  # skip=True because record exists

    count = db.query(ComplianceRecord).filter_by(employee_id=emp.id).count()
    assert count == 1


# ── Force re-evaluation updates existing record ───────────────────────────────

def test_force_reevaluation_updates_record(db: Session):
    """Force=True should update an existing compliance record."""
    emp = create_test_employee(db, email="force@test.com")
    db.commit()

    # First evaluation: non-compliant (no attendance)
    evaluate_week_compliance(db, PAST_MONDAY, force=True)
    rec = db.query(ComplianceRecord).filter_by(employee_id=emp.id).first()
    assert rec.is_compliant is False

    # Add enough attendance
    for i in range(3):
        _add_completed_session(db, emp.id, PAST_MONDAY + timedelta(days=i), 5.0, "OFFICE")
    db.commit()

    # Force re-evaluation: should now be compliant
    evaluate_week_compliance(db, PAST_MONDAY, force=True)
    db.refresh(rec)
    assert rec.is_compliant is True
