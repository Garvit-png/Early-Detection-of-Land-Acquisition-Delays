# Predictive Analytics System for Early Detection of Land Acquisition Delays

**Organization:** Ministry of Rural Development — Department of Land Resources (DoLR)  
**Problem Statement:** SIH 2026  
**Tech Stack:** Python · FastAPI · XGBoost · SHAP · PostgreSQL · React · Leaflet.js

---

## What This System Does

Land acquisition is the most common bottleneck in Indian infrastructure projects. This system monitors every ongoing land acquisition project and **predicts delay risk before it happens** — giving officers time to intervene.

- 🔴 **High / Medium / Low risk score** for every project (0–100)
- 🧠 **SHAP-based explanation** — shows *why* a project is at risk (top 8 factors)
- 💡 **Recommended actions** — plain-language next steps for each high-risk project
- 🗺️ **GIS map** — color-coded markers across India (red = high risk)
- 🔔 **Automatic alerts** — generated when risk crosses threshold
- 🔒 **Role-based access** — Central / State / District officers see only their scope
- 📋 **Audit logs** — every view and action is logged

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entry point
│   │   ├── core/
│   │   │   ├── config.py            # Settings from .env
│   │   │   ├── security.py          # JWT + bcrypt
│   │   │   └── deps.py              # Auth dependencies + audit logger
│   │   ├── db/
│   │   │   ├── database.py          # SQLAlchemy engine + session
│   │   │   └── models.py            # ORM models (User, Project, Alert, AuditLog)
│   │   ├── ml/
│   │   │   ├── train_model.py       # XGBoost training script
│   │   │   └── predictor.py         # Singleton predictor with SHAP
│   │   ├── schemas/
│   │   │   └── schemas.py           # Pydantic request/response models
│   │   └── api/routes/
│   │       ├── auth.py              # Login, register, /me
│   │       ├── projects.py          # List, get, filter, CSV import
│   │       ├── predictions.py       # Score project, batch score, feature importance
│   │       ├── dashboard.py         # Aggregated stats for dashboard
│   │       ├── alerts.py            # List, mark read/resolved
│   │       └── audit.py             # Audit log viewer (central only)
│   ├── migrations/
│   │   └── schema.sql               # Full PostgreSQL schema + indexes + views
│   ├── scripts/
│   │   └── seed_db.py               # Creates tables + default users
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx                  # Router + auth context
│   │   ├── index.css                # Global styles
│   │   ├── services/api.js          # Axios client + all API calls
│   │   ├── store/authStore.js       # Auth context + localStorage
│   │   ├── components/shared/
│   │   │   └── Layout.jsx           # Sidebar + topbar
│   │   └── pages/
│   │       ├── LoginPage.jsx
│   │       ├── DashboardPage.jsx    # KPIs + charts
│   │       ├── ProjectsPage.jsx     # Filterable project table
│   │       ├── ProjectDetailPage.jsx # Risk score + SHAP chart + recommendations
│   │       ├── MapPage.jsx          # Leaflet GIS map
│   │       ├── AlertsPage.jsx       # Alert management
│   │       └── AuditPage.jsx        # Audit trail (central only)
│   ├── vite.config.mjs
│   └── package.json
│
├── data/
│   ├── generate_data.py             # Synthetic dataset generator (5000 projects)
│   ├── raw/projects_raw.csv         # Generated raw dataset
│   ├── processed/projects_ml.csv   # ML-ready features
│   └── models/
│       ├── xgb_delay_model.json     # Trained XGBoost model
│       ├── shap_explainer.pkl       # SHAP TreeExplainer
│       ├── model_metrics.json       # Accuracy, AUC, F1 etc.
│       └── feature_config.json     # Feature names + global SHAP importance
│
├── .env.example                     # Environment template
├── .gitignore
└── README.md
```

---

## Setup Instructions

### Prerequisites
- Python 3.9+
- Node.js 18+
- PostgreSQL 16+

### 1. Clone & enter the project
```bash
cd Early-Detection-of-Land-Acquisition-Delays
```

### 2. Create the database
```bash
createdb land_acquisition
```

### 3. Configure environment
```bash
cp .env.example .env
# Edit .env — set your DATABASE_URL and a strong SECRET_KEY
```

### 4. Install Python dependencies
```bash
pip install -r backend/requirements.txt
```

### 5. Seed the database (creates tables + default users)
```bash
python backend/scripts/seed_db.py
```

### 6. Generate synthetic data + train model
```bash
python data/generate_data.py
python backend/app/ml/train_model.py
```

### 7. Start the backend
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### 8. Import project data into DB
```bash
# Get admin token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin@123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Import all 5000 projects
curl -X POST http://localhost:8000/api/projects/import-csv \
  -H "Authorization: Bearer $TOKEN"
```

### 9. Start the frontend
```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

---

## Default Users

| Username           | Password       | Role     | Scope          |
|--------------------|----------------|----------|----------------|
| `admin`            | `Admin@123`    | Central  | All India      |
| `up_officer`       | `State@123`    | State    | Uttar Pradesh  |
| `lucknow_officer`  | `District@123` | District | Lucknow, UP    |
| `mh_officer`       | `State@123`    | State    | Maharashtra    |

---

## API Reference

| Method | Endpoint                              | Description                          |
|--------|---------------------------------------|--------------------------------------|
| POST   | `/api/auth/login`                     | Get JWT token                        |
| POST   | `/api/auth/register`                  | Create new user                      |
| GET    | `/api/auth/me`                        | Current user info                    |
| GET    | `/api/projects`                       | List projects (filterable, paginated)|
| GET    | `/api/projects/map`                   | Lightweight list for GIS map         |
| GET    | `/api/projects/{id}`                  | Single project detail                |
| POST   | `/api/projects/import-csv`            | Bulk import from CSV (central only)  |
| POST   | `/api/predictions/{id}`               | Score a project (runs ML + SHAP)     |
| POST   | `/api/predictions/batch/score-all`    | Score all unscored projects          |
| GET    | `/api/predictions/feature-importance/global` | Global SHAP feature importance |
| GET    | `/api/dashboard/stats`                | Aggregated KPIs for dashboard        |
| GET    | `/api/alerts`                         | List alerts (scoped by role)         |
| GET    | `/api/alerts/unread-count`            | Unread alert count                   |
| PATCH  | `/api/alerts/{id}`                    | Mark read / resolve alert            |
| GET    | `/api/audit`                          | Audit logs (central only)            |

Full interactive docs: **http://localhost:8000/docs**

---

## ML Model Details

| Metric        | Value  |
|---------------|--------|
| Algorithm     | XGBoost (gradient boosted trees) |
| CV ROC-AUC    | 0.62 ± 0.02 |
| Test Accuracy | 0.61   |
| Test F1       | 0.71   |
| Features      | 23     |
| Training rows | 4,000  |
| Explainability | SHAP TreeExplainer |

**Top risk factors (by SHAP importance):**
1. Officer Responsiveness Score
2. Days Since Last Official Action
3. R&R Completion (%)
4. Compensation Disbursed (%)
5. Number of Legal Cases
6. Land Possession (%)
7. Days Stuck in Current Stage
8. Pending Approvals Count

---

## Role-Based Access Control

| Feature                    | Central | State | District |
|----------------------------|---------|-------|----------|
| View all projects           | ✅      | ❌    | ❌       |
| View own state's projects   | ✅      | ✅    | ❌       |
| View own district's projects| ✅      | ✅    | ✅       |
| Batch score projects        | ✅      | ✅    | ❌       |
| Import CSV data             | ✅      | ❌    | ❌       |
| View audit logs             | ✅      | ❌    | ❌       |
| Resolve alerts              | ✅      | ✅    | ✅       |
| Delete alerts               | ✅      | ✅    | ❌       |

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    React Frontend (port 3000)                  │
│  Login → Dashboard → Projects → Map → Alerts → Detail        │
└────────────────────────┬─────────────────────────────────────┘
                         │ REST API (proxied)
┌────────────────────────▼─────────────────────────────────────┐
│                FastAPI Backend (port 8000)                     │
│  Auth (JWT) → Projects → Predictions → Dashboard → Alerts    │
│                         │                                      │
│              ┌──────────▼──────────┐                          │
│              │  XGBoost + SHAP      │                          │
│              │  Predictor (singleton)│                         │
│              └─────────────────────┘                          │
└────────────────────────┬─────────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────────┐
│              PostgreSQL (land_acquisition DB)                  │
│  users · projects · alerts · audit_logs                       │
│  Views: v_high_risk_projects · v_district_summary             │
└──────────────────────────────────────────────────────────────┘
```

---

## Future Scope

- **NLP layer** — parse court judgments and officer notes using BERT/LLM to extract delay signals from unstructured text
- **Continuous retraining** — Apache Airflow pipeline to retrain model monthly as new project outcomes are recorded
- **WhatsApp/SMS alerts** — escalation to field officers via WhatsApp Business API
- **Bhuvan integration** — overlay on ISRO's national GIS platform instead of OpenStreetMap
- **MeghRaj deployment** — host on India's national government cloud (NIC Cloud)
- **OAuth2 SSO** — integrate with existing government identity systems (e-Pramaan)
