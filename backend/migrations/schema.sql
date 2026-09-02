-- ============================================================
-- Land Acquisition Delay Predictor — Full Database Schema
-- PostgreSQL 16+
-- Run: psql -U postgres -d land_acquisition -f schema.sql
-- ============================================================

-- ─── Extensions ──────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS postgis;   -- optional, for geo queries

-- ─── Enums ───────────────────────────────────────────────────
DO $$ BEGIN
  CREATE TYPE user_role AS ENUM ('central', 'state', 'district');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE risk_category AS ENUM ('Low', 'Medium', 'High');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE acquisition_stage AS ENUM (
    'Section 11 Notification',
    'Section 19 Declaration',
    'Award Passed',
    'Compensation Disbursed',
    'Possession Taken',
    'R&R Completed'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ─── Users ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id                SERIAL PRIMARY KEY,
    username          VARCHAR(64)  UNIQUE NOT NULL,
    email             VARCHAR(128) UNIQUE NOT NULL,
    hashed_password   VARCHAR(256) NOT NULL,
    full_name         VARCHAR(128),
    role              user_role    NOT NULL DEFAULT 'district',
    state             VARCHAR(64),
    district          VARCHAR(64),
    is_active         BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    last_login        TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role     ON users(role);

-- ─── Projects ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS projects (
    id                              SERIAL PRIMARY KEY,
    project_id                      VARCHAR(16)  UNIQUE NOT NULL,
    project_name                    VARCHAR(128) NOT NULL,
    project_type                    VARCHAR(64)  NOT NULL,
    state                           VARCHAR(64)  NOT NULL,
    district                        VARCHAR(64)  NOT NULL,
    latitude                        DOUBLE PRECISION,
    longitude                       DOUBLE PRECISION,
    start_date                      VARCHAR(16),

    -- Land details
    land_area_ha                    DOUBLE PRECISION,
    families_affected               INTEGER,

    -- Acquisition progress
    current_stage                   VARCHAR(64),
    current_stage_index             INTEGER,
    days_in_current_stage           INTEGER,
    days_since_last_action          INTEGER,
    pending_approvals               INTEGER,
    pending_notifications           INTEGER,

    -- Legal
    has_legal_dispute               BOOLEAN DEFAULT FALSE,
    num_legal_cases                 INTEGER DEFAULT 0,

    -- Financial
    compensation_pct                DOUBLE PRECISION,
    compensation_pending_months     INTEGER,
    rr_completion_pct               DOUBLE PRECISION,
    possession_pct                  DOUBLE PRECISION,
    budget_released                 BOOLEAN DEFAULT TRUE,
    noc_pending_count               INTEGER,
    land_cost_cr                    DOUBLE PRECISION,
    amount_paid_cr                  DOUBLE PRECISION,
    project_value_cr                DOUBLE PRECISION,

    -- Historical / district context
    district_historical_delay_rate  DOUBLE PRECISION,
    prev_delayed_district           INTEGER,
    officer_responsiveness          DOUBLE PRECISION,

    -- ML encoding
    project_type_code               INTEGER,
    state_code                      INTEGER,

    -- ML outputs (updated on each scoring)
    delay_probability               DOUBLE PRECISION,
    risk_score                      DOUBLE PRECISION,
    risk_category                   risk_category,
    top_delay_reasons               JSONB,
    shap_factors                    JSONB,
    recommendations                 JSONB,
    last_scored_at                  TIMESTAMPTZ,

    -- Ground truth
    is_delayed                      BOOLEAN DEFAULT FALSE,

    created_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_projects_state          ON projects(state);
CREATE INDEX IF NOT EXISTS idx_projects_district        ON projects(district);
CREATE INDEX IF NOT EXISTS idx_projects_risk_category   ON projects(risk_category);
CREATE INDEX IF NOT EXISTS idx_projects_risk_score      ON projects(risk_score DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_projects_project_type    ON projects(project_type);
CREATE INDEX IF NOT EXISTS idx_projects_current_stage   ON projects(current_stage);
CREATE INDEX IF NOT EXISTS idx_projects_last_scored     ON projects(last_scored_at);

-- Composite index for RBAC queries
CREATE INDEX IF NOT EXISTS idx_projects_state_district  ON projects(state, district);

-- ─── Alerts ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS alerts (
    id              SERIAL PRIMARY KEY,
    project_id_fk   INTEGER      NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title           VARCHAR(256) NOT NULL,
    message         TEXT         NOT NULL,
    risk_category   risk_category NOT NULL,
    risk_score      DOUBLE PRECISION,
    is_read         BOOLEAN      NOT NULL DEFAULT FALSE,
    is_resolved     BOOLEAN      NOT NULL DEFAULT FALSE,
    assigned_to     INTEGER      REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    resolved_at     TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_alerts_project     ON alerts(project_id_fk);
CREATE INDEX IF NOT EXISTS idx_alerts_is_read     ON alerts(is_read);
CREATE INDEX IF NOT EXISTS idx_alerts_is_resolved ON alerts(is_resolved);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at  ON alerts(created_at DESC);

-- ─── Audit Logs ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_logs (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER     REFERENCES users(id) ON DELETE SET NULL,
    action      VARCHAR(64) NOT NULL,
    resource    VARCHAR(64),
    resource_id VARCHAR(32),
    detail      TEXT,
    ip_address  VARCHAR(45),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_user_id    ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_action     ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_logs(created_at DESC);

-- ─── Auto-update updated_at on projects ──────────────────────
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_projects_updated_at ON projects;
CREATE TRIGGER trg_projects_updated_at
  BEFORE UPDATE ON projects
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ─── Useful views ─────────────────────────────────────────────

-- High-risk projects summary view
CREATE OR REPLACE VIEW v_high_risk_projects AS
SELECT
    p.project_id,
    p.project_name,
    p.project_type,
    p.state,
    p.district,
    p.risk_score,
    p.risk_category,
    p.delay_probability,
    p.current_stage,
    p.compensation_pct,
    p.rr_completion_pct,
    p.has_legal_dispute,
    p.days_since_last_action,
    p.last_scored_at
FROM projects p
WHERE p.risk_category::text = 'High'
ORDER BY p.risk_score DESC NULLS LAST;

-- District-level summary view
CREATE OR REPLACE VIEW v_district_summary AS
SELECT
    state,
    district,
    COUNT(*)                                                    AS total_projects,
    COUNT(*) FILTER (WHERE risk_category::text = 'High')             AS high_risk,
    COUNT(*) FILTER (WHERE risk_category::text = 'Medium')           AS medium_risk,
    COUNT(*) FILTER (WHERE risk_category::text = 'Low')              AS low_risk,
    ROUND(AVG(risk_score)::NUMERIC, 1)                         AS avg_risk_score,
    ROUND(AVG(compensation_pct)::NUMERIC, 1)                   AS avg_compensation_pct,
    COUNT(*) FILTER (WHERE has_legal_dispute = TRUE)           AS projects_with_legal_dispute,
    COUNT(*) FILTER (WHERE is_delayed = TRUE)                  AS confirmed_delayed
FROM projects
GROUP BY state, district
ORDER BY avg_risk_score DESC NULLS LAST;

-- Unresolved high-risk alerts view
CREATE OR REPLACE VIEW v_pending_alerts AS
SELECT
    a.id          AS alert_id,
    a.title,
    a.risk_score,
    a.created_at,
    p.project_id,
    p.project_name,
    p.state,
    p.district
FROM alerts a
JOIN projects p ON a.project_id_fk = p.id
WHERE a.is_resolved = FALSE
ORDER BY a.risk_score DESC NULLS LAST, a.created_at DESC;
