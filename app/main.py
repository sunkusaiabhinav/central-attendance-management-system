"""
app/main.py
-----------
FastAPI application entry point.

Startup sequence
----------------
1. Configure structured logging.
2. Mount all API v1 routes.
3. Start the APScheduler background scheduler in the lifespan context.
4. Expose /docs (Swagger UI) and /redoc for API exploration.

The application should be launched with a single Uvicorn worker when the
scheduler is running in-process to avoid duplicate job execution.
For multi-worker deployments, run the scheduler in a dedicated process.
"""

from __future__ import annotations

import logging
import logging.config
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.jobs.weekly_compliance import start_scheduler, stop_scheduler

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)
settings = get_settings()


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage resources that must be set up before the app serves requests
    and torn down after the last request.
    """
    logger.info("Starting Central Attendance Management System")
    try:
        start_scheduler()
    except Exception:
        logger.exception("Failed to start compliance scheduler; continuing without it")
    yield
    logger.info("Shutting down")
    try:
        stop_scheduler()
    except Exception:
        logger.exception("Error stopping scheduler")


# ── Application factory ───────────────────────────────────────────────────────
def create_app() -> FastAPI:
    app = FastAPI(
        title="Central Attendance Management System",
        description="""
## Overview

A complete backend API for managing employee attendance, calculating working hours,
evaluating office attendance policy compliance, and generating reports.

## Key Features

- **JWT Authentication** with role-based access (ADMIN / EMPLOYEE)
- **Attendance Tracking**: Check-in/out with OFFICE and WORK_FROM_HOME locations
- **Compliance Engine**: Evaluates the 3-day/15-hour/5-avg-hour weekly policy
- **Unified Reporting**: One endpoint for daily, weekly, monthly, yearly, and custom reports
- **Email Notifications**: Automatic compliance violation warnings via SMTP
- **Scheduled Evaluation**: APScheduler-driven weekly compliance job

## Roles

| Role | Capabilities |
|------|-------------|
| ADMIN | Full access: manage employees, view all reports, trigger evaluations |
| EMPLOYEE | Check in/out, view own attendance and compliance |

## Getting Started

1. Create an admin using the seed script or POST `/api/v1/employees` with a bootstrap token.
2. Login at `/api/v1/auth/login` to obtain a JWT token.
3. Use the **Authorize** button (🔒) to set your Bearer token.
4. Explore all endpoints below.
""",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS (adjust origins for production) ─────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routes ────────────────────────────────────────────────────────────────
    app.include_router(api_router)

    # ── Error handlers ────────────────────────────────────────────────────────
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = []
        for error in exc.errors():
            errors.append({
                "field": " → ".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            })
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "Validation error", "errors": errors},
        )

    @app.get("/health", tags=["System"], summary="Health check")
    def health_check():
        return {"status": "ok", "version": "1.0.0"}

    return app


app = create_app()
