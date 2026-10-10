"""
app/api/v1/notifications.py
-----------------------------
Notification log retrieval endpoints (ADMIN only).
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import require_admin
from app.db.session import get_db
from app.models.notification import NotificationLog

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class NotificationLogResponse(BaseModel):
    id: int
    employee_id: int
    compliance_record_id: Optional[int]
    recipient_email: str
    notification_type: str
    status: str
    attempt_count: int
    sent_at: Optional[str]
    error_message: Optional[str]
    created_at: str

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    notifications: list[NotificationLogResponse]


@router.get(
    "",
    response_model=NotificationListResponse,
    summary="List notification logs (ADMIN)",
)
def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    employee_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
):
    q = select(NotificationLog)
    if status_filter:
        q = q.where(NotificationLog.status == status_filter.upper())
    if employee_id:
        q = q.where(NotificationLog.employee_id == employee_id)

    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    logs = db.scalars(
        q.order_by(NotificationLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return NotificationListResponse(
        total=total,
        page=page,
        page_size=page_size,
        notifications=[
            NotificationLogResponse(
                id=log_item.id,
                employee_id=log_item.employee_id,
                compliance_record_id=log_item.compliance_record_id,
                recipient_email=log_item.recipient_email,
                notification_type=log_item.notification_type,
                status=log_item.status,
                attempt_count=log_item.attempt_count,
                sent_at=log_item.sent_at.isoformat() if log_item.sent_at else None,
                error_message=log_item.error_message,
                created_at=log_item.created_at.isoformat(),
            )
            for log_item in logs
        ],
    )
