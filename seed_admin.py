"""
seed_admin.py
-------------
Bootstrap script to create the first administrator account.

Usage
-----
    python seed_admin.py

The admin credentials are read from environment variables (or prompted
interactively if not set):

    SEED_ADMIN_NAME     Full name  (default: "System Administrator")
    SEED_ADMIN_EMAIL    Email      (required)
    SEED_ADMIN_PASSWORD Password   (required, min 8 chars)
    SEED_ADMIN_DEPT     Department (default: "Administration")

This script is safe to run multiple times; it will skip creation if the
email already exists.
"""

from __future__ import annotations

import os
import sys

# Ensure the project root is on sys.path so app imports work
sys.path.insert(0, os.path.dirname(__file__))

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.employee import Employee, EmployeeRole
from sqlalchemy import select


def seed_admin() -> None:
    name = os.environ.get("SEED_ADMIN_NAME", "System Administrator")
    dept = os.environ.get("SEED_ADMIN_DEPT", "Administration")

    email = os.environ.get("SEED_ADMIN_EMAIL") or input("Admin email: ").strip()
    if not email:
        print("ERROR: Email is required.")
        sys.exit(1)

    password = os.environ.get("SEED_ADMIN_PASSWORD") or input("Admin password (min 8 chars): ")
    if len(password) < 8:
        print("ERROR: Password must be at least 8 characters.")
        sys.exit(1)

    db = SessionLocal()
    try:
        existing = db.scalar(select(Employee).where(Employee.email == email))
        if existing:
            print(f"Admin with email '{email}' already exists (id={existing.id}). Skipping.")
            return

        admin = Employee(
            full_name=name,
            email=email,
            department=dept,
            hashed_password=hash_password(password),
            role=EmployeeRole.ADMIN,
            is_active=True,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print(f"[OK] Admin created: id={admin.id} email={admin.email} name={admin.full_name}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_admin()
