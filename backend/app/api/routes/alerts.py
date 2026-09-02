"""Alert management endpoints."""

import math
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db, log_action
from app.db.models import Alert, Project, UserRole
from app.schemas.schemas import AlertOut, AlertUpdate, PaginatedResponse

router = APIRouter(prefix="/alerts", tags=["Alerts"])


def _enrich(alert: Alert) -> dict:
    d = {
        "id": alert.id,
        "project_id_fk": alert.project_id_fk,
        "title": alert.title,
        "message": alert.message,
        "risk_category": alert.risk_category.value if alert.risk_category else None,
        "risk_score": alert.risk_score,
        "is_read": alert.is_read,
        "is_resolved": alert.is_resolved,
        "created_at": alert.created_at,
        "resolved_at": alert.resolved_at,
        "project_name": alert.project.project_name if alert.project else None,
        "state": alert.project.state if alert.project else None,
        "district": alert.project.district if alert.project else None,
    }
    return d


@router.get("", response_model=PaginatedResponse)
def list_alerts(
    request: Request,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    is_read: Optional[bool] = Query(None),
    is_resolved: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = db.query(Alert).join(Project, Alert.project_id_fk == Project.id)

    # Scope
    if current_user.role == UserRole.DISTRICT:
        query = query.filter(
            Project.state == current_user.state,
            Project.district == current_user.district,
        )
    elif current_user.role == UserRole.STATE:
        query = query.filter(Project.state == current_user.state)

    if is_read is not None:
        query = query.filter(Alert.is_read == is_read)
    if is_resolved is not None:
        query = query.filter(Alert.is_resolved == is_resolved)

    total = query.count()
    alerts = (
        query.order_by(Alert.created_at.desc())
             .offset((page - 1) * page_size)
             .limit(page_size)
             .all()
    )

    return PaginatedResponse(
        items=[_enrich(a) for a in alerts],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 1,
    )


@router.get("/unread-count")
def unread_count(current_user: CurrentUser, db: Session = Depends(get_db)):
    query = db.query(Alert).join(Project, Alert.project_id_fk == Project.id).filter(
        Alert.is_read == False, Alert.is_resolved == False
    )
    if current_user.role == UserRole.DISTRICT:
        query = query.filter(
            Project.state == current_user.state,
            Project.district == current_user.district,
        )
    elif current_user.role == UserRole.STATE:
        query = query.filter(Project.state == current_user.state)
    return {"count": query.count()}


@router.patch("/{alert_id}", response_model=dict)
def update_alert(
    alert_id: int,
    payload: AlertUpdate,
    request: Request,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if payload.is_read is not None:
        alert.is_read = payload.is_read
    if payload.is_resolved is not None:
        alert.is_resolved = payload.is_resolved
        if payload.is_resolved:
            alert.resolved_at = datetime.now(timezone.utc)

    db.commit()
    log_action(db, current_user, "UPDATE_ALERT", "alert", str(alert_id),
               ip_address=request.client.host if request.client else None)
    return {"success": True, "alert_id": alert_id}


@router.delete("/{alert_id}", status_code=204)
def delete_alert(
    alert_id: int,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    if current_user.role == UserRole.DISTRICT:
        raise HTTPException(status_code=403, detail="Not authorized to delete alerts")

    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    db.delete(alert)
    db.commit()
