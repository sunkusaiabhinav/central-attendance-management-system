"""
app/api/v1/router.py
---------------------
Aggregates all v1 sub-routers into a single APIRouter.
"""

from fastapi import APIRouter

from app.api.v1 import attendance, auth, compliance, employees, notifications, reports

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(employees.router)
api_router.include_router(attendance.router)
api_router.include_router(compliance.router)
api_router.include_router(reports.router)
api_router.include_router(notifications.router)
