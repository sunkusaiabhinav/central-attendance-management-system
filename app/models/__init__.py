"""
app/models/__init__.py
----------------------
Re-export all models so that Alembic env.py can import Base and discover
every table by importing this module.
"""

from app.db.session import Base
from app.models.attendance import AttendanceRecord, AttendanceStatus, WorkLocation
from app.models.compliance import ComplianceRecord
from app.models.employee import Employee, EmployeeRole
from app.models.notification import NotificationLog, NotificationStatus, NotificationType

__all__ = [
    "Base",
    "Employee",
    "EmployeeRole",
    "AttendanceRecord",
    "AttendanceStatus",
    "WorkLocation",
    "ComplianceRecord",
    "NotificationLog",
    "NotificationStatus",
    "NotificationType",
]
