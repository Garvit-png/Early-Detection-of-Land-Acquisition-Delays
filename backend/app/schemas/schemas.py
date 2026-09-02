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


class ProjectOut(ProjectBase):
    id: int
    delay_probability: Optional[float] = None
    risk_score: Optional[float] = None
    risk_category: Optional[str] = None
    top_delay_reasons: Optional[Any] = None
    shap_factors: Optional[Any] = None
    recommendations: Optional[Any] = None
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
    scored_at: datetime


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
