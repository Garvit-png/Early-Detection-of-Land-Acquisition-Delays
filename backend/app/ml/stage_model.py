"""
stage_model.py — Dedicated stage-wise delay prediction model.

Trains one XGBoost model per acquisition stage (6 stages).
Each model predicts delay probability specifically for projects at that stage,
using stage-relevant features weighted accordingly.

Stages:
  0 — Section 11 Notification
  1 — Section 19 Declaration
  2 — Award Passed
  3 — Compensation Disbursed
  4 — Possession Taken
  5 — R&R Completed
"""

import json, os, logging
import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import roc_auc_score, f1_score, accuracy_score
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "../../.."))
CSV_PATH     = os.path.join(PROJECT_ROOT, "data/processed/projects_ml.csv")


def get_models_dir() -> str:
    vercel_dir = os.path.join(PROJECT_ROOT, "backend", "data", "models")
    if os.path.exists(vercel_dir):
        return vercel_dir
    return os.path.join(PROJECT_ROOT, "data", "models")


MODELS_DIR = get_models_dir()

STAGE_NAMES = [
    "Section 11 Notification",
    "Section 19 Declaration",
    "Award Passed",
    "Compensation Disbursed",
    "Possession Taken",
    "R&R Completed",
]

# Features most relevant at each stage (weighted by domain knowledge)
STAGE_FEATURE_WEIGHTS = {
    0: ["pending_notifications", "documentation_pct", "notice_delivery_pct",
        "stakeholder_response_pct", "days_in_current_stage", "days_since_last_action"],
    1: ["pending_approvals", "documentation_pct", "stakeholder_response_pct",
        "num_legal_cases", "ownership_conflicts", "days_in_current_stage"],
    2: ["award_overdue", "days_in_current_stage", "num_legal_cases",
        "ownership_conflicts", "funding_readiness", "pending_approvals"],
    3: ["compensation_pct", "compensation_pending_months", "funding_readiness",
        "notice_delivery_pct", "num_legal_cases", "budget_released"],
    4: ["possession_pct", "compensation_pct", "mutation_completion_pct",
        "num_legal_cases", "ownership_conflicts", "days_since_last_action"],
    5: ["rr_completion_pct", "families_affected", "stakeholder_response_pct",
        "days_in_current_stage", "officer_responsiveness", "days_since_update"],
}

# All features used by stage models
STAGE_FEATURES = [
    "days_in_current_stage", "days_since_last_action", "days_since_update",
    "pending_approvals", "pending_notifications", "budget_released",
    "has_legal_dispute", "num_legal_cases", "ownership_conflicts",
    "compensation_pct", "compensation_pending_months",
    "rr_completion_pct", "documentation_pct", "stakeholder_response_pct",
    "possession_pct", "funding_readiness", "notice_delivery_pct", "mutation_completion_pct",
    "award_overdue", "noc_pending_count",
    "land_area_ha", "families_affected",
    "officer_responsiveness", "district_historical_delay_rate",
]


def train_stage_models(csv_path: str = CSV_PATH) -> dict:
    """Train one model per stage. Returns metrics dict."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)
    # Fill missing new columns with defaults
    for col, default in [("funding_readiness",75),("notice_delivery_pct",75),
                         ("mutation_completion_pct",0),("award_overdue",0)]:
        if col not in df.columns:
            df[col] = default

    metrics = {}
    models  = {}

    for stage_idx in range(6):
        stage_df = df[df["current_stage_index"] == stage_idx].copy()
        if len(stage_df) < 30:
            logger.warning(f"Stage {stage_idx} has only {len(stage_df)} rows — skipping.")
            continue

        # Ensure all features exist
        for feat in STAGE_FEATURES:
            if feat not in stage_df.columns:
                stage_df[feat] = 0

        X = stage_df[STAGE_FEATURES]
        y = stage_df["is_delayed"].astype(int)

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y if y.nunique() > 1 else None
        )

        model = xgb.XGBClassifier(
            n_estimators=200, max_depth=5, learning_rate=0.08,
            subsample=0.8, colsample_bytree=0.8,
            eval_metric="logloss", random_state=42, n_jobs=-1,
        )
        model.fit(X_train, y_train, verbose=False)

        y_prob = model.predict_proba(X_test)[:, 1]
        y_pred = model.predict(X_test)

        auc = round(float(roc_auc_score(y_test, y_prob)), 4) if y_test.nunique() > 1 else 0.5
        f1  = round(float(f1_score(y_test, y_pred, zero_division=0)), 4)
        acc = round(float(accuracy_score(y_test, y_pred)), 4)

        metrics[stage_idx] = {
            "stage_name": STAGE_NAMES[stage_idx],
            "n_train":    len(X_train),
            "n_test":     len(X_test),
            "roc_auc":    auc,
            "f1_score":   f1,
            "accuracy":   acc,
        }
        models[stage_idx] = model
        logger.info(f"Stage {stage_idx} ({STAGE_NAMES[stage_idx]}): "
                    f"ROC-AUC={auc}, F1={f1}, n={len(stage_df)}")

    # Save models and metrics
    os.makedirs(MODELS_DIR, exist_ok=True)
    for idx, model in models.items():
        model.save_model(os.path.join(MODELS_DIR, f"stage_model_{idx}.json"))

    with open(os.path.join(MODELS_DIR, "stage_model_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    with open(os.path.join(MODELS_DIR, "stage_model_features.json"), "w") as f:
        json.dump({
            "features":       STAGE_FEATURES,
            "stage_weights":  {str(k): v for k, v in STAGE_FEATURE_WEIGHTS.items()},
            "stage_names":    {str(i): n for i, n in enumerate(STAGE_NAMES)},
        }, f, indent=2)

    logger.info("Stage models saved.")
    return metrics


# ─── Inference ────────────────────────────────────────────────────────────────

class StagePredictor:
    """Singleton that loads all stage models and serves per-stage risk."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def load(self):
        if self._loaded:
            return
        self.models   = {}
        self.features = STAGE_FEATURES
        self.stage_names = STAGE_NAMES

        for idx in range(6):
            path = os.path.join(MODELS_DIR, f"stage_model_{idx}.json")
            if os.path.exists(path):
                m = xgb.XGBClassifier()
                m.load_model(path)
                self.models[idx] = m

        self._loaded = bool(self.models)

    def predict_all_stages(self, features: dict) -> list[dict]:
        """
        Predict delay risk at every stage for a given project.
        Returns list of 6 dicts ordered by stage index.
        """
        self.load()
        results = []
        for idx, name in enumerate(STAGE_NAMES):
            model = self.models.get(idx)
            if model is None:
                results.append({
                    "stage_index": idx, "stage_name": name,
                    "delay_probability": None, "risk_score": None,
                    "risk_category": None, "top_drivers": [],
                })
                continue

            X   = pd.DataFrame([features])[self.features]
            prob = float(model.predict_proba(X)[0][1])
            score = round(prob * 100, 1)
            cat   = "High" if score >= 70 else "Medium" if score >= 40 else "Low"

            # Top drivers for this stage (feature importances)
            imp    = model.feature_importances_
            top3   = sorted(zip(self.features, imp), key=lambda x: x[1], reverse=True)[:3]
            drivers = [{"feature": f, "importance": round(float(v), 4)} for f, v in top3]

            # Stage-specific corrective action
            action = _stage_action(idx, features, score)

            results.append({
                "stage_index":       idx,
                "stage_name":        name,
                "delay_probability": round(prob, 4),
                "risk_score":        score,
                "risk_category":     cat,
                "top_drivers":       drivers,
                "corrective_action": action,
            })

        return results

    def predict_current_stage(self, stage_index: int, features: dict) -> dict:
        """Predict risk only for the current stage."""
        self.load()
        all_stages = self.predict_all_stages(features)
        for s in all_stages:
            if s["stage_index"] == stage_index:
                return s
        return {}

    @property
    def metrics(self) -> dict:
        path = os.path.join(MODELS_DIR, "stage_model_metrics.json")
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return {}


def _stage_action(stage_idx: int, f: dict, score: float) -> str:
    """Return the most relevant corrective action for this stage's risk."""
    if score < 40:
        return "Stage risk is low — maintain current pace."
    actions = {
        0: f"Ensure all Section 11 notices delivered ({f.get('notice_delivery_pct',75)}% done). Complete documentation before proceeding.",
        1: f"Resolve {f.get('num_legal_cases',0)} legal cases and clear {f.get('pending_approvals',0)} pending approvals before Section 19 declaration.",
        2: f"Expedite award finalization — {int(f.get('days_in_current_stage',0))} days elapsed. Check funding readiness ({f.get('funding_readiness',75)}%).",
        3: f"Release compensation to remaining {100 - f.get('compensation_pct',0):.0f}% of beneficiaries. Verify bank details and funding receipt.",
        4: f"Possession at {f.get('possession_pct',0)}% — ensure compensation prerequisites met before taking further possession.",
        5: f"R&R at {f.get('rr_completion_pct',0)}% — prioritize {f.get('families_affected',0)} affected families. Complete colony allotment.",
    }
    return actions.get(stage_idx, "Review stage-specific risk factors and escalate.")


stage_predictor = StagePredictor()


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    print("Training stage-wise models...")
    metrics = train_stage_models()
    print("\n=== Stage Model Metrics ===")
    for idx, m in metrics.items():
        print(f"  Stage {idx} ({m['stage_name'][:25]:25s}): ROC-AUC={m['roc_auc']} F1={m['f1_score']} n={m['n_train']}")
