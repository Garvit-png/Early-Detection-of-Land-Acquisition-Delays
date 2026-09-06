"""
seed_demo_data.py — populates Risk History snapshots and demo Action Items
for demonstration purposes.

Run: python backend/scripts/seed_demo_data.py
"""

import sys, os, random
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db.database import SessionLocal
from app.db.models import (
    Project, RiskHistory, ActionItem, ActionStatus, RiskCategory, User
)
from app.ml.predictor import predictor

random.seed(42)


def _project_to_features(p: Project) -> dict:
    from app.ml.trainer import STAGE_EXPECTED_DAYS
    stage_idx = p.current_stage_index or 0
    exp_days  = STAGE_EXPECTED_DAYS[stage_idx] if stage_idx < len(STAGE_EXPECTED_DAYS) else 90
    return {
        "land_area_ha":                   p.land_area_ha or 0,
        "families_affected":              p.families_affected or 0,
        "current_stage_index":            stage_idx,
        "days_in_current_stage":          p.days_in_current_stage or 0,
        "award_overdue":                  int(p.current_stage == "Award Passed" and (p.days_in_current_stage or 0) > exp_days * 1.5),
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
        "funding_readiness":              getattr(p, "funding_readiness", None) or 75,
        "notice_delivery_pct":            getattr(p, "notice_delivery_pct", None) or 75,
        "mutation_completion_pct":        getattr(p, "mutation_completion_pct", None) or 0,
        "project_type_code":              p.project_type_code or 0,
        "state_code":                     p.state_code or 0,
    }


def seed_risk_history(db, projects: list[Project], admin: User) -> int:
    """
    For each demo project, create 3–5 historical risk snapshots spread over
    the past 6 months, simulating project evolution over time.
    """
    predictor.load()
    created = 0
    now = datetime.now(timezone.utc)

    for p in projects:
        features = _project_to_features(p)
        n_snaps  = random.randint(3, 5)

        for i in range(n_snaps):
            # Create a slightly different snapshot going back in time
            days_ago  = int((n_snaps - i) * random.uniform(20, 45))
            snap_time = now - timedelta(days=days_ago)

            # Simulate improvement over time: early snapshots worse
            noise     = random.uniform(-8, 4) * (n_snaps - i)
            snap_feat = {**features}
            # Earlier = less compensation paid, fewer days of action taken
            if i < n_snaps - 1:
                snap_feat["compensation_pct"]         = max(0, (features["compensation_pct"] or 0) - random.uniform(5, 20))
                snap_feat["rr_completion_pct"]         = max(0, (features["rr_completion_pct"] or 0) - random.uniform(3, 15))
                snap_feat["days_since_last_action"]    = min(730, (features["days_since_last_action"] or 0) + random.randint(10, 60))

            result = predictor.predict(snap_feat)
            score  = max(0, min(100, result["risk_score"] + noise))

            if score >= 70:
                rc = RiskCategory.HIGH
            elif score >= 40:
                rc = RiskCategory.MEDIUM
            else:
                rc = RiskCategory.LOW

            triggers = ["manual", "update", "batch", "action_completed"]
            db.add(RiskHistory(
                project_id_fk     = p.id,
                risk_score        = round(score, 1),
                delay_probability = round(result["delay_probability"] + random.uniform(-0.05, 0.02), 4),
                risk_category     = rc,
                rules_triggered   = result.get("rules_triggered", []),
                scored_by         = admin.id,
                trigger           = triggers[i % len(triggers)],
                notes             = f"Demo snapshot {i+1}/{n_snaps} — simulated historical state",
                scored_at         = snap_time,
            ))
            created += 1

    db.commit()
    return created


DEMO_ACTIONS = [
    # (rule_id, title, officer_decision, priority, status, completion_note)
    ("R-01", "Release pending compensation payments to Agra landowners",
     "accept", "critical", "in_progress", None),
    ("R-02", "Fast-track R&R colony construction in Varanasi package",
     "accept", "high", "open", None),
    ("R-03", "Refer 4 ownership-dispute cases to LARR Authority",
     "accept", "high", "completed",
     "All 4 cases referred to LARR Authority on 28 Aug 2026. Hearings scheduled."),
    ("R-04", "Complete survey record validation before Section 19 declaration",
     "modify", "medium", "in_progress", None),
    ("R-05", "Conduct consultation camp for 320 objecting landowners in Kanpur",
     "accept", "medium", "open", None),
    ("R-06", "Escalate award delay — prepare extension proposal for State committee",
     "accept", "high", "completed",
     "Extension proposal submitted to State Committee on 1 Sep 2026. Approved."),
    ("R-07", "Halt possession until compensation reaches 80% — document handover status",
     "accept", "high", "open", None),
    ("R-08", "Reassign update responsibility to new District Coordinator",
     "override", "medium", "completed",
     "Override: existing officer retained but weekly update mandate issued."),
    ("R-01", "Verify bank account details for 87 un-disbursed compensation cases",
     "accept", "high", "in_progress", None),
    ("R-05", "Issue revised notices to 140 landowners with undelivered first notices",
     "accept", "medium", "open", None),
]


def seed_action_items(db, projects: list[Project], admin: User) -> int:
    created = 0
    now = datetime.now(timezone.utc)

    for i, p in enumerate(projects):
        action_data = DEMO_ACTIONS[i % len(DEMO_ACTIONS)]
        rule_id, title, decision, priority, status_str, completion_note = action_data

        try:
            status = ActionStatus(status_str)
        except ValueError:
            status = ActionStatus.OPEN

        completed_at = None
        if status == ActionStatus.COMPLETED:
            completed_at = now - timedelta(days=random.randint(1, 10))

        due_days = {"critical": 7, "high": 14, "medium": 30, "low": 60}.get(priority, 30)

        db.add(ActionItem(
            project_id_fk    = p.id,
            rule_id          = rule_id,
            title            = f"{title} — {p.district}",
            description      = f"AI-identified risk driver for {p.project_name}. "
                               f"Risk score: {p.risk_score or 'N/A'}/100.",
            officer_decision = decision,
            override_note    = "Reviewed and modified per local conditions." if decision == "modify" else
                               "Officer disagrees with AI recommendation — manual approach taken." if decision == "override" else None,
            assigned_to      = admin.id,
            assigned_by      = admin.id,
            status           = status,
            priority         = priority,
            due_date         = now + timedelta(days=due_days),
            completed_at     = completed_at,
            completion_note  = completion_note,
            created_at       = now - timedelta(days=random.randint(1, 20)),
        ))
        created += 1

    db.commit()
    return created


def main():
    db    = SessionLocal()
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        print("ERROR: admin user not found — run seed_db.py first")
        return

    # Pick 20 high-risk projects spread across states for demo
    projects = (
        db.query(Project)
        .filter(Project.risk_score >= 75)
        .order_by(Project.risk_score.desc())
        .limit(20)
        .all()
    )
    print(f"Seeding demo data for {len(projects)} high-risk projects...")

    # ── Risk History ────────────────────────────────────────────────────────────
    existing_rh = db.query(RiskHistory).count()
    if existing_rh > 0:
        print(f"  Risk history already has {existing_rh} rows — skipping.")
    else:
        rh_count = seed_risk_history(db, projects, admin)
        print(f"  Risk history snapshots created : {rh_count}")

    # ── Action Items ────────────────────────────────────────────────────────────
    existing_ai = db.query(ActionItem).count()
    if existing_ai > 0:
        print(f"  Action items already has {existing_ai} rows — skipping.")
    else:
        ai_count = seed_action_items(db, projects[:10], admin)
        print(f"  Action items created           : {ai_count}")

    # Final counts
    print()
    print("=== DB Counts ===")
    print(f"  risk_history  : {db.query(RiskHistory).count()}")
    print(f"  action_items  : {db.query(ActionItem).count()}")
    db.close()
    print("Done.")


if __name__ == "__main__":
    main()
