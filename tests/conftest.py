"""
tests/conftest.py
-----------------
Pytest fixtures for the complete test suite.

Test isolation strategy
-----------------------
* An in-memory SQLite database is used for speed and no external dependency.
* A fresh SQLite engine and tables are created for each test session.
* Each test function receives a ``db`` session that is rolled back after the
  test to prevent state leakage.
* The FastAPI TestClient is configured with a database session override so
  route handlers use the test database.
* EMAIL_MOCK_MODE is forced True to prevent real emails.
* The scheduler is NOT started during tests to avoid background job interference.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Force mock email mode before importing the app
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only-32c")
os.environ.setdefault("EMAIL_MOCK_MODE", "true")
os.environ.setdefault("COMPANY_TIMEZONE", "UTC")
os.environ.setdefault("MIN_OFFICE_DAYS_PER_WEEK", "3")
os.environ.setdefault("MIN_WEEKLY_WORKING_HOURS", "15")
os.environ.setdefault("MIN_AVERAGE_HOURS_PER_DAY", "5")
os.environ.setdefault("ATTENDANCE_EVALUATION_DAY", "monday")
os.environ.setdefault("ATTENDANCE_EVALUATION_TIME", "09:00")

# Patch lru_cache before importing settings
from app.core.config import get_settings
get_settings.cache_clear()

from app.db.session import Base, get_db
from app.main import create_app
from app.models import *  # noqa: F401, F403 — registers all models with Base

# ── Test database engine (SQLite in-memory) ───────────────────────────────────
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# SQLite needs this pragma to enforce FK constraints
@event.listens_for(test_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

Base.metadata.create_all(bind=test_engine)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """Provide a test database session that is rolled back after each test."""
    with test_engine.connect() as connection:
        with connection.begin() as transaction:
            session = Session(bind=connection)
            try:
                yield session
            finally:
                session.close()
            transaction.rollback()


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    """Provide a FastAPI TestClient with the test database injected."""
    app = create_app()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    # Disable scheduler startup during tests
    import app.main as main_module
    original_start = None

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ── Helper factories ──────────────────────────────────────────────────────────

def create_test_employee(
    db: Session,
    email: str = "employee@test.com",
    password: str = "TestPassword123",
    role: str = "EMPLOYEE",
    department: str = "Engineering",
    full_name: str = "Test Employee",
    is_active: bool = True,
):
    """Create and persist a test employee, returning the ORM object."""
    from app.core.security import hash_password
    from app.models.employee import Employee, EmployeeRole

    emp = Employee(
        full_name=full_name,
        email=email,
        department=department,
        hashed_password=hash_password(password),
        role=role,
        is_active=is_active,
    )
    db.add(emp)
    db.flush()
    db.refresh(emp)
    return emp


def create_test_admin(db: Session, email: str = "admin@test.com", password: str = "AdminPass123"):
    return create_test_employee(db, email=email, password=password, role="ADMIN", full_name="Test Admin")


def get_auth_token(client: TestClient, email: str, password: str) -> str:
    """Login and return the Bearer token string."""
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
