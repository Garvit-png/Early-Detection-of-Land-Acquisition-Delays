"""SQLAlchemy ORM models."""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    Text, ForeignKey, Enum as SAEnum, JSON
)
from sqlalchemy.orm import relationship
import enum

from app.db.database import Base


# ─── Enums ───────────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    CENTRAL   = "central"    # Ministry / DoLR — sees all India
    STATE     = "state"      # State-level official — sees own state
    DISTRICT  = "district"   # District officer — sees own district


class RiskCategory(str, enum.Enum):
    LOW    = "Low"
    MEDIUM = "Medium"
    HIGH   = "High"


# SQLAlchemy Enum types that map to the existing Postgres enums created by schema.sql
# values_callable ensures we send the .value ("central") not .name ("CENTRAL")
_pg_user_role     = SAEnum(UserRole,     name="user_role",     create_type=False,
                           values_callable=lambda x: [e.value for e in x])
_pg_risk_category = SAEnum(RiskCategory, name="risk_category", create_type=False,
                           values_callable=lambda x: [e.value for e in x])


class AcquisitionStage(str, enum.Enum):
    SECTION_11        = "Section 11 Notification"
    SECTION_19        = "Section 19 Declaration"
    AWARD_PASSED      = "Award Passed"
    COMPENSATION_PAID = "Compensation Disbursed"
    POSSESSION_TAKEN  = "Possession Taken"
    RR_COMPLETED      = "R&R Completed"


# ─── Users ───────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    username      = Column(String(64), unique=True, nullable=False, index=True)
    email         = Column(String(128), unique=True, nullable=False)
    hashed_password = Column(String(256), nullable=False)
    full_name     = Column(String(128))
    role          = Column(_pg_user_role, nullable=False, default=UserRole.DISTRICT)
    state         = Column(String(64))     # null for central users
    district      = Column(String(64))     # null for central/state users
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_login    = Column(DateTime, nullable=True)

    audit_logs    = relationship("AuditLog", back_populates="user")
    alerts        = relationship("Alert", back_populates="assigned_to_user")
    actions_assigned = relationship("ActionItem", foreign_keys="ActionItem.assigned_to", back_populates="assignee")
    actions_created  = relationship("ActionItem", foreign_keys="ActionItem.assigned_by",  back_populates="assigner")


# ─── Projects ────────────────────────────────────────────────────────────────────

class Project(Base):
    __tablename__ = "projects"

    id                            = Column(Integer, primary_key=True, index=True)
    project_id                    = Column(String(16), unique=True, nullable=False, index=True)
    project_name                  = Column(String(128), nullable=False)
    project_type                  = Column(String(64), nullable=False)
    state                         = Column(String(64), nullable=False, index=True)
    district                      = Column(String(64), nullable=False, index=True)
    latitude                      = Column(Float)
    longitude                     = Column(Float)
    start_date                    = Column(String(16))
    land_area_ha                  = Column(Float)
    families_affected             = Column(Integer)
    current_stage                 = Column(String(64))
    current_stage_index           = Column(Integer)
    days_in_current_stage         = Column(Integer)
    days_since_last_action        = Column(Integer)
    pending_approvals             = Column(Integer)
    pending_notifications         = Column(Integer)
    has_legal_dispute             = Column(Boolean, default=False)
    num_legal_cases               = Column(Integer, default=0)
    ownership_conflicts           = Column(Integer, default=0)   # R-03
    documentation_pct             = Column(Float, nullable=True) # R-04
    stakeholder_response_pct      = Column(Float, nullable=True) # R-05
    days_since_update             = Column(Integer, default=0)   # R-08
    award_overdue                 = Column(Boolean, default=False) # R-06
    compensation_pct              = Column(Float)
    compensation_pending_months   = Column(Integer)
    rr_completion_pct             = Column(Float)
    possession_pct                = Column(Float)
    budget_released               = Column(Boolean, default=True)
    noc_pending_count             = Column(Integer)
    land_cost_cr                  = Column(Float)
    amount_paid_cr                = Column(Float)
    project_value_cr              = Column(Float)
    district_historical_delay_rate = Column(Float)
    prev_delayed_district         = Column(Integer)
    officer_responsiveness        = Column(Float)
    funding_readiness             = Column(Float, nullable=True)   # FM-12 / CAG-03
    notice_delivery_pct           = Column(Float, nullable=True)   # FM-13 / CAG-04
    mutation_completion_pct       = Column(Float, nullable=True)   # FM-14 / CAG-13
    project_type_code             = Column(Integer)
    state_code                    = Column(Integer)

    # ML outputs (updated periodically)
    delay_probability             = Column(Float, nullable=True)
    risk_score                    = Column(Float, nullable=True)
    risk_category                 = Column(_pg_risk_category, nullable=True)
    top_delay_reasons             = Column(JSON, nullable=True)
    shap_factors                  = Column(JSON, nullable=True)
    recommendations               = Column(JSON, nullable=True)
    rules_triggered               = Column(JSON, nullable=True)  # e.g. ["R-01","R-03"]
    expected_delay_days           = Column(Integer, nullable=True)
    expected_delay_label          = Column(String(128), nullable=True)
    model_confidence              = Column(String(64), nullable=True)
    last_scored_at                = Column(DateTime, nullable=True)

    is_delayed                    = Column(Boolean, default=False)
    created_at                    = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at                    = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                                           onupdate=lambda: datetime.now(timezone.utc))

    alerts                        = relationship("Alert", back_populates="project")
    risk_history                  = relationship("RiskHistory", back_populates="project", order_by="RiskHistory.scored_at")
    action_items                  = relationship("ActionItem", back_populates="project")


# ─── Alerts ──────────────────────────────────────────────────────────────────────

class Alert(Base):
    __tablename__ = "alerts"

    id              = Column(Integer, primary_key=True, index=True)
    project_id_fk   = Column(Integer, ForeignKey("projects.id"), nullable=False)
    title           = Column(String(256), nullable=False)
    message         = Column(Text, nullable=False)
    risk_category   = Column(_pg_risk_category, nullable=False)
    risk_score      = Column(Float)
    is_read         = Column(Boolean, default=False)
    is_resolved     = Column(Boolean, default=False)
    assigned_to     = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at      = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    resolved_at     = Column(DateTime, nullable=True)

    project         = relationship("Project", back_populates="alerts")
    assigned_to_user = relationship("User", back_populates="alerts")


# ─── Audit Logs ──────────────────────────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=True)
    action      = Column(String(64), nullable=False)   # e.g. "LOGIN", "VIEW_PROJECT"
    resource    = Column(String(64), nullable=True)    # e.g. "project", "alert"
    resource_id = Column(String(32), nullable=True)
    detail      = Column(Text, nullable=True)
    ip_address  = Column(String(45), nullable=True)
    created_at  = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user        = relationship("User", back_populates="audit_logs")


# ─── Risk History ─────────────────────────────────────────────────────────────
# Every time a project is scored/re-scored, one row is appended here.
# This gives us the time-series needed for the "Risk History" chart in the flow.

class RiskHistory(Base):
    __tablename__ = "risk_history"

    id               = Column(Integer, primary_key=True, index=True)
    project_id_fk    = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    risk_score       = Column(Float, nullable=False)
    delay_probability = Column(Float, nullable=False)
    risk_category    = Column(_pg_risk_category, nullable=False)
    rules_triggered  = Column(JSON, nullable=True)
    scored_by        = Column(Integer, ForeignKey("users.id"), nullable=True)   # null = system
    trigger          = Column(String(32), default="manual")                     # manual | update | batch | submit
    notes            = Column(Text, nullable=True)
    scored_at        = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    project          = relationship("Project", back_populates="risk_history")
    scorer           = relationship("User", foreign_keys=[scored_by])


# ─── Action Items ─────────────────────────────────────────────────────────────
# Officer review → Accept/Modify/Override → Assign Action → Action Tracking

class ActionStatus(str, enum.Enum):
    OPEN       = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED  = "completed"
    OVERRIDDEN = "overridden"

_pg_action_status = SAEnum(ActionStatus, name="actionstatus", create_type=True,
                           values_callable=lambda x: [e.value for e in x])


class ActionItem(Base):
    __tablename__ = "action_items"

    id             = Column(Integer, primary_key=True, index=True)
    project_id_fk  = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    # Which rule/recommendation triggered this
    rule_id        = Column(String(8), nullable=True)    # e.g. "R-01"
    title          = Column(String(256), nullable=False)
    description    = Column(Text, nullable=True)
    # Officer review outcome
    officer_decision = Column(String(16), default="accept")   # accept | modify | override
    override_note  = Column(Text, nullable=True)              # reason if overridden
    # Assignment
    assigned_to    = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_by    = Column(Integer, ForeignKey("users.id"), nullable=True)
    # Status tracking
    status         = Column(_pg_action_status, default=ActionStatus.OPEN, index=True)
    priority       = Column(String(8), default="medium")      # low | medium | high | critical
    due_date       = Column(DateTime, nullable=True)
    completed_at   = Column(DateTime, nullable=True)
    completion_note = Column(Text, nullable=True)
    # Timestamps
    created_at     = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at     = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                            onupdate=lambda: datetime.now(timezone.utc))

    project        = relationship("Project", back_populates="action_items")
    assignee       = relationship("User", foreign_keys=[assigned_to])
    assigner       = relationship("User", foreign_keys=[assigned_by])
