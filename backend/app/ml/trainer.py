"""
trainer.py — retraining pipeline.
Aligned with SIH_Land_Acquisition_Recommendation_Rules.csv (8 rules, 26 features).
"""

import json
import logging
import os
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
import shap
import xgboost as xgb
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "../../.."))


def get_models_dir() -> str:
    """Get models directory — works locally and on Vercel."""
    vercel_dir = os.path.join(PROJECT_ROOT, "backend", "data", "models")
    if os.path.exists(vercel_dir):
        return vercel_dir
    return os.path.join(PROJECT_ROOT, "data", "models")


MODELS_DIR = get_models_dir()
CSV_FALLBACK = os.path.join(PROJECT_ROOT, "data/processed/projects_ml.csv")

# ── 31 features — all 8 CSV rules + FM-12/13/14 covered ─────────────────────────
FEATURE_COLS = [
    # Scale
    "land_area_ha", "families_affected",
    # Stage (R-06)
    "current_stage_index", "days_in_current_stage", "award_overdue",
    # Governance / inactivity (R-08)
    "days_since_last_action", "days_since_update",
    # Approvals
    "pending_approvals", "pending_notifications", "noc_pending_count", "budget_released",
    # Legal (R-03)
    "has_legal_dispute", "num_legal_cases", "ownership_conflicts",
    # Compensation (R-01)
    "compensation_pct", "compensation_pending_months",
    # R&R (R-02)
    "rr_completion_pct",
    # Documentation (R-04)
    "documentation_pct",
    # Stakeholder (R-05)
    "stakeholder_response_pct",
    # Possession (R-07)
    "possession_pct",
    # Financial
    "land_cost_cr", "amount_paid_cr", "project_value_cr",
    # District context
    "district_historical_delay_rate", "prev_delayed_district",
    # Governance (R-08)
    "officer_responsiveness",
    # FM-12: Funding readiness (CAG-03 / ADMIN-03)
    "funding_readiness",
    # FM-13: Notice delivery (CAG-04 / ADMIN-04)
    "notice_delivery_pct",
    # FM-14: Mutation completion (CAG-13 / ADMIN-09)
    "mutation_completion_pct",
    # Encodings
    "project_type_code", "state_code",
]

FEATURE_DISPLAY_NAMES = {
    "land_area_ha":                   "Land Area (ha)",
    "families_affected":              "Families Affected",
    "current_stage_index":            "Current Acquisition Stage",
    "days_in_current_stage":          "Days Stuck in Current Stage",
    "award_overdue":                  "Award Milestone Overdue",
    "days_since_last_action":         "Days Since Last Official Action",
    "days_since_update":              "Days Since System Update (R-08)",
    "pending_approvals":              "Pending Approvals Count",
    "pending_notifications":          "Pending Legal Notifications",
    "noc_pending_count":              "Inter-Dept NOCs Pending",
    "budget_released":                "Budget Released",
    "has_legal_dispute":              "Active Legal Dispute (R-03)",
    "num_legal_cases":                "Number of Legal Cases (R-03)",
    "ownership_conflicts":            "Ownership Conflicts (R-03)",
    "compensation_pct":               "Compensation Disbursed % (R-01)",
    "compensation_pending_months":    "Months Compensation Pending (R-01)",
    "rr_completion_pct":              "R&R Completion % (R-02)",
    "documentation_pct":              "Documentation Completeness % (R-04)",
    "stakeholder_response_pct":       "Stakeholder Response % (R-05)",
    "possession_pct":                 "Land Possession % (R-07)",
    "land_cost_cr":                   "Total Land Cost (Cr)",
    "amount_paid_cr":                 "Amount Paid So Far (Cr)",
    "project_value_cr":               "Project Value (Cr)",
    "district_historical_delay_rate": "District Historical Delay Rate",
    "prev_delayed_district":          "Prev Delayed Projects in District",
    "officer_responsiveness":         "Officer Responsiveness Score (R-08)",
    "funding_readiness":              "Funding Readiness % (FM-12 / CAG-03)",
    "notice_delivery_pct":            "Notice Delivery % (FM-13 / CAG-04)",
    "mutation_completion_pct":        "Mutation Completion % (FM-14 / CAG-13)",
    "project_type_code":              "Project Type",
    "state_code":                     "State",
}

PROJECT_TYPE_MAP = {
    "National Highway": 0, "State Highway": 1, "Railway Line": 2,
    "Metro Rail": 3, "Expressway": 4, "Dam / Reservoir": 5,
    "Irrigation Canal": 6, "Industrial Corridor": 7, "Power Plant": 8,
    "Solar Park": 9, "Transmission Line": 10, "Airport Expansion": 11,
    "Port Development": 12, "Smart City": 13, "Housing Scheme": 14,
}
STATE_MAP = {
    "Andhra Pradesh": 0, "Bihar": 1, "Gujarat": 2, "Haryana": 3,
    "Jharkhand": 4, "Karnataka": 5, "Madhya Pradesh": 6, "Maharashtra": 7,
    "Odisha": 8, "Punjab": 9, "Rajasthan": 10, "Tamil Nadu": 11,
    "Telangana": 12, "Uttar Pradesh": 13, "West Bengal": 14,
}

# Expected days per acquisition stage — used for award_overdue flag
STAGE_EXPECTED_DAYS = [60, 90, 120, 90, 60, 180]


def _load_training_data(db=None) -> pd.DataFrame:
    if db is not None:
        try:
            from app.db.models import Project
            rows = db.query(Project).filter(Project.is_delayed.isnot(None)).all()
            if len(rows) >= 100:
                records = []
                for p in rows:
                    stage_idx = p.current_stage_index or 0
                    exp_days  = STAGE_EXPECTED_DAYS[stage_idx] if stage_idx < len(STAGE_EXPECTED_DAYS) else 90
                    records.append({
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
                        "funding_readiness":              getattr(p, "funding_readiness",       None) or 75,
                        "notice_delivery_pct":            getattr(p, "notice_delivery_pct",     None) or 75,
                        "mutation_completion_pct":        getattr(p, "mutation_completion_pct", None) or 0,
                        "project_type_code":              p.project_type_code or 0,
                        "state_code":                     p.state_code or 0,
                        "is_delayed":                     int(p.is_delayed),
                    })
                df = pd.DataFrame(records)
                logger.info(f"Loaded {len(df)} labelled rows from DB")
                return df
        except Exception as e:
            logger.warning(f"DB load failed, fallback to CSV: {e}")

    if not os.path.exists(CSV_FALLBACK):
        raise FileNotFoundError(f"Training data not found: {CSV_FALLBACK}")
    df = pd.read_csv(CSV_FALLBACK)
    # Fill any missing new columns with safe defaults
    for col, default in [("documentation_pct", 75), ("stakeholder_response_pct", 75),
                         ("ownership_conflicts", 0), ("days_since_update", 0),
                         ("award_overdue", 0)]:
        if col not in df.columns:
            df[col] = default
    logger.info(f"Loaded {len(df)} rows from CSV")
    return df


def retrain(db=None) -> dict:
    os.makedirs(MODELS_DIR, exist_ok=True)
    started_at = datetime.now(timezone.utc)
    logger.info("Retraining started (26 features, 8 CSV rules)...")

    df = _load_training_data(db)

    # Ensure all feature columns present
    for col in FEATURE_COLS:
        if col not in df.columns:
            df[col] = 0

    X = df[FEATURE_COLS]
    y = df["is_delayed"].astype(int)

    if len(X) < 50:
        raise ValueError(f"Not enough data: {len(X)} rows (need ≥ 50)")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = xgb.XGBClassifier(
        n_estimators=400, max_depth=6, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, min_child_weight=3,
        gamma=0.1, reg_alpha=0.1, reg_lambda=1.0,
        eval_metric="logloss", random_state=42, n_jobs=-1,
    )
    model.fit(X_train, y_train, verbose=False)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]
    metrics = {
        "accuracy":    round(float(accuracy_score(y_test, y_pred)), 4),
        "roc_auc":     round(float(roc_auc_score(y_test, y_prob)), 4),
        "f1_score":    round(float(f1_score(y_test, y_pred)), 4),
        "train_rows":  int(len(X_train)),
        "test_rows":   int(len(X_test)),
        "feature_count": len(FEATURE_COLS),
        "trained_at":  started_at.isoformat(),
        "data_source": "database" if db else "csv",
    }
    logger.info(f"Metrics: {metrics}")

    explainer = shap.TreeExplainer(model)
    shap_vals = explainer.shap_values(X_test.iloc[:200])
    mean_abs_shap = pd.Series(
        np.abs(shap_vals).mean(axis=0), index=FEATURE_COLS
    ).sort_values(ascending=False)

    model_path     = os.path.join(MODELS_DIR, "xgb_delay_model.json")
    explainer_path = os.path.join(MODELS_DIR, "shap_explainer.pkl")
    metrics_path   = os.path.join(MODELS_DIR, "model_metrics.json")
    features_path  = os.path.join(MODELS_DIR, "feature_config.json")

    model.save_model(model_path)
    joblib.dump(explainer, explainer_path)

    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    with open(features_path, "w") as f:
        json.dump({
            "feature_cols":           FEATURE_COLS,
            "feature_display_names":  FEATURE_DISPLAY_NAMES,
            "global_shap_importance": {k: round(float(v), 4) for k, v in mean_abs_shap.items()},
        }, f, indent=2)

    try:
        from app.ml.predictor import predictor
        predictor._loaded = False
        predictor.load()
        logger.info("Live predictor hot-swapped")
    except Exception as e:
        logger.warning(f"Hot-swap warning: {e}")

    logger.info("Retraining complete.")
    return metrics
