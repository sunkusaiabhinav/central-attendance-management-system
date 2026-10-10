"""
seed_employees.py
-----------------
Seeds 10 sample employees (1 admin + 9 regular employees) for development
and testing purposes.

Usage
-----
    python seed_employees.py

All employees get the password: ``Test@12345``
The admin gets email: admin@company.com
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.employee import Employee, EmployeeRole
from sqlalchemy import select

SAMPLE_EMPLOYEES = [
    {"full_name": "Admin User",    "email": "admin@company.com",   "dept": "Administration", "role": "ADMIN"},
    {"full_name": "Abhi Sharma",   "email": "abhi@company.com",    "dept": "Engineering",    "role": "EMPLOYEE"},
    {"full_name": "Priya Patel",   "email": "priya@company.com",   "dept": "Finance",        "role": "EMPLOYEE"},
    {"full_name": "Rahul Gupta",   "email": "rahul@company.com",   "dept": "Engineering",    "role": "EMPLOYEE"},
    {"full_name": "Sneha Kumar",   "email": "sneha@company.com",   "dept": "HR",             "role": "EMPLOYEE"},
    {"full_name": "Vikram Singh",  "email": "vikram@company.com",  "dept": "Marketing",      "role": "EMPLOYEE"},
    {"full_name": "Ananya Roy",    "email": "ananya@company.com",  "dept": "Engineering",    "role": "EMPLOYEE"},
    {"full_name": "Deepak Nair",   "email": "deepak@company.com",  "dept": "Finance",        "role": "EMPLOYEE"},
    {"full_name": "Kavya Menon",   "email": "kavya@company.com",   "dept": "HR",             "role": "EMPLOYEE"},
    {"full_name": "Arjun Reddy",   "email": "arjun@company.com",   "dept": "Marketing",      "role": "EMPLOYEE"},
]

DEFAULT_PASSWORD = "Test@12345"


def seed() -> None:
    db = SessionLocal()
    try:
        hashed = hash_password(DEFAULT_PASSWORD)
        created = skipped = 0
        for emp_data in SAMPLE_EMPLOYEES:
            existing = db.scalar(
                select(Employee).where(Employee.email == emp_data["email"])
            )
            if existing:
                skipped += 1
                continue
            emp = Employee(
                full_name=emp_data["full_name"],
                email=emp_data["email"],
                department=emp_data["dept"],
                hashed_password=hashed,
                role=emp_data["role"],
                is_active=True,
            )
            db.add(emp)
            created += 1

        db.commit()
        print(f"[OK] Seeded {created} employee(s); skipped {skipped} existing.")
        print(f"  Default password for all: {DEFAULT_PASSWORD}")
        print(f"  Admin login: admin@company.com / {DEFAULT_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
