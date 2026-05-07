-- Day 71d v3: Plain INSERTs with ON CONFLICT support via NULLS NOT DISTINCT (PG15+)
-- Falls back to delete-then-insert if needed.

-- Step 1: Wipe global tools (tenant_id IS NULL) to start fresh
DELETE FROM tools WHERE tenant_id IS NULL;

-- Step 2: Insert all 29 tools
INSERT INTO tools (id, tenant_id, name, schema, handler_type, handler_config,
                   scopes_required, is_active, risk_level, policy, max_calls_per_day, created_at) VALUES
  (gen_random_uuid(), NULL, 'memory_write',       '{}'::jsonb, 'builtin', '{}'::jsonb, '{}'::text[], true, 'low',      '{}'::jsonb, 1000, NOW()),
  (gen_random_uuid(), NULL, 'memory_search',      '{}'::jsonb, 'builtin', '{}'::jsonb, '{}'::text[], true, 'low',      '{}'::jsonb, 5000, NOW()),
  (gen_random_uuid(), NULL, 'generate_image',     '{}'::jsonb, 'builtin', '{}'::jsonb, '{}'::text[], true, 'medium',   '{}'::jsonb,  100, NOW()),
  (gen_random_uuid(), NULL, 'read_file',          '{}'::jsonb, 'builtin', '{}'::jsonb, '{}'::text[], true, 'low',      '{}'::jsonb, 1000, NOW()),
  (gen_random_uuid(), NULL, 'write_file',         '{}'::jsonb, 'builtin', '{}'::jsonb, '{}'::text[], true, 'low',      '{}'::jsonb,  500, NOW()),
  (gen_random_uuid(), NULL, 'text_to_speech',     '{}'::jsonb, 'builtin', '{}'::jsonb, '{}'::text[], true, 'medium',   '{}'::jsonb,  200, NOW()),
  (gen_random_uuid(), NULL, 'analyze_image',      '{}'::jsonb, 'builtin', '{}'::jsonb, '{}'::text[], true, 'medium',   '{}'::jsonb,  100, NOW()),
  (gen_random_uuid(), NULL, 'web_read',           '{}'::jsonb, 'builtin', '{}'::jsonb, '{}'::text[], true, 'low',      '{}'::jsonb,  500, NOW()),
  (gen_random_uuid(), NULL, 'export_pdf',         '{}'::jsonb, 'builtin', '{}'::jsonb, '{}'::text[], true, 'medium',   '{}'::jsonb,  100, NOW()),
  (gen_random_uuid(), NULL, 'export_slides',      '{}'::jsonb, 'builtin', '{}'::jsonb, '{}'::text[], true, 'medium',   '{}'::jsonb,   50, NOW()),
  (gen_random_uuid(), NULL, 'onamix_get',         '{}'::jsonb, 'builtin', '{}'::jsonb, '{}'::text[], true, 'low',      '{}'::jsonb,  500, NOW()),
  (gen_random_uuid(), NULL, 'onamix_search',      '{}'::jsonb, 'builtin', '{}'::jsonb, '{}'::text[], true, 'low',      '{}'::jsonb,  500, NOW()),
  (gen_random_uuid(), NULL, 'onamix_scrape',      '{}'::jsonb, 'builtin', '{}'::jsonb, '{}'::text[], true, 'medium',   '{}'::jsonb,  100, NOW()),
  (gen_random_uuid(), NULL, 'onamix_post',        '{}'::jsonb, 'builtin', '{}'::jsonb, '{}'::text[], true, 'high',     '{"requires_confirmation": true}'::jsonb,   50, NOW()),
  (gen_random_uuid(), NULL, 'onamix_crawl',       '{}'::jsonb, 'builtin', '{}'::jsonb, '{}'::text[], true, 'medium',   '{}'::jsonb,   30, NOW()),
  (gen_random_uuid(), NULL, 'onamix_history',     '{}'::jsonb, 'builtin', '{}'::jsonb, '{}'::text[], true, 'low',      '{}'::jsonb,  200, NOW()),
  (gen_random_uuid(), NULL, 'onamix_links',       '{}'::jsonb, 'builtin', '{}'::jsonb, '{}'::text[], true, 'low',      '{}'::jsonb,  200, NOW()),
  (gen_random_uuid(), NULL, 'onamix_config',      '{}'::jsonb, 'builtin', '{}'::jsonb, '{}'::text[], true, 'high',     '{"requires_confirmation": true}'::jsonb,   20, NOW()),
  (gen_random_uuid(), NULL, 'onamix_multi',       '{}'::jsonb, 'builtin', '{}'::jsonb, '{}'::text[], true, 'medium',   '{}'::jsonb,  100, NOW()),
  (gen_random_uuid(), NULL, 'tavily_search',      '{}'::jsonb, 'builtin', '{}'::jsonb, '{}'::text[], true, 'low',      '{}'::jsonb,  200, NOW()),
  (gen_random_uuid(), NULL, 'serper_search',      '{}'::jsonb, 'builtin', '{}'::jsonb, '{}'::text[], true, 'low',      '{}'::jsonb,  200, NOW()),
  (gen_random_uuid(), NULL, 'think',              '{}'::jsonb, 'builtin', '{}'::jsonb, '{}'::text[], true, 'low',      '{}'::jsonb, 1000, NOW()),
  (gen_random_uuid(), NULL, 'synthesize',         '{}'::jsonb, 'builtin', '{}'::jsonb, '{}'::text[], true, 'medium',   '{}'::jsonb,  100, NOW()),
  (gen_random_uuid(), NULL, 'teacher_ask',        '{}'::jsonb, 'builtin', '{}'::jsonb, '{}'::text[], true, 'high',     '{}'::jsonb,   50, NOW()),
  (gen_random_uuid(), NULL, 'multi_teacher',      '{}'::jsonb, 'builtin', '{}'::jsonb, '{}'::text[], true, 'high',     '{}'::jsonb,   20, NOW()),
  (gen_random_uuid(), NULL, 'calculate',          '{}'::jsonb, 'builtin', '{}'::jsonb, '{}'::text[], true, 'low',      '{}'::jsonb, 1000, NOW()),
  (gen_random_uuid(), NULL, 'run_python',         '{}'::jsonb, 'builtin', '{}'::jsonb, '{}'::text[], true, 'critical', '{"requires_confirmation": true}'::jsonb,   30, NOW()),
  (gen_random_uuid(), NULL, 'extract_insights',   '{}'::jsonb, 'builtin', '{}'::jsonb, '{}'::text[], true, 'low',      '{}'::jsonb,  200, NOW()),
  (gen_random_uuid(), NULL, 'knowledge_discover', '{}'::jsonb, 'builtin', '{}'::jsonb, '{}'::text[], true, 'medium',   '{}'::jsonb,   50, NOW());

-- Verify
SELECT COUNT(*) AS active_count FROM tools WHERE is_active = true AND tenant_id IS NULL;
