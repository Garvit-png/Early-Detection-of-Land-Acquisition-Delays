"""
Synthetic Data Generator for Land Acquisition Projects
Generates 5000 realistic Indian land acquisition project records
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import json
import os

random.seed(42)
np.random.seed(42)

# ─── Indian Geography ───────────────────────────────────────────────────────────

STATES_DISTRICTS = {
    "Uttar Pradesh": {
        "districts": ["Lucknow", "Agra", "Varanasi", "Kanpur", "Allahabad", "Meerut", "Noida", "Ghaziabad", "Mathura", "Aligarh"],
        "lat_range": (23.9, 30.4), "lon_range": (77.1, 84.6),
        "delay_bias": 0.70  # historically slow
    },
    "Bihar": {
        "districts": ["Patna", "Gaya", "Muzaffarpur", "Bhagalpur", "Darbhanga", "Purnia", "Ara", "Hajipur", "Chapra", "Sitamarhi"],
        "lat_range": (24.3, 27.5), "lon_range": (83.3, 88.3),
        "delay_bias": 0.72
    },
    "Rajasthan": {
        "districts": ["Jaipur", "Jodhpur", "Udaipur", "Kota", "Ajmer", "Bikaner", "Alwar", "Bharatpur", "Sikar", "Nagaur"],
        "lat_range": (23.1, 30.2), "lon_range": (69.5, 78.3),
        "delay_bias": 0.55
    },
    "Maharashtra": {
        "districts": ["Mumbai", "Pune", "Nagpur", "Nashik", "Aurangabad", "Solapur", "Amravati", "Kolhapur", "Thane", "Latur"],
        "lat_range": (15.6, 22.1), "lon_range": (72.6, 80.9),
        "delay_bias": 0.45
    },
    "Gujarat": {
        "districts": ["Ahmedabad", "Surat", "Vadodara", "Rajkot", "Bhavnagar", "Jamnagar", "Gandhinagar", "Anand", "Mehsana", "Bharuch"],
        "lat_range": (20.1, 24.7), "lon_range": (68.2, 74.5),
        "delay_bias": 0.38
    },
    "Madhya Pradesh": {
        "districts": ["Bhopal", "Indore", "Gwalior", "Jabalpur", "Ujjain", "Rewa", "Satna", "Sagar", "Ratlam", "Dewas"],
        "lat_range": (21.1, 26.9), "lon_range": (74.0, 82.8),
        "delay_bias": 0.60
    },
    "West Bengal": {
        "districts": ["Kolkata", "Howrah", "North 24 Parganas", "South 24 Parganas", "Bardhaman", "Murshidabad", "Nadia", "Malda", "Jalpaiguri", "Darjeeling"],
        "lat_range": (21.5, 27.2), "lon_range": (85.8, 89.9),
        "delay_bias": 0.62
    },
    "Odisha": {
        "districts": ["Bhubaneswar", "Cuttack", "Berhampur", "Sambalpur", "Rourkela", "Brahmapur", "Puri", "Koraput", "Balasore", "Kendujhar"],
        "lat_range": (17.8, 22.6), "lon_range": (81.4, 87.5),
        "delay_bias": 0.58
    },
    "Jharkhand": {
        "districts": ["Ranchi", "Jamshedpur", "Dhanbad", "Bokaro", "Deoghar", "Hazaribagh", "Giridih", "Ramgarh", "Chaibasa", "Dumka"],
        "lat_range": (21.9, 25.3), "lon_range": (83.3, 87.9),
        "delay_bias": 0.68
    },
    "Karnataka": {
        "districts": ["Bengaluru", "Mysuru", "Hubballi", "Mangaluru", "Belagavi", "Davangere", "Ballari", "Tumakuru", "Shivamogga", "Vijayapura"],
        "lat_range": (11.6, 18.5), "lon_range": (74.0, 78.6),
        "delay_bias": 0.42
    },
    "Tamil Nadu": {
        "districts": ["Chennai", "Coimbatore", "Madurai", "Tiruchirappalli", "Salem", "Tirunelveli", "Erode", "Vellore", "Thoothukudi", "Dindigul"],
        "lat_range": (8.1, 13.6), "lon_range": (76.2, 80.3),
        "delay_bias": 0.40
    },
    "Andhra Pradesh": {
        "districts": ["Visakhapatnam", "Vijayawada", "Guntur", "Tirupati", "Kakinada", "Nellore", "Kurnool", "Rajahmundry", "Anantapur", "Kadapa"],
        "lat_range": (12.4, 19.9), "lon_range": (76.8, 84.8),
        "delay_bias": 0.50
    },
    "Telangana": {
        "districts": ["Hyderabad", "Warangal", "Nizamabad", "Karimnagar", "Khammam", "Nalgonda", "Medak", "Mahbubnagar", "Adilabad", "Rangareddy"],
        "lat_range": (15.8, 19.9), "lon_range": (77.2, 81.3),
        "delay_bias": 0.48
    },
    "Punjab": {
        "districts": ["Ludhiana", "Amritsar", "Jalandhar", "Patiala", "Bathinda", "Mohali", "Pathankot", "Hoshiarpur", "Firozpur", "Moga"],
        "lat_range": (29.5, 32.5), "lon_range": (73.9, 76.9),
        "delay_bias": 0.44
    },
    "Haryana": {
        "districts": ["Faridabad", "Gurugram", "Hisar", "Rohtak", "Ambala", "Karnal", "Sonipat", "Panipat", "Yamunanagar", "Bhiwani"],
        "lat_range": (27.6, 30.9), "lon_range": (74.5, 77.6),
        "delay_bias": 0.47
    }
}

PROJECT_TYPES = [
    "National Highway", "State Highway", "Railway Line", "Metro Rail",
    "Expressway", "Dam / Reservoir", "Irrigation Canal", "Industrial Corridor",
    "Power Plant", "Solar Park", "Transmission Line", "Airport Expansion",
    "Port Development", "Smart City", "Housing Scheme"
]

PROJECT_TYPE_DELAY_BIAS = {
    "National Highway": 0.50,
    "State Highway": 0.55,
    "Railway Line": 0.48,
    "Metro Rail": 0.42,
    "Expressway": 0.52,
    "Dam / Reservoir": 0.72,  # most complex
    "Irrigation Canal": 0.65,
    "Industrial Corridor": 0.55,
    "Power Plant": 0.58,
    "Solar Park": 0.35,  # usually faster
    "Transmission Line": 0.40,
    "Airport Expansion": 0.45,
    "Port Development": 0.43,
    "Smart City": 0.38,
    "Housing Scheme": 0.60
}

ACQUISITION_STAGES = [
    "Section 11 Notification",   # initial notification
    "Section 19 Declaration",    # formal declaration
    "Award Passed",              # compensation determined
    "Compensation Disbursed",    # money paid
    "Possession Taken",          # land physically taken
    "R&R Completed"              # rehabilitation done
]

DELAY_REASONS = [
    "Legal dispute filed by landowner",
    "Compensation amount contested in court",
    "Budget not released by state government",
    "Bank account mismatch for beneficiary",
    "Pending revenue records update",
    "Forest department NOC pending",
    "Environment clearance pending",
    "Multiple ownership claims on same plot",
    "R&R colony construction not started",
    "Beneficiaries refusing relocation",
    "Inter-departmental coordination pending",
    "District collector approval pending",
    "State level committee approval pending",
    "Survey and measurement disputed",
    "Encroachment on acquired land"
]


def random_date(start: datetime, end: datetime) -> datetime:
    delta = end - start
    return start + timedelta(days=random.randint(0, delta.days))


def generate_project(project_id: int) -> dict:
    # Pick state and district
    state = random.choice(list(STATES_DISTRICTS.keys()))
    state_data = STATES_DISTRICTS[state]
    district = random.choice(state_data["districts"])

    lat = round(random.uniform(*state_data["lat_range"]), 6)
    lon = round(random.uniform(*state_data["lon_range"]), 6)

    project_type = random.choice(PROJECT_TYPES)

    # Project start date: between 2015 and 2023
    start_date = random_date(datetime(2015, 1, 1), datetime(2023, 6, 1))

    # Land area in hectares
    land_area_ha = round(random.uniform(5, 2000), 2)

    # Number of affected families
    families_affected = int(land_area_ha * random.uniform(0.5, 4))
    families_affected = max(10, min(families_affected, 5000))

    # ─── Compute delay probability from biases ──────────────────────────────────
    base_delay_prob = (
        state_data["delay_bias"] * 0.4 +
        PROJECT_TYPE_DELAY_BIAS[project_type] * 0.3 +
        random.uniform(0, 0.3)  # random noise
    )
    base_delay_prob = min(base_delay_prob, 0.97)

    # ─── Generate correlated features ───────────────────────────────────────────

    # Legal disputes: higher for delayed projects
    has_legal_dispute = 1 if random.random() < (base_delay_prob * 0.8) else 0
    num_legal_cases = 0
    if has_legal_dispute:
        num_legal_cases = random.randint(1, 15)
        base_delay_prob = min(base_delay_prob + 0.10, 0.97)

    # Compensation disbursement percentage
    if base_delay_prob > 0.65:
        compensation_pct = round(random.uniform(10, 70), 1)
    else:
        compensation_pct = round(random.uniform(50, 100), 1)

    compensation_pending_months = 0
    if compensation_pct < 80:
        compensation_pending_months = random.randint(1, 36)
        if compensation_pending_months > 12:
            base_delay_prob = min(base_delay_prob + 0.08, 0.97)

    # R&R completion percentage
    if base_delay_prob > 0.65:
        rr_completion_pct = round(random.uniform(0, 60), 1)
    else:
        rr_completion_pct = round(random.uniform(40, 100), 1)

    if rr_completion_pct < 50 and families_affected > 200:
        base_delay_prob = min(base_delay_prob + 0.07, 0.97)

    # Pending approvals count
    pending_approvals = random.randint(0, 8)
    if base_delay_prob > 0.6:
        pending_approvals = random.randint(2, 12)

    # Days since last approval action (inactivity = bad sign)
    if base_delay_prob > 0.65:
        days_since_last_action = random.randint(60, 730)
    else:
        days_since_last_action = random.randint(0, 90)

    # Pending notifications (Section 11, 19, etc.)
    pending_notifications = random.randint(0, 3)
    if base_delay_prob > 0.6:
        pending_notifications = random.randint(1, 5)

    # Current stage
    if base_delay_prob > 0.7:
        # Stuck early
        current_stage_idx = random.randint(0, 3)
    else:
        current_stage_idx = random.randint(2, 5)

    current_stage = ACQUISITION_STAGES[current_stage_idx]

    # Days in current stage
    if base_delay_prob > 0.65:
        days_in_current_stage = random.randint(90, 1200)
    else:
        days_in_current_stage = random.randint(10, 180)

    # Budget released flag
    budget_released = 1 if random.random() > (base_delay_prob * 0.5) else 0

    # Inter-departmental NOCs pending
    noc_pending_count = random.randint(0, 5)
    if base_delay_prob > 0.6:
        noc_pending_count = random.randint(1, 8)

    # Possession percentage
    if current_stage_idx >= 4:
        possession_pct = round(random.uniform(50, 100), 1)
    elif base_delay_prob > 0.65:
        possession_pct = round(random.uniform(0, 40), 1)
    else:
        possession_pct = round(random.uniform(20, 80), 1)

    # Total land cost (in Crores INR)
    land_cost_cr = round(land_area_ha * random.uniform(0.5, 50), 2)

    # Amount paid so far
    amount_paid_cr = round(land_cost_cr * (compensation_pct / 100), 2)

    # Project total value (in Crores INR)
    project_value_cr = round(land_cost_cr * random.uniform(2, 20), 2)

    # Historical delay rate in the district (simulated)
    district_historical_delay_rate = round(state_data["delay_bias"] + random.uniform(-0.1, 0.1), 2)
    district_historical_delay_rate = max(0.1, min(district_historical_delay_rate, 0.95))

    # Number of previous projects in district that got delayed
    prev_projects_district = random.randint(5, 50)
    prev_delayed_district = int(prev_projects_district * district_historical_delay_rate)

    # Officer responsiveness score (1–10, lower = more delays)
    officer_responsiveness = round(10 - (base_delay_prob * 8) + random.uniform(-1, 1), 1)
    officer_responsiveness = max(1.0, min(officer_responsiveness, 10.0))

    # ─── Final label: is_delayed ─────────────────────────────────────────────────
    # Add final noise
    final_delay_prob = base_delay_prob + random.uniform(-0.05, 0.05)
    final_delay_prob = max(0.05, min(final_delay_prob, 0.97))
    is_delayed = 1 if random.random() < final_delay_prob else 0

    # Risk score (0–100), correlated with delay probability
    risk_score = round(final_delay_prob * 100 + random.uniform(-5, 5), 1)
    risk_score = max(0, min(risk_score, 100))

    # Risk category
    if risk_score >= 70:
        risk_category = "High"
    elif risk_score >= 40:
        risk_category = "Medium"
    else:
        risk_category = "Low"

    # Top delay reasons (if high risk)
    top_delay_reasons = []
    if has_legal_dispute:
        top_delay_reasons.append("Legal dispute filed")
    if compensation_pct < 50:
        top_delay_reasons.append(f"Only {compensation_pct}% compensation disbursed")
    if compensation_pending_months > 6:
        top_delay_reasons.append(f"Compensation pending for {compensation_pending_months} months")
    if rr_completion_pct < 40:
        top_delay_reasons.append(f"Only {rr_completion_pct}% R&R completed")
    if pending_approvals > 4:
        top_delay_reasons.append(f"{pending_approvals} approvals still pending")
    if days_since_last_action > 180:
        top_delay_reasons.append(f"No action for {days_since_last_action} days")
    if noc_pending_count > 3:
        top_delay_reasons.append(f"{noc_pending_count} inter-dept NOCs pending")
    if not budget_released:
        top_delay_reasons.append("Budget not released")

    # Project name
    type_abbr = {
        "National Highway": "NH", "State Highway": "SH", "Railway Line": "RLY",
        "Metro Rail": "METRO", "Expressway": "EXP", "Dam / Reservoir": "DAM",
        "Irrigation Canal": "CANAL", "Industrial Corridor": "IND",
        "Power Plant": "PWR", "Solar Park": "SOLAR", "Transmission Line": "TXLINE",
        "Airport Expansion": "ARPT", "Port Development": "PORT",
        "Smart City": "SC", "Housing Scheme": "HS"
    }
    project_name = f"{type_abbr[project_type]}-{district[:3].upper()}-{project_id:04d}"

    return {
        "project_id": f"PRJ{project_id:05d}",
        "project_name": project_name,
        "project_type": project_type,
        "state": state,
        "district": district,
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "land_area_ha": land_area_ha,
        "families_affected": families_affected,
        "current_stage": current_stage,
        "current_stage_index": current_stage_idx,
        "days_in_current_stage": days_in_current_stage,
        "days_since_last_action": days_since_last_action,
        "pending_approvals": pending_approvals,
        "pending_notifications": pending_notifications,
        "has_legal_dispute": has_legal_dispute,
        "num_legal_cases": num_legal_cases,
        "compensation_pct": compensation_pct,
        "compensation_pending_months": compensation_pending_months,
        "rr_completion_pct": rr_completion_pct,
        "possession_pct": possession_pct,
        "budget_released": budget_released,
        "noc_pending_count": noc_pending_count,
        "land_cost_cr": land_cost_cr,
        "amount_paid_cr": amount_paid_cr,
        "project_value_cr": project_value_cr,
        "district_historical_delay_rate": district_historical_delay_rate,
        "prev_projects_district": prev_projects_district,
        "prev_delayed_district": prev_delayed_district,
        "officer_responsiveness": officer_responsiveness,
        "delay_probability": round(final_delay_prob, 4),
        "risk_score": risk_score,
        "risk_category": risk_category,
        "is_delayed": is_delayed,
        "top_delay_reasons": json.dumps(top_delay_reasons[:3])  # top 3 reasons
    }


def main():
    print("Generating 5000 synthetic land acquisition project records...")
    records = [generate_project(i + 1) for i in range(5000)]
    df = pd.DataFrame(records)

    # ─── Save raw data ───────────────────────────────────────────────────────────
    raw_path = os.path.join(os.path.dirname(__file__), "raw", "projects_raw.csv")
    df.to_csv(raw_path, index=False)
    print(f"Raw data saved: {raw_path}  ({len(df)} rows)")

    # ─── Save processed (ML-ready) data — drop non-feature columns ──────────────
    feature_cols = [
        "land_area_ha", "families_affected", "current_stage_index",
        "days_in_current_stage", "days_since_last_action", "pending_approvals",
        "pending_notifications", "has_legal_dispute", "num_legal_cases",
        "compensation_pct", "compensation_pending_months", "rr_completion_pct",
        "possession_pct", "budget_released", "noc_pending_count",
        "land_cost_cr", "amount_paid_cr", "project_value_cr",
        "district_historical_delay_rate", "prev_delayed_district",
        "officer_responsiveness", "is_delayed"
    ]

    df_processed = df[feature_cols].copy()

    # Encode project_type and state as category codes for ML
    df_processed["project_type_code"] = df["project_type"].astype("category").cat.codes
    df_processed["state_code"] = df["state"].astype("category").cat.codes

    proc_path = os.path.join(os.path.dirname(__file__), "processed", "projects_ml.csv")
    df_processed.to_csv(proc_path, index=False)
    print(f"Processed data saved: {proc_path}  ({len(df_processed)} rows, {len(df_processed.columns)} features)")

    # ─── Save label encoders mapping ─────────────────────────────────────────────
    mappings = {
        "project_type": dict(enumerate(df["project_type"].astype("category").cat.categories.tolist())),
        "state": dict(enumerate(df["state"].astype("category").cat.categories.tolist())),
        "acquisition_stages": {i: s for i, s in enumerate(ACQUISITION_STAGES)}
    }
    mappings_path = os.path.join(os.path.dirname(__file__), "processed", "label_mappings.json")
    with open(mappings_path, "w") as f:
        json.dump(mappings, f, indent=2)
    print(f"Label mappings saved: {mappings_path}")

    # ─── Print quick summary ─────────────────────────────────────────────────────
    print("\n=== Dataset Summary ===")
    print(f"Total projects     : {len(df)}")
    print(f"Delayed projects   : {df['is_delayed'].sum()} ({df['is_delayed'].mean()*100:.1f}%)")
    print(f"High risk          : {(df['risk_category']=='High').sum()}")
    print(f"Medium risk        : {(df['risk_category']=='Medium').sum()}")
    print(f"Low risk           : {(df['risk_category']=='Low').sum()}")
    print(f"States covered     : {df['state'].nunique()}")
    print(f"Project types      : {df['project_type'].nunique()}")
    print(f"Avg land area (ha) : {df['land_area_ha'].mean():.1f}")
    print(f"Avg families       : {df['families_affected'].mean():.0f}")
    print("\nRisk by project type:")
    print(df.groupby("project_type")["is_delayed"].mean().sort_values(ascending=False).to_string())


if __name__ == "__main__":
    main()
