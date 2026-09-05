"""Pydantic request/response schemas."""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, EmailStr, Field


# ─── Auth ────────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str
    state: Optional[str] = None
    district: Optional[str] = None


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = None
    role: str = "district"
    state: Optional[str] = None
    district: Optional[str] = None


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    role: str
    state: Optional[str]
    district: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Projects ────────────────────────────────────────────────────────────────────

class ProjectBase(BaseModel):
    project_id: str
    project_name: str
    project_type: str
    state: str
    district: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    start_date: Optional[str] = None
    land_area_ha: Optional[float] = None
    families_affected: Optional[int] = None
    current_stage: Optional[str] = None
    current_stage_index: Optional[int] = None
    days_in_current_stage: Optional[int] = None
    days_since_last_action: Optional[int] = None
    pending_approvals: Optional[int] = None
    pending_notifications: Optional[int] = None
    has_legal_dispute: Optional[bool] = None
    num_legal_cases: Optional[int] = None
    ownership_conflicts: Optional[int] = None
    documentation_pct: Optional[float] = None
    stakeholder_response_pct: Optional[float] = None
    days_since_update: Optional[int] = None
    award_overdue: Optional[bool] = None
    compensation_pct: Optional[float] = None
    compensation_pending_months: Optional[int] = None
    rr_completion_pct: Optional[float] = None
    possession_pct: Optional[float] = None
    budget_released: Optional[bool] = None
    noc_pending_count: Optional[int] = None
    land_cost_cr: Optional[float] = None
    amount_paid_cr: Optional[float] = None
    project_value_cr: Optional[float] = None
    is_delayed: Optional[bool] = None
    funding_readiness: Optional[float] = None
    notice_delivery_pct: Optional[float] = None
    mutation_completion_pct: Optional[float] = None


class ProjectOut(ProjectBase):
    id: int
    delay_probability: Optional[float] = None
    risk_score: Optional[float] = None
    risk_category: Optional[str] = None
    top_delay_reasons: Optional[Any] = None
    shap_factors: Optional[Any] = None
    recommendations: Optional[Any] = None
    rules_triggered: Optional[Any] = None
    expected_delay_days: Optional[int] = None
    expected_delay_label: Optional[str] = None
    model_confidence: Optional[str] = None
    last_scored_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectListItem(BaseModel):
    """Lightweight version for list/map views."""
    id: int
    project_id: str
    project_name: str
    project_type: str
    state: str
    district: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    current_stage: Optional[str] = None
    risk_score: Optional[float] = None
    risk_category: Optional[str] = None
    delay_probability: Optional[float] = None
    families_affected: Optional[int] = None
    compensation_pct: Optional[float] = None
    has_legal_dispute: Optional[bool] = None
    last_scored_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProjectFilters(BaseModel):
    state: Optional[str] = None
    district: Optional[str] = None
    project_type: Optional[str] = None
    risk_category: Optional[str] = None
    current_stage: Optional[str] = None
    search: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class ProjectCreate(BaseModel):
    """Payload for submitting a new project — AI scores it immediately on creation."""
    project_name:                 str   = Field(..., min_length=2, max_length=128)
    project_type:                 str
    state:                        str
    district:                     str
    latitude:                     Optional[float] = None
    longitude:                    Optional[float] = None
    start_date:                   Optional[str]   = None

    # Land details
    land_area_ha:                 float = Field(..., gt=0)
    families_affected:            int   = Field(..., ge=0)

    # Acquisition status
    current_stage:                str   = "Section 11 Notification"
    days_in_current_stage:        int   = Field(default=0, ge=0)
    days_since_last_action:       int   = Field(default=0, ge=0)
    pending_approvals:            int   = Field(default=0, ge=0)
    pending_notifications:        int   = Field(default=0, ge=0)

    # Legal
    has_legal_dispute:            bool  = False
    num_legal_cases:              int   = Field(default=0, ge=0)
    ownership_conflicts:          int   = Field(default=0, ge=0)

    # Documentation (R-04)
    documentation_pct:            float = Field(default=75.0, ge=0, le=100)
    # Stakeholder (R-05)
    stakeholder_response_pct:     float = Field(default=75.0, ge=0, le=100)

    # Financial
    compensation_pct:             float = Field(default=0.0, ge=0, le=100)
    compensation_pending_months:  int   = Field(default=0, ge=0)
    rr_completion_pct:            float = Field(default=0.0, ge=0, le=100)
    possession_pct:               float = Field(default=0.0, ge=0, le=100)
    budget_released:              bool  = True
    noc_pending_count:            int   = Field(default=0, ge=0)
    land_cost_cr:                 float = Field(default=0.0, ge=0)
    amount_paid_cr:               float = Field(default=0.0, ge=0)
    project_value_cr:             float = Field(default=0.0, ge=0)

    # Context
    officer_responsiveness:       float = Field(default=5.0, ge=1, le=10)
    # FM-12 / FM-13 / FM-14
    funding_readiness:            float = Field(default=75.0, ge=0, le=100)
    notice_delivery_pct:          float = Field(default=75.0, ge=0, le=100)
    mutation_completion_pct:      float = Field(default=0.0,  ge=0, le=100)


class ProjectCreateResponse(BaseModel):
    """Returned immediately after project creation — includes live AI score."""
    project_id:        str
    project_name:      str
    state:             str
    district:          str
    # Live AI result
    delay_probability: float
    risk_score:        float
    risk_category:     str
    top_factors:       list[dict]
    recommendations:   list[str]
    scored_at:         datetime
    message:           str = "Project submitted and scored successfully"


# ─── Prediction ──────────────────────────────────────────────────────────────────

class ShapFactor(BaseModel):
    feature: str
    display_name: str
    value: float
    shap_value: float
    direction: str  # "increases_risk" | "decreases_risk"


class PredictionResponse(BaseModel):
    project_id: str
    delay_probability: float
    risk_score: float
    risk_category: str
    top_factors: list[ShapFactor]
    recommendations: list[str]
    rules_triggered: list[str] = []
    expected_delay_days: Optional[int] = None
    expected_delay_label: Optional[str] = None
    model_confidence: Optional[str] = None
    scored_at: datetime


# ─── Risk History ─────────────────────────────────────────────────────────────

class RiskHistoryItem(BaseModel):
    id: int
    risk_score: float
    delay_probability: float
    risk_category: str
    rules_triggered: Optional[list] = []
    trigger: Optional[str] = None
    notes: Optional[str] = None
    scored_at: datetime

    class Config:
        from_attributes = True


# ─── Action Items ─────────────────────────────────────────────────────────────

class ActionItemCreate(BaseModel):
    title:             str   = Field(..., min_length=3)
    description:       Optional[str] = None
    rule_id:           Optional[str] = None
    officer_decision:  str   = "accept"   # accept | modify | override
    override_note:     Optional[str] = None
    priority:          str   = "medium"   # low | medium | high | critical
    due_date:          Optional[datetime] = None

class ActionItemUpdate(BaseModel):
    status:            Optional[str] = None   # open | in_progress | completed | overridden
    completion_note:   Optional[str] = None
    priority:          Optional[str] = None
    due_date:          Optional[datetime] = None
    assigned_to:       Optional[int] = None
    officer_decision:  Optional[str] = None
    override_note:     Optional[str] = None

class ActionItemOut(BaseModel):
    id: int
    project_id_fk: int
    rule_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    officer_decision: Optional[str] = None
    override_note: Optional[str] = None
    assigned_to: Optional[int] = None
    assigned_to_name: Optional[str] = None
    assigned_by: Optional[int] = None
    status: str
    priority: str
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    completion_note: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    project_name: Optional[str] = None
    project_id: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None

    class Config:
        from_attributes = True


# ─── Similar Projects ─────────────────────────────────────────────────────────

class SimilarProject(BaseModel):
    project_id: str
    project_name: str
    project_type: str
    state: str
    district: str
    risk_score: Optional[float] = None
    risk_category: Optional[str] = None
    delay_probability: Optional[float] = None
    compensation_pct: Optional[float] = None
    is_delayed: Optional[bool] = None
    similarity_score: float   # 0–1

    class Config:
        from_attributes = True


# ─── Dashboard ───────────────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_projects: int
    high_risk: int
    medium_risk: int
    low_risk: int
    unscored: int
    delayed_confirmed: int
    avg_risk_score: float
    avg_compensation_pct: float
    avg_rr_completion_pct: float
    projects_with_legal_dispute: int
    by_state: list[dict]
    by_project_type: list[dict]
    by_stage: list[dict]
    recent_high_risk: list[dict]


# ─── Alerts ──────────────────────────────────────────────────────────────────────

class AlertOut(BaseModel):
    id: int
    project_id_fk: int
    title: str
    message: str
    risk_category: str
    risk_score: Optional[float] = None
    is_read: bool
    is_resolved: bool
    created_at: datetime
    resolved_at: Optional[datetime] = None
    project_name: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None

    class Config:
        from_attributes = True


class AlertUpdate(BaseModel):
    is_read: Optional[bool] = None
    is_resolved: Optional[bool] = None


# ─── Pagination ──────────────────────────────────────────────────────────────────

class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


# ─── Model / Retraining ──────────────────────────────────────────────────────────

class ModelStatus(BaseModel):
    loaded:        bool
    accuracy:      Optional[float] = None
    roc_auc:       Optional[float] = None
    f1_score:      Optional[float] = None
    train_rows:    Optional[int]   = None
    trained_at:    Optional[str]   = None
    data_source:   Optional[str]   = None
    feature_count: int = 0


class RetrainResponse(BaseModel):
    success:     bool
    accuracy:    float
    roc_auc:     float
    f1_score:    float
    train_rows:  int
    trained_at:  str
    data_source: str
    message:     str
