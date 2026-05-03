-- Day 24 — Tool Expansion: fal.ai image generation + sandboxed file system
-- Run manually: psql -U ado_app -d ado -f 024_day24_tool_expansion.sql
--
-- Adds 3 new tools (write_file, generate_image) and fixes read_file policy
-- which was unintentionally restricted to pro/enterprise + requires_approval.
--
-- Idempotent: uses INSERT ... ON CONFLICT and UPDATE.

-- ============================================================
-- 1. FIX read_file POLICY
-- ============================================================
-- read_file was set to ['pro','enterprise'] + requires_approval=true,
-- which blocked the free tier from using basic file reads. Day 24 reframes
-- this as a low-risk sandboxed operation (workspace path traversal blocked
-- in tool_executor.py via Path.resolve() + relative_to(WORKSPACE_DIR)).

UPDATE tools SET
    risk_level = 'low',
    policy = '{"classes":["read_only"],"requires_approval":false,"sandbox_required":false,"allowed_plans":["free","pro","enterprise"]}',
    max_calls_per_day = 200
WHERE name = 'read_file';

-- ============================================================
-- 2. ADD write_file TOOL
-- ============================================================
-- Sandboxed write to /app/workspace. Path traversal blocked the same way
-- as read_file. 200KB content cap. Free plan allowed (low risk).
-- Note: tools.name has no UNIQUE constraint, so we use WHERE NOT EXISTS
-- pattern instead of ON CONFLICT.

INSERT INTO tools (name, description, schema, handler_type, handler_config, scopes_required, risk_level, policy, max_calls_per_day, is_active, tenant_id)
SELECT
    'write_file',
    'Write content to a file in the agent sandboxed workspace. Creates parent directories automatically.',
    '{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}'::jsonb,
    'builtin', '{}'::jsonb, ARRAY[]::text[],
    'low',
    '{"classes":["write"],"requires_approval":false,"sandbox_required":false,"allowed_plans":["free","pro","enterprise"]}'::jsonb,
    200, true, NULL
WHERE NOT EXISTS (SELECT 1 FROM tools WHERE name = 'write_file');

-- Idempotent UPDATE for re-runs
UPDATE tools SET
    risk_level = 'low',
    policy = '{"classes":["write"],"requires_approval":false,"sandbox_required":false,"allowed_plans":["free","pro","enterprise"]}'::jsonb,
    max_calls_per_day = 200,
    is_active = true
WHERE name = 'write_file';

-- ============================================================
-- 3. ADD generate_image TOOL (fal.ai FLUX schnell)
-- ============================================================
-- External API call (fal.ai). ~$0.003 per image. Rate limit: 100/day on free.
-- requires_approval=false because cost-controlled by max_calls_per_day.

INSERT INTO tools (name, description, schema, handler_type, handler_config, scopes_required, risk_level, policy, max_calls_per_day, is_active, tenant_id)
SELECT
    'generate_image',
    'Generate an image from a text prompt via fal.ai FLUX schnell. Returns URL.',
    '{"type":"object","properties":{"prompt":{"type":"string"},"image_size":{"type":"string"},"num_images":{"type":"integer"}},"required":["prompt"]}'::jsonb,
    'builtin', '{}'::jsonb, ARRAY[]::text[],
    'medium',
    '{"classes":["open_world","write"],"requires_approval":false,"sandbox_required":false,"allowed_plans":["free","pro","enterprise"]}'::jsonb,
    100, true, NULL
WHERE NOT EXISTS (SELECT 1 FROM tools WHERE name = 'generate_image');

UPDATE tools SET
    risk_level = 'medium',
    policy = '{"classes":["open_world","write"],"requires_approval":false,"sandbox_required":false,"allowed_plans":["free","pro","enterprise"]}'::jsonb,
    max_calls_per_day = 100,
    is_active = true
WHERE name = 'generate_image';

-- ============================================================
-- 4. VERIFY
-- ============================================================
-- After running, verify with:
--   SELECT name, risk_level, max_calls_per_day, policy->>'allowed_plans'
--   FROM tools WHERE name IN ('read_file','write_file','generate_image');
--
-- Expected:
--   read_file       | low    | 200 | ["free","pro","enterprise"]
--   write_file      | low    | 200 | ["free","pro","enterprise"]
--   generate_image  | medium | 100 | ["free","pro","enterprise"]
