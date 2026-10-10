"""
tests/test_reports.py
---------------------
Tests for the unified attendance reporting endpoint.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.attendance import AttendanceRecord, AttendanceStatus, WorkLocation
from tests.conftest import auth_header, create_test_admin, create_test_employee, get_auth_token

# Fixed week for deterministic tests
WEEK_MON = date(2026, 9, 28)
WEEK_SUN = date(2026, 10, 4)


def _add_session(db, emp_id, day: date, hours: float, location="OFFICE"):
    entry = datetime(day.year, day.month, day.day, 9, 0, 0, tzinfo=timezone.utc)
    exit_dt = entry + timedelta(hours=hours)
    r = AttendanceRecord(
        employee_id=emp_id,
        entry_time=entry,
        exit_time=exit_dt,
        work_location=location,
        working_minutes=int(hours * 60),
        status=AttendanceStatus.COMPLETED,
    )
    db.add(r)
    db.flush()


# ── Authorization ─────────────────────────────────────────────────────────────

def test_report_requires_admin(client: TestClient, db: Session):
    """Non-admin should receive 403."""
    emp = create_test_employee(db, email="emp@test.com", password="TestPass123")
    token = get_auth_token(client, "emp@test.com", "TestPass123")
    resp = client.get(
        f"/api/v1/reports/attendance?period=daily&date={WEEK_MON}",
        headers=auth_header(token),
    )
    assert resp.status_code == 403


# ── Daily report ──────────────────────────────────────────────────────────────

def test_daily_report_includes_all_employees(client: TestClient, db: Session):
    """Daily report must include all active employees, even those not attended."""
    create_test_admin(db, email="admin@test.com")
    emp1 = create_test_employee(db, email="emp1@test.com", full_name="Emp1")
    emp2 = create_test_employee(db, email="emp2@test.com", full_name="Emp2")

    _add_session(db, emp1.id, WEEK_MON, 5.0)
    db.commit()

    token = get_auth_token(client, "admin@test.com", "AdminPass123")
    resp = client.get(
        f"/api/v1/reports/attendance?period=daily&date={WEEK_MON}",
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["report_type"] == "daily"
    employee_ids = {e["employee_id"] for e in data["employees"]}
    assert emp1.id in employee_ids
    assert emp2.id in employee_ids

    # emp2 should show NOT_ATTENDED
    emp2_data = next(e for e in data["employees"] if e["employee_id"] == emp2.id)
    assert emp2_data["attendance_status"] == "NOT_ATTENDED"
    assert emp2_data["attendance_days"] == 0
    assert emp2_data["daily_records"][0]["status"] == "NOT_ATTENDED"


def test_daily_report_attended_employee(client: TestClient, db: Session):
    """Attended employee should show correct entry/exit and working hours."""
    create_test_admin(db, email="admin@test.com")
    emp = create_test_employee(db, email="emp@test.com")
    _add_session(db, emp.id, WEEK_MON, 5.5)
    db.commit()

    token = get_auth_token(client, "admin@test.com", "AdminPass123")
    resp = client.get(
        f"/api/v1/reports/attendance?period=daily&date={WEEK_MON}",
        headers=auth_header(token),
    )
    emp_data = next(e for e in resp.json()["employees"] if e["employee_id"] == emp.id)
    assert emp_data["attendance_status"] == "ATTENDED"
    assert emp_data["total_working_hours"] >= 5.4
    record = emp_data["daily_records"][0]
    assert record["entry_time"] is not None
    assert record["exit_time"] is not None
    assert record["status"] == "COMPLETED"


# ── Weekly report ─────────────────────────────────────────────────────────────

def test_weekly_report_structure(client: TestClient, db: Session):
    """Weekly report should return 7 daily_records and weekly_summaries."""
    create_test_admin(db, email="admin@test.com")
    emp = create_test_employee(db, email="emp@test.com")
    _add_session(db, emp.id, WEEK_MON, 5.0)
    db.commit()

    token = get_auth_token(client, "admin@test.com", "AdminPass123")
    resp = client.get(
        f"/api/v1/reports/attendance?period=weekly&date={WEEK_MON}",
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    emp_data = next(e for e in resp.json()["employees"] if e["employee_id"] == emp.id)
    assert len(emp_data["daily_records"]) == 7  # Mon-Sun
    assert len(emp_data["weekly_summaries"]) >= 1


# ── Monthly report ────────────────────────────────────────────────────────────

def test_monthly_report(client: TestClient, db: Session):
    """Monthly report should span the full calendar month."""
    create_test_admin(db, email="admin@test.com")
    emp = create_test_employee(db, email="emp@test.com")
    _add_session(db, emp.id, date(2026, 9, 15), 6.0)
    db.commit()

    token = get_auth_token(client, "admin@test.com", "AdminPass123")
    resp = client.get(
        "/api/v1/reports/attendance?period=monthly&year=2026&month=9",
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["start_date"] == "2026-09-01"
    assert data["end_date"] == "2026-09-30"


# ── Yearly report ─────────────────────────────────────────────────────────────

def test_yearly_report(client: TestClient, db: Session):
    """Yearly report should span Jan 1 – Dec 31."""
    create_test_admin(db, email="admin@test.com")
    create_test_employee(db, email="emp@test.com")
    db.commit()

    token = get_auth_token(client, "admin@test.com", "AdminPass123")
    resp = client.get(
        "/api/v1/reports/attendance?period=yearly&year=2026",
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["start_date"] == "2026-01-01"
    assert data["end_date"] == "2026-12-31"


# ── Custom range report ───────────────────────────────────────────────────────

def test_custom_range_report(client: TestClient, db: Session):
    """Custom report should use the specified start and end dates."""
    create_test_admin(db, email="admin@test.com")
    create_test_employee(db, email="emp@test.com")
    db.commit()

    token = get_auth_token(client, "admin@test.com", "AdminPass123")
    resp = client.get(
        "/api/v1/reports/attendance?period=custom&start_date=2026-10-01&end_date=2026-10-09",
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["start_date"] == "2026-10-01"
    assert data["end_date"] == "2026-10-09"


# ── Invalid parameters ────────────────────────────────────────────────────────

def test_daily_report_missing_date(client: TestClient, db: Session):
    """Daily report without date should return 422."""
    create_test_admin(db, email="admin@test.com")
    token = get_auth_token(client, "admin@test.com", "AdminPass123")
    resp = client.get("/api/v1/reports/attendance?period=daily", headers=auth_header(token))
    assert resp.status_code == 422


def test_monthly_report_missing_month(client: TestClient, db: Session):
    """Monthly report without month should return 422."""
    create_test_admin(db, email="admin@test.com")
    token = get_auth_token(client, "admin@test.com", "AdminPass123")
    resp = client.get(
        "/api/v1/reports/attendance?period=monthly&year=2026",
        headers=auth_header(token),
    )
    assert resp.status_code == 422


def test_custom_report_start_after_end(client: TestClient, db: Session):
    """Custom range with start > end should return 422."""
    create_test_admin(db, email="admin@test.com")
    token = get_auth_token(client, "admin@test.com", "AdminPass123")
    resp = client.get(
        "/api/v1/reports/attendance?period=custom&start_date=2026-10-09&end_date=2026-10-01",
        headers=auth_header(token),
    )
    assert resp.status_code == 422


# ── Department filter ─────────────────────────────────────────────────────────

def test_report_department_filter(client: TestClient, db: Session):
    """Department filter should return only employees in that department."""
    create_test_admin(db, email="admin@test.com")
    eng = create_test_employee(db, email="eng@test.com", department="Engineering")
    fin = create_test_employee(db, email="fin@test.com", department="Finance")
    db.commit()

    token = get_auth_token(client, "admin@test.com", "AdminPass123")
    resp = client.get(
        f"/api/v1/reports/attendance?period=daily&date={WEEK_MON}&department=Engineering",
        headers=auth_header(token),
    )
    data = resp.json()
    returned_ids = {e["employee_id"] for e in data["employees"]}
    assert eng.id in returned_ids
    assert fin.id not in returned_ids


# ── Multiple sessions aggregated ──────────────────────────────────────────────

def test_report_aggregates_multiple_sessions(client: TestClient, db: Session):
    """Multiple sessions on the same day should be summed."""
    create_test_admin(db, email="admin@test.com")
    emp = create_test_employee(db, email="emp@test.com")

    # Morning session: 3h, Afternoon session: 2h → total 5h
    entry1 = datetime(2026, 9, 28, 9, 0, 0, tzinfo=timezone.utc)
    r1 = AttendanceRecord(
        employee_id=emp.id, entry_time=entry1,
        exit_time=entry1 + timedelta(hours=3),
        work_location="OFFICE", working_minutes=180, status="COMPLETED",
    )
    entry2 = datetime(2026, 9, 28, 13, 0, 0, tzinfo=timezone.utc)
    r2 = AttendanceRecord(
        employee_id=emp.id, entry_time=entry2,
        exit_time=entry2 + timedelta(hours=2),
        work_location="OFFICE", working_minutes=120, status="COMPLETED",
    )
    db.add_all([r1, r2])
    db.commit()

    token = get_auth_token(client, "admin@test.com", "AdminPass123")
    resp = client.get(
        f"/api/v1/reports/attendance?period=daily&date=2026-09-28",
        headers=auth_header(token),
    )
    emp_data = next(e for e in resp.json()["employees"] if e["employee_id"] == emp.id)
    assert abs(emp_data["total_working_hours"] - 5.0) < 0.01
