"""
predictor.py — XGBoost + SHAP singleton.
Recommendations implement all 8 rules from SIH_Land_Acquisition_Recommendation_Rules.csv
"""

import json
import os
from typing import Any

try:
    import joblib
    import numpy as np
    import pandas as pd
    import xgboost as xgb
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "../../.."))


def get_models_dir() -> str:
    """Get models directory — works locally and on Vercel."""
    # Vercel: backend/data/models (copied via includeFiles)
    vercel_dir = os.path.join(PROJECT_ROOT, "backend", "data", "models")
    if os.path.exists(vercel_dir):
        return vercel_dir
    # Local: data/models at project root
    return os.path.join(PROJECT_ROOT, "data", "models")


MODELS_DIR = get_models_dir()


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
        
        if not ML_AVAILABLE:
            self.feature_cols = ["compensation_pct", "rr_completion_pct", "num_legal_cases"]
            self.feature_display_names = {"compensation_pct": "Compensation Paid %", "rr_completion_pct": "R&R Complete %", "num_legal_cases": "Legal Cases"}
            self.global_shap_importance = {"compensation_pct": 0.4, "rr_completion_pct": 0.3, "num_legal_cases": 0.3}
            self._loaded = True
            return

        self.model    = xgb.XGBClassifier()
        self.model.load_model(os.path.join(MODELS_DIR, "xgb_delay_model.json"))
        self.explainer = joblib.load(os.path.join(MODELS_DIR, "shap_explainer.pkl"))
        with open(os.path.join(MODELS_DIR, "feature_config.json")) as f:
            cfg = json.load(f)
        self.feature_cols          = cfg["feature_cols"]
        self.feature_display_names = cfg["feature_display_names"]
        self.global_shap_importance = cfg["global_shap_importance"]
        self._loaded = True

    def predict(self, features: dict[str, Any]) -> dict:
        self.load()
        
        if not ML_AVAILABLE:
            # Rule-based fallback for Vercel
            prob = 0.5
            if features.get("compensation_pct", 100) < 50: prob += 0.2
            if features.get("num_legal_cases", 0) > 0: prob += 0.2
            prob = min(prob, 0.95)
            risk_score = round(prob * 100, 1)
            
            if risk_score >= 70:
                risk_category = "High"
            elif risk_score >= 40:
                risk_category = "Medium"
            else:
                risk_category = "Low"
                
            factors = [
                {"feature": "compensation_pct", "display_name": "Compensation Paid %", "value": features.get("compensation_pct", 0), "shap_value": 1.5 if features.get("compensation_pct", 100) < 50 else -0.5, "direction": "increases_risk" if features.get("compensation_pct", 100) < 50 else "decreases_risk"},
                {"feature": "num_legal_cases", "display_name": "Legal Cases", "value": features.get("num_legal_cases", 0), "shap_value": 1.2 if features.get("num_legal_cases", 0) > 0 else -0.2, "direction": "increases_risk" if features.get("num_legal_cases", 0) > 0 else "decreases_risk"}
            ]
        else:
            X          = pd.DataFrame([features])[self.feature_cols]
            prob       = float(self.model.predict_proba(X)[0][1])
            risk_score = round(prob * 100, 1)

            if risk_score >= 70:
                risk_category = "High"
            elif risk_score >= 40:
                risk_category = "Medium"
            else:
                risk_category = "Low"

            shap_vals = self.explainer.shap_values(X)[0]
            factors   = []
            for feat, sv in zip(self.feature_cols, shap_vals):
                factors.append({
                    "feature":      feat,
                    "display_name": self.feature_display_names.get(feat, feat),
                    "value":        float(X[feat].iloc[0]),
                    "shap_value":   round(float(sv), 4),
                    "direction":    "increases_risk" if sv > 0 else "decreases_risk",
                })
            factors.sort(key=lambda x: abs(x["shap_value"]), reverse=True)

        recommendations  = _apply_rules(features)
        expected_delay   = _estimate_delay_days(features, prob)

        return {
            "delay_probability":   round(prob, 4),
            "risk_score":          risk_score,
            "risk_category":       risk_category,
            "top_factors":         factors[:8],
            "recommendations":     recommendations,
            "rules_triggered":     _triggered_rules(features),
            "expected_delay_days": expected_delay["days"],
            "expected_delay_label": expected_delay["label"],
            "model_confidence":    expected_delay["confidence"],
        }

    def get_global_importance(self) -> list[dict]:
        self.load()
        return [
            {"feature": k, "display_name": self.feature_display_names.get(k, k), "importance": v}
            for k, v in sorted(self.global_shap_importance.items(), key=lambda x: x[1], reverse=True)
        ]


# ─── Rule engine (all 8 CSV rules) ───────────────────────────────────────────────

def _triggered_rules(f: dict) -> list[str]:
    """Return list of rule IDs that fire for this feature set."""
    triggered = []
    if f.get("compensation_pct", 100) < 50:
        triggered.append("R-01")
    if f.get("rr_completion_pct", 100) < 50:
        triggered.append("R-02")
    if f.get("num_legal_cases", 0) >= 3 or f.get("ownership_conflicts", 0) >= 3:
        triggered.append("R-03")
    if f.get("documentation_pct", 100) < 60:
        triggered.append("R-04")
    if f.get("stakeholder_response_pct", 100) < 50:
        triggered.append("R-05")
    if f.get("award_overdue", 0) == 1:
        triggered.append("R-06")
    # R-07: compensation substantially incomplete AND possession pending
    if f.get("compensation_pct", 100) < 50 and f.get("possession_pct", 100) < 50:
        triggered.append("R-07")
    # R-08: repeated missed updates / missing data
    if f.get("days_since_update", 0) > 90 or f.get("officer_responsiveness", 10) < 4:
        triggered.append("R-08")
    return triggered


def _apply_rules(f: dict) -> list[str]:
    """
    Apply all 8 rules from SIH_Land_Acquisition_Recommendation_Rules.csv.
    Returns up to 4 recommendations, one per triggered rule, priority-ordered.
    """
    recs = []

    # R-01 — Compensation risk
    comp = f.get("compensation_pct", 100)
    if comp < 50:
        months = f.get("compensation_pending_months", 0)
        recs.append(
            f"R-01 | Compensation only {comp}% disbursed"
            + (f" ({months} months pending)" if months > 0 else "")
            + " — prioritize payment blockers; verify funding availability, "
              "award details and notice delivery."
        )

    # R-02 — R&R risk
    rr = f.get("rr_completion_pct", 100)
    if rr < 50:
        recs.append(
            f"R-02 | R&R only {rr}% complete — prioritize unresolved R&R actions "
            "and affected-family follow-up."
        )

    # R-03 — Legal risk
    cases     = f.get("num_legal_cases", 0)
    conflicts = f.get("ownership_conflicts", 0)
    if cases >= 3 or conflicts >= 3:
        recs.append(
            f"R-03 | {cases} legal case(s) and {conflicts} ownership conflict(s) "
            "— escalate for legal/record review and track dispute age."
        )

    # R-04 — Documentation risk
    doc = f.get("documentation_pct", 100)
    if doc < 60:
        recs.append(
            f"R-04 | Documentation only {doc}% complete — trigger document and "
            "survey validation before next milestone."
        )

    # R-05 — Stakeholder risk
    shr = f.get("stakeholder_response_pct", 100)
    if shr < 50:
        recs.append(
            f"R-05 | Only {shr}% stakeholder response — increase communication/"
            "consultation and track objections/grievances."
        )

    # R-06 — Award overdue
    if f.get("award_overdue", 0) == 1:
        days_stuck = f.get("days_in_current_stage", 0)
        recs.append(
            f"R-06 | Award milestone overdue ({days_stuck} days in stage) — "
            "escalate milestone delay and review causes/required extension process."
        )

    # R-07 — Possession blocked by incomplete compensation
    if comp < 50 and f.get("possession_pct", 100) < 50:
        if "R-01" not in [r[:4] for r in recs]:   # avoid duplicate if R-01 already added
            recs.append(
                f"R-07 | Compensation {comp}% and possession {f.get('possession_pct',0)}% both incomplete "
                "— do not treat possession as ready; prioritize prerequisites and record handover status."
            )
        else:
            # Add possession-specific note if R-01 already present
            recs.append(
                f"R-07 | Possession {f.get('possession_pct',0)}% while compensation incomplete "
                "— record actual handover status; possession cannot proceed without full award."
            )

    # R-08 — Governance / data freshness
    days_update  = f.get("days_since_update", 0)
    officer_score = f.get("officer_responsiveness", 10)
    if days_update > 90 or officer_score < 4:
        detail = []
        if days_update > 90:
            detail.append(f"no system update in {days_update} days")
        if officer_score < 4:
            detail.append(f"officer responsiveness {officer_score}/10")
        recs.append(
            f"R-08 | Governance gap ({', '.join(detail)}) — escalate data completeness "
            "and assign responsible owner for update cadence."
        )

    # If nothing fired, give a clean all-clear
    if not recs:
        recs.append("No critical risk rules triggered — monitor regularly and maintain update cadence.")

    return recs[:4]   # cap at 4


# Singleton
predictor = DelayPredictor()


def _estimate_delay_days(f: dict, prob: float) -> dict:
    """
    Estimate expected total delay in calendar days for the project.

    Logic:
    - Start from expected remaining stage durations
    - Apply delay multipliers based on risk drivers
    - Return days + human label + model confidence band
    """
    # Expected days per remaining stage (benchmark)
    STAGE_EXPECTED = [60, 90, 120, 90, 60, 180]
    current_idx = int(f.get("current_stage_index", 0))

    # Sum remaining expected days from current stage onward
    remaining_expected = sum(STAGE_EXPECTED[current_idx:])

    # Already spent in current stage (excess = delay already happening)
    days_stuck   = f.get("days_in_current_stage", 0)
    stage_budget = STAGE_EXPECTED[current_idx] if current_idx < len(STAGE_EXPECTED) else 90
    excess_days  = max(0, days_stuck - stage_budget)

    # Multiplier from risk drivers
    multiplier = 1.0
    if f.get("compensation_pct", 100) < 50:
        multiplier += 0.4
    if f.get("rr_completion_pct", 100) < 50:
        multiplier += 0.3
    if f.get("num_legal_cases", 0) >= 3 or f.get("ownership_conflicts", 0) >= 3:
        multiplier += 0.5
    if f.get("documentation_pct", 100) < 60:
        multiplier += 0.25
    if f.get("stakeholder_response_pct", 100) < 50:
        multiplier += 0.2
    if f.get("award_overdue", 0):
        multiplier += 0.35
    if not f.get("budget_released", True):
        multiplier += 0.3
    if f.get("days_since_last_action", 0) > 180:
        multiplier += 0.2
    if f.get("officer_responsiveness", 10) < 4:
        multiplier += 0.25

    # Scale multiplier by probability (low risk → closer to expected baseline)
    effective_mult = 1.0 + (multiplier - 1.0) * prob

    estimated_days = int(round(remaining_expected * effective_mult + excess_days))

    # Human-readable label
    if estimated_days <= 180:
        label = f"~{estimated_days} days (within 6 months)"
    elif estimated_days <= 365:
        label = f"~{estimated_days} days (~{round(estimated_days/30)} months)"
    elif estimated_days <= 730:
        label = f"~{round(estimated_days/30)} months (~{round(estimated_days/365, 1)} years)"
    else:
        label = f"~{round(estimated_days/365, 1)} years (severe delay likely)"

    # Confidence band: ± 20% at high probability, ± 40% at low
    band_pct  = 0.20 + (1 - prob) * 0.20
    conf_low  = int(estimated_days * (1 - band_pct))
    conf_high = int(estimated_days * (1 + band_pct))
    confidence = f"{conf_low}–{conf_high} days"

    return {
        "days":       estimated_days,
        "label":      label,
        "confidence": confidence,
        "remaining_expected_baseline": remaining_expected,
    }
