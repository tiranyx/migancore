-- Day 10 Schema Sync — Agent Spawning Foundation
-- Run manually on existing DBs: psql -U ado_app -d ado -f 010_day10_schema_sync.sql

-- Columns already present on some deployments (ensure idempotent)
ALTER TABLE agents ADD COLUMN IF NOT EXISTS description VARCHAR(1024);
ALTER TABLE agents ADD COLUMN IF NOT EXISTS model_version VARCHAR(64) NOT NULL DEFAULT 'qwen2.5:7b-instruct-q4_K_M';
ALTER TABLE agents ADD COLUMN IF NOT EXISTS system_prompt TEXT;

-- Columns missing from ORM / new for spawn feature
ALTER TABLE agents ADD COLUMN IF NOT EXISTS letta_agent_id VARCHAR(255);
ALTER TABLE agents ADD COLUMN IF NOT EXISTS webhook_url VARCHAR(512);
ALTER TABLE agents ADD COLUMN IF NOT EXISTS avg_quality_score FLOAT;
ALTER TABLE agents ADD COLUMN IF NOT EXISTS template_id VARCHAR(64);
ALTER TABLE agents ADD COLUMN IF NOT EXISTS persona_locked BOOLEAN NOT NULL DEFAULT false;
