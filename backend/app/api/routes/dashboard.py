"""Dashboard aggregation endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from app.core.deps import CurrentUser, get_db
from app.db.models import Project, RiskCategory, UserRole
from app.schemas.schemas import DashboardStats

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_stats(current_user: CurrentUser, db: Session = Depends(get_db)):
    query = db.query(Project)

    if current_user.role == UserRole.DISTRICT:
        query = query.filter(
            Project.state == current_user.state,
            Project.district == current_user.district,
        )
    elif current_user.role == UserRole.STATE:
        query = query.filter(Project.state == current_user.state)

    projects = query.all()
    total = len(projects)

    if total == 0:
        return DashboardStats(
            total_projects=0, high_risk=0, medium_risk=0, low_risk=0,
            unscored=0, delayed_confirmed=0, avg_risk_score=0,
            avg_compensation_pct=0, avg_rr_completion_pct=0,
            projects_with_legal_dispute=0,
            by_state=[], by_project_type=[], by_stage=[], recent_high_risk=[],
        )

    high   = sum(1 for p in projects if p.risk_category == RiskCategory.HIGH)
    medium = sum(1 for p in projects if p.risk_category == RiskCategory.MEDIUM)
    low    = sum(1 for p in projects if p.risk_category == RiskCategory.LOW)
    unscored = sum(1 for p in projects if p.risk_score is None)
    delayed  = sum(1 for p in projects if p.is_delayed)

    scored = [p for p in projects if p.risk_score is not None]
    avg_risk = round(sum(p.risk_score for p in scored) / len(scored), 1) if scored else 0
    comp_vals = [p.compensation_pct for p in projects if p.compensation_pct is not None]
    rr_vals   = [p.rr_completion_pct for p in projects if p.rr_completion_pct is not None]
    avg_comp = round(sum(comp_vals) / len(comp_vals), 1) if comp_vals else 0
    avg_rr   = round(sum(rr_vals) / len(rr_vals), 1) if rr_vals else 0
    legal    = sum(1 for p in projects if p.has_legal_dispute)

    # By state
    state_map: dict[str, dict] = {}
    for p in projects:
        s = p.state
        if s not in state_map:
            state_map[s] = {"state": s, "total": 0, "high": 0, "medium": 0, "low": 0}
        state_map[s]["total"] += 1
        if p.risk_category == RiskCategory.HIGH:
            state_map[s]["high"] += 1
        elif p.risk_category == RiskCategory.MEDIUM:
            state_map[s]["medium"] += 1
        elif p.risk_category == RiskCategory.LOW:
            state_map[s]["low"] += 1
    by_state = sorted(state_map.values(), key=lambda x: x["high"], reverse=True)

    # By project type
    type_map: dict[str, dict] = {}
    for p in projects:
        t = p.project_type
        if t not in type_map:
            type_map[t] = {"project_type": t, "total": 0, "high": 0, "avg_risk": 0, "_scores": []}
        type_map[t]["total"] += 1
        if p.risk_category == RiskCategory.HIGH:
            type_map[t]["high"] += 1
        if p.risk_score is not None:
            type_map[t]["_scores"].append(p.risk_score)
    for t in type_map.values():
        t["avg_risk"] = round(sum(t["_scores"]) / len(t["_scores"]), 1) if t["_scores"] else 0
        del t["_scores"]
    by_type = sorted(type_map.values(), key=lambda x: x["avg_risk"], reverse=True)

    # By stage
    stage_map: dict[str, int] = {}
    for p in projects:
        s = p.current_stage or "Unknown"
        stage_map[s] = stage_map.get(s, 0) + 1
    by_stage = [{"stage": k, "count": v} for k, v in stage_map.items()]

    # Recent high risk
    recent_hr = sorted(
        [p for p in projects if p.risk_category == RiskCategory.HIGH],
        key=lambda x: x.risk_score or 0, reverse=True
    )[:5]
    recent_high_risk = [
        {
            "project_id": p.project_id,
            "project_name": p.project_name,
            "state": p.state,
            "district": p.district,
            "risk_score": p.risk_score,
        }
        for p in recent_hr
    ]

    return DashboardStats(
        total_projects=total,
        high_risk=high,
        medium_risk=medium,
        low_risk=low,
        unscored=unscored,
        delayed_confirmed=delayed,
        avg_risk_score=avg_risk,
        avg_compensation_pct=avg_comp,
        avg_rr_completion_pct=avg_rr,
        projects_with_legal_dispute=legal,
        by_state=by_state,
        by_project_type=by_type,
        by_stage=by_stage,
        recent_high_risk=recent_high_risk,
    )


@router.get("/state-analytics")
def get_state_analytics(current_user: CurrentUser, db: Session = Depends(get_db)):
    """
    Per-state aggregated metrics for the State Comparison page.
    Returns one row per state with risk breakdown, avg compensation, R&R, rules breakdown.
    """
    query = db.query(Project)
    if current_user.role == UserRole.STATE:
        query = query.filter(Project.state == current_user.state)
    elif current_user.role == UserRole.DISTRICT:
        query = query.filter(Project.state == current_user.state, Project.district == current_user.district)

    projects = query.all()

    state_map: dict[str, dict] = {}
    for p in projects:
        s = p.state
        if s not in state_map:
            state_map[s] = {
                "state": s,
                "total": 0, "high": 0, "medium": 0, "low": 0, "unscored": 0,
                "delayed": 0,
                "_risk_scores": [], "_comp": [], "_rr": [], "_doc": [], "_shr": [],
                "_rules": {"R-01": 0, "R-02": 0, "R-03": 0, "R-04": 0,
                           "R-05": 0, "R-06": 0, "R-07": 0, "R-08": 0},
            }
        d = state_map[s]
        d["total"] += 1
        if p.risk_category and p.risk_category.value == "High":   d["high"] += 1
        elif p.risk_category and p.risk_category.value == "Medium": d["medium"] += 1
        elif p.risk_category and p.risk_category.value == "Low":    d["low"] += 1
        else:                                                        d["unscored"] += 1
        if p.is_delayed:  d["delayed"] += 1
        if p.risk_score is not None: d["_risk_scores"].append(p.risk_score)
        if p.compensation_pct is not None: d["_comp"].append(p.compensation_pct)
        if p.rr_completion_pct is not None: d["_rr"].append(p.rr_completion_pct)
        if getattr(p, "documentation_pct", None) is not None: d["_doc"].append(p.documentation_pct)
        if getattr(p, "stakeholder_response_pct", None) is not None: d["_shr"].append(p.stakeholder_response_pct)
        # Count rule hits
        rules = p.rules_triggered or []
        for r in rules:
            if r in d["_rules"]:
                d["_rules"][r] += 1

    result = []
    for s, d in state_map.items():
        avg = lambda lst: round(sum(lst) / len(lst), 1) if lst else 0
        result.append({
            "state":          s,
            "total":          d["total"],
            "high":           d["high"],
            "medium":         d["medium"],
            "low":            d["low"],
            "delayed":        d["delayed"],
            "delay_rate":     round(d["delayed"] / d["total"] * 100, 1) if d["total"] else 0,
            "avg_risk_score": avg(d["_risk_scores"]),
            "avg_compensation_pct": avg(d["_comp"]),
            "avg_rr_pct":     avg(d["_rr"]),
            "avg_doc_pct":    avg(d["_doc"]),
            "avg_stakeholder_pct": avg(d["_shr"]),
            "rule_hits":      d["_rules"],
        })

    result.sort(key=lambda x: x["avg_risk_score"], reverse=True)
    return result
