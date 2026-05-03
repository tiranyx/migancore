-- Day 27 — Long-Lived API Keys for MCP/REST Headless Clients
-- Run: psql -U ado_app -d ado -f 025_day27_api_keys.sql
--
-- Design (from research):
--   format:    mgn_live_<key_id_8hex>_<secret_43chars_urlsafe>
--   prefix:    "mgn_live_<key_id>" stored & shown in UI (revoke by prefix)
--   key_hash:  HMAC-SHA256(server_pepper, full_key) — fast verify, no Argon2 needed
--                (256-bit entropy in secret = brute force infeasible)
--
-- Verify path:
--   1. parse incoming "Authorization: Bearer mgn_live_..."
--   2. compute hmac(pepper, presented).digest() = key_hash
--   3. SELECT WHERE key_hash = $1 AND revoked_at IS NULL AND (expires_at IS NULL OR expires_at > now())
--   4. (optional Redis revoke list for sub-1s revoke propagation)
--
-- Stripe/OpenAI/Anthropic all use this exact pattern.

CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,

    -- Display (safe to log/show)
    name TEXT NOT NULL,                            -- user-given label e.g. "claude-code-laptop"
    prefix TEXT NOT NULL,                          -- "mgn_live_aB3xK9F2" (~20 chars, shown in UI)

    -- Secret (NEVER log/show after creation)
    key_hash BYTEA NOT NULL,                       -- HMAC-SHA256 32 bytes
    -- key_hash UNIQUE handled via index below

    -- Authorization
    scopes TEXT[] NOT NULL DEFAULT ARRAY['tools:exec','chat:read','chat:write']::text[],

    -- Lifecycle
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,                        -- NULL = no expiry
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Hot-path index: verify lookup by hash, only active keys
CREATE UNIQUE INDEX IF NOT EXISTS idx_api_keys_hash_active
    ON api_keys(key_hash) WHERE revoked_at IS NULL;

-- For revoke-by-prefix UX (user sees prefix in UI, clicks revoke)
CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(prefix);

-- For listing user's keys
CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id) WHERE revoked_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_api_keys_tenant ON api_keys(tenant_id) WHERE revoked_at IS NULL;
