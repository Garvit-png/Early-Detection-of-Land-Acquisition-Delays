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
        "delay_bias": 0.70,
    },
    "Bihar": {
        "districts": ["Patna","Gaya","Muzaffarpur","Bhagalpur","Darbhanga","Purnia","Ara","Hajipur","Chapra","Sitamarhi"],
        "delay_bias": 0.72,
    },
    "Rajasthan": {
        "districts": ["Jaipur","Jodhpur","Udaipur","Kota","Ajmer","Bikaner","Alwar","Bharatpur","Sikar","Nagaur"],
        "delay_bias": 0.55,
    },
    "Maharashtra": {
        "districts": ["Mumbai","Pune","Nagpur","Nashik","Aurangabad","Solapur","Amravati","Kolhapur","Thane","Latur"],
        "delay_bias": 0.45,
    },
    "Gujarat": {
        "districts": ["Ahmedabad","Surat","Vadodara","Rajkot","Bhavnagar","Jamnagar","Gandhinagar","Anand","Mehsana","Bharuch"],
        "delay_bias": 0.38,
    },
    "Madhya Pradesh": {
        "districts": ["Bhopal","Indore","Gwalior","Jabalpur","Ujjain","Rewa","Satna","Sagar","Ratlam","Dewas"],
        "delay_bias": 0.60,
    },
    "West Bengal": {
        "districts": ["Kolkata","Howrah","North 24 Parganas","South 24 Parganas","Bardhaman","Murshidabad","Nadia","Malda","Jalpaiguri","Darjeeling"],
        "delay_bias": 0.62,
    },
    "Odisha": {
        "districts": ["Bhubaneswar","Cuttack","Berhampur","Sambalpur","Rourkela","Brahmapur","Puri","Koraput","Balasore","Kendujhar"],
        "delay_bias": 0.58,
    },
    "Jharkhand": {
        "districts": ["Ranchi","Jamshedpur","Dhanbad","Bokaro","Deoghar","Hazaribagh","Giridih","Ramgarh","Chaibasa","Dumka"],
        "delay_bias": 0.68,
    },
    "Karnataka": {
        "districts": ["Bengaluru","Mysuru","Hubballi","Mangaluru","Belagavi","Davangere","Ballari","Tumakuru","Shivamogga","Vijayapura"],
        "delay_bias": 0.42,
    },
    "Tamil Nadu": {
        "districts": ["Chennai","Coimbatore","Madurai","Tiruchirappalli","Salem","Tirunelveli","Erode","Vellore","Thoothukudi","Dindigul"],
        "delay_bias": 0.40,
    },
    "Andhra Pradesh": {
        "districts": ["Visakhapatnam","Vijayawada","Guntur","Tirupati","Kakinada","Nellore","Kurnool","Rajahmundry","Anantapur","Kadapa"],
        "delay_bias": 0.50,
    },
    "Telangana": {
        "districts": ["Hyderabad","Warangal","Nizamabad","Karimnagar","Khammam","Nalgonda","Medak","Mahbubnagar","Adilabad","Rangareddy"],
        "delay_bias": 0.48,
    },
    "Punjab": {
        "districts": ["Ludhiana","Amritsar","Jalandhar","Patiala","Bathinda","Mohali","Pathankot","Hoshiarpur","Firozpur","Moga"],
        "delay_bias": 0.44,
    },
    "Haryana": {
        "districts": ["Faridabad","Gurugram","Hisar","Rohtak","Ambala","Karnal","Sonipat","Panipat","Yamunanagar","Bhiwani"],
        "delay_bias": 0.47,
    },
}

# Real district centroids (lat, lon) — jitter applied per-project for spread
DISTRICT_COORDS = {
    # Uttar Pradesh
    "Lucknow":(26.85,80.95),"Agra":(27.18,78.01),"Varanasi":(25.32,83.01),
    "Kanpur":(26.46,80.33),"Allahabad":(25.44,81.84),"Meerut":(28.98,77.71),
    "Noida":(28.54,77.39),"Ghaziabad":(28.67,77.45),"Mathura":(27.49,77.67),
    "Aligarh":(27.88,78.08),
    # Bihar
    "Patna":(25.59,85.14),"Gaya":(24.80,84.99),"Muzaffarpur":(26.12,85.39),
    "Bhagalpur":(25.25,86.97),"Darbhanga":(26.15,85.90),"Purnia":(25.78,87.47),
    "Ara":(25.55,84.66),"Hajipur":(25.69,85.21),"Chapra":(25.78,84.74),
    "Sitamarhi":(26.59,85.48),
    # Rajasthan
    "Jaipur":(26.91,75.79),"Jodhpur":(26.30,73.02),"Udaipur":(24.58,73.68),
    "Kota":(25.18,75.83),"Ajmer":(26.45,74.64),"Bikaner":(28.02,73.31),
    "Alwar":(27.56,76.63),"Bharatpur":(27.22,77.49),"Sikar":(27.61,75.14),
    "Nagaur":(27.20,73.73),
    # Maharashtra
    "Mumbai":(19.08,72.88),"Pune":(18.52,73.86),"Nagpur":(21.15,79.09),
    "Nashik":(19.99,73.79),"Aurangabad":(19.88,75.34),"Solapur":(17.68,75.91),
    "Amravati":(20.93,77.75),"Kolhapur":(16.70,74.24),"Thane":(19.21,72.97),
    "Latur":(18.40,76.56),
    # Gujarat
    "Ahmedabad":(23.02,72.57),"Surat":(21.17,72.83),"Vadodara":(22.31,73.18),
    "Rajkot":(22.30,70.80),"Bhavnagar":(21.76,72.15),"Jamnagar":(22.47,70.07),
    "Gandhinagar":(23.22,72.65),"Anand":(22.56,72.93),"Mehsana":(23.59,72.38),
    "Bharuch":(21.70,72.99),
    # Madhya Pradesh
    "Bhopal":(23.26,77.41),"Indore":(22.72,75.86),"Gwalior":(26.21,78.18),
    "Jabalpur":(23.17,79.94),"Ujjain":(23.18,75.77),"Rewa":(24.53,81.30),
    "Satna":(24.60,80.83),"Sagar":(23.84,78.73),"Ratlam":(23.33,75.04),
    "Dewas":(22.96,76.05),
    # West Bengal
    "Kolkata":(22.57,88.36),"Howrah":(22.59,88.31),"North 24 Parganas":(22.93,88.53),
    "South 24 Parganas":(22.16,88.55),"Bardhaman":(23.23,87.86),"Murshidabad":(24.18,88.27),
    "Nadia":(23.47,88.56),"Malda":(25.01,88.14),"Jalpaiguri":(26.54,88.73),
    "Darjeeling":(27.04,88.27),
    # Odisha
    "Bhubaneswar":(20.30,85.84),"Cuttack":(20.46,85.88),"Berhampur":(19.31,84.79),
    "Sambalpur":(21.47,83.97),"Rourkela":(22.22,84.86),"Brahmapur":(19.31,84.79),
    "Puri":(19.81,85.83),"Koraput":(18.81,82.71),"Balasore":(21.49,86.93),
    "Kendujhar":(21.63,85.58),
    # Jharkhand
    "Ranchi":(23.34,85.31),"Jamshedpur":(22.80,86.20),"Dhanbad":(23.80,86.44),
    "Bokaro":(23.67,86.15),"Deoghar":(24.48,86.70),"Hazaribagh":(23.99,85.36),
    "Giridih":(24.19,86.31),"Ramgarh":(23.63,85.51),"Chaibasa":(22.55,85.80),
    "Dumka":(24.27,87.25),
    # Karnataka
    "Bengaluru":(12.97,77.59),"Mysuru":(12.30,76.65),"Hubballi":(15.36,75.12),
    "Mangaluru":(12.87,74.84),"Belagavi":(15.85,74.50),"Davangere":(14.46,75.92),
    "Ballari":(15.15,76.92),"Tumakuru":(13.34,77.10),"Shivamogga":(13.93,75.57),
    "Vijayapura":(16.83,75.72),
    # Tamil Nadu
    "Chennai":(13.08,80.27),"Coimbatore":(11.02,76.96),"Madurai":(9.93,78.12),
    "Tiruchirappalli":(10.79,78.70),"Salem":(11.65,78.16),"Tirunelveli":(8.73,77.70),
    "Erode":(11.34,77.73),"Vellore":(12.92,79.13),"Thoothukudi":(8.76,78.14),
    "Dindigul":(10.36,77.97),
    # Andhra Pradesh
    "Visakhapatnam":(17.69,83.22),"Vijayawada":(16.51,80.62),"Guntur":(16.30,80.44),
    "Tirupati":(13.63,79.42),"Kakinada":(16.93,82.24),"Nellore":(14.44,79.99),
    "Kurnool":(15.83,78.04),"Rajahmundry":(16.98,81.78),"Anantapur":(14.68,77.60),
    "Kadapa":(14.47,78.82),
    # Telangana
    "Hyderabad":(17.38,78.49),"Warangal":(17.97,79.59),"Nizamabad":(18.67,78.09),
    "Karimnagar":(18.43,79.13),"Khammam":(17.25,80.15),"Nalgonda":(17.05,79.27),
    "Medak":(18.05,78.26),"Mahbubnagar":(16.74,77.98),"Adilabad":(19.67,78.53),
    "Rangareddy":(17.24,78.39),
    # Punjab
    "Ludhiana":(30.90,75.85),"Amritsar":(31.63,74.87),"Jalandhar":(31.33,75.57),
    "Patiala":(30.34,76.39),"Bathinda":(30.21,74.95),"Mohali":(30.70,76.72),
    "Pathankot":(32.27,75.65),"Hoshiarpur":(31.53,75.91),"Firozpur":(30.93,74.61),
    "Moga":(30.82,75.17),
    # Haryana
    "Faridabad":(28.41,77.31),"Gurugram":(28.46,77.03),"Hisar":(29.15,75.72),
    "Rohtak":(28.89,76.61),"Ambala":(30.38,76.78),"Karnal":(29.69,76.99),
    "Sonipat":(28.99,77.02),"Panipat":(29.39,76.97),"Yamunanagar":(30.13,77.27),
    "Bhiwani":(28.79,76.14),
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
    # Use district centroid + small jitter so dots spread across the real India map
    base_lat, base_lon = DISTRICT_COORDS.get(district, (20.0, 78.0))
    lat = round(base_lat + random.uniform(-0.25, 0.25), 6)
    lon = round(base_lon + random.uniform(-0.25, 0.25), 6)
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

    # ── Funding readiness (FM-12 / ADMIN-03 / CAG-03) ────────────────────────────
    # 0–100: how ready is the requiring body to release funds
    if bdp > 0.65:
        funding_readiness = round(random.uniform(10, 60), 1)
    else:
        funding_readiness = round(random.uniform(55, 100), 1)
    if funding_readiness < 50:
        bdp = min(bdp + 0.05, 0.97)

    # ── Notice delivery % (FM-13 / ADMIN-04 / CAG-04) ────────────────────────────
    # % of affected landowners/families who have received formal notices
    if bdp > 0.65:
        notice_delivery_pct = round(random.uniform(20, 70), 1)
    else:
        notice_delivery_pct = round(random.uniform(60, 100), 1)
    if notice_delivery_pct < 60:
        bdp = min(bdp + 0.04, 0.97)

    # ── Mutation completion % (FM-14 / ADMIN-09 / CAG-13) ────────────────────────
    # % of acquired parcels where ownership mutation in land records is complete
    # Only meaningful post-possession; earlier stages default to 0
    if current_stage_idx >= 4:
        mutation_completion_pct = round(random.uniform(30, 95) if bdp > 0.5 else random.uniform(60, 100), 1)
    else:
        mutation_completion_pct = 0.0

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
        # New: FM-12, FM-13, FM-14
        "funding_readiness":        funding_readiness,
        "notice_delivery_pct":      notice_delivery_pct,
        "mutation_completion_pct":  mutation_completion_pct,
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
        "funding_readiness", "notice_delivery_pct", "mutation_completion_pct",
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
