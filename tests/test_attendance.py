"""
tests/test_attendance.py
------------------------
Tests for check-in, check-out, duration calculations, and validations.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.attendance import AttendanceRecord, AttendanceStatus, WorkLocation
from tests.conftest import auth_header, create_test_employee, get_auth_token


def _checkin(client, token, location="OFFICE"):
    return client.post(
        "/api/v1/attendance/check-in",
        json={"work_location": location},
        headers=auth_header(token),
    )


def _checkout(client, token):
    return client.post("/api/v1/attendance/check-out", headers=auth_header(token))


# ── Basic flow ────────────────────────────────────────────────────────────────

def test_checkin_success(client: TestClient, db: Session):
    """Successful check-in should return 201 with ACTIVE status."""
    emp = create_test_employee(db, email="emp@test.com", password="TestPass123")
    token = get_auth_token(client, "emp@test.com", "TestPass123")
    resp = _checkin(client, token, "OFFICE")
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "ACTIVE"
    assert data["work_location"] == "OFFICE"
    assert data["employee_id"] == emp.id


def test_checkout_success(client: TestClient, db: Session):
    """Check-out should close the session and return working hours > 0."""
    create_test_employee(db, email="emp@test.com", password="TestPass123")
    token = get_auth_token(client, "emp@test.com", "TestPass123")
    _checkin(client, token)

    # Manually advance the entry time to simulate time passing
    record = db.query(AttendanceRecord).first()
    record.entry_time = datetime.now(timezone.utc) - timedelta(hours=5)
    db.commit()

    resp = _checkout(client, token)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "COMPLETED"
    assert data["working_hours"] >= 4.9  # ~5 hours


def test_duplicate_checkin_rejected(client: TestClient, db: Session):
    """A second check-in without check-out should return 409."""
    create_test_employee(db, email="emp@test.com", password="TestPass123")
    token = get_auth_token(client, "emp@test.com", "TestPass123")
    _checkin(client, token)
    resp = _checkin(client, token)
    assert resp.status_code == 409


def test_checkout_without_active_session(client: TestClient, db: Session):
    """Check-out with no active session should return 404."""
    create_test_employee(db, email="emp@test.com", password="TestPass123")
    token = get_auth_token(client, "emp@test.com", "TestPass123")
    resp = _checkout(client, token)
    assert resp.status_code == 404


def test_wfh_checkin(client: TestClient, db: Session):
    """WFH check-in should record the correct work location."""
    create_test_employee(db, email="emp@test.com", password="TestPass123")
    token = get_auth_token(client, "emp@test.com", "TestPass123")
    resp = _checkin(client, token, "WORK_FROM_HOME")
    assert resp.status_code == 201
    assert resp.json()["work_location"] == "WORK_FROM_HOME"


def test_invalid_work_location(client: TestClient, db: Session):
    """Invalid work location should return 422."""
    create_test_employee(db, email="emp@test.com", password="TestPass123")
    token = get_auth_token(client, "emp@test.com", "TestPass123")
    resp = client.post(
        "/api/v1/attendance/check-in",
        json={"work_location": "HYBRID"},
        headers=auth_header(token),
    )
    assert resp.status_code == 422


def test_get_my_attendance(client: TestClient, db: Session):
    """Employee should be able to view their own attendance."""
    emp = create_test_employee(db, email="emp@test.com", password="TestPass123")
    token = get_auth_token(client, "emp@test.com", "TestPass123")
    _checkin(client, token)
    resp = client.get("/api/v1/attendance/me", headers=auth_header(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


def test_employee_cannot_view_others_attendance(client: TestClient, db: Session):
    """Employee should not be able to view another employee's attendance."""
    emp1 = create_test_employee(db, email="emp1@test.com", password="TestPass123")
    emp2 = create_test_employee(db, email="emp2@test.com")
    token = get_auth_token(client, "emp1@test.com", "TestPass123")
    resp = client.get(f"/api/v1/attendance/{emp2.id}", headers=auth_header(token))
    assert resp.status_code == 403


def test_working_hours_calculation(client: TestClient, db: Session):
    """Working hours should equal the session duration."""
    create_test_employee(db, email="emp@test.com", password="TestPass123")
    token = get_auth_token(client, "emp@test.com", "TestPass123")
    _checkin(client, token)

    # Force entry to exactly 6 hours ago
    record = db.query(AttendanceRecord).first()
    record.entry_time = datetime.now(timezone.utc) - timedelta(hours=6)
    db.commit()

    resp = _checkout(client, token)
    data = resp.json()
    assert abs(data["working_hours"] - 6.0) < 0.05  # within 3 minutes tolerance


def test_multiple_sessions_per_day(client: TestClient, db: Session):
    """An employee can have multiple completed sessions in one day."""
    emp = create_test_employee(db, email="emp@test.com", password="TestPass123")
    token = get_auth_token(client, "emp@test.com", "TestPass123")

    # Session 1 (morning)
    _checkin(client, token)
    record1 = db.query(AttendanceRecord).filter_by(employee_id=emp.id).first()
    record1.entry_time = datetime.now(timezone.utc) - timedelta(hours=8)
    db.commit()
    _checkout(client, token)

    # Session 2 (afternoon)
    _checkin(client, token)
    record2 = db.query(AttendanceRecord).filter_by(
        employee_id=emp.id, status=AttendanceStatus.ACTIVE
    ).first()
    record2.entry_time = datetime.now(timezone.utc) - timedelta(hours=3)
    db.commit()
    _checkout(client, token)

    resp = client.get("/api/v1/attendance/me", headers=auth_header(token))
    assert resp.json()["total"] == 2


def test_attendance_summary(client: TestClient, db: Session):
    """Summary should aggregate multiple sessions correctly."""
    emp = create_test_employee(db, email="emp@test.com", password="TestPass123")
    token = get_auth_token(client, "emp@test.com", "TestPass123")

    _checkin(client, token, "OFFICE")
    record = db.query(AttendanceRecord).filter_by(employee_id=emp.id).first()
    record.entry_time = datetime.now(timezone.utc) - timedelta(hours=5)
    db.commit()
    _checkout(client, token)

    resp = client.get(f"/api/v1/attendance/{emp.id}/summary", headers=auth_header(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_working_hours"] >= 4.9
    assert data["office_days"] == 1
    assert data["wfh_days"] == 0
