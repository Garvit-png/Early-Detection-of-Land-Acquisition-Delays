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
