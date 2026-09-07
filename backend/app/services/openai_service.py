"""
openai_service.py — AI Explanation Brain

Uses GPT-4o-mini (cost-efficient) with RAG context from the 4 SIH knowledge-base
files to generate grounded, citable explanations for each project's risk score.

Architecture:
  XGBoost  →  risk score + SHAP top factors       (prediction brain)
  This     →  natural-language explanation         (explanation brain)
                grounded in LARR Act + CAG audits  (RAG knowledge base)
                with actionable recommendations
                citing rule IDs (R-01..R-08)

Falls back gracefully to rule-based text if:
  - OPENAI_API_KEY is not set
  - API call fails / times out
  - Rate limit hit
"""

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# ─── Try to import openai (v1.x) ─────────────────────────────────────────────
try:
    from openai import OpenAI
    _OPENAI_AVAILABLE = True
except ImportError:
    _OPENAI_AVAILABLE = False
    logger.warning("openai package not available — using fallback recommendations")

from app.services.rag_kb import (
    get_chunks_for_rules,
    get_chunks_for_stage,
    get_rule_summary,
    chunks_to_context,
)

# ─── System prompt ────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an expert advisor on Indian land acquisition law and infrastructure project governance.
You help government officials understand why a land acquisition project is at risk of delay, 
citing specific provisions of the LARR Act 2013 and findings from CAG audit reports.

Rules:
1. Be concise and factual. No fluff.
2. Always cite the knowledge-base record IDs provided (e.g. [CAG-02], [LARR-11], [R-01]).
3. Structure your response in exactly 3 sections:
   - WHY: What factors are driving the risk score, grounded in the KB context provided.
   - ACTIONS: 2-4 specific, prioritized actions the officer should take, referencing rule IDs.
   - LEGAL BASIS: Relevant LARR Act provision or CAG audit finding for the top risk driver.
4. Keep total response under 350 words.
5. Use plain language — the reader is a district/state government officer, not a lawyer.
6. Do NOT invent facts. Only use what is in the project data and KB context provided.
"""

# ─── Fallback (no API key) ─────────────────────────────────────────────────────
def _rule_fallback(project_data: dict, rules_triggered: list[str]) -> dict:
    """Rule-based explanation when OpenAI is unavailable."""
    from app.services.rag_kb import _load_all_chunks
    chunks = _load_all_chunks()

    why_parts     = []
    action_parts  = []
    legal_parts   = []

    for rid in rules_triggered[:4]:
        c = chunks.get(rid)
        if c:
            why_parts.append(f"[{rid}] {c.topic}: {c.fact}")
            action_parts.append(f"[{rid}] {c.action}")

    # Legal basis from top rule
    top_rule = rules_triggered[0] if rules_triggered else None
    if top_rule:
        for prefix in ["LARR", "CAG"]:
            for cid, c in chunks.items():
                if cid.startswith(prefix) and top_rule.replace("R-", "").lower() in c.fact.lower():
                    legal_parts.append(f"[{cid}] {c.source}: {c.fact[:200]}")
                    break

    return {
        "why":         "\n".join(why_parts)    or "Risk driven by multiple delay factors detected in project data.",
        "actions":     "\n".join(action_parts) or "Review flagged fields and escalate to responsible officer.",
        "legal_basis": "\n".join(legal_parts)  or "Refer to LARR Act 2013 and applicable CAG audit findings.",
        "sources":     rules_triggered,
        "model_used":  "rule-based-fallback",
        "kb_chunks_used": len(why_parts),
    }


# ─── Main explanation function ─────────────────────────────────────────────────
def explain_project(
    project_data: dict[str, Any],
    shap_factors: list[dict],
    rules_triggered: list[str],
    risk_score: float,
    risk_category: str,
    expected_delay_label: str | None = None,
) -> dict:
    """
    Generate a grounded AI explanation for a project's risk.

    Returns:
      {
        why:           str,   # risk drivers explained with KB citations
        actions:       str,   # prioritized recommended actions
        legal_basis:   str,   # LARR/CAG grounding
        sources:       list,  # record IDs cited
        model_used:    str,   # "gpt-4o-mini" or "rule-based-fallback"
        kb_chunks_used: int,
      }
    """
    api_key = os.getenv("OPENAI_API_KEY", "").strip()

    # Graceful fallback if key missing or openai not installed
    if not api_key or not _OPENAI_AVAILABLE:
        logger.info("OpenAI key not set — using rule-based fallback")
        return _rule_fallback(project_data, rules_triggered)

    # ── Retrieve relevant KB chunks ───────────────────────────────────────────
    rule_chunks  = get_chunks_for_rules(rules_triggered)
    stage        = project_data.get("current_stage", "")
    stage_chunks = get_chunks_for_stage(stage)
    all_chunks   = rule_chunks + [c for c in stage_chunks if c not in rule_chunks]
    kb_context   = chunks_to_context(all_chunks[:14])

    # ── Build project summary for prompt ─────────────────────────────────────
    top_shap = [
        f"{f['display_name']}: {f['shap_value']:+.3f} ({f['direction'].replace('_',' ')})"
        for f in (shap_factors or [])[:5]
    ]

    project_summary = f"""
Project: {project_data.get('project_name', 'Unknown')} ({project_data.get('project_id', '')})
Type: {project_data.get('project_type', '')} | State: {project_data.get('state', '')} | District: {project_data.get('district', '')}
Current Stage: {stage}
Risk Score: {risk_score}/100 ({risk_category} Risk)
Expected Delay: {expected_delay_label or 'Not computed'}

Key Metrics:
- Compensation disbursed: {project_data.get('compensation_pct', 'N/A')}%
- R&R completion: {project_data.get('rr_completion_pct', 'N/A')}%
- Documentation: {project_data.get('documentation_pct', 'N/A')}%
- Stakeholder response: {project_data.get('stakeholder_response_pct', 'N/A')}%
- Legal cases: {project_data.get('num_legal_cases', 0)}, Ownership conflicts: {project_data.get('ownership_conflicts', 0)}
- Days since last action: {project_data.get('days_since_last_action', 0)}
- Days since system update: {project_data.get('days_since_update', 0)}
- Officer responsiveness: {project_data.get('officer_responsiveness', 'N/A')}/10
- Budget released: {project_data.get('budget_released', 'N/A')}
- Award overdue: {project_data.get('award_overdue', False)}

Rules triggered: {', '.join(rules_triggered) or 'None'}

Top SHAP risk drivers:
{chr(10).join(top_shap) or 'N/A'}
""".strip()

    user_prompt = f"""
KNOWLEDGE BASE CONTEXT (cite record IDs in your response):
{kb_context}

RULE DEFINITIONS:
{get_rule_summary()}

PROJECT DATA:
{project_summary}

Generate the explanation now using the 3-section format (WHY / ACTIONS / LEGAL BASIS).
""".strip()

    # ── Call OpenAI ────────────────────────────────────────────────────────────
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=600,
            timeout=30,
        )
        raw = response.choices[0].message.content.strip()

        # Parse sections
        sections = _parse_sections(raw)

        # Extract cited record IDs
        cited_ids = list(set(
            m.strip("[]")
            for m in __import__("re").findall(r"\[(?:R-\d{2}|LARR-\d+|CAG-\d+|FM-\d+|LIFE-\d+|ADMIN-\d+)\]", raw)
        ))

        return {
            "why":           sections.get("WHY",         raw),
            "actions":       sections.get("ACTIONS",     ""),
            "legal_basis":   sections.get("LEGAL BASIS", ""),
            "full_text":     raw,
            "sources":       cited_ids or rules_triggered,
            "model_used":    "gpt-4o-mini",
            "kb_chunks_used": len(all_chunks),
            "tokens_used":   response.usage.total_tokens if response.usage else 0,
        }

    except Exception as e:
        logger.error(f"OpenAI call failed: {e} — falling back to rule-based")
        return _rule_fallback(project_data, rules_triggered)


def _parse_sections(text: str) -> dict[str, str]:
    """Extract WHY / ACTIONS / LEGAL BASIS sections from GPT response."""
    import re
    sections = {}
    pattern  = re.compile(
        r"(?:^|\n)\s*(?:\*\*)?("
        r"WHY|ACTIONS?|LEGAL\s+BASIS"
        r")(?:\*\*)?\s*[:\-]?\s*\n(.*?)(?=\n\s*(?:\*\*)?(?:WHY|ACTIONS?|LEGAL\s+BASIS)|\Z)",
        re.IGNORECASE | re.DOTALL,
    )
    for m in pattern.finditer(text):
        key   = m.group(1).strip().upper().replace("ACTION", "ACTIONS")
        value = m.group(2).strip()
        sections[key] = value
    return sections


# ─── Stage-wise + Overall Recommendations ────────────────────────────────────

STAGES = [
    "Section 11 Notification",
    "Section 19 Declaration",
    "Award Passed",
    "Compensation Disbursed",
    "Possession Taken",
    "R&R Completed",
]

STAGE_SYSTEM_PROMPT = """You are an expert on Indian land acquisition law (LARR Act 2013) and infrastructure project governance.
Given project data and the current acquisition stage, generate stage-specific recommendations.

Rules:
1. Be concise and actionable. Max 200 words per stage.
2. Cite rule IDs [R-01..R-08] and KB records [LARR-xx], [CAG-xx] where relevant.
3. Structure: STATUS (1 line: on-track/delayed/critical) | BLOCKERS (key issues) | ACTIONS (2-3 specific steps)
4. Only comment on stages relevant to the project's current position — past stages: summarize completion; future stages: flag pre-requisites.
5. Use plain language for district/state government officers.
"""

OVERALL_SYSTEM_PROMPT = """You are an expert on Indian land acquisition law (LARR Act 2013) and infrastructure project governance.
Generate a comprehensive overall recommendation for a land acquisition project.

Rules:
1. Max 400 words total.
2. Cite rule IDs [R-01..R-08] and KB records where relevant.
3. Structure in exactly 4 sections:
   - SUMMARY: 2-line executive summary of project status
   - CRITICAL ACTIONS: Top 3 immediate actions (numbered, priority order)
   - BOTTLENECKS: Key systemic issues causing delays
   - OUTLOOK: Expected timeline and risk trajectory if actions taken vs not taken
4. Use plain language for district/state government officers.
"""


def explain_stage_wise(
    project_data: dict,
    shap_factors: list,
    rules_triggered: list,
    risk_score: float,
    risk_category: str,
    api_key: str | None = None,
) -> dict:
    """
    Generate per-stage recommendations for all 6 acquisition stages.
    api_key: if provided by frontend (test mode), use it; else fall back to env var.
    """
    resolved_key = (api_key or "").strip() or os.getenv("OPENAI_API_KEY", "").strip()

    if not resolved_key or not _OPENAI_AVAILABLE:
        return _stage_fallback(project_data, rules_triggered)

    current_stage = project_data.get("current_stage", "")
    current_idx   = STAGES.index(current_stage) if current_stage in STAGES else 0

    stage_results = []

    for idx, stage in enumerate(STAGES):
        rel = "past" if idx < current_idx else ("current" if idx == current_idx else "future")

        # Get relevant KB chunks for this stage
        stage_chunks = get_chunks_for_stage(stage)
        rule_chunks  = get_chunks_for_rules(rules_triggered) if rel == "current" else []
        all_chunks   = stage_chunks + [c for c in rule_chunks if c not in stage_chunks]
        kb_ctx       = chunks_to_context(all_chunks[:8])

        user_prompt = f"""
STAGE: {stage} (Stage {idx+1}/6) — Status relative to project: {rel.upper()}
CURRENT STAGE OF PROJECT: {current_stage}

PROJECT METRICS:
- Risk Score: {risk_score}/100 ({risk_category})
- Compensation: {project_data.get('compensation_pct', 'N/A')}%
- R&R completion: {project_data.get('rr_completion_pct', 'N/A')}%
- Documentation: {project_data.get('documentation_pct', 'N/A')}%
- Stakeholder response: {project_data.get('stakeholder_response_pct', 'N/A')}%
- Legal cases: {project_data.get('num_legal_cases', 0)}, Ownership conflicts: {project_data.get('ownership_conflicts', 0)}
- Days since last action: {project_data.get('days_since_last_action', 0)}
- Award overdue: {project_data.get('award_overdue', False)}
- Rules triggered: {', '.join(rules_triggered) or 'None'}

KNOWLEDGE BASE CONTEXT:
{kb_ctx}

Generate stage-specific recommendation for "{stage}" using STATUS | BLOCKERS | ACTIONS format.
""".strip()

        try:
            client   = OpenAI(api_key=resolved_key)
            response = client.chat.completions.create(
                model       = "gpt-4o-mini",
                messages    = [
                    {"role": "system", "content": STAGE_SYSTEM_PROMPT},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature = 0.2,
                max_tokens  = 300,
                timeout     = 20,
            )
            text   = response.choices[0].message.content.strip()
            tokens = response.usage.total_tokens if response.usage else 0
            stage_results.append({
                "stage_name":   stage,
                "stage_index":  idx,
                "relation":     rel,
                "text":         text,
                "tokens_used":  tokens,
                "model_used":   "gpt-4o-mini",
            })
        except Exception as e:
            logger.error(f"Stage explain failed for {stage}: {e}")
            stage_results.append({
                "stage_name":  stage,
                "stage_index": idx,
                "relation":    rel,
                "text":        _stage_fallback_single(stage, rel, project_data, rules_triggered),
                "tokens_used": 0,
                "model_used":  "rule-based-fallback",
            })

    return {
        "stage_recommendations": stage_results,
        "model_used":  "gpt-4o-mini",
        "total_tokens": sum(s["tokens_used"] for s in stage_results),
    }


def explain_overall(
    project_data: dict,
    shap_factors: list,
    rules_triggered: list,
    risk_score: float,
    risk_category: str,
    expected_delay_label: str | None = None,
    api_key: str | None = None,
) -> dict:
    """
    Generate a comprehensive overall recommendation.
    api_key: if provided by frontend (test mode), use it; else fall back to env var.
    """
    resolved_key = (api_key or "").strip() or os.getenv("OPENAI_API_KEY", "").strip()

    if not resolved_key or not _OPENAI_AVAILABLE:
        return _overall_fallback(project_data, rules_triggered)

    rule_chunks  = get_chunks_for_rules(rules_triggered)
    stage        = project_data.get("current_stage", "")
    stage_chunks = get_chunks_for_stage(stage)
    all_chunks   = rule_chunks + [c for c in stage_chunks if c not in rule_chunks]
    kb_ctx       = chunks_to_context(all_chunks[:14])

    top_shap = [
        f"{f['display_name']}: {f['shap_value']:+.3f} ({f['direction'].replace('_',' ')})"
        for f in (shap_factors or [])[:5]
    ]

    user_prompt = f"""
PROJECT: {project_data.get('project_name')} ({project_data.get('project_id')})
Type: {project_data.get('project_type')} | State: {project_data.get('state')} | District: {project_data.get('district')}
Current Stage: {stage} | Risk: {risk_score}/100 ({risk_category})
Expected Delay: {expected_delay_label or 'Not computed'}

KEY METRICS:
- Compensation: {project_data.get('compensation_pct')}% | R&R: {project_data.get('rr_completion_pct')}%
- Documentation: {project_data.get('documentation_pct')}% | Stakeholder: {project_data.get('stakeholder_response_pct')}%
- Legal cases: {project_data.get('num_legal_cases', 0)}, Ownership conflicts: {project_data.get('ownership_conflicts', 0)}
- Days since action: {project_data.get('days_since_last_action', 0)} | Budget released: {project_data.get('budget_released')}
- Award overdue: {project_data.get('award_overdue', False)}
- Rules triggered: {', '.join(rules_triggered) or 'None'}

TOP SHAP RISK DRIVERS:
{chr(10).join(top_shap) or 'N/A'}

KNOWLEDGE BASE CONTEXT:
{kb_ctx}

{get_rule_summary()}

Generate comprehensive overall recommendation using SUMMARY | CRITICAL ACTIONS | BOTTLENECKS | OUTLOOK format.
""".strip()

    try:
        client   = OpenAI(api_key=resolved_key)
        response = client.chat.completions.create(
            model       = "gpt-4o-mini",
            messages    = [
                {"role": "system", "content": OVERALL_SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            temperature = 0.2,
            max_tokens  = 600,
            timeout     = 30,
        )
        raw    = response.choices[0].message.content.strip()
        tokens = response.usage.total_tokens if response.usage else 0

        sections = _parse_overall_sections(raw)
        return {
            "summary":          sections.get("SUMMARY", raw),
            "critical_actions": sections.get("CRITICAL ACTIONS", ""),
            "bottlenecks":      sections.get("BOTTLENECKS", ""),
            "outlook":          sections.get("OUTLOOK", ""),
            "full_text":        raw,
            "model_used":       "gpt-4o-mini",
            "tokens_used":      tokens,
        }
    except Exception as e:
        logger.error(f"Overall explain failed: {e}")
        return _overall_fallback(project_data, rules_triggered)


def _parse_overall_sections(text: str) -> dict:
    import re
    sections = {}
    pattern  = re.compile(
        r"(?:^|\n)\s*(?:\*\*)?("
        r"SUMMARY|CRITICAL\s+ACTIONS?|BOTTLENECKS?|OUTLOOK"
        r")(?:\*\*)?\s*[:\-]?\s*\n(.*?)(?=\n\s*(?:\*\*)?(?:SUMMARY|CRITICAL\s+ACTIONS?|BOTTLENECKS?|OUTLOOK)|\Z)",
        re.IGNORECASE | re.DOTALL,
    )
    for m in pattern.finditer(text):
        key   = m.group(1).strip().upper()
        key   = key.replace("CRITICAL ACTION", "CRITICAL ACTIONS").replace("BOTTLENECK", "BOTTLENECKS")
        value = m.group(2).strip()
        sections[key] = value
    return sections


def _stage_fallback_single(stage: str, rel: str, project_data: dict, rules: list) -> str:
    if rel == "past":
        return f"STATUS: Completed\nBLOCKERS: Stage passed\nACTIONS: Review records and ensure documentation is archived."
    elif rel == "future":
        prereqs = {
            "Award Passed":          "Ensure Section 19 declaration is notified. Verify all survey records.",
            "Compensation Disbursed":"Award must be passed. Verify bank details for all affected families.",
            "Possession Taken":      "Compensation must reach 80%+ before possession. Check R&R readiness.",
            "R&R Completed":         "Possession must be handed over. Ensure R&R colony/allotment is ready.",
        }
        return f"STATUS: Not yet reached\nBLOCKERS: Pre-requisites pending\nACTIONS: {prereqs.get(stage, 'Complete current stage milestones first.')}"
    else:
        issues = []
        if project_data.get("compensation_pct", 100) < 50: issues.append("[R-01] Compensation below 50%")
        if project_data.get("rr_completion_pct", 100) < 50: issues.append("[R-02] R&R below 50%")
        if project_data.get("num_legal_cases", 0) >= 3: issues.append("[R-03] Multiple legal cases")
        if project_data.get("award_overdue", False): issues.append("[R-06] Award overdue")
        status = "CRITICAL" if len(issues) >= 2 else ("DELAYED" if issues else "ON TRACK")
        return f"STATUS: {status}\nBLOCKERS: {'; '.join(issues) or 'None detected'}\nACTIONS: Address flagged rules and update system records."


def _stage_fallback(project_data: dict, rules: list) -> dict:
    current_stage = project_data.get("current_stage", "")
    current_idx   = STAGES.index(current_stage) if current_stage in STAGES else 0
    results = []
    for idx, stage in enumerate(STAGES):
        rel = "past" if idx < current_idx else ("current" if idx == current_idx else "future")
        results.append({
            "stage_name":  stage, "stage_index": idx, "relation": rel,
            "text":        _stage_fallback_single(stage, rel, project_data, rules),
            "tokens_used": 0, "model_used": "rule-based-fallback",
        })
    return {"stage_recommendations": results, "model_used": "rule-based-fallback", "total_tokens": 0}


def _overall_fallback(project_data: dict, rules: list) -> dict:
    issues = []
    if project_data.get("compensation_pct", 100) < 50:
        issues.append("[R-01] Compensation below 50% — disbursement blocked")
    if project_data.get("rr_completion_pct", 100) < 50:
        issues.append("[R-02] R&R completion below 50%")
    if project_data.get("num_legal_cases", 0) >= 3:
        issues.append("[R-03] Multiple legal disputes unresolved")
    if project_data.get("award_overdue", False):
        issues.append("[R-06] Award milestone overdue")
    return {
        "summary":          f"Project {project_data.get('project_id')} is at risk. {len(issues)} critical rule(s) triggered.",
        "critical_actions": "\n".join(f"{i+1}. {issue}" for i, issue in enumerate(issues[:3])) or "1. Review all pending milestones and update system records.",
        "bottlenecks":      "Compensation disbursement, legal disputes, and documentation gaps are the primary bottlenecks.",
        "outlook":          "Without intervention, further delays are likely. Immediate escalation recommended.",
        "full_text":        "",
        "model_used":       "rule-based-fallback",
        "tokens_used":      0,
    }
