"""
rag_kb.py — RAG Knowledge Base
Parses the 4 SIH markdown files into retrievable chunks.
No external vector DB needed — uses keyword + rule-ID matching for fast retrieval.
Falls back gracefully if files are missing.

Knowledge sources:
  - SIH_Feature_Mapping.md          (FM-01 to FM-14)
  - SIH_Legal_Audit_Knowledge_Base.md (LARR-01..15, CAG-01..18)
  - SIH_Recommendation_Rules.md     (R-01 to R-08)
  - SIH_Stage_Admin_Knowledge_Base.md (LIFE-01..10, ADMIN-01..10)
"""

import os
import re
from functools import lru_cache
from typing import Optional

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../..")
)

KB_FILES = {
    "feature_mapping":   "SIH_Feature_Mapping.md",
    "legal_audit":       "SIH_Legal_Audit_Knowledge_Base.md",
    "recommendation":    "SIH_Recommendation_Rules.md",
    "stage_admin":       "SIH_Stage_Admin_Knowledge_Base.md",
}

# ─── Rule → feature mapping ────────────────────────────────────────────────────
RULE_FEATURE_MAP = {
    "R-01": ["compensation_pct", "compensation_pending_months", "amount_paid_cr"],
    "R-02": ["rr_completion_pct"],
    "R-03": ["num_legal_cases", "ownership_conflicts", "has_legal_dispute"],
    "R-04": ["documentation_pct"],
    "R-05": ["stakeholder_response_pct"],
    "R-06": ["award_overdue", "days_in_current_stage", "current_stage"],
    "R-07": ["possession_pct", "compensation_pct"],
    "R-08": ["days_since_update", "officer_responsiveness", "days_since_last_action"],
}

# ─── Stage → KB record IDs ─────────────────────────────────────────────────────
STAGE_KB_MAP = {
    "Section 11 Notification":  ["LIFE-03", "LARR-03", "ADMIN-04"],
    "Section 19 Declaration":   ["LIFE-05", "LARR-05", "ADMIN-01"],
    "Award Passed":             ["LIFE-06", "LARR-08", "CAG-05", "CAG-06", "ADMIN-03"],
    "Compensation Disbursed":   ["LIFE-07", "LARR-09", "CAG-02", "CAG-03", "ADMIN-03"],
    "Possession Taken":         ["LIFE-09", "LARR-11", "CAG-14"],
    "R&R Completed":            ["LIFE-08", "LARR-06", "LARR-07", "LARR-10"],
}


class KBChunk:
    def __init__(self, record_id: str, source: str, topic: str,
                 fact: str, action: str, url: str = ""):
        self.record_id = record_id
        self.source    = source
        self.topic     = topic
        self.fact      = fact
        self.action    = action
        self.url       = url

    def to_context_str(self) -> str:
        parts = [f"[{self.record_id}] {self.source}"]
        if self.topic:
            parts.append(f"Topic: {self.topic}")
        if self.fact:
            parts.append(f"Finding: {self.fact}")
        if self.action:
            parts.append(f"Action: {self.action}")
        if self.url:
            parts.append(f"Source: {self.url}")
        return " | ".join(parts)


def _parse_md_table(path: str) -> list[dict]:
    """Parse a markdown table file into list of row dicts."""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    headers = []
    rows    = []
    in_table = False

    for line in lines:
        line = line.strip()
        if not line.startswith("|"):
            if in_table:
                break
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if not headers:
            headers = cells
            in_table = True
        elif all(c.startswith("-") or c == "" for c in cells):
            continue   # separator row
        else:
            rows.append(dict(zip(headers, cells)))

    return rows


@lru_cache(maxsize=1)
def _load_all_chunks() -> dict[str, KBChunk]:
    """Load and index all KB records by their record_id."""
    chunks: dict[str, KBChunk] = {}

    for key, filename in KB_FILES.items():
        path = os.path.join(PROJECT_ROOT, filename)
        rows = _parse_md_table(path)
        for row in rows:
            record_id = (
                row.get("record_id") or row.get("Rule_ID") or
                row.get("Mapping_ID") or row.get("Mapping_id", "")
            ).strip()
            if not record_id:
                continue

            source = (
                row.get("source_type") or row.get("source_file") or
                row.get("source_reference") or key
            )
            topic = (
                row.get("topic") or row.get("Risk_Type") or
                row.get("Feature") or row.get("category") or ""
            )
            fact = (
                row.get("fact") or row.get("Condition") or
                row.get("Rationale") or row.get("delay_signal") or
                row.get("what_it_means") or ""
            )
            action = (
                row.get("prototype_action") or row.get("recommended_action") or
                row.get("Prototype_Recommendation") or row.get("Prototype_Action") or ""
            )
            url = row.get("official_source_url") or row.get("source_reference") or ""

            chunks[record_id] = KBChunk(
                record_id=record_id,
                source=source,
                topic=topic,
                fact=fact,
                action=action,
                url=url,
            )

    return chunks


def get_chunks_for_rules(rules_triggered: list[str]) -> list[KBChunk]:
    """Return KB chunks relevant to the triggered rule IDs."""
    chunks = _load_all_chunks()
    result = []
    seen   = set()

    for rule_id in rules_triggered:
        # Direct rule record
        if rule_id in chunks and rule_id not in seen:
            result.append(chunks[rule_id])
            seen.add(rule_id)
        # Feature-mapping records for this rule
        for feat in RULE_FEATURE_MAP.get(rule_id, []):
            for cid, c in chunks.items():
                if feat.lower() in (c.topic + c.fact + c.action).lower() and cid not in seen:
                    result.append(c)
                    seen.add(cid)
                    break  # one per feature
        # Legal / CAG records mapped to this rule
        rule_keywords = {
            "R-01": ["compensation", "payment", "funding"],
            "R-02": ["r&r", "rehabilitation", "resettlement"],
            "R-03": ["dispute", "legal", "ownership", "conflict"],
            "R-04": ["documentation", "record", "survey"],
            "R-05": ["stakeholder", "objection", "notice"],
            "R-06": ["award", "milestone", "declaration"],
            "R-07": ["possession", "handover"],
            "R-08": ["governance", "monitoring", "update", "officer"],
        }.get(rule_id, [])

        for kw in rule_keywords:
            for cid, c in chunks.items():
                if (kw in c.fact.lower() or kw in c.action.lower()) and cid not in seen:
                    result.append(c)
                    seen.add(cid)
                    if len([x for x in result if x.record_id.startswith("CAG") or x.record_id.startswith("LARR")]) >= 6:
                        break

    return result[:12]   # cap context size


def get_chunks_for_stage(stage: str) -> list[KBChunk]:
    """Return KB chunks relevant to a given acquisition stage."""
    chunks  = _load_all_chunks()
    ids     = STAGE_KB_MAP.get(stage, [])
    result  = [chunks[i] for i in ids if i in chunks]
    return result


def get_rule_summary() -> str:
    """Return all 8 rules as a compact string for system prompt context."""
    chunks = _load_all_chunks()
    lines  = []
    for rid in ["R-01","R-02","R-03","R-04","R-05","R-06","R-07","R-08"]:
        if rid in chunks:
            c = chunks[rid]
            lines.append(f"{rid} ({c.topic}): condition={c.fact} → action={c.action}")
    return "\n".join(lines)


def get_stage_admin_summary() -> str:
    """Return lifecycle + admin bottleneck records as compact string."""
    chunks = _load_all_chunks()
    lines  = []
    for cid, c in chunks.items():
        if cid.startswith("LIFE") or cid.startswith("ADMIN"):
            lines.append(f"{cid} [{c.topic or c.source}]: {c.fact[:120]}")
    return "\n".join(lines)


def chunks_to_context(chunks: list[KBChunk]) -> str:
    return "\n".join(c.to_context_str() for c in chunks)
