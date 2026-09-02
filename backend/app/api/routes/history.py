"""
history.py — Risk history + similar projects endpoints.
Implements: Risk History chart, Similar Projects + GIS, Model Evaluation nodes.
"""

import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db, log_action
from app.db.models import Project, RiskHistory, RiskCategory, UserRole
from app.schemas.schemas import RiskHistoryItem, SimilarProject, PaginatedResponse

router = APIRouter(prefix="/history", tags=["History & Similar"])


# ─── GET /history/{project_id} — time-series risk snapshots ──────────────────

@router.get("/{project_id}", response_model=list[RiskHistoryItem])
def get_risk_history(
    project_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
):
    """
    Returns all risk score snapshots for a project in chronological order.
    Feeds the Risk History chart in the EXISTING PROJECT flow.
    """
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

    snapshots = (
        db.query(RiskHistory)
        .filter(RiskHistory.project_id_fk == project.id)
        .order_by(RiskHistory.scored_at.asc())
        .limit(limit)
        .all()
    )

    return [
        RiskHistoryItem(
            id               = s.id,
            risk_score       = s.risk_score,
            delay_probability= s.delay_probability,
            risk_category    = s.risk_category.value if s.risk_category else "Medium",
            rules_triggered  = s.rules_triggered or [],
            trigger          = s.trigger,
            notes            = s.notes,
            scored_at        = s.scored_at,
        )
        for s in snapshots
    ]


# ─── GET /history/{project_id}/similar — similar projects ────────────────────

@router.get("/{project_id}/similar", response_model=list[SimilarProject])
def get_similar_projects(
    project_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    top_n: int = Query(default=5, ge=1, le=20),
):
    """
    Returns top-N projects most similar to the given project.
    Similarity computed from matching: project_type, risk_category, stage,
    and closeness of key numeric features.

    Feeds: Similar Projects + GIS node in the flow.
    """
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # RBAC — similar projects can be broader (central sees all)
    candidates_q = (
        db.query(Project)
        .filter(
            Project.id != project.id,
            Project.risk_score.isnot(None),
        )
    )
    if current_user.role == UserRole.STATE:
        candidates_q = candidates_q.filter(Project.state == current_user.state)

    candidates = candidates_q.limit(2000).all()

    def similarity(p: Project) -> float:
        score = 0.0
        # Type match (highest weight)
        if p.project_type == project.project_type:
            score += 0.25
        # Risk category match
        if p.risk_category == project.risk_category:
            score += 0.15
        # Stage match
        if p.current_stage == project.current_stage:
            score += 0.10
        # Numeric proximity (normalized diff, each max 0.1)
        def numeric_sim(a, b, scale):
            if a is None or b is None:
                return 0.05
            return max(0, 0.1 - abs(a - b) / scale * 0.1)
        score += numeric_sim(p.compensation_pct,  project.compensation_pct,  100)
        score += numeric_sim(p.rr_completion_pct,  project.rr_completion_pct, 100)
        score += numeric_sim(p.risk_score,          project.risk_score,        100)
        score += numeric_sim(p.land_area_ha,        project.land_area_ha,      2000)
        score += numeric_sim(p.families_affected,   project.families_affected, 5000)
        score += numeric_sim(p.delay_probability,   project.delay_probability, 1.0)
        # Same state bonus
        if p.state == project.state:
            score += 0.05
        return round(min(score, 1.0), 3)

    scored = [(p, similarity(p)) for p in candidates]
    scored.sort(key=lambda x: x[1], reverse=True)

    return [
        SimilarProject(
            project_id        = p.project_id,
            project_name      = p.project_name,
            project_type      = p.project_type,
            state             = p.state,
            district          = p.district,
            risk_score        = p.risk_score,
            risk_category     = p.risk_category.value if p.risk_category else None,
            delay_probability = p.delay_probability,
            compensation_pct  = p.compensation_pct,
            is_delayed        = p.is_delayed,
            similarity_score  = sim,
        )
        for p, sim in scored[:top_n]
    ]
