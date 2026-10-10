"""
tests/test_employees.py
-----------------------
Tests for employee management CRUD endpoints.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import auth_header, create_test_admin, create_test_employee, get_auth_token


def test_create_employee(client: TestClient, db: Session):
    """Admin should be able to create an employee."""
    create_test_admin(db, email="admin@test.com")
    token = get_auth_token(client, "admin@test.com", "AdminPass123")
    resp = client.post(
        "/api/v1/employees",
        json={
            "full_name": "Alice Johnson",
            "email": "alice@test.com",
            "department": "Engineering",
            "password": "SecurePass123",
            "role": "EMPLOYEE",
        },
        headers=auth_header(token),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "alice@test.com"
    assert data["role"] == "EMPLOYEE"
    assert "hashed_password" not in data


def test_create_employee_duplicate_email(client: TestClient, db: Session):
    """Duplicate email should return 409 Conflict."""
    create_test_admin(db, email="admin@test.com")
    token = get_auth_token(client, "admin@test.com", "AdminPass123")
    payload = {
        "full_name": "Bob Smith",
        "email": "bob@test.com",
        "department": "Finance",
        "password": "SecurePass123",
        "role": "EMPLOYEE",
    }
    client.post("/api/v1/employees", json=payload, headers=auth_header(token))
    resp2 = client.post("/api/v1/employees", json=payload, headers=auth_header(token))
    assert resp2.status_code == 409


def test_create_employee_non_admin_forbidden(client: TestClient, db: Session):
    """Non-admin employee should not be able to create employees."""
    create_test_employee(db, email="emp@test.com", password="TestPass123")
    token = get_auth_token(client, "emp@test.com", "TestPass123")
    resp = client.post(
        "/api/v1/employees",
        json={
            "full_name": "Carol",
            "email": "carol@test.com",
            "department": "HR",
            "password": "SecurePass123",
        },
        headers=auth_header(token),
    )
    assert resp.status_code == 403


def test_list_employees(client: TestClient, db: Session):
    """Admin should receive a paginated list of employees."""
    admin = create_test_admin(db, email="admin@test.com")
    create_test_employee(db, email="emp1@test.com")
    create_test_employee(db, email="emp2@test.com")
    token = get_auth_token(client, "admin@test.com", "AdminPass123")
    resp = client.get("/api/v1/employees", headers=auth_header(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 3
    assert "employees" in data


def test_get_employee_by_id_admin(client: TestClient, db: Session):
    """Admin can retrieve any employee by ID."""
    admin = create_test_admin(db, email="admin@test.com")
    emp = create_test_employee(db, email="emp@test.com")
    token = get_auth_token(client, "admin@test.com", "AdminPass123")
    resp = client.get(f"/api/v1/employees/{emp.id}", headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.json()["email"] == "emp@test.com"


def test_get_own_profile(client: TestClient, db: Session):
    """Employee can retrieve their own profile."""
    emp = create_test_employee(db, email="emp@test.com", password="TestPass123")
    token = get_auth_token(client, "emp@test.com", "TestPass123")
    resp = client.get(f"/api/v1/employees/{emp.id}", headers=auth_header(token))
    assert resp.status_code == 200


def test_get_other_employee_profile_forbidden(client: TestClient, db: Session):
    """Employee should not be able to view another employee's profile."""
    emp1 = create_test_employee(db, email="emp1@test.com", password="TestPass123")
    emp2 = create_test_employee(db, email="emp2@test.com")
    token = get_auth_token(client, "emp1@test.com", "TestPass123")
    resp = client.get(f"/api/v1/employees/{emp2.id}", headers=auth_header(token))
    assert resp.status_code == 403


def test_update_employee(client: TestClient, db: Session):
    """Admin can update an employee's department."""
    create_test_admin(db, email="admin@test.com")
    emp = create_test_employee(db, email="emp@test.com")
    token = get_auth_token(client, "admin@test.com", "AdminPass123")
    resp = client.patch(
        f"/api/v1/employees/{emp.id}",
        json={"department": "Marketing"},
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    assert resp.json()["department"] == "Marketing"


def test_update_employee_status(client: TestClient, db: Session):
    """Admin can deactivate and reactivate an employee."""
    create_test_admin(db, email="admin@test.com")
    emp = create_test_employee(db, email="emp@test.com")
    token = get_auth_token(client, "admin@test.com", "AdminPass123")

    # Deactivate
    resp = client.patch(
        f"/api/v1/employees/{emp.id}/status",
        json={"is_active": False},
        headers=auth_header(token),
    )
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    # Reactivate
    resp2 = client.patch(
        f"/api/v1/employees/{emp.id}/status",
        json={"is_active": True},
        headers=auth_header(token),
    )
    assert resp2.json()["is_active"] is True


def test_create_employee_invalid_role(client: TestClient, db: Session):
    """Creating an employee with an invalid role should fail validation."""
    create_test_admin(db, email="admin@test.com")
    token = get_auth_token(client, "admin@test.com", "AdminPass123")
    resp = client.post(
        "/api/v1/employees",
        json={
            "full_name": "Test",
            "email": "test@test.com",
            "department": "IT",
            "password": "SecurePass123",
            "role": "SUPERUSER",  # invalid
        },
        headers=auth_header(token),
    )
    assert resp.status_code == 422
