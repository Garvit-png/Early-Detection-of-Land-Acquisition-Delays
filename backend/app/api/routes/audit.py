"""Audit log endpoint — central users only."""

import math

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db, require_roles
from app.db.models import AuditLog, UserRole
from app.schemas.schemas import PaginatedResponse

router = APIRouter(prefix="/audit", tags=["Audit"])

CentralOnly = Depends(require_roles(UserRole.CENTRAL))


@router.get("", response_model=PaginatedResponse, dependencies=[CentralOnly])
def list_audit_logs(
    db: Session = Depends(get_db),
    action: str | None = Query(None),
    user_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action.upper())
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)

    total = query.count()
    logs = (
        query.order_by(AuditLog.created_at.desc())
             .offset((page - 1) * page_size)
             .limit(page_size)
             .all()
    )

    items = [
        {
            "id": log.id,
            "user_id": log.user_id,
            "username": log.user.username if log.user else "system",
            "action": log.action,
            "resource": log.resource,
            "resource_id": log.resource_id,
            "detail": log.detail,
            "ip_address": log.ip_address,
            "created_at": log.created_at,
        }
        for log in logs
    ]

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 1,
    )
