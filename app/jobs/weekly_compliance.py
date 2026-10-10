"""
app/jobs/weekly_compliance.py
------------------------------
APScheduler job that automatically evaluates weekly compliance.

Scheduling strategy
-------------------
* The scheduler runs in-process with the FastAPI application.
* To prevent multiple workers from running the job simultaneously, the job
  checks for an existing compliance record for the target week before
  proceeding (database-level idempotency via the UNIQUE constraint on
  (employee_id, week_start)).
* For single-worker deployments (Uvicorn single process) this is sufficient.
* For multi-worker deployments: run the scheduler in a dedicated worker
  (e.g. ``uvicorn app.main:app --workers 1`` for the scheduler process) or
  use a distributed lock such as Redis Redlock.

The ``trigger_weekly_evaluation`` function can also be called from the
admin API for manual evaluation.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.compliance import ComplianceRecord
from app.models.employee import Employee
from app.models.notification import NotificationLog, NotificationStatus
from app.services.compliance_service import evaluate_week_compliance
from app.services.email_service import send_compliance_warning
from app.utils.datetime_utils import is_week_complete, week_bounds

logger = logging.getLogger(__name__)
settings = get_settings()

_scheduler: BackgroundScheduler | None = None


# ── Core job function ─────────────────────────────────────────────────────────

def run_weekly_compliance_job() -> None:
    """
    Evaluate the most-recently completed ISO week and send violation warnings.

    This function is designed to be idempotent:
    * ``evaluate_week_compliance`` skips employees who already have a record.
    * ``send_compliance_warning`` checks for SENT notifications before sending.
    """
    from sqlalchemy.orm import Session
    from sqlalchemy import select

    logger.info("Starting weekly compliance job")
    db: Session = SessionLocal()
    try:
        # Determine the target week: the last completed ISO week (Mon–Sun)
        from app.utils.datetime_utils import now_company
        today = now_company().date()
        # Most recent Monday that has passed (i.e. the week that just ended)
        days_since_monday = today.weekday()
        last_monday = today - timedelta(days=days_since_monday + 7)
        week_start = last_monday
        week_end = week_start + timedelta(days=6)

        if not is_week_complete(week_end):
            logger.info(
                "Week %s–%s is not complete yet; skipping job", week_start, week_end
            )
            return

        logger.info("Evaluating compliance for week %s–%s", week_start, week_end)
        result = evaluate_week_compliance(db, week_start, force=False)
        logger.info("Evaluation result: %s", result)

        # Send violation warnings
        if result.get("skipped_incomplete_week"):
            return

        non_compliant_records = db.scalars(
            select(ComplianceRecord).where(
                ComplianceRecord.week_start == week_start,
                ComplianceRecord.is_compliant == False,
            )
        ).all()

        sent = 0
        for record in non_compliant_records:
            employee = db.get(Employee, record.employee_id)
            if not employee or not employee.is_active:
                continue
            try:
                log = send_compliance_warning(db, employee, record)
                if log.status == NotificationStatus.SENT:
                    sent += 1
            except Exception:  # noqa: BLE001
                logger.exception(
                    "Unexpected error sending warning to employee_id=%d", employee.id
                )

        logger.info("Weekly compliance job complete. Warnings sent: %d", sent)

    except Exception:
        logger.exception("Weekly compliance job failed")
    finally:
        db.close()


# ── Manual trigger (usable from API) ─────────────────────────────────────────

def trigger_weekly_evaluation(week_start: date, force: bool = False) -> dict:
    """
    Manually trigger compliance evaluation for a specific week.
    Used by the admin API endpoint.
    Returns the evaluation result dict from ``evaluate_week_compliance``.
    """
    from sqlalchemy import select

    db: "Session" = SessionLocal()
    try:
        result = evaluate_week_compliance(db, week_start, force=force)

        if result.get("skipped_incomplete_week"):
            return {**result, "notifications_queued": 0}

        week_end = week_start + timedelta(days=6)
        non_compliant = db.scalars(
            select(ComplianceRecord).where(
                ComplianceRecord.week_start == week_start,
                ComplianceRecord.is_compliant == False,
            )
        ).all()

        queued = 0
        for record in non_compliant:
            employee = db.get(Employee, record.employee_id)
            if not employee or not employee.is_active:
                continue
            try:
                send_compliance_warning(db, employee, record)
                queued += 1
            except Exception:  # noqa: BLE001
                logger.exception(
                    "Error sending warning for employee_id=%d", employee.id
                )

        return {**result, "notifications_queued": queued}
    finally:
        db.close()


# ── Scheduler lifecycle ───────────────────────────────────────────────────────

def start_scheduler() -> None:
    """
    Start the APScheduler background scheduler.

    Call this once from app startup (``lifespan`` context).
    """
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        logger.warning("Scheduler is already running; skipping start")
        return

    day_of_week = settings.ATTENDANCE_EVALUATION_DAY[:3]  # e.g. "mon"
    hour = settings.evaluation_hour
    minute = settings.evaluation_minute

    _scheduler = BackgroundScheduler(
        timezone=settings.COMPANY_TIMEZONE
    )
    _scheduler.add_job(
        run_weekly_compliance_job,
        trigger=CronTrigger(
            day_of_week=day_of_week,
            hour=hour,
            minute=minute,
            timezone=settings.COMPANY_TIMEZONE,
        ),
        id="weekly_compliance",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=3600,  # 1 hour grace period for missed fires
    )
    _scheduler.start()
    logger.info(
        "Compliance scheduler started: runs every %s at %02d:%02d %s",
        settings.ATTENDANCE_EVALUATION_DAY,
        hour,
        minute,
        settings.COMPANY_TIMEZONE,
    )


def stop_scheduler() -> None:
    """Stop the scheduler on application shutdown."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Compliance scheduler stopped")
