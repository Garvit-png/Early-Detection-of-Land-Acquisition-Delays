"""
explain.py — AI Explanation endpoints.

POST /api/explain/{project_id}              — original: WHY / ACTIONS / LEGAL BASIS
POST /api/explain/{project_id}/stage-wise   — per-stage recommendations (all 6 stages)
POST /api/explain/{project_id}/overall      — comprehensive overall recommendation

All endpoints accept an optional X-OpenAI-Key header so the frontend
can supply its own API key in test mode (overrides the env var).
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional

from app.core.deps import CurrentUser, get_db, log_action
from app.db.models import Project, UserRole
from app.services.openai_service import explain_project, explain_stage_wise, explain_overall

router = APIRouter(prefix="/explain", tags=["AI Explanation"])


# ─── Shared helpers ───────────────────────────────────────────────────────────

def _get_project_or_404(project_id: str, current_user, db: Session) -> Project:
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
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
    return project


def _build_project_data(project: Project) -> dict:
    return {
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
        "funding_readiness":        getattr(project, "funding_readiness",        None),
        "notice_delivery_pct":      getattr(project, "notice_delivery_pct",      None),
        "mutation_completion_pct":  getattr(project, "mutation_completion_pct",  None),
    }


# ─── Original explain endpoint ────────────────────────────────────────────────

@router.post("/{project_id}")
def get_explanation(
    project_id: str,
    request: Request,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    x_openai_key: Optional[str] = Header(default=None, alias="X-OpenAI-Key"),
):
    project      = _get_project_or_404(project_id, current_user, db)
    project_data = _build_project_data(project)
    shap_factors    = project.shap_factors    or []
    rules_triggered = project.rules_triggered or []

    result = explain_project(
        project_data         = project_data,
        shap_factors         = shap_factors,
        rules_triggered      = rules_triggered,
        risk_score           = project.risk_score,
        risk_category        = project.risk_category.value if project.risk_category else "Medium",
        expected_delay_label = project.expected_delay_label,
    )

    # If frontend supplied a key and env key was empty, retry with frontend key
    if result.get("model_used") == "rule-based-fallback" and x_openai_key:
        import os
        old = os.environ.get("OPENAI_API_KEY", "")
        os.environ["OPENAI_API_KEY"] = x_openai_key
        result = explain_project(
            project_data=project_data, shap_factors=shap_factors,
            rules_triggered=rules_triggered, risk_score=project.risk_score,
            risk_category=project.risk_category.value if project.risk_category else "Medium",
            expected_delay_label=project.expected_delay_label,
        )
        os.environ["OPENAI_API_KEY"] = old

    log_action(db, current_user, "EXPLAIN_PROJECT", "project", project_id,
               detail=f"model={result.get('model_used')},chunks={result.get('kb_chunks_used')}",
               ip_address=request.client.host if request.client else None)

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


# ─── Per-stage recommendations ────────────────────────────────────────────────

@router.post("/{project_id}/stage-wise")
def get_stage_wise_explanation(
    project_id: str,
    request: Request,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    x_openai_key: Optional[str] = Header(default=None, alias="X-OpenAI-Key"),
):
    """
    Generate per-stage recommendations for all 6 acquisition stages.
    Pass X-OpenAI-Key header to use a custom API key (test mode).

    Returns:
      {
        project_id, project_name, risk_score, current_stage,
        stage_recommendations: [
          { stage_name, stage_index, relation (past/current/future),
            text, tokens_used, model_used }
          ... x6
        ],
        model_used, total_tokens, generated_at
      }
    """
    project         = _get_project_or_404(project_id, current_user, db)
    project_data    = _build_project_data(project)
    shap_factors    = project.shap_factors    or []
    rules_triggered = project.rules_triggered or []

    result = explain_stage_wise(
        project_data    = project_data,
        shap_factors    = shap_factors,
        rules_triggered = rules_triggered,
        risk_score      = project.risk_score,
        risk_category   = project.risk_category.value if project.risk_category else "Medium",
        api_key         = x_openai_key,
    )

    log_action(db, current_user, "EXPLAIN_STAGE_WISE", "project", project_id,
               detail=f"model={result.get('model_used')},tokens={result.get('total_tokens')}",
               ip_address=request.client.host if request.client else None)

    return {
        "project_id":            project_id,
        "project_name":          project.project_name,
        "risk_score":            project.risk_score,
        "risk_category":         project.risk_category.value if project.risk_category else None,
        "current_stage":         project.current_stage,
        "stage_recommendations": result.get("stage_recommendations", []),
        "model_used":            result.get("model_used", "rule-based-fallback"),
        "total_tokens":          result.get("total_tokens", 0),
        "generated_at":          datetime.now(timezone.utc).isoformat(),
    }


# ─── Overall recommendations ──────────────────────────────────────────────────

@router.post("/{project_id}/overall")
def get_overall_explanation(
    project_id: str,
    request: Request,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    x_openai_key: Optional[str] = Header(default=None, alias="X-OpenAI-Key"),
):
    """
    Generate a comprehensive overall recommendation.
    Pass X-OpenAI-Key header to use a custom API key (test mode).

    Returns:
      {
        project_id, project_name, risk_score, risk_category,
        summary, critical_actions, bottlenecks, outlook,
        full_text, model_used, tokens_used, generated_at
      }
    """
    project         = _get_project_or_404(project_id, current_user, db)
    project_data    = _build_project_data(project)
    shap_factors    = project.shap_factors    or []
    rules_triggered = project.rules_triggered or []

    result = explain_overall(
        project_data         = project_data,
        shap_factors         = shap_factors,
        rules_triggered      = rules_triggered,
        risk_score           = project.risk_score,
        risk_category        = project.risk_category.value if project.risk_category else "Medium",
        expected_delay_label = project.expected_delay_label,
        api_key              = x_openai_key,
    )

    log_action(db, current_user, "EXPLAIN_OVERALL", "project", project_id,
               detail=f"model={result.get('model_used')},tokens={result.get('tokens_used')}",
               ip_address=request.client.host if request.client else None)

    return {
        "project_id":       project_id,
        "project_name":     project.project_name,
        "risk_score":       project.risk_score,
        "risk_category":    project.risk_category.value if project.risk_category else None,
        "rules_triggered":  rules_triggered,
        "summary":          result.get("summary",          ""),
        "critical_actions": result.get("critical_actions", ""),
        "bottlenecks":      result.get("bottlenecks",      ""),
        "outlook":          result.get("outlook",          ""),
        "full_text":        result.get("full_text",        ""),
        "model_used":       result.get("model_used",       "rule-based-fallback"),
        "tokens_used":      result.get("tokens_used",      0),
        "generated_at":     datetime.now(timezone.utc).isoformat(),
    }


# ─── Project-aware Chat endpoint ─────────────────────────────────────────────

from pydantic import BaseModel

class ChatMessage(BaseModel):
    role: str   # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []   # previous turns sent from frontend


CHAT_SYSTEM_PROMPT = """You are an expert advisor on Indian land acquisition law (LARR Act 2013), \
infrastructure project governance, and CAG audit findings.

You have been given full details of a specific land acquisition project. \
Your job is to help the government officer understand the project's risks, \
recommend actions, answer questions, and provide grounded advice.

Rules:
1. Always ground your answers in the project data provided in the system context.
2. Cite rule IDs [R-01..R-08] and KB references [LARR-xx], [CAG-xx] where relevant.
3. Be concise and practical — the user is a district/state government officer.
4. If asked something not related to this project or land acquisition, \
   politely redirect to the project.
5. Never invent data — only use what is in the project context below.
"""


def _build_chat_system_context(project: "Project") -> str:
    """Build a rich system message with full project details for the chat."""
    p = project
    rules = p.rules_triggered or []
    shap  = p.shap_factors    or []
    recs  = p.recommendations or []

    top_shap = "\n".join(
        f"  - {f['display_name']}: {f['shap_value']:+.3f} ({f['direction'].replace('_',' ')})"
        for f in shap[:6]
    ) or "  N/A"

    top_recs = "\n".join(f"  {i+1}. {r}" for i, r in enumerate(recs[:4])) or "  None"

    return f"""=== PROJECT CONTEXT ===
ID: {p.project_id} | Name: {p.project_name}
Type: {p.project_type} | State: {p.state} | District: {p.district}
Current Stage: {p.current_stage} (index {p.current_stage_index})
Start Date: {p.start_date}

RISK ASSESSMENT:
  Risk Score: {p.risk_score}/100 | Category: {p.risk_category.value if p.risk_category else 'N/A'}
  Delay Probability: {round((p.delay_probability or 0)*100, 1)}%
  Expected Delay: {p.expected_delay_label or 'Not computed'}
  Rules Triggered: {', '.join(rules) or 'None'}

KEY METRICS:
  Compensation disbursed: {p.compensation_pct}%
  R&R completion: {p.rr_completion_pct}%
  Documentation: {p.documentation_pct}%
  Stakeholder response: {p.stakeholder_response_pct}%
  Possession: {p.possession_pct}%
  Funding readiness: {p.funding_readiness}%
  Notice delivery: {p.notice_delivery_pct}%
  Mutation completion: {p.mutation_completion_pct}%

LEGAL STATUS:
  Legal dispute: {'Yes' if p.has_legal_dispute else 'No'}
  Legal cases: {p.num_legal_cases}
  Ownership conflicts: {p.ownership_conflicts}
  Award overdue: {'Yes' if p.award_overdue else 'No'}

TIMELINE:
  Days in current stage: {p.days_in_current_stage}
  Days since last action: {p.days_since_last_action}
  Days since system update: {p.days_since_update}
  Pending approvals: {p.pending_approvals}
  NOC pending: {p.noc_pending_count}

FINANCIAL:
  Land cost: ₹{p.land_cost_cr} Cr | Amount paid: ₹{p.amount_paid_cr} Cr
  Project value: ₹{p.project_value_cr} Cr | Budget released: {p.budget_released}
  Compensation pending: {p.compensation_pending_months} months

CONTEXT:
  District historical delay rate: {p.district_historical_delay_rate}
  Officer responsiveness: {p.officer_responsiveness}/10
  Land area: {p.land_area_ha} ha | Families affected: {p.families_affected}

TOP SHAP RISK DRIVERS:
{top_shap}

AI RECOMMENDATIONS ALREADY GENERATED:
{top_recs}
=== END PROJECT CONTEXT ==="""


@router.post("/{project_id}/chat")
def chat_with_project(
    project_id: str,
    body: ChatRequest,
    request: Request,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
    x_openai_key: Optional[str] = Header(default=None, alias="X-OpenAI-Key"),
    x_ai_provider: Optional[str] = Header(default="openai", alias="X-AI-Provider"),
):
    """
    Project-aware chat endpoint.
    - Loads full project data as system context
    - Accepts message history from frontend (stateless on backend)
    - Provider: openai | nvidia | openrouter (via X-AI-Provider header)
    - API key via X-OpenAI-Key header or env var

    Request body:
      { message: str, history: [{role, content}, ...] }

    Returns:
      { reply: str, model_used: str, tokens_used: int }
    """
    import os
    from openai import OpenAI as _OAI
    from app.services.openai_service import PROVIDERS, _make_client

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

    resolved_key = (x_openai_key or "").strip() or os.getenv(
        PROVIDERS.get(x_ai_provider or "openai", PROVIDERS["openai"])["env_key"], ""
    )

    # ── Fallback: no API key ──────────────────────────────────────────────────
    if not resolved_key:
        rules = project.rules_triggered or []
        recs  = project.recommendations or []
        fallback = (
            f"**{project.project_name}** ({project.project_id}) — "
            f"Risk: **{project.risk_score}/100** ({project.risk_category.value if project.risk_category else 'N/A'})\n\n"
        )
        if rules:
            fallback += f"**Triggered rules:** {', '.join(rules)}\n\n"
        if recs:
            fallback += "**Top recommendations:**\n" + "\n".join(f"{i+1}. {r}" for i, r in enumerate(recs[:3]))
        fallback += "\n\n*(Set your OpenAI API key above for full conversational AI analysis.)*"
        return {"reply": fallback, "model_used": "rule-based-fallback", "tokens_used": 0}

    # ── Build messages ────────────────────────────────────────────────────────
    project_context = _build_chat_system_context(project)
    system_msg = CHAT_SYSTEM_PROMPT + "\n\n" + project_context

    messages = [{"role": "system", "content": system_msg}]

    # Add conversation history (max last 20 turns to stay within context)
    for turn in body.history[-20:]:
        messages.append({"role": turn.role, "content": turn.content})

    # Add current user message
    messages.append({"role": "user", "content": body.message})

    try:
        client, model = _make_client(x_ai_provider or "openai", resolved_key)
        if not client:
            raise HTTPException(status_code=400, detail="Could not initialize AI client")
        response = client.chat.completions.create(
            model       = model,
            messages    = messages,
            temperature = 0.3,
            max_tokens  = 500,
            timeout     = 30,
        )
        reply  = response.choices[0].message.content.strip()
        tokens = response.usage.total_tokens if response.usage else 0

        log_action(db, current_user, "CHAT_PROJECT", "project", project_id,
                   detail=f"tokens={tokens}",
                   ip_address=request.client.host if request.client else None)

        return {"reply": reply, "model_used": "gpt-4o-mini", "tokens_used": tokens}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI chat failed: {str(e)}")
