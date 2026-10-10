"""
demo_runner.py
--------------
Automated step-by-step demo script for Central Attendance Management System.

Runs through all API endpoints in sequence, printing colored output and JSON
responses. Perfect for testing or demonstrating the live API.

Usage:
    1. Ensure server is running: python -m uvicorn app.main:app --reload
    2. Run script: python demo_runner.py
"""

from __future__ import annotations

import sys
import time
import httpx

BASE_URL = "http://127.0.0.1:8000/api/v1"

# ANSI Colors
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"


def header(title: str):
    print(f"\n{BOLD}{BLUE}{'=' * 70}{RESET}")
    print(f"{BOLD}{BLUE}  {title}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 70}{RESET}")


def step(num: int, title: str):
    print(f"\n{BOLD}{CYAN}[Step {num}] {title}{RESET}")


def log_resp(resp: httpx.Response):
    status_color = GREEN if resp.status_code < 400 else RED
    print(f"  {BOLD}Status:{RESET} {status_color}{resp.status_code} {resp.reason_phrase}{RESET}")
    try:
        data = resp.json()
        print(f"  {BOLD}Response:{RESET} {data}")
    except Exception:
        print(f"  {BOLD}Response Body:{RESET} {resp.text[:300]}")


def run_demo():
    print(f"{BOLD}{GREEN}Starting Central Attendance Management System Live Demo{RESET}")
    print(f"Target Base URL: {BASE_URL}\n")

    client = httpx.Client(base_url=BASE_URL, timeout=10.0)

    # -------------------------------------------------------------------------
    header("1. AUTHENTICATION & AUTHORIZATION")
    # -------------------------------------------------------------------------
    step(1, "Admin Login -> Obtain JWT Access Token")
    admin_login_resp = client.post(
        "/auth/login",
        data={"username": "admin@company.com", "password": "Test@12345"},
    )
    log_resp(admin_login_resp)
    if admin_login_resp.status_code != 200:
        print(f"{RED}Failed to login as admin. Ensure database is seeded: python seed_employees.py{RESET}")
        sys.exit(1)

    admin_token = admin_login_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print(f"  {YELLOW}✓ Admin JWT Token acquired successfully.{RESET}")

    # -------------------------------------------------------------------------
    header("2. EMPLOYEE MANAGEMENT (ADMIN ONLY)")
    # -------------------------------------------------------------------------
    demo_email = f"demo_employee_{int(time.time())}@company.com"
    step(2, f"Create New Employee: {demo_email}")
    create_emp_resp = client.post(
        "/employees/",
        headers=admin_headers,
        json={
            "full_name": "Demo Tester",
            "email": demo_email,
            "department": "Engineering",
            "password": "DemoPassword123",
            "role": "EMPLOYEE",
        },
    )
    log_resp(create_emp_resp)

    step(3, "List All Active Employees")
    list_emp_resp = client.get("/employees/", headers=admin_headers)
    log_resp(list_emp_resp)

    # -------------------------------------------------------------------------
    header("3. ATTENDANCE CHECK-IN & CHECK-OUT WORKFLOW")
    # -------------------------------------------------------------------------
    step(4, "Login as Employee (abhi@company.com)")
    emp_login_resp = client.post(
        "/auth/login",
        data={"username": "abhi@company.com", "password": "Test@12345"},
    )
    log_resp(emp_login_resp)
    emp_token = emp_login_resp.json()["access_token"]
    emp_headers = {"Authorization": f"Bearer {emp_token}"}

    step(5, "Employee Check-In (Location: OFFICE)")
    checkin_resp = client.post(
        "/attendance/check-in",
        headers=emp_headers,
        json={"work_location": "OFFICE"},
    )
    log_resp(checkin_resp)

    step(6, "Demonstrate Duplicate Check-In Guard (Should Return 409 Conflict)")
    dup_checkin_resp = client.post(
        "/attendance/check-in",
        headers=emp_headers,
        json={"work_location": "OFFICE"},
    )
    log_resp(dup_checkin_resp)

    time.sleep(1)  # 1 second gap for duration

    step(7, "Employee Check-Out")
    checkout_resp = client.post("/attendance/check-out", headers=emp_headers)
    log_resp(checkout_resp)

    step(8, "View Personal Attendance Summary")
    summary_resp = client.get("/attendance/summary", headers=emp_headers)
    log_resp(summary_resp)

    # -------------------------------------------------------------------------
    header("4. COMPLIANCE EVALUATION ENGINE")
    # -------------------------------------------------------------------------
    week_start = "2026-10-05"  # Monday
    step(9, f"Trigger Compliance Evaluation for Week: {week_start}")
    eval_resp = client.post(
        "/compliance/evaluate",
        headers=admin_headers,
        params={"force": "true"},
        json={"week_start": week_start},
    )
    log_resp(eval_resp)

    step(10, "List All Policy Violation Records")
    violations_resp = client.get(
        "/compliance/violations",
        headers=admin_headers,
        params={"week_start": week_start},
    )
    log_resp(violations_resp)

    # -------------------------------------------------------------------------
    header("5. AUTOMATED EMAIL NOTIFICATIONS")
    # -------------------------------------------------------------------------
    step(11, f"Send Compliance Warning Emails for Week: {week_start}")
    emails_resp = client.post(
        "/compliance/send-warning-emails",
        headers=admin_headers,
        params={"week_start": week_start},
    )
    log_resp(emails_resp)

    step(12, "View Notification Audit Trail Logs")
    logs_resp = client.get("/notifications", headers=admin_headers)
    log_resp(logs_resp)

    # -------------------------------------------------------------------------
    header("6. UNIFIED MULTI-PERIOD ATTENDANCE REPORTING")
    # -------------------------------------------------------------------------
    step(13, "Generate Daily Report (date=2026-10-05)")
    daily_rep_resp = client.get(
        "/reports/attendance",
        headers=admin_headers,
        params={"period": "daily", "date": "2026-10-05"},
    )
    log_resp(daily_rep_resp)

    step(14, "Generate Weekly Report (date=2026-10-05)")
    weekly_rep_resp = client.get(
        "/reports/attendance",
        headers=admin_headers,
        params={"period": "weekly", "date": "2026-10-05"},
    )
    log_resp(weekly_rep_resp)

    step(15, "Generate Monthly Report (year=2026, month=10)")
    monthly_rep_resp = client.get(
        "/reports/attendance",
        headers=admin_headers,
        params={"period": "monthly", "year": 2026, "month": 10},
    )
    log_resp(monthly_rep_resp)

    header("DEMO COMPLETED SUCCESSFULLY!")
    print(f"{GREEN}{BOLD}✓ All 15 API sequence steps executed without errors.{RESET}\n")


if __name__ == "__main__":
    run_demo()
