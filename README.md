# Central Attendance Management System (Backend API)

[![CI Pipeline](https://github.com/USERNAME/REPO_NAME/actions/workflows/ci.yml/badge.svg)](https://github.com/USERNAME/REPO_NAME/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.12%20%7C%203.14-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-enabled-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

A robust, enterprise-grade Central Attendance Management System backend built with **FastAPI**, **PostgreSQL**, **SQLAlchemy 2.0**, and **APScheduler**. Features automated hybrid-work compliance evaluation, attendance tracking, customizable policy rules, scheduled background evaluations, and automated email warning dispatches with full retry mechanics.

---

## Key Features

- **Authentication & RBAC**: JWT bearer authentication with role-based access control (`ADMIN` vs `EMPLOYEE`).
- **Attendance Tracking**: Real-time check-in and check-out with automatic daily/weekly duration calculations, dual work locations (`OFFICE`, `WFH`), and concurrent session prevention.
- **Weekly Compliance Engine**: Evaluates employee compliance against company policy:
  - Minimum office days per week (default: 3 days).
  - Minimum weekly working hours (default: 15.0 hrs).
  - Minimum daily average working hours (default: 5.0 hrs/day).
- **Automated Email Notifications**:
  - Dispatches compliance violation warnings.
  - Built-in retry mechanism with max attempts tracking.
  - Duplicate dispatch prevention per evaluation period.
  - Safe mock mode (`EMAIL_MOCK_MODE=true`) for CI/testing without external SMTP dependencies.
- **Reporting Engine**: Aggregated attendance reports (Daily, Weekly, Monthly, Yearly, Custom date range) filterable by department and employee.
- **Background Scheduler**: APScheduler cron job automatically evaluates completed work weeks every Monday morning.
- **Containerized**: Full multi-container setup via Docker and Docker Compose (PostgreSQL 16 + FastAPI).
- **Continuous Integration (CI)**: Automated GitHub Actions pipeline running 55 unit/integration tests, Ruff linting, and Docker build verification on every push and pull request.

---

## Project Architecture

```
Central Attendance Management System/
├── .github/workflows/
│   └── ci.yml               # GitHub Actions CI workflow (linting, tests, docker)
├── alembic/                 # Database migrations
│   └── versions/            # Migration revisions
├── app/
│   ├── api/v1/              # API router endpoints (auth, attendance, compliance, reports, notifications)
│   ├── core/                # Core configuration, JWT security, and exception handlers
│   ├── db/                  # Database engine and session lifecycle
│   ├── models/              # SQLAlchemy 2.0 ORM models
│   ├── schemas/             # Pydantic v2 validation models
│   ├── services/            # Business logic (attendance, compliance, email, reports)
│   └── utils/               # Timezone-aware date and time utilities
├── tests/                   # 55 pytest test cases (auth, attendance, compliance, email, reports)
├── docker-compose.yml       # Production-ready PostgreSQL + API compose definition
├── Dockerfile               # Container build file
├── requirements.txt         # Pinned application dependencies
├── ruff.toml                # Ruff linter rules configuration
└── pytest.ini               # Pytest configuration
```

---

## Quick Start (Docker Compose)

The easiest way to run the entire stack (FastAPI application + PostgreSQL 16 database):

```bash
# 1. Clone repository
git clone https://github.com/<your-username>/<repo-name>.git
cd "Central Attendance Management System"

# 2. Configure environment file
cp .env.example .env

# 3. Spin up PostgreSQL and the FastAPI application
docker compose up -d --build

# 4. View application logs
docker compose logs -f app
```

Once started:
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## Local Development Setup

### 1. Prerequisites
- Python 3.12+ (or 3.14)
- PostgreSQL (or SQLite for local testing)

### 2. Installation
```bash
# Create and activate virtual environment
python -m venv .venv

# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file based on `.env.example`:
```bash
cp .env.example .env
```

Ensure your `.env` contains:
```ini
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/attendance_db
JWT_SECRET_KEY=change-this-to-a-very-secure-random-secret-key-32-chars
COMPANY_TIMEZONE=Asia/Kolkata
EMAIL_MOCK_MODE=true
```

### 4. Database Setup & Seed
```bash
# Run database migrations
alembic upgrade head

# Seed initial admin and test employees
python seed_admin.py
python seed_employees.py
```

### 5. Start Application
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Running Tests & Linters

Run the test suite locally with SQLite in-memory:
```bash
# Run all 55 test cases
python -m pytest -v

# Run with coverage report
python -m pytest --cov=app -v

# Run code style and linter checks
python -m ruff check .
```

---

## GitHub Actions CI Pipeline

The included CI workflow (`.github/workflows/ci.yml`) automatically executes on every `push` and `pull_request` targeting `main`:

1. **Linting Job**: Validates codebase against Ruff linter rules.
2. **Test Suite Job**: Runs all 55 test cases with SQLite in-memory and mock email mode.
3. **Docker Build Job**: Verifies that the Docker container builds without errors.

---

## API Overview

| Method | Endpoint | Description | Access |
|---|---|---|---|
| `POST` | `/api/v1/auth/login` | Authenticate and obtain JWT token | Public |
| `POST` | `/api/v1/attendance/check-in` | Record employee check-in | Employee / Admin |
| `POST` | `/api/v1/attendance/check-out` | Record employee check-out | Employee / Admin |
| `GET` | `/api/v1/attendance/my` | View logged-in employee's attendance | Employee / Admin |
| `POST` | `/api/v1/compliance/evaluate` | Trigger weekly compliance evaluation | Admin |
| `GET` | `/api/v1/compliance/summary` | Retrieve compliance stats for a week | Admin |
| `GET` | `/api/v1/reports/attendance` | Aggregated attendance reports (Daily, Weekly, Monthly) | Admin |
| `GET` | `/api/v1/notifications` | View notification delivery logs & statuses | Admin |

---

## License

This project is licensed under the MIT License.
