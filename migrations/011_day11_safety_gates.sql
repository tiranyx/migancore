-- Day 11 — Safety Gates: Tool Policy Taxonomy + Enforcement Foundation
-- Run manually: psql -U ado_app -d ado -f 011_day11_safety_gates.sql

-- ============================================================
-- 1. TOOL POLICY SCHEMA
-- ============================================================

ALTER TABLE tools ADD COLUMN IF NOT EXISTS risk_level VARCHAR(16) NOT NULL DEFAULT 'medium'
    CHECK (risk_level IN ('low', 'medium', 'high', 'critical'));

ALTER TABLE tools ADD COLUMN IF NOT EXISTS policy JSONB NOT NULL DEFAULT '{}';

ALTER TABLE tools ADD COLUMN IF NOT EXISTS max_calls_per_day INT NOT NULL DEFAULT 1000;

-- ============================================================
-- 2. UPDATE SEED DATA WITH POLICY
-- ============================================================

-- web_search: read_only + open_world, low risk
UPDATE tools SET
    risk_level = 'low',
    policy = '{"classes":["read_only","open_world"],"requires_approval":false,"sandbox_required":false,"allowed_plans":["free","pro","enterprise"]}',
    max_calls_per_day = 100
WHERE name = 'web_search';

-- memory_search: read_only, low risk
UPDATE tools SET
    risk_level = 'low',
    policy = '{"classes":["read_only"],"requires_approval":false,"sandbox_required":false,"allowed_plans":["free","pro","enterprise"]}',
    max_calls_per_day = 1000
WHERE name = 'memory_search';

-- memory_write: write, low risk
UPDATE tools SET
    risk_level = 'low',
    policy = '{"classes":["write"],"requires_approval":false,"sandbox_required":false,"allowed_plans":["free","pro","enterprise"]}',
    max_calls_per_day = 500
WHERE name = 'memory_write';

-- http_get: open_world, medium risk
UPDATE tools SET
    risk_level = 'medium',
    policy = '{"classes":["open_world"],"requires_approval":false,"sandbox_required":false,"allowed_plans":["pro","enterprise"]}',
    max_calls_per_day = 200
WHERE name = 'http_get';

-- read_file: read_only, medium risk (filesystem access)
UPDATE tools SET
    risk_level = 'medium',
    policy = '{"classes":["read_only"],"requires_approval":true,"sandbox_required":false,"allowed_plans":["pro","enterprise"]}',
    max_calls_per_day = 50
WHERE name = 'read_file';

-- python_repl: destructive + sandbox_required, critical risk
UPDATE tools SET
    risk_level = 'critical',
    policy = '{"classes":["destructive","sandbox_required"],"requires_approval":true,"sandbox_required":true,"allowed_plans":["enterprise"]}',
    max_calls_per_day = 10
WHERE name = 'python_repl';

-- spawn_agent: destructive, high risk
UPDATE tools SET
    risk_level = 'high',
    policy = '{"classes":["destructive"],"requires_approval":true,"sandbox_required":false,"allowed_plans":["pro","enterprise"]}',
    max_calls_per_day = 20
WHERE name = 'spawn_agent';

-- ============================================================
-- 3. TENANT MESSAGE QUOTA TRACKING
-- ============================================================

ALTER TABLE tenants ADD COLUMN IF NOT EXISTS messages_today INT NOT NULL DEFAULT 0;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS messages_day_reset TIMESTAMPTZ;

-- ============================================================
-- 4. AUDIT EVENT TYPE EXTENSION
-- ============================================================

-- policy_violation events will be logged into audit_events table
-- (no schema change needed — audit_events.type is VARCHAR(32))

-- ============================================================
-- 5. INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_tools_risk_level ON tools(risk_level);
CREATE INDEX IF NOT EXISTS idx_tools_policy ON tools USING GIN (policy);
