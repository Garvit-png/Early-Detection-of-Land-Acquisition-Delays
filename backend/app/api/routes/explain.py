"""
explain.py — AI Explanation endpoint.

POST /api/explain/{project_id}
  → fetches project + its latest ML scores from DB
  → retrieves relevant RAG chunks from the 4 SIH knowledge-base MD files
  → calls OpenAI GPT-4o-mini with grounded context
  → returns structured explanation: WHY / ACTIONS / LEGAL BASIS + source citations

Falls back to rule-based text if OPENAI_API_KEY is not set.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, get_db, log_action
from app.db.models import Project, UserRole
from app.services.openai_service import explain_project

router = APIRouter(prefix="/explain", tags=["AI Explanation"])


@router.post("/{project_id}")
def get_explanation(
    project_id: str,
    request: Request,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    """
    Generate an AI-grounded explanation for a project's risk score.

    Uses:
      - XGBoost SHAP factors (already stored on the project row)
      - Triggered rules R-01..R-08
      - RAG retrieval from SIH_Legal_Audit_Knowledge_Base.md,
        SIH_Stage_Admin_Knowledge_Base.md, SIH_Recommendation_Rules.md,
        SIH_Feature_Mapping.md
      - GPT-4o-mini to synthesize a natural-language explanation
        with LARR Act + CAG audit citations

    Returns:
      {
        project_id, risk_score, risk_category,
        why:          str  — why this risk score, citing KB records
        actions:      str  — 2-4 prioritized actions with rule IDs
        legal_basis:  str  — LARR/CAG grounding for top risk driver
        full_text:    str  — complete GPT response
        sources:      list — KB record IDs cited (e.g. ["R-01","CAG-02"])
        model_used:   str  — "gpt-4o-mini" or "rule-based-fallback"
        kb_chunks_used: int
        generated_at: str
      }
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

    if project.risk_score is None:
        raise HTTPException(
            status_code=400,
            detail="Project has not been scored yet. Run /api/predictions/{project_id} first.",
        )

    # Build project_data dict for the OpenAI service
    project_data = {
        "project_id":               project.project_id,
        "project_name":             project.project_name,
        "project_type":             project.project_type,
        "state":                    project.state,
        "district":                 project.district,
        "current_stage":            project.current_stage,
        "compensation_pct":         project.compensation_pct,
        "rr_completion_pct":        project.rr_completion_pct,
        "documentation_pct":        project.documentation_pct,
        "stakeholder_response_pct": project.stakeholder_response_pct,
        "num_legal_cases":          project.num_legal_cases,
        "ownership_conflicts":      project.ownership_conflicts,
        "has_legal_dispute":        project.has_legal_dispute,
        "award_overdue":            project.award_overdue,
        "days_since_last_action":   project.days_since_last_action,
        "days_since_update":        project.days_since_update,
        "officer_responsiveness":   project.officer_responsiveness,
        "budget_released":          project.budget_released,
        "possession_pct":           project.possession_pct,
        "compensation_pending_months": project.compensation_pending_months,
        "families_affected":        project.families_affected,
        "land_area_ha":             project.land_area_ha,
        # New FM-12/13/14 features
        "funding_readiness":        getattr(project, "funding_readiness",        None),
        "notice_delivery_pct":      getattr(project, "notice_delivery_pct",      None),
        "mutation_completion_pct":  getattr(project, "mutation_completion_pct",  None),
    }

    shap_factors    = project.shap_factors    or []
    rules_triggered = project.rules_triggered or []

    # ── Call OpenAI service (with RAG grounding) ──────────────────────────────
    result = explain_project(
        project_data         = project_data,
        shap_factors         = shap_factors,
        rules_triggered      = rules_triggered,
        risk_score           = project.risk_score,
        risk_category        = project.risk_category.value if project.risk_category else "Medium",
        expected_delay_label = project.expected_delay_label,
    )

    log_action(
        db, current_user, "EXPLAIN_PROJECT", "project", project_id,
        detail=f"model={result.get('model_used')},chunks={result.get('kb_chunks_used')}",
        ip_address=request.client.host if request.client else None,
    )

    return {
        "project_id":      project_id,
        "project_name":    project.project_name,
        "risk_score":      project.risk_score,
        "risk_category":   project.risk_category.value if project.risk_category else None,
        "rules_triggered": rules_triggered,
        "why":             result.get("why",         ""),
        "actions":         result.get("actions",     ""),
        "legal_basis":     result.get("legal_basis", ""),
        "full_text":       result.get("full_text",   ""),
        "sources":         result.get("sources",     []),
        "model_used":      result.get("model_used",  "rule-based-fallback"),
        "kb_chunks_used":  result.get("kb_chunks_used", 0),
        "tokens_used":     result.get("tokens_used", 0),
        "generated_at":    datetime.now(timezone.utc).isoformat(),
    }
