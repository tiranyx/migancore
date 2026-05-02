-- Migration 011: Add description, model_version, system_prompt to agents

ALTER TABLE agents
    ADD COLUMN IF NOT EXISTS description VARCHAR(1024),
    ADD COLUMN IF NOT EXISTS model_version VARCHAR(64) NOT NULL DEFAULT 'qwen2.5:7b-instruct-q4_K_M',
    ADD COLUMN IF NOT EXISTS system_prompt TEXT;
