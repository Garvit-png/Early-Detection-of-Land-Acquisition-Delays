"""Prediction endpoints — score project, batch score, retrain model, model status."""

import json
import os
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db, log_action
from app.db.models import Alert, Project, RiskCategory, UserRole
from app.ml.predictor import predictor
from app.schemas.schemas import (
    ModelStatus, PredictionResponse, RetrainResponse,
)

router = APIRouter(prefix="/predictions", tags=["Predictions"])

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "../../../.."))
MODELS_DIR   = os.path.join(PROJECT_ROOT, "data/models")


# ─── Helpers ─────────────────────────────────────────────────────────────────────

def _project_to_features(p: Project) -> dict:
    stage_idx = p.current_stage_index or 0
    from app.ml.trainer import STAGE_EXPECTED_DAYS
    exp_days  = STAGE_EXPECTED_DAYS[stage_idx] if stage_idx < len(STAGE_EXPECTED_DAYS) else 90
    return {
        "land_area_ha":                   p.land_area_ha or 0,
        "families_affected":              p.families_affected or 0,
        "current_stage_index":            stage_idx,
        "days_in_current_stage":          p.days_in_current_stage or 0,
        "award_overdue":                  int(
            p.current_stage == "Award Passed" and
            (p.days_in_current_stage or 0) > exp_days * 1.5
        ),
        "days_since_last_action":         p.days_since_last_action or 0,
        "days_since_update":              getattr(p, "days_since_update", None) or 0,
        "pending_approvals":              p.pending_approvals or 0,
        "pending_notifications":          p.pending_notifications or 0,
        "noc_pending_count":              p.noc_pending_count or 0,
        "budget_released":                int(p.budget_released or False),
        "has_legal_dispute":              int(p.has_legal_dispute or False),
        "num_legal_cases":                p.num_legal_cases or 0,
        "ownership_conflicts":            getattr(p, "ownership_conflicts", None) or 0,
        "compensation_pct":               p.compensation_pct or 0,
        "compensation_pending_months":    p.compensation_pending_months or 0,
        "rr_completion_pct":              p.rr_completion_pct or 0,
        "documentation_pct":              getattr(p, "documentation_pct", None) or 75,
        "stakeholder_response_pct":       getattr(p, "stakeholder_response_pct", None) or 75,
        "possession_pct":                 p.possession_pct or 0,
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
    """Create alert only when risk is HIGH and no unresolved alert exists."""
    if result["risk_category"] != "High":
        return
    existing = (
        db.query(Alert)
        .filter(Alert.project_id_fk == project.id, Alert.is_resolved == False)
        .first()
    )
    if existing:
        return
    recs    = result.get("recommendations", [])
    top_rec = recs[0] if recs else "Review project immediately."
    db.add(Alert(
        project_id_fk=project.id,
        title=f"High Risk: {project.project_name}",
        message=(
            f"Project {project.project_id} in {project.district}, {project.state} "
            f"has a risk score of {result['risk_score']:.1f}/100. "
            f"Recommended action: {top_rec}"
        ),
        risk_category=RiskCategory.HIGH,
        risk_score=result["risk_score"],
    ))


# ─── Score a single project ───────────────────────────────────────────────────────

@router.post("/{project_id}", response_model=PredictionResponse)
def score_project(
    project_id: str,
    request: Request,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """Run live AI inference on a project and persist results."""
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role == UserRole.DISTRICT and (
        project.district != current_user.district or project.state != current_user.state
    ):
        raise HTTPException(status_code=403, detail="Access denied")
    if current_user.role == UserRole.STATE and project.state != current_user.state:
        raise HTTPException(status_code=403, detail="Access denied")

    features = _project_to_features(project)
    result   = predictor.predict(features)          # ← LIVE XGBoost + SHAP
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

    _upsert_alert(db, project, result)

    # ── Append risk history snapshot ─────────────────────────────────────────
    from app.db.models import RiskHistory
    db.add(RiskHistory(
        project_id_fk    = project.id,
        risk_score       = result["risk_score"],
        delay_probability= result["delay_probability"],
        risk_category    = rc,
        rules_triggered  = result.get("rules_triggered", []),
        scored_by        = current_user.id,
        trigger          = "manual",
    ))

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
        rules_triggered=result.get("rules_triggered", []),
        expected_delay_days=result.get("expected_delay_days"),
        expected_delay_label=result.get("expected_delay_label"),
        model_confidence=result.get("model_confidence"),
        scored_at=now,
    )


# ─── Batch score ─────────────────────────────────────────────────────────────────

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
    scored   = 0
    now      = datetime.now(timezone.utc)

    for project in projects:
        try:
            features = _project_to_features(project)
            result   = predictor.predict(features)
            try:
                rc = RiskCategory(result["risk_category"])
            except ValueError:
                rc = RiskCategory.MEDIUM
            project.delay_probability = result["delay_probability"]
            project.risk_score        = result["risk_score"]
            project.risk_category     = rc
            project.shap_factors      = result["top_factors"]
            project.recommendations   = result["recommendations"]
            project.rules_triggered   = result.get("rules_triggered", [])
            project.last_scored_at    = now
            _upsert_alert(db, project, result)
            scored += 1
        except Exception:
            continue

    db.commit()
    log_action(db, current_user, "BATCH_SCORE", detail=f"scored={scored}",
               ip_address=request.client.host if request.client else None)
    return {"scored": scored, "message": f"Successfully scored {scored} projects"}


# ─── Global feature importance ────────────────────────────────────────────────────

@router.get("/feature-importance/global")
def global_feature_importance(current_user: CurrentUser):
    """Return global SHAP-based feature importance rankings."""
    return predictor.get_global_importance()


# ─── Model status ─────────────────────────────────────────────────────────────────

@router.get("/model/status", response_model=ModelStatus)
def model_status(current_user: CurrentUser):
    """
    Returns current model load state, metrics, and training provenance.
    Used by the dashboard to show model health.
    """
    metrics_path = os.path.join(MODELS_DIR, "model_metrics.json")
    loaded       = predictor._loaded

    if not os.path.exists(metrics_path):
        return ModelStatus(loaded=loaded, feature_count=len(predictor.feature_cols) if loaded else 0)

    with open(metrics_path) as f:
        m = json.load(f)

    return ModelStatus(
        loaded=loaded,
        accuracy=m.get("accuracy"),
        roc_auc=m.get("roc_auc"),
        f1_score=m.get("f1_score"),
        train_rows=m.get("train_rows"),
        trained_at=m.get("trained_at"),
        data_source=m.get("data_source", "csv"),
        feature_count=len(predictor.feature_cols) if loaded else 0,
    )


# ─── Retrain model ────────────────────────────────────────────────────────────────

@router.post("/model/retrain", response_model=RetrainResponse)
def retrain_model(
    request: Request,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """
    Trigger model retraining on current database contents.
    Central users only. Synchronous — waits for completion (~10-30s).

    After retraining:
    - New model file is saved to data/models/
    - Live predictor is hot-swapped in-process
    - All subsequent predictions use the new model immediately
    """
    if current_user.role != UserRole.CENTRAL:
        raise HTTPException(status_code=403, detail="Only central users can trigger retraining")

    from app.ml.trainer import retrain

    try:
        metrics = retrain(db=db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retraining failed: {str(e)}")

    log_action(
        db, current_user, "RETRAIN_MODEL",
        detail=f"roc_auc={metrics.get('roc_auc')},rows={metrics.get('train_rows')},source={metrics.get('data_source')}",
        ip_address=request.client.host if request.client else None,
    )

    return RetrainResponse(
        success=True,
        accuracy=metrics["accuracy"],
        roc_auc=metrics["roc_auc"],
        f1_score=metrics["f1_score"],
        train_rows=metrics["train_rows"],
        trained_at=metrics["trained_at"],
        data_source=metrics["data_source"],
        message=f"Model retrained successfully on {metrics['train_rows']} rows from {metrics['data_source']}. Live predictor updated.",
    )
