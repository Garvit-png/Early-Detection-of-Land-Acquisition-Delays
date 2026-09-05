"""Projects CRUD + filtering + bulk import from CSV."""

import json
import math
import uuid
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.deps import CurrentUser, get_db, log_action
from app.db.models import Project, RiskCategory, UserRole
from app.ml.trainer import PROJECT_TYPE_MAP, STATE_MAP
from app.schemas.schemas import (
    PaginatedResponse, ProjectListItem, ProjectOut,
    ProjectCreate, ProjectCreateResponse,
)

router = APIRouter(prefix="/projects", tags=["Projects"])

STAGE_INDEX = {
    "Section 11 Notification": 0,
    "Section 19 Declaration":  1,
    "Award Passed":            2,
    "Compensation Disbursed":  3,
    "Possession Taken":        4,
    "R&R Completed":           5,
}


def _apply_scope(query, user):
    """Restrict results based on user role."""
    if user.role == UserRole.DISTRICT:
        query = query.filter(Project.district == user.district, Project.state == user.state)
    elif user.role == UserRole.STATE:
        query = query.filter(Project.state == user.state)
    return query


# ─── POST /projects — Submit new project + instant AI scoring ────────────────────

@router.post("", response_model=ProjectCreateResponse, status_code=201)
def create_project(
    payload: ProjectCreate,
    request: Request,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """
    Submit a new land acquisition project.
    The AI model scores it immediately — response contains risk score,
    delay probability, SHAP factors and recommended actions.
    """
    from app.ml.predictor import predictor

    # Auto-generate a unique project ID
    project_id = f"PRJ{str(uuid.uuid4().int)[:8].upper()}"
    while db.query(Project).filter(Project.project_id == project_id).first():
        project_id = f"PRJ{str(uuid.uuid4().int)[:8].upper()}"

    # Encode categorical fields
    type_code  = PROJECT_TYPE_MAP.get(payload.project_type, 0)
    state_code = STATE_MAP.get(payload.state, 0)
    stage_idx  = STAGE_INDEX.get(payload.current_stage, 0)

    # District historical delay rate — average of same district in DB
    existing = db.query(Project).filter(Project.district == payload.district).all()
    if existing:
        rates = [p.district_historical_delay_rate for p in existing if p.district_historical_delay_rate]
        dist_delay_rate = sum(rates) / len(rates) if rates else 0.5
        prev_delayed    = sum(1 for p in existing if p.is_delayed)
    else:
        dist_delay_rate = 0.5
        prev_delayed    = 0

    # Build feature vector
    features = {
        "land_area_ha":                   payload.land_area_ha,
        "families_affected":              payload.families_affected,
        "current_stage_index":            stage_idx,
        "days_in_current_stage":          payload.days_in_current_stage,
        "award_overdue":                  int(
            payload.current_stage == "Award Passed" and
            payload.days_in_current_stage > 180
        ),
        "days_since_last_action":         payload.days_since_last_action,
        "days_since_update":              0,
        "pending_approvals":              payload.pending_approvals,
        "pending_notifications":          payload.pending_notifications,
        "noc_pending_count":              payload.noc_pending_count,
        "budget_released":                int(payload.budget_released),
        "has_legal_dispute":              int(payload.has_legal_dispute),
        "num_legal_cases":                payload.num_legal_cases,
        "ownership_conflicts":            payload.ownership_conflicts,
        "compensation_pct":               payload.compensation_pct,
        "compensation_pending_months":    payload.compensation_pending_months,
        "rr_completion_pct":              payload.rr_completion_pct,
        "documentation_pct":              payload.documentation_pct,
        "stakeholder_response_pct":       payload.stakeholder_response_pct,
        "possession_pct":                 payload.possession_pct,
        "budget_released":                int(payload.budget_released),
        "land_cost_cr":                   payload.land_cost_cr,
        "amount_paid_cr":                 payload.amount_paid_cr,
        "project_value_cr":               payload.project_value_cr,
        "district_historical_delay_rate": dist_delay_rate,
        "prev_delayed_district":          prev_delayed,
        "officer_responsiveness":         payload.officer_responsiveness,
        "funding_readiness":              getattr(payload, "funding_readiness",       75),
        "notice_delivery_pct":            getattr(payload, "notice_delivery_pct",     75),
        "mutation_completion_pct":        getattr(payload, "mutation_completion_pct", 0),
        "project_type_code":              type_code,
        "state_code":                     state_code,
    }

    # ── LIVE AI INFERENCE ────────────────────────────────────────────────────────
    result = predictor.predict(features)
    now    = datetime.now(timezone.utc)

    try:
        rc = RiskCategory(result["risk_category"])
    except ValueError:
        rc = RiskCategory.MEDIUM

    # Persist project with AI results
    project = Project(
        project_id=project_id,
        project_name=payload.project_name,
        project_type=payload.project_type,
        state=payload.state,
        district=payload.district,
        latitude=payload.latitude,
        longitude=payload.longitude,
        start_date=payload.start_date,
        land_area_ha=payload.land_area_ha,
        families_affected=payload.families_affected,
        current_stage=payload.current_stage,
        current_stage_index=stage_idx,
        days_in_current_stage=payload.days_in_current_stage,
        days_since_last_action=payload.days_since_last_action,
        pending_approvals=payload.pending_approvals,
        pending_notifications=payload.pending_notifications,
        has_legal_dispute=payload.has_legal_dispute,
        num_legal_cases=payload.num_legal_cases,
        ownership_conflicts=payload.ownership_conflicts,
        documentation_pct=payload.documentation_pct,
        stakeholder_response_pct=payload.stakeholder_response_pct,
        compensation_pct=payload.compensation_pct,
        compensation_pending_months=payload.compensation_pending_months,
        rr_completion_pct=payload.rr_completion_pct,
        possession_pct=payload.possession_pct,
        budget_released=payload.budget_released,
        noc_pending_count=payload.noc_pending_count,
        land_cost_cr=payload.land_cost_cr,
        amount_paid_cr=payload.amount_paid_cr,
        project_value_cr=payload.project_value_cr,
        district_historical_delay_rate=dist_delay_rate,
        prev_delayed_district=prev_delayed,
        officer_responsiveness=payload.officer_responsiveness,
        funding_readiness=getattr(payload, "funding_readiness", 75),
        notice_delivery_pct=getattr(payload, "notice_delivery_pct", 75),
        mutation_completion_pct=getattr(payload, "mutation_completion_pct", 0),
        project_type_code=type_code,
        state_code=state_code,
        # AI outputs
        delay_probability=result["delay_probability"],
        risk_score=result["risk_score"],
        risk_category=rc,
        shap_factors=result["top_factors"],
        recommendations=result["recommendations"],
        last_scored_at=now,
    )
    db.add(project)
    db.commit()       # commit project first so it has a real PK
    db.refresh(project)

    # Auto-generate alert if High risk (project.id now valid)
    if rc == RiskCategory.HIGH:
        from app.db.models import Alert
        recs = result.get("recommendations", [])
        db.add(Alert(
            project_id_fk=project.id,
            title=f"High Risk Project Submitted: {payload.project_name}",
            message=(
                f"New project {project_id} in {payload.district}, {payload.state} "
                f"scored {result['risk_score']}/100. "
                f"{recs[0] if recs else 'Requires immediate review.'}"
            ),
            risk_category=RiskCategory.HIGH,
            risk_score=result["risk_score"],
        ))
        db.commit()

    log_action(db, current_user, "CREATE_PROJECT", "project", project_id,
               detail=f"risk_score={result['risk_score']},category={result['risk_category']}",
               ip_address=request.client.host if request.client else None)

    return ProjectCreateResponse(
        project_id=project_id,
        project_name=payload.project_name,
        state=payload.state,
        district=payload.district,
        delay_probability=result["delay_probability"],
        risk_score=result["risk_score"],
        risk_category=result["risk_category"],
        top_factors=result["top_factors"],
        recommendations=result["recommendations"],
        scored_at=now,
    )


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
            days_since_update=int(row.get("days_since_update", 0)),
            award_overdue=bool(row.get("award_overdue", 0)),
            pending_approvals=int(row["pending_approvals"]),
            pending_notifications=int(row["pending_notifications"]),
            has_legal_dispute=bool(row["has_legal_dispute"]),
            num_legal_cases=int(row["num_legal_cases"]),
            ownership_conflicts=int(row.get("ownership_conflicts", 0)),
            compensation_pct=float(row["compensation_pct"]),
            compensation_pending_months=int(row["compensation_pending_months"]),
            rr_completion_pct=float(row["rr_completion_pct"]),
            documentation_pct=float(row.get("documentation_pct", 75)),
            stakeholder_response_pct=float(row.get("stakeholder_response_pct", 75)),
            possession_pct=float(row["possession_pct"]),
            budget_released=bool(row["budget_released"]),
            noc_pending_count=int(row["noc_pending_count"]),
            land_cost_cr=float(row["land_cost_cr"]),
            amount_paid_cr=float(row["amount_paid_cr"]),
            project_value_cr=float(row["project_value_cr"]),
            district_historical_delay_rate=float(row["district_historical_delay_rate"]),
            prev_delayed_district=int(row["prev_delayed_district"]),
            officer_responsiveness=float(row["officer_responsiveness"]),
            funding_readiness=float(row.get("funding_readiness", 75)),
            notice_delivery_pct=float(row.get("notice_delivery_pct", 75)),
            mutation_completion_pct=float(row.get("mutation_completion_pct", 0)),
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


# ─── PUT /projects/:id — Update + re-analyze ─────────────────────────────────

@router.put("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: str,
    payload: dict,
    request: Request,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """
    Update a project's fields and immediately re-run AI analysis.
    Saves a RiskHistory snapshot before + after so risk evolution is tracked.
    This implements the EXISTING PROJECT → Update Details → Validate → Re-Analyze path.
    """
    from app.ml.predictor import predictor
    from app.db.models import RiskHistory

    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # RBAC
    if current_user.role == UserRole.DISTRICT and (
        project.district != current_user.district or project.state != current_user.state
    ):
        raise HTTPException(status_code=403, detail="Access denied")
    if current_user.role == UserRole.STATE and project.state != current_user.state:
        raise HTTPException(status_code=403, detail="Access denied")

    # Updatable fields — everything except project_id, state_code, project_type_code
    UPDATABLE = {
        "project_name", "project_type", "state", "district", "latitude", "longitude",
        "start_date", "land_area_ha", "families_affected",
        "current_stage", "current_stage_index", "days_in_current_stage",
        "days_since_last_action", "days_since_update",
        "pending_approvals", "pending_notifications", "noc_pending_count",
        "has_legal_dispute", "num_legal_cases", "ownership_conflicts", "award_overdue",
        "compensation_pct", "compensation_pending_months", "rr_completion_pct",
        "possession_pct", "documentation_pct", "stakeholder_response_pct",
        "budget_released", "land_cost_cr", "amount_paid_cr", "project_value_cr",
        "officer_responsiveness", "is_delayed",
    }

    for field, value in payload.items():
        if field in UPDATABLE and value is not None:
            setattr(project, field, value)

    # Re-encode categorical codes if type/state changed
    from app.ml.trainer import PROJECT_TYPE_MAP, STATE_MAP, STAGE_EXPECTED_DAYS
    project.project_type_code = PROJECT_TYPE_MAP.get(project.project_type, 0)
    project.state_code        = STATE_MAP.get(project.state, 0)
    if project.current_stage:
        stage_map = {
            "Section 11 Notification": 0, "Section 19 Declaration": 1,
            "Award Passed": 2, "Compensation Disbursed": 3,
            "Possession Taken": 4, "R&R Completed": 5,
        }
        project.current_stage_index = stage_map.get(project.current_stage, project.current_stage_index or 0)

    project.days_since_update = 0  # reset staleness on update

    # ── Re-analyze with updated data ──────────────────────────────────────────
    from app.api.routes.predictions import _project_to_features, _upsert_alert
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

    # ── Append risk history snapshot ──────────────────────────────────────────
    db.add(RiskHistory(
        project_id_fk    = project.id,
        risk_score       = result["risk_score"],
        delay_probability= result["delay_probability"],
        risk_category    = rc,
        rules_triggered  = result.get("rules_triggered", []),
        scored_by        = current_user.id,
        trigger          = "update",
        notes            = f"Updated by {current_user.username}",
    ))

    _upsert_alert(db, project, result)
    db.commit()
    db.refresh(project)

    log_action(db, current_user, "UPDATE_PROJECT", "project", project_id,
               detail=f"risk_score={result['risk_score']},trigger=update",
               ip_address=request.client.host if request.client else None)

    return ProjectOut.model_validate(project)
