"""Prediction endpoints — score a project, batch score, global feature importance."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db, log_action
from app.db.models import Alert, Project, RiskCategory, UserRole
from app.ml.predictor import predictor
from app.schemas.schemas import PredictionResponse

router = APIRouter(prefix="/predictions", tags=["Predictions"])


def _project_to_features(p: Project) -> dict:
    return {
        "land_area_ha":                   p.land_area_ha or 0,
        "families_affected":              p.families_affected or 0,
        "current_stage_index":            p.current_stage_index or 0,
        "days_in_current_stage":          p.days_in_current_stage or 0,
        "days_since_last_action":         p.days_since_last_action or 0,
        "pending_approvals":              p.pending_approvals or 0,
        "pending_notifications":          p.pending_notifications or 0,
        "has_legal_dispute":              int(p.has_legal_dispute or False),
        "num_legal_cases":                p.num_legal_cases or 0,
        "compensation_pct":               p.compensation_pct or 0,
        "compensation_pending_months":    p.compensation_pending_months or 0,
        "rr_completion_pct":              p.rr_completion_pct or 0,
        "possession_pct":                 p.possession_pct or 0,
        "budget_released":                int(p.budget_released or False),
        "noc_pending_count":              p.noc_pending_count or 0,
        "land_cost_cr":                   p.land_cost_cr or 0,
        "amount_paid_cr":                 p.amount_paid_cr or 0,
        "project_value_cr":               p.project_value_cr or 0,
        "district_historical_delay_rate": p.district_historical_delay_rate or 0.5,
        "prev_delayed_district":          p.prev_delayed_district or 0,
        "officer_responsiveness":         p.officer_responsiveness or 5,
        "project_type_code":              p.project_type_code or 0,
        "state_code":                     p.state_code or 0,
    }


def _upsert_alert(db: Session, project: Project, result: dict):
    """Create or skip alert when risk crosses HIGH threshold."""
    if result["risk_category"] != "High":
        return
    # Avoid duplicate unresolved alerts for same project
    existing = (
        db.query(Alert)
        .filter(Alert.project_id_fk == project.id, Alert.is_resolved == False)
        .first()
    )
    if existing:
        return

    recs = result.get("recommendations", [])
    top_rec = recs[0] if recs else "Review project immediately."
    alert = Alert(
        project_id_fk=project.id,
        title=f"High Risk: {project.project_name}",
        message=(
            f"Project {project.project_id} in {project.district}, {project.state} "
            f"has a risk score of {result['risk_score']:.1f}/100. "
            f"Recommended action: {top_rec}"
        ),
        risk_category=RiskCategory.HIGH,
        risk_score=result["risk_score"],
    )
    db.add(alert)


@router.post("/{project_id}", response_model=PredictionResponse)
def score_project(
    project_id: str,
    request: Request,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Score a single project and persist the result."""
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

    features = _project_to_features(project)
    result = predictor.predict(features)
    now = datetime.now(timezone.utc)

    try:
        rc = RiskCategory(result["risk_category"])
    except ValueError:
        rc = RiskCategory.MEDIUM

    # Persist ML outputs
    project.delay_probability = result["delay_probability"]
    project.risk_score        = result["risk_score"]
    project.risk_category     = rc
    project.shap_factors      = result["top_factors"]
    project.recommendations   = result["recommendations"]
    project.last_scored_at    = now

    _upsert_alert(db, project, result)
    db.commit()

    log_action(db, current_user, "SCORE_PROJECT", "project", project_id,
               detail=f"risk_score={result['risk_score']}",
               ip_address=request.client.host if request.client else None)

    return PredictionResponse(
        project_id=project_id,
        delay_probability=result["delay_probability"],
        risk_score=result["risk_score"],
        risk_category=result["risk_category"],
        top_factors=result["top_factors"],
        recommendations=result["recommendations"],
        scored_at=now,
    )


@router.post("/batch/score-all", status_code=202)
def batch_score(
    request: Request,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Score all unscored projects. Central/State users only."""
    if current_user.role == UserRole.DISTRICT:
        raise HTTPException(status_code=403, detail="Not authorized for batch scoring")

    query = db.query(Project).filter(Project.risk_score.is_(None))
    if current_user.role == UserRole.STATE:
        query = query.filter(Project.state == current_user.state)

    projects = query.limit(500).all()
    scored = 0
    now = datetime.now(timezone.utc)

    for project in projects:
        try:
            features = _project_to_features(project)
            result = predictor.predict(features)
            try:
                rc = RiskCategory(result["risk_category"])
            except ValueError:
                rc = RiskCategory.MEDIUM

            project.delay_probability = result["delay_probability"]
            project.risk_score        = result["risk_score"]
            project.risk_category     = rc
            project.shap_factors      = result["top_factors"]
            project.recommendations   = result["recommendations"]
            project.last_scored_at    = now
            _upsert_alert(db, project, result)
            scored += 1
        except Exception:
            continue

    db.commit()
    log_action(db, current_user, "BATCH_SCORE", detail=f"scored={scored}",
               ip_address=request.client.host if request.client else None)

    return {"scored": scored, "message": f"Successfully scored {scored} projects"}


@router.get("/feature-importance/global")
def global_feature_importance(current_user: CurrentUser):
    """Return global SHAP-based feature importance."""
    return predictor.get_global_importance()
