"""
tests/test_auth.py
------------------
Tests for authentication: login, token validation, role enforcement.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import auth_header, create_test_admin, create_test_employee, get_auth_token


def test_login_success(client: TestClient, db: Session):
    """Valid credentials should return a JWT token."""
    create_test_employee(db, email="emp@test.com", password="TestPass123")
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "emp@test.com", "password": "TestPass123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client: TestClient, db: Session):
    """Wrong password should return 401."""
    create_test_employee(db, email="emp2@test.com", password="TestPass123")
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "emp2@test.com", "password": "WrongPassword"},
    )
    assert resp.status_code == 401


def test_login_nonexistent_user(client: TestClient, db: Session):
    """Login with a non-existent email should return 401."""
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "nobody@test.com", "password": "TestPass123"},
    )
    assert resp.status_code == 401


def test_login_deactivated_user(client: TestClient, db: Session):
    """Deactivated employees should receive 403."""
    create_test_employee(db, email="inactive@test.com", password="TestPass123", is_active=False)
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "inactive@test.com", "password": "TestPass123"},
    )
    assert resp.status_code == 403


def test_protected_endpoint_without_token(client: TestClient, db: Session):
    """Requests without a Bearer token should receive 401."""
    resp = client.get("/api/v1/employees")
    assert resp.status_code == 401


def test_protected_endpoint_with_invalid_token(client: TestClient, db: Session):
    """Requests with a tampered token should receive 401."""
    resp = client.get("/api/v1/employees", headers={"Authorization": "Bearer invalid.token.here"})
    assert resp.status_code == 401


def test_employee_cannot_access_admin_endpoint(client: TestClient, db: Session):
    """Employees should receive 403 on admin-only endpoints."""
    create_test_employee(db, email="emp3@test.com", password="TestPass123")
    token = get_auth_token(client, "emp3@test.com", "TestPass123")
    resp = client.get("/api/v1/employees", headers=auth_header(token))
    assert resp.status_code == 403


def test_token_contains_role(client: TestClient, db: Session):
    """Login response should include role information."""
    create_test_admin(db, email="admin2@test.com", password="AdminPass123")
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": "admin2@test.com", "password": "AdminPass123"},
    )
    data = resp.json()
    assert data["role"] == "ADMIN"
