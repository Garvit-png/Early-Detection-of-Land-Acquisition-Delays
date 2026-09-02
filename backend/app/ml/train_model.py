"""
XGBoost Model Training Script
Trains delay prediction model and saves it with SHAP explainer
"""

import pandas as pd
import numpy as np
import json
import os
import joblib
import shap
import xgboost as xgb
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import (
    accuracy_score, roc_auc_score, f1_score,
    precision_score, recall_score, classification_report, confusion_matrix
)
from sklearn.preprocessing import StandardScaler

# ─── Paths ───────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "../../.."))
DATA_PATH    = os.path.join(PROJECT_ROOT, "data/processed/projects_ml.csv")
MODELS_DIR   = os.path.join(PROJECT_ROOT, "data/models")
os.makedirs(MODELS_DIR, exist_ok=True)

FEATURE_COLS = [
    "land_area_ha", "families_affected", "current_stage_index",
    "days_in_current_stage", "days_since_last_action", "pending_approvals",
    "pending_notifications", "has_legal_dispute", "num_legal_cases",
    "compensation_pct", "compensation_pending_months", "rr_completion_pct",
    "possession_pct", "budget_released", "noc_pending_count",
    "land_cost_cr", "amount_paid_cr", "project_value_cr",
    "district_historical_delay_rate", "prev_delayed_district",
    "officer_responsiveness", "project_type_code", "state_code"
]
TARGET_COL = "is_delayed"

# Human-readable feature names (for SHAP display)
FEATURE_DISPLAY_NAMES = {
    "land_area_ha": "Land Area (ha)",
    "families_affected": "Families Affected",
    "current_stage_index": "Current Acquisition Stage",
    "days_in_current_stage": "Days Stuck in Current Stage",
    "days_since_last_action": "Days Since Last Official Action",
    "pending_approvals": "Pending Approvals Count",
    "pending_notifications": "Pending Legal Notifications",
    "has_legal_dispute": "Active Legal Dispute",
    "num_legal_cases": "Number of Legal Cases",
    "compensation_pct": "Compensation Disbursed (%)",
    "compensation_pending_months": "Months Compensation Pending",
    "rr_completion_pct": "R&R Completion (%)",
    "possession_pct": "Land Possession (%)",
    "budget_released": "Budget Released",
    "noc_pending_count": "Inter-Dept NOCs Pending",
    "land_cost_cr": "Total Land Cost (Cr)",
    "amount_paid_cr": "Amount Paid So Far (Cr)",
    "project_value_cr": "Project Value (Cr)",
    "district_historical_delay_rate": "District Historical Delay Rate",
    "prev_delayed_district": "Previous Delayed Projects in District",
    "officer_responsiveness": "Officer Responsiveness Score",
    "project_type_code": "Project Type",
    "state_code": "State"
}


def load_data():
    print(f"Loading data from: {DATA_PATH}")
    df = pd.read_csv(DATA_PATH)
    X = df[FEATURE_COLS]
    y = df[TARGET_COL]
    print(f"Dataset: {X.shape[0]} rows, {X.shape[1]} features")
    print(f"Class distribution — Delayed: {y.sum()} ({y.mean()*100:.1f}%), On-time: {(~y.astype(bool)).sum()}")
    return X, y


def train_model(X_train, y_train):
    """Train XGBoost classifier with tuned hyperparameters"""
    model = xgb.XGBClassifier(
        n_estimators=400,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        gamma=0.1,
        reg_alpha=0.1,
        reg_lambda=1.0,
        scale_pos_weight=1,
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=42,
        n_jobs=-1
    )
    model.fit(
        X_train, y_train,
        eval_set=[(X_train, y_train)],
        verbose=False
    )
    return model


def evaluate_model(model, X_test, y_test):
    """Print evaluation metrics"""
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    print("\n=== Model Evaluation ===")
    print(f"Accuracy  : {accuracy_score(y_test, y_pred):.4f}")
    print(f"ROC-AUC   : {roc_auc_score(y_test, y_prob):.4f}")
    print(f"F1 Score  : {f1_score(y_test, y_pred):.4f}")
    print(f"Precision : {precision_score(y_test, y_pred):.4f}")
    print(f"Recall    : {recall_score(y_test, y_pred):.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=["On-Time", "Delayed"]))
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))

    return {
        "accuracy": round(accuracy_score(y_test, y_pred), 4),
        "roc_auc": round(roc_auc_score(y_test, y_prob), 4),
        "f1_score": round(f1_score(y_test, y_pred), 4),
        "precision": round(precision_score(y_test, y_pred), 4),
        "recall": round(recall_score(y_test, y_pred), 4)
    }


def compute_shap(model, X_train, X_test):
    """Compute SHAP values and build explainer"""
    print("\nComputing SHAP values...")
    explainer = shap.TreeExplainer(model)
    # Compute on a sample for speed
    sample_size = min(500, len(X_test))
    X_sample = X_test.iloc[:sample_size]
    shap_values = explainer.shap_values(X_sample)

    # Global feature importance from SHAP
    mean_abs_shap = pd.Series(
        np.abs(shap_values).mean(axis=0),
        index=FEATURE_COLS
    ).sort_values(ascending=False)

    print("\nTop 10 features by SHAP importance:")
    for feat, val in mean_abs_shap.head(10).items():
        display = FEATURE_DISPLAY_NAMES.get(feat, feat)
        print(f"  {display:<40}: {val:.4f}")

    return explainer, mean_abs_shap


def get_project_explanation(model, explainer, project_features: dict) -> dict:
    """
    Given a single project's features dict, return:
    - delay_probability (0-1)
    - risk_score (0-100)
    - risk_category (Low/Medium/High)
    - top_factors: list of {feature, display_name, value, shap_value, direction}
    """
    # Build feature vector
    X = pd.DataFrame([project_features])[FEATURE_COLS]

    # Predict
    prob = float(model.predict_proba(X)[0][1])
    risk_score = round(prob * 100, 1)

    if risk_score >= 70:
        risk_category = "High"
    elif risk_score >= 40:
        risk_category = "Medium"
    else:
        risk_category = "Low"

    # SHAP explanation
    shap_vals = explainer.shap_values(X)[0]  # shape: (n_features,)

    factors = []
    for i, (feat, shap_val) in enumerate(zip(FEATURE_COLS, shap_vals)):
        factors.append({
            "feature": feat,
            "display_name": FEATURE_DISPLAY_NAMES.get(feat, feat),
            "value": float(X[feat].iloc[0]),
            "shap_value": round(float(shap_val), 4),
            "direction": "increases_risk" if shap_val > 0 else "decreases_risk"
        })

    # Sort by absolute SHAP value — top risk drivers first
    factors.sort(key=lambda x: abs(x["shap_value"]), reverse=True)

    return {
        "delay_probability": round(prob, 4),
        "risk_score": risk_score,
        "risk_category": risk_category,
        "top_factors": factors[:8]  # top 8 drivers
    }


def main():
    # 1. Load data
    X, y = load_data()

    # 2. Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"\nTrain: {len(X_train)} | Test: {len(X_test)}")

    # 3. Cross-validation
    print("\nRunning 5-fold cross-validation...")
    cv_model = xgb.XGBClassifier(
        n_estimators=400, max_depth=6, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, min_child_weight=3,
        use_label_encoder=False, eval_metric="logloss",
        random_state=42, n_jobs=-1
    )
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(cv_model, X, y, cv=cv, scoring="roc_auc", n_jobs=-1)
    print(f"CV ROC-AUC: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    # 4. Train final model
    print("\nTraining final model...")
    model = train_model(X_train, y_train)

    # 5. Evaluate
    metrics = evaluate_model(model, X_test, y_test)

    # 6. SHAP explainer
    explainer, mean_abs_shap = compute_shap(model, X_train, X_test)

    # 7. Test single-project explanation
    sample_project = X_test.iloc[0].to_dict()
    explanation = get_project_explanation(model, explainer, sample_project)
    print(f"\nSample prediction: risk_score={explanation['risk_score']}, category={explanation['risk_category']}")
    print("Top 3 risk drivers:")
    for f in explanation["top_factors"][:3]:
        print(f"  {f['display_name']}: SHAP={f['shap_value']:+.4f} ({f['direction']})")

    # 8. Save model artifacts
    model_path    = os.path.join(MODELS_DIR, "xgb_delay_model.json")
    explainer_path = os.path.join(MODELS_DIR, "shap_explainer.pkl")
    metrics_path   = os.path.join(MODELS_DIR, "model_metrics.json")
    features_path  = os.path.join(MODELS_DIR, "feature_config.json")

    model.save_model(model_path)
    joblib.dump(explainer, explainer_path)

    with open(metrics_path, "w") as f:
        json.dump({**metrics, "cv_roc_auc_mean": round(cv_scores.mean(), 4),
                   "cv_roc_auc_std": round(cv_scores.std(), 4)}, f, indent=2)

    with open(features_path, "w") as f:
        json.dump({
            "feature_cols": FEATURE_COLS,
            "feature_display_names": FEATURE_DISPLAY_NAMES,
            "global_shap_importance": {
                k: round(float(v), 4)
                for k, v in mean_abs_shap.items()
            }
        }, f, indent=2)

    print(f"\n=== Saved Artifacts ===")
    print(f"Model      : {model_path}")
    print(f"Explainer  : {explainer_path}")
    print(f"Metrics    : {metrics_path}")
    print(f"Features   : {features_path}")
    print("\nTraining complete!")


if __name__ == "__main__":
    main()
