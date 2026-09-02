"""
Model Predictor — loads trained XGBoost + SHAP explainer and serves predictions.
Singleton pattern so model loads once at startup.
"""

import os
import json
import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from typing import Any

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "../../.."))
MODELS_DIR   = os.path.join(PROJECT_ROOT, "data/models")


class DelayPredictor:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def load(self):
        if self._loaded:
            return

        model_path     = os.path.join(MODELS_DIR, "xgb_delay_model.json")
        explainer_path = os.path.join(MODELS_DIR, "shap_explainer.pkl")
        features_path  = os.path.join(MODELS_DIR, "feature_config.json")

        self.model = xgb.XGBClassifier()
        self.model.load_model(model_path)

        self.explainer = joblib.load(explainer_path)

        with open(features_path) as f:
            config = json.load(f)

        self.feature_cols         = config["feature_cols"]
        self.feature_display_names = config["feature_display_names"]
        self.global_shap_importance = config["global_shap_importance"]

        self._loaded = True

    def predict(self, features: dict[str, Any]) -> dict:
        """
        Accepts a flat dict with all feature values.
        Returns delay_probability, risk_score, risk_category, top_factors.
        """
        self.load()

        X = pd.DataFrame([features])[self.feature_cols]

        prob       = float(self.model.predict_proba(X)[0][1])
        risk_score = round(prob * 100, 1)

        if risk_score >= 70:
            risk_category = "High"
        elif risk_score >= 40:
            risk_category = "Medium"
        else:
            risk_category = "Low"

        shap_vals = self.explainer.shap_values(X)[0]

        factors = []
        for feat, shap_val in zip(self.feature_cols, shap_vals):
            factors.append({
                "feature":      feat,
                "display_name": self.feature_display_names.get(feat, feat),
                "value":        float(X[feat].iloc[0]),
                "shap_value":   round(float(shap_val), 4),
                "direction":    "increases_risk" if shap_val > 0 else "decreases_risk",
            })

        factors.sort(key=lambda x: abs(x["shap_value"]), reverse=True)

        # Build plain-language recommendation for top risk driver
        recommendations = _build_recommendations(factors[:5], features)

        return {
            "delay_probability": round(prob, 4),
            "risk_score":        risk_score,
            "risk_category":     risk_category,
            "top_factors":       factors[:8],
            "recommendations":   recommendations,
        }

    def get_global_importance(self) -> list[dict]:
        self.load()
        return [
            {
                "feature":      k,
                "display_name": self.feature_display_names.get(k, k),
                "importance":   v,
            }
            for k, v in sorted(
                self.global_shap_importance.items(),
                key=lambda x: x[1],
                reverse=True,
            )
        ]


def _build_recommendations(top_factors: list[dict], features: dict) -> list[str]:
    """Generate plain-language recommended actions based on top risk drivers."""
    recs = []
    seen = set()

    for f in top_factors:
        if f["direction"] != "increases_risk":
            continue
        feat = f["feature"]
        if feat in seen:
            continue
        seen.add(feat)

        if feat == "days_since_last_action" and features.get("days_since_last_action", 0) > 90:
            recs.append(
                f"No official action in {int(features['days_since_last_action'])} days — "
                "escalate to District Collector for immediate review."
            )
        elif feat == "compensation_pct" and features.get("compensation_pct", 100) < 60:
            recs.append(
                f"Only {features['compensation_pct']}% compensation disbursed — "
                "verify bank account details and release pending payments urgently."
            )
        elif feat == "has_legal_dispute" and features.get("has_legal_dispute", 0) == 1:
            recs.append(
                f"{int(features.get('num_legal_cases', 1))} active legal case(s) — "
                "engage legal team and consider alternate dispute resolution (ADR)."
            )
        elif feat == "rr_completion_pct" and features.get("rr_completion_pct", 100) < 50:
            recs.append(
                f"Only {features['rr_completion_pct']}% R&R completed — "
                "fast-track construction of rehabilitation colony and allotment."
            )
        elif feat == "pending_approvals" and features.get("pending_approvals", 0) > 3:
            recs.append(
                f"{int(features['pending_approvals'])} approvals pending — "
                "convene inter-departmental meeting to clear bottlenecks."
            )
        elif feat == "noc_pending_count" and features.get("noc_pending_count", 0) > 2:
            recs.append(
                f"{int(features['noc_pending_count'])} departmental NOCs pending — "
                "issue formal reminders to Forest/Revenue/Irrigation departments."
            )
        elif feat == "budget_released" and features.get("budget_released", 1) == 0:
            recs.append(
                "Project budget not released — submit urgent requisition to State Finance Department."
            )
        elif feat == "days_in_current_stage" and features.get("days_in_current_stage", 0) > 180:
            recs.append(
                f"Stuck in '{features.get('current_stage', 'current stage')}' for "
                f"{int(features['days_in_current_stage'])} days — flag for senior officer review."
            )
        elif feat == "officer_responsiveness" and features.get("officer_responsiveness", 10) < 4:
            recs.append(
                "Low officer responsiveness score — consider reassigning to a more active officer."
            )

        if len(recs) >= 3:
            break

    if not recs:
        recs.append("Monitor regularly — no immediate critical action required.")

    return recs


# Module-level singleton
predictor = DelayPredictor()
