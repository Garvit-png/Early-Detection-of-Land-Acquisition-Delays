"""
Synthetic Data Generator — Land Acquisition Projects
5000 records aligned with SIH_Land_Acquisition_Recommendation_Rules.csv
New fields: documentation_pct, stakeholder_response_pct, ownership_conflicts
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import json
import os

random.seed(42)
np.random.seed(42)

STATES_DISTRICTS = {
    "Uttar Pradesh": {
        "districts": ["Lucknow","Agra","Varanasi","Kanpur","Allahabad","Meerut","Noida","Ghaziabad","Mathura","Aligarh"],
        "lat_range": (23.9, 30.4), "lon_range": (77.1, 84.6), "delay_bias": 0.70
    },
    "Bihar": {
        "districts": ["Patna","Gaya","Muzaffarpur","Bhagalpur","Darbhanga","Purnia","Ara","Hajipur","Chapra","Sitamarhi"],
        "lat_range": (24.3, 27.5), "lon_range": (83.3, 88.3), "delay_bias": 0.72
    },
    "Rajasthan": {
        "districts": ["Jaipur","Jodhpur","Udaipur","Kota","Ajmer","Bikaner","Alwar","Bharatpur","Sikar","Nagaur"],
        "lat_range": (23.1, 30.2), "lon_range": (69.5, 78.3), "delay_bias": 0.55
    },
    "Maharashtra": {
        "districts": ["Mumbai","Pune","Nagpur","Nashik","Aurangabad","Solapur","Amravati","Kolhapur","Thane","Latur"],
        "lat_range": (15.6, 22.1), "lon_range": (72.6, 80.9), "delay_bias": 0.45
    },
    "Gujarat": {
        "districts": ["Ahmedabad","Surat","Vadodara","Rajkot","Bhavnagar","Jamnagar","Gandhinagar","Anand","Mehsana","Bharuch"],
        "lat_range": (20.1, 24.7), "lon_range": (68.2, 74.5), "delay_bias": 0.38
    },
    "Madhya Pradesh": {
        "districts": ["Bhopal","Indore","Gwalior","Jabalpur","Ujjain","Rewa","Satna","Sagar","Ratlam","Dewas"],
        "lat_range": (21.1, 26.9), "lon_range": (74.0, 82.8), "delay_bias": 0.60
    },
    "West Bengal": {
        "districts": ["Kolkata","Howrah","North 24 Parganas","South 24 Parganas","Bardhaman","Murshidabad","Nadia","Malda","Jalpaiguri","Darjeeling"],
        "lat_range": (21.5, 27.2), "lon_range": (85.8, 89.9), "delay_bias": 0.62
    },
    "Odisha": {
        "districts": ["Bhubaneswar","Cuttack","Berhampur","Sambalpur","Rourkela","Brahmapur","Puri","Koraput","Balasore","Kendujhar"],
        "lat_range": (17.8, 22.6), "lon_range": (81.4, 87.5), "delay_bias": 0.58
    },
    "Jharkhand": {
        "districts": ["Ranchi","Jamshedpur","Dhanbad","Bokaro","Deoghar","Hazaribagh","Giridih","Ramgarh","Chaibasa","Dumka"],
        "lat_range": (21.9, 25.3), "lon_range": (83.3, 87.9), "delay_bias": 0.68
    },
    "Karnataka": {
        "districts": ["Bengaluru","Mysuru","Hubballi","Mangaluru","Belagavi","Davangere","Ballari","Tumakuru","Shivamogga","Vijayapura"],
        "lat_range": (11.6, 18.5), "lon_range": (74.0, 78.6), "delay_bias": 0.42
    },
    "Tamil Nadu": {
        "districts": ["Chennai","Coimbatore","Madurai","Tiruchirappalli","Salem","Tirunelveli","Erode","Vellore","Thoothukudi","Dindigul"],
        "lat_range": (8.1, 13.6), "lon_range": (76.2, 80.3), "delay_bias": 0.40
    },
    "Andhra Pradesh": {
        "districts": ["Visakhapatnam","Vijayawada","Guntur","Tirupati","Kakinada","Nellore","Kurnool","Rajahmundry","Anantapur","Kadapa"],
        "lat_range": (12.4, 19.9), "lon_range": (76.8, 84.8), "delay_bias": 0.50
    },
    "Telangana": {
        "districts": ["Hyderabad","Warangal","Nizamabad","Karimnagar","Khammam","Nalgonda","Medak","Mahbubnagar","Adilabad","Rangareddy"],
        "lat_range": (15.8, 19.9), "lon_range": (77.2, 81.3), "delay_bias": 0.48
    },
    "Punjab": {
        "districts": ["Ludhiana","Amritsar","Jalandhar","Patiala","Bathinda","Mohali","Pathankot","Hoshiarpur","Firozpur","Moga"],
        "lat_range": (29.5, 32.5), "lon_range": (73.9, 76.9), "delay_bias": 0.44
    },
    "Haryana": {
        "districts": ["Faridabad","Gurugram","Hisar","Rohtak","Ambala","Karnal","Sonipat","Panipat","Yamunanagar","Bhiwani"],
        "lat_range": (27.6, 30.9), "lon_range": (74.5, 77.6), "delay_bias": 0.47
    },
}

PROJECT_TYPES = [
    "National Highway","State Highway","Railway Line","Metro Rail","Expressway",
    "Dam / Reservoir","Irrigation Canal","Industrial Corridor","Power Plant",
    "Solar Park","Transmission Line","Airport Expansion","Port Development",
    "Smart City","Housing Scheme",
]

PROJECT_TYPE_DELAY_BIAS = {
    "National Highway": 0.50, "State Highway": 0.55, "Railway Line": 0.48,
    "Metro Rail": 0.42,       "Expressway": 0.52,    "Dam / Reservoir": 0.72,
    "Irrigation Canal": 0.65, "Industrial Corridor": 0.55, "Power Plant": 0.58,
    "Solar Park": 0.35,       "Transmission Line": 0.40,   "Airport Expansion": 0.45,
    "Port Development": 0.43, "Smart City": 0.38,   "Housing Scheme": 0.60,
}

ACQUISITION_STAGES = [
    "Section 11 Notification", "Section 19 Declaration", "Award Passed",
    "Compensation Disbursed",  "Possession Taken",        "R&R Completed",
]

TYPE_ABBR = {
    "National Highway":"NH","State Highway":"SH","Railway Line":"RLY",
    "Metro Rail":"METRO","Expressway":"EXP","Dam / Reservoir":"DAM",
    "Irrigation Canal":"CANAL","Industrial Corridor":"IND","Power Plant":"PWR",
    "Solar Park":"SOLAR","Transmission Line":"TXLINE","Airport Expansion":"ARPT",
    "Port Development":"PORT","Smart City":"SC","Housing Scheme":"HS",
}


def rdate(start, end):
    return start + timedelta(days=random.randint(0, (end - start).days))


def generate_project(pid: int) -> dict:
    state      = random.choice(list(STATES_DISTRICTS.keys()))
    sd         = STATES_DISTRICTS[state]
    district   = random.choice(sd["districts"])
    lat        = round(random.uniform(*sd["lat_range"]), 6)
    lon        = round(random.uniform(*sd["lon_range"]), 6)
    ptype      = random.choice(PROJECT_TYPES)
    start_date = rdate(datetime(2015, 1, 1), datetime(2023, 6, 1))

    land_area_ha      = round(random.uniform(5, 2000), 2)
    families_affected = max(10, min(int(land_area_ha * random.uniform(0.5, 4)), 5000))

    # Base delay probability
    bdp = (sd["delay_bias"] * 0.4 + PROJECT_TYPE_DELAY_BIAS[ptype] * 0.3 + random.uniform(0, 0.3))
    bdp = min(bdp, 0.97)

    # ── Legal (R-03) ─────────────────────────────────────────────────────────────
    has_legal_dispute  = 1 if random.random() < bdp * 0.8 else 0
    num_legal_cases    = random.randint(1, 15) if has_legal_dispute else 0
    ownership_conflicts = 0
    if bdp > 0.55:
        ownership_conflicts = random.randint(0, 8)
    else:
        ownership_conflicts = random.randint(0, 2)
    if has_legal_dispute or num_legal_cases >= 3 or ownership_conflicts >= 3:
        bdp = min(bdp + 0.10, 0.97)

    # ── Compensation (R-01) ───────────────────────────────────────────────────────
    compensation_pct = round(random.uniform(10, 70) if bdp > 0.65 else random.uniform(50, 100), 1)
    compensation_pending_months = 0
    if compensation_pct < 80:
        compensation_pending_months = random.randint(1, 36)
        if compensation_pending_months > 12:
            bdp = min(bdp + 0.08, 0.97)

    # ── R&R (R-02) ────────────────────────────────────────────────────────────────
    rr_completion_pct = round(random.uniform(0, 60) if bdp > 0.65 else random.uniform(40, 100), 1)
    if rr_completion_pct < 50 and families_affected > 200:
        bdp = min(bdp + 0.07, 0.97)

    # ── Documentation (R-04) ─────────────────────────────────────────────────────
    # Lower documentation % → higher delay probability
    if bdp > 0.65:
        documentation_pct = round(random.uniform(15, 65), 1)
    else:
        documentation_pct = round(random.uniform(55, 100), 1)
    if documentation_pct < 60:
        bdp = min(bdp + 0.06, 0.97)

    # ── Stakeholder (R-05) ────────────────────────────────────────────────────────
    # % of affected stakeholders who have responded / been consulted
    if bdp > 0.65:
        stakeholder_response_pct = round(random.uniform(10, 55), 1)
    else:
        stakeholder_response_pct = round(random.uniform(45, 100), 1)
    if stakeholder_response_pct < 50:
        bdp = min(bdp + 0.05, 0.97)

    # ── Pending approvals / notifications ────────────────────────────────────────
    pending_approvals    = random.randint(2, 12) if bdp > 0.6 else random.randint(0, 8)
    pending_notifications = random.randint(1, 5) if bdp > 0.6 else random.randint(0, 3)

    # ── Days since last action (R-08: governance) ─────────────────────────────────
    days_since_last_action = random.randint(60, 730) if bdp > 0.65 else random.randint(0, 90)

    # ── Current stage & days in stage (R-06: award overdue) ──────────────────────
    current_stage_idx    = random.randint(0, 3) if bdp > 0.7 else random.randint(2, 5)
    current_stage        = ACQUISITION_STAGES[current_stage_idx]
    days_in_current_stage = random.randint(90, 1200) if bdp > 0.65 else random.randint(10, 180)

    # Expected days per stage (benchmark — for overdue detection)
    STAGE_EXPECTED_DAYS = [60, 90, 120, 90, 60, 180]
    expected_days_in_stage = STAGE_EXPECTED_DAYS[current_stage_idx]
    award_overdue = 1 if (current_stage == "Award Passed" and
                          days_in_current_stage > expected_days_in_stage * 1.5) else 0
    if award_overdue:
        bdp = min(bdp + 0.06, 0.97)

    # ── Budget & NOCs ─────────────────────────────────────────────────────────────
    budget_released   = 1 if random.random() > (bdp * 0.5) else 0
    noc_pending_count = random.randint(1, 8) if bdp > 0.6 else random.randint(0, 5)

    # ── Possession (R-07) ─────────────────────────────────────────────────────────
    if current_stage_idx >= 4:
        possession_pct = round(random.uniform(50, 100), 1)
    elif bdp > 0.65:
        possession_pct = round(random.uniform(0, 40), 1)
    else:
        possession_pct = round(random.uniform(20, 80), 1)

    # ── Financial ─────────────────────────────────────────────────────────────────
    land_cost_cr    = round(land_area_ha * random.uniform(0.5, 50), 2)
    amount_paid_cr  = round(land_cost_cr * (compensation_pct / 100), 2)
    project_value_cr = round(land_cost_cr * random.uniform(2, 20), 2)

    # ── District context ──────────────────────────────────────────────────────────
    dist_delay_rate      = round(max(0.1, min(sd["delay_bias"] + random.uniform(-0.1, 0.1), 0.95)), 2)
    prev_projects_district = random.randint(5, 50)
    prev_delayed_district  = int(prev_projects_district * dist_delay_rate)

    # ── Officer responsiveness (proxy for R-08 governance) ───────────────────────
    officer_responsiveness = round(max(1.0, min(10 - (bdp * 8) + random.uniform(-1, 1), 10.0)), 1)

    # ── days_since_update (R-08: missing progress data) ──────────────────────────
    # How many days since ANY field was last updated in the system
    if bdp > 0.65:
        days_since_update = random.randint(30, 400)
    else:
        days_since_update = random.randint(0, 60)
    if days_since_update > 90:
        bdp = min(bdp + 0.04, 0.97)

    # ── Final label ───────────────────────────────────────────────────────────────
    fdp       = max(0.05, min(bdp + random.uniform(-0.05, 0.05), 0.97))
    is_delayed = 1 if random.random() < fdp else 0
    risk_score = round(max(0, min(fdp * 100 + random.uniform(-5, 5), 100)), 1)
    risk_category = "High" if risk_score >= 70 else ("Medium" if risk_score >= 40 else "Low")

    # ── Top delay reasons (human-readable) ───────────────────────────────────────
    reasons = []
    if compensation_pct < 50:               reasons.append(f"Only {compensation_pct}% compensation disbursed (R-01)")
    if rr_completion_pct < 50:              reasons.append(f"Only {rr_completion_pct}% R&R completed (R-02)")
    if num_legal_cases >= 3 or ownership_conflicts >= 3:
        reasons.append(f"{num_legal_cases} legal case(s), {ownership_conflicts} ownership conflict(s) (R-03)")
    if documentation_pct < 60:             reasons.append(f"Documentation only {documentation_pct}% complete (R-04)")
    if stakeholder_response_pct < 50:      reasons.append(f"Only {stakeholder_response_pct}% stakeholder response (R-05)")
    if award_overdue:                       reasons.append("Award milestone materially overdue (R-06)")
    if days_since_update > 90:             reasons.append(f"No system update for {days_since_update} days (R-08)")

    project_name = f"{TYPE_ABBR[ptype]}-{district[:3].upper()}-{pid:04d}"

    return {
        # Identifiers
        "project_id": f"PRJ{pid:05d}",
        "project_name": project_name,
        "project_type": ptype,
        "state": state,
        "district": district,
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date.strftime("%Y-%m-%d"),
        # Scale
        "land_area_ha": land_area_ha,
        "families_affected": families_affected,
        # Stage
        "current_stage": current_stage,
        "current_stage_index": current_stage_idx,
        "days_in_current_stage": days_in_current_stage,
        "days_since_last_action": days_since_last_action,
        "days_since_update": days_since_update,
        "award_overdue": award_overdue,
        # Approvals
        "pending_approvals": pending_approvals,
        "pending_notifications": pending_notifications,
        "noc_pending_count": noc_pending_count,
        "budget_released": budget_released,
        # Legal (R-03)
        "has_legal_dispute": has_legal_dispute,
        "num_legal_cases": num_legal_cases,
        "ownership_conflicts": ownership_conflicts,
        # Compensation (R-01)
        "compensation_pct": compensation_pct,
        "compensation_pending_months": compensation_pending_months,
        # R&R (R-02)
        "rr_completion_pct": rr_completion_pct,
        # Documentation (R-04)
        "documentation_pct": documentation_pct,
        # Stakeholder (R-05)
        "stakeholder_response_pct": stakeholder_response_pct,
        # Possession (R-07)
        "possession_pct": possession_pct,
        # Financial
        "land_cost_cr": land_cost_cr,
        "amount_paid_cr": amount_paid_cr,
        "project_value_cr": project_value_cr,
        # District context
        "district_historical_delay_rate": dist_delay_rate,
        "prev_projects_district": prev_projects_district,
        "prev_delayed_district": prev_delayed_district,
        # Governance (R-08)
        "officer_responsiveness": officer_responsiveness,
        # Labels
        "delay_probability": round(fdp, 4),
        "risk_score": risk_score,
        "risk_category": risk_category,
        "is_delayed": is_delayed,
        "top_delay_reasons": json.dumps(reasons[:3]),
    }


def main():
    print("Generating 5000 synthetic land acquisition project records...")
    records = [generate_project(i + 1) for i in range(5000)]
    df      = pd.DataFrame(records)

    # ── Raw CSV ───────────────────────────────────────────────────────────────────
    raw_path = os.path.join(os.path.dirname(__file__), "raw", "projects_raw.csv")
    df.to_csv(raw_path, index=False)
    print(f"Raw data saved   : {raw_path}  ({len(df)} rows, {len(df.columns)} cols)")

    # ── ML-ready CSV (26 features) ────────────────────────────────────────────────
    feature_cols = [
        "land_area_ha", "families_affected", "current_stage_index",
        "days_in_current_stage", "days_since_last_action", "days_since_update",
        "award_overdue", "pending_approvals", "pending_notifications",
        "noc_pending_count", "budget_released",
        "has_legal_dispute", "num_legal_cases", "ownership_conflicts",
        "compensation_pct", "compensation_pending_months",
        "rr_completion_pct", "documentation_pct", "stakeholder_response_pct",
        "possession_pct",
        "land_cost_cr", "amount_paid_cr", "project_value_cr",
        "district_historical_delay_rate", "prev_delayed_district",
        "officer_responsiveness",
        "is_delayed",
    ]
    df_ml = df[feature_cols].copy()
    df_ml["project_type_code"] = df["project_type"].astype("category").cat.codes
    df_ml["state_code"]        = df["state"].astype("category").cat.codes

    proc_path = os.path.join(os.path.dirname(__file__), "processed", "projects_ml.csv")
    df_ml.to_csv(proc_path, index=False)
    print(f"Processed data   : {proc_path}  ({len(df_ml)} rows, {len(df_ml.columns)} features)")

    # ── Label mappings ────────────────────────────────────────────────────────────
    mappings = {
        "project_type": dict(enumerate(df["project_type"].astype("category").cat.categories.tolist())),
        "state":        dict(enumerate(df["state"].astype("category").cat.categories.tolist())),
        "acquisition_stages": {i: s for i, s in enumerate([
            "Section 11 Notification","Section 19 Declaration","Award Passed",
            "Compensation Disbursed","Possession Taken","R&R Completed",
        ])},
    }
    map_path = os.path.join(os.path.dirname(__file__), "processed", "label_mappings.json")
    with open(map_path, "w") as f:
        json.dump(mappings, f, indent=2)
    print(f"Label mappings   : {map_path}")

    # ── Summary ───────────────────────────────────────────────────────────────────
    print(f"\n=== Dataset Summary ===")
    print(f"Total projects     : {len(df)}")
    print(f"Delayed            : {df['is_delayed'].sum()} ({df['is_delayed'].mean()*100:.1f}%)")
    print(f"High / Med / Low   : {(df['risk_category']=='High').sum()} / {(df['risk_category']=='Medium').sum()} / {(df['risk_category']=='Low').sum()}")
    print(f"documentation<60%  : {(df['documentation_pct']<60).sum()}")
    print(f"stakeholder<50%    : {(df['stakeholder_response_pct']<50).sum()}")
    print(f"ownership_conflicts: {df['ownership_conflicts'].sum()} total across all projects")
    print(f"award_overdue      : {df['award_overdue'].sum()}")
    print(f"Features in ML CSV : {len(df_ml.columns)}")


if __name__ == "__main__":
    main()
