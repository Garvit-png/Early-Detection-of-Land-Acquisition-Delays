"""Projects CRUD + filtering + bulk import from CSV."""

import json
import math
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.core.deps import CurrentUser, get_db, log_action
from app.db.models import Project, RiskCategory, UserRole
from app.schemas.schemas import PaginatedResponse, ProjectListItem, ProjectOut

router = APIRouter(prefix="/projects", tags=["Projects"])


def _apply_scope(query, user):
    """Restrict results based on user role."""
    if user.role == UserRole.DISTRICT:
        query = query.filter(Project.district == user.district, Project.state == user.state)
    elif user.role == UserRole.STATE:
        query = query.filter(Project.state == user.state)
    return query


@router.get("", response_model=PaginatedResponse)
def list_projects(
    request: Request,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    state: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    project_type: Optional[str] = Query(None),
    risk_category: Optional[str] = Query(None),
    current_stage: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = db.query(Project)
    query = _apply_scope(query, current_user)

    if state:
        query = query.filter(Project.state == state)
    if district:
        query = query.filter(Project.district == district)
    if project_type:
        query = query.filter(Project.project_type == project_type)
    if risk_category:
        try:
            rc = RiskCategory(risk_category)
            query = query.filter(Project.risk_category == rc)
        except ValueError:
            pass
    if current_stage:
        query = query.filter(Project.current_stage == current_stage)
    if search:
        query = query.filter(
            or_(
                Project.project_name.ilike(f"%{search}%"),
                Project.project_id.ilike(f"%{search}%"),
                Project.district.ilike(f"%{search}%"),
            )
        )

    total = query.count()
    items = (
        query.order_by(Project.risk_score.desc().nullslast())
             .offset((page - 1) * page_size)
             .limit(page_size)
             .all()
    )

    log_action(db, current_user, "LIST_PROJECTS",
               detail=f"page={page} filters: state={state},district={district},risk={risk_category}",
               ip_address=request.client.host if request.client else None)

    return PaginatedResponse(
        items=[ProjectListItem.model_validate(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 1,
    )


@router.get("/map", response_model=list[ProjectListItem])
def projects_for_map(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    state: Optional[str] = Query(None),
    risk_category: Optional[str] = Query(None),
):
    """Returns lightweight list for GIS map — no pagination, only scored projects with coords."""
    query = db.query(Project).filter(
        Project.latitude.isnot(None),
        Project.longitude.isnot(None),
        Project.risk_score.isnot(None),
    )
    query = _apply_scope(query, current_user)
    if state:
        query = query.filter(Project.state == state)
    if risk_category:
        try:
            query = query.filter(Project.risk_category == RiskCategory(risk_category))
        except ValueError:
            pass

    return [ProjectListItem.model_validate(p) for p in query.limit(2000).all()]


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: str,
    request: Request,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # RBAC check
    if current_user.role == UserRole.DISTRICT and (
        project.district != current_user.district or project.state != current_user.state
    ):
        raise HTTPException(status_code=403, detail="Access denied")
    if current_user.role == UserRole.STATE and project.state != current_user.state:
        raise HTTPException(status_code=403, detail="Access denied")

    log_action(db, current_user, "VIEW_PROJECT", "project", project_id,
               ip_address=request.client.host if request.client else None)

    return ProjectOut.model_validate(project)


@router.post("/import-csv", status_code=201)
def import_csv(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """
    Seed the database from the generated CSV.
    Only callable by central users. Idempotent — skips existing project_ids.
    """
    import os
    if current_user.role != UserRole.CENTRAL:
        raise HTTPException(status_code=403, detail="Only central users can import data")

    base = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../../data/raw/projects_raw.csv")
    )
    if not os.path.exists(base):
        raise HTTPException(status_code=404, detail="Raw CSV not found — run generate_data.py first")

    df = pd.read_csv(base)
    inserted = 0
    skipped = 0

    for _, row in df.iterrows():
        existing = db.query(Project).filter(Project.project_id == row["project_id"]).first()
        if existing:
            skipped += 1
            continue

        top_reasons = row.get("top_delay_reasons", "[]")
        if isinstance(top_reasons, str):
            try:
                top_reasons = json.loads(top_reasons)
            except Exception:
                top_reasons = []

        rc_val = row.get("risk_category", "Medium")
        try:
            rc = RiskCategory(rc_val)
        except ValueError:
            rc = RiskCategory.MEDIUM

        proj = Project(
            project_id=row["project_id"],
            project_name=row["project_name"],
            project_type=row["project_type"],
            state=row["state"],
            district=row["district"],
            latitude=float(row["latitude"]) if pd.notna(row.get("latitude")) else None,
            longitude=float(row["longitude"]) if pd.notna(row.get("longitude")) else None,
            start_date=str(row.get("start_date", "")),
            land_area_ha=float(row["land_area_ha"]),
            families_affected=int(row["families_affected"]),
            current_stage=row["current_stage"],
            current_stage_index=int(row["current_stage_index"]),
            days_in_current_stage=int(row["days_in_current_stage"]),
            days_since_last_action=int(row["days_since_last_action"]),
            pending_approvals=int(row["pending_approvals"]),
            pending_notifications=int(row["pending_notifications"]),
            has_legal_dispute=bool(row["has_legal_dispute"]),
            num_legal_cases=int(row["num_legal_cases"]),
            compensation_pct=float(row["compensation_pct"]),
            compensation_pending_months=int(row["compensation_pending_months"]),
            rr_completion_pct=float(row["rr_completion_pct"]),
            possession_pct=float(row["possession_pct"]),
            budget_released=bool(row["budget_released"]),
            noc_pending_count=int(row["noc_pending_count"]),
            land_cost_cr=float(row["land_cost_cr"]),
            amount_paid_cr=float(row["amount_paid_cr"]),
            project_value_cr=float(row["project_value_cr"]),
            district_historical_delay_rate=float(row["district_historical_delay_rate"]),
            prev_delayed_district=int(row["prev_delayed_district"]),
            officer_responsiveness=float(row["officer_responsiveness"]),
            project_type_code=int(row.get("project_type_code", 0)),
            state_code=int(row.get("state_code", 0)),
            delay_probability=float(row["delay_probability"]),
            risk_score=float(row["risk_score"]),
            risk_category=rc,
            top_delay_reasons=top_reasons,
            is_delayed=bool(row["is_delayed"]),
            last_scored_at=datetime.now(timezone.utc),
        )
        db.add(proj)
        inserted += 1

    db.commit()
    return {"inserted": inserted, "skipped": skipped, "total": inserted + skipped}
