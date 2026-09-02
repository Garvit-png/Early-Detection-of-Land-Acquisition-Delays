"""
actions.py — Action item CRUD.
Implements: Officer Review → Accept/Modify/Override → Assign Action →
            Action Tracking → Action Completed → Update Project nodes.
"""

import math
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db, log_action
from app.db.models import ActionItem, ActionStatus, Project, RiskCategory, UserRole
from app.schemas.schemas import (
    ActionItemCreate, ActionItemOut, ActionItemUpdate, PaginatedResponse
)

router = APIRouter(prefix="/actions", tags=["Action Items"])


def _enrich(a: ActionItem) -> dict:
    assignee_name = None
    if a.assignee:
        assignee_name = a.assignee.full_name or a.assignee.username
    return {
        "id":               a.id,
        "project_id_fk":    a.project_id_fk,
        "rule_id":          a.rule_id,
        "title":            a.title,
        "description":      a.description,
        "officer_decision": a.officer_decision,
        "override_note":    a.override_note,
        "assigned_to":      a.assigned_to,
        "assigned_to_name": assignee_name,
        "assigned_by":      a.assigned_by,
        "status":           a.status.value if a.status else "open",
        "priority":         a.priority,
        "due_date":         a.due_date,
        "completed_at":     a.completed_at,
        "completion_note":  a.completion_note,
        "created_at":       a.created_at,
        "updated_at":       a.updated_at,
        "project_name":     a.project.project_name if a.project else None,
        "project_id":       a.project.project_id  if a.project else None,
        "state":            a.project.state        if a.project else None,
        "district":         a.project.district     if a.project else None,
    }


# ─── List all actions (for ActionTrackingPage) ────────────────────────────────

@router.get("", response_model=PaginatedResponse)
def list_actions(
    request: Request,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    status: Optional[str]  = Query(None),
    priority: Optional[str] = Query(None),
    assigned_to_me: bool   = Query(False),
    project_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = (
        db.query(ActionItem)
        .join(Project, ActionItem.project_id_fk == Project.id)
    )

    # Scope by role
    if current_user.role == UserRole.DISTRICT:
        query = query.filter(
            Project.state    == current_user.state,
            Project.district == current_user.district,
        )
    elif current_user.role == UserRole.STATE:
        query = query.filter(Project.state == current_user.state)

    if status:
        try:
            query = query.filter(ActionItem.status == ActionStatus(status))
        except ValueError:
            pass
    if priority:
        query = query.filter(ActionItem.priority == priority)
    if assigned_to_me:
        query = query.filter(ActionItem.assigned_to == current_user.id)
    if project_id:
        proj  = db.query(Project).filter(Project.project_id == project_id).first()
        if proj:
            query = query.filter(ActionItem.project_id_fk == proj.id)

    total  = query.count()
    items  = (
        query.order_by(ActionItem.created_at.desc())
             .offset((page - 1) * page_size)
             .limit(page_size)
             .all()
    )
    return PaginatedResponse(
        items=[_enrich(a) for a in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total else 1,
    )


# ─── Actions for a specific project ──────────────────────────────────────────

@router.get("/project/{project_id}", response_model=list[dict])
def list_project_actions(
    project_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    actions = (
        db.query(ActionItem)
        .filter(ActionItem.project_id_fk == project.id)
        .order_by(ActionItem.created_at.desc())
        .all()
    )
    return [_enrich(a) for a in actions]


# ─── Create action for a project (Officer Review → Assign Action) ─────────────

@router.post("/project/{project_id}", response_model=dict, status_code=201)
def create_action(
    project_id: str,
    payload: ActionItemCreate,
    request: Request,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """
    Officer reviews a recommendation and creates an action item.
    officer_decision: accept | modify | override
    """
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    action = ActionItem(
        project_id_fk    = project.id,
        rule_id          = payload.rule_id,
        title            = payload.title,
        description      = payload.description,
        officer_decision = payload.officer_decision,
        override_note    = payload.override_note,
        assigned_by      = current_user.id,
        priority         = payload.priority,
        due_date         = payload.due_date,
        status           = ActionStatus.OPEN,
    )
    db.add(action)
    db.commit()
    db.refresh(action)

    log_action(db, current_user, "CREATE_ACTION", "action_item", str(action.id),
               detail=f"project={project_id}, decision={payload.officer_decision}",
               ip_address=request.client.host if request.client else None)

    return _enrich(action)


# ─── Assign action to an officer ─────────────────────────────────────────────

@router.patch("/{action_id}/assign", response_model=dict)
def assign_action(
    action_id: int,
    assigned_to: int,
    request: Request,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Assign an action to a specific user (officer). Prioritize / Escalate node."""
    action = db.query(ActionItem).filter(ActionItem.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    action.assigned_to = assigned_to
    action.status      = ActionStatus.IN_PROGRESS
    db.commit()

    log_action(db, current_user, "ASSIGN_ACTION", "action_item", str(action_id),
               detail=f"assigned_to={assigned_to}",
               ip_address=request.client.host if request.client else None)
    return _enrich(action)


# ─── Update action status (Action Tracking → Action Completed) ────────────────

@router.patch("/{action_id}", response_model=dict)
def update_action(
    action_id: int,
    payload: ActionItemUpdate,
    request: Request,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """
    Update action status, priority, completion note.
    Completing an action triggers re-analysis of the parent project.
    """
    from app.ml.predictor import predictor
    from app.db.models import RiskHistory
    from app.api.routes.predictions import _project_to_features, _upsert_alert

    action = db.query(ActionItem).filter(ActionItem.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    if payload.status:
        try:
            action.status = ActionStatus(payload.status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {payload.status}")
    if payload.priority:
        action.priority = payload.priority
    if payload.due_date is not None:
        action.due_date = payload.due_date
    if payload.assigned_to is not None:
        action.assigned_to = payload.assigned_to
    if payload.completion_note is not None:
        action.completion_note = payload.completion_note
    if payload.officer_decision is not None:
        action.officer_decision = payload.officer_decision
    if payload.override_note is not None:
        action.override_note = payload.override_note

    if action.status == ActionStatus.COMPLETED and not action.completed_at:
        action.completed_at = datetime.now(timezone.utc)

    db.commit()

    # ── On completion → re-analyze parent project ─────────────────────────────
    if action.status == ActionStatus.COMPLETED:
        project = db.query(Project).filter(Project.id == action.project_id_fk).first()
        if project:
            features = _project_to_features(project)
            result   = predictor.predict(features)
            now      = datetime.now(timezone.utc)
            try:
                rc = RiskCategory(result["risk_category"])
            except ValueError:
                rc = RiskCategory.MEDIUM

            project.delay_probability    = result["delay_probability"]
            project.risk_score           = result["risk_score"]
            project.risk_category        = rc
            project.shap_factors         = result["top_factors"]
            project.recommendations      = result["recommendations"]
            project.rules_triggered      = result.get("rules_triggered", [])
            project.expected_delay_days  = result.get("expected_delay_days")
            project.expected_delay_label = result.get("expected_delay_label")
            project.model_confidence     = result.get("model_confidence")
            project.last_scored_at       = now

            db.add(RiskHistory(
                project_id_fk    = project.id,
                risk_score       = result["risk_score"],
                delay_probability= result["delay_probability"],
                risk_category    = rc,
                rules_triggered  = result.get("rules_triggered", []),
                scored_by        = current_user.id,
                trigger          = "action_completed",
                notes            = f"Action #{action_id} completed: {action.title[:60]}",
            ))
            _upsert_alert(db, project, result)
            db.commit()

    log_action(db, current_user, "UPDATE_ACTION", "action_item", str(action_id),
               detail=f"status={action.status.value if action.status else '?'}",
               ip_address=request.client.host if request.client else None)

    db.refresh(action)
    return _enrich(action)


# ─── Action summary counts ────────────────────────────────────────────────────

@router.get("/counts/summary", response_model=dict)
def action_counts(current_user: CurrentUser, db: Session = Depends(get_db)):
    """Summary counts for sidebar badge / dashboard."""
    query = db.query(ActionItem).join(Project, ActionItem.project_id_fk == Project.id)
    if current_user.role == UserRole.DISTRICT:
        query = query.filter(
            Project.state    == current_user.state,
            Project.district == current_user.district,
        )
    elif current_user.role == UserRole.STATE:
        query = query.filter(Project.state == current_user.state)

    all_items = query.all()
    return {
        "open":        sum(1 for a in all_items if a.status == ActionStatus.OPEN),
        "in_progress": sum(1 for a in all_items if a.status == ActionStatus.IN_PROGRESS),
        "completed":   sum(1 for a in all_items if a.status == ActionStatus.COMPLETED),
        "overridden":  sum(1 for a in all_items if a.status == ActionStatus.OVERRIDDEN),
        "my_open":     sum(1 for a in all_items
                          if a.assigned_to == current_user.id
                          and a.status in (ActionStatus.OPEN, ActionStatus.IN_PROGRESS)),
    }
