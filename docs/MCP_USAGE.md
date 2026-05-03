# MiganCore MCP Server — Usage Guide

**Endpoint:** `https://api.migancore.com/mcp/`
**Transport:** Streamable HTTP (MCP spec 2025-06-18)
**Auth:** Bearer JWT (15min) **or** Bearer API key (`mgn_live_*`, long-lived) — Day 27
**Protocol Version:** 2025-06-18

---

## ⚡ ONE-LINE SETUP (Day 27 — Recommended)

**Linux / macOS / WSL:**
```bash
curl -sL https://raw.githubusercontent.com/tiranyx/migancore/main/scripts/migan-setup.sh | bash
```

**Windows PowerShell:**
```powershell
iwr https://raw.githubusercontent.com/tiranyx/migancore/main/scripts/migan-setup.ps1 | iex
```

The script will:
1. Prompt for MiganCore email + password
2. Login (get JWT)
3. Create a long-lived API key named `claude-code-<hostname>`
4. Run `claude mcp add` to register it with Claude Code CLI
5. Done — tools available in every Claude Code session forever

---

## Manual Setup (3 steps)

### 1. Get a JWT Token (short-lived, 15 min)

```bash
TOKEN=$(curl -s -X POST https://api.migancore.com/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"YOU@example.com","password":"YOUR_PASSWORD"}' \
  | jq -r .access_token)

echo "Token: $TOKEN"
# Token expires in 15 minutes (configurable via JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
```

---

### 2a. (Optional but recommended) Convert JWT to long-lived API key

```bash
API_KEY=$(curl -s -X POST https://api.migancore.com/v1/api-keys \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"my-laptop"}' | jq -r .key)

# API_KEY format: mgn_live_<id>_<secret>
# This key NEVER expires until you revoke it.
# SAVE IT NOW — the secret cannot be recovered.
```

### 2b. Connect from Claude Code CLI

Use **either** the JWT (re-login every 15min) **or** the API key (permanent):

```bash
claude mcp add --transport http migancore https://api.migancore.com/mcp/ \
  --header "Authorization: Bearer $API_KEY"
```

After this, in any Claude Code session, the following tools become available:
- `mcp__migancore__write_file`
- `mcp__migancore__read_file`
- `mcp__migancore__generate_image`
- `mcp__migancore__web_search`
- `mcp__migancore__memory_write`
- `mcp__migancore__memory_search`
- `mcp__migancore__python_repl`

---

## 3. Connect from Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or
`%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "migancore": {
      "url": "https://api.migancore.com/mcp/",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN_HERE"
      }
    }
  }
}
```

Restart Claude Desktop. Tools appear under "Custom Integrations".

---

## 4. Connect from Cursor

Edit `~/.cursor/mcp.json` (or via Cursor Settings → MCP):

```json
{
  "mcpServers": {
    "migancore": {
      "url": "https://api.migancore.com/mcp/",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN_HERE"
      }
    }
  }
}
```

---

## 5. Manual Test (curl)

```bash
# Initialize handshake
curl -X POST https://api.migancore.com/mcp/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2025-06-18",
      "capabilities": {},
      "clientInfo": {"name": "manual-test", "version": "1.0"}
    }
  }'
# Response includes Mcp-Session-Id header — save it

# List tools (use the session ID from above)
curl -X POST https://api.migancore.com/mcp/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Mcp-Session-Id: <session-id>" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'

# Call write_file
curl -X POST https://api.migancore.com/mcp/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Mcp-Session-Id: <session-id>" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0", "id": 3, "method": "tools/call",
    "params": {
      "name": "write_file",
      "arguments": {"path": "hello.txt", "content": "Hello from MCP!"}
    }
  }'
```

---

## 6. Available Tools

| Tool | Description | Free tier limit |
|------|-------------|-----------------|
| `web_search` | DuckDuckGo search for current info | 100/day |
| `generate_image` | fal.ai FLUX schnell, returns URL | 100/day (~$0.30/day max) |
| `write_file` | Sandboxed write to agent workspace | 200/day |
| `read_file` | Sandboxed read from agent workspace | 200/day |
| `memory_write` | Save fact to long-term memory (Redis + Qdrant) | 500/day |
| `memory_search` | Semantic search of saved facts | 1000/day |
| `python_repl` | Sandboxed Python computation | enterprise plan only |

---

## 7a. API Key Management (Day 27)

**Create a key:**
```bash
curl -X POST https://api.migancore.com/v1/api-keys \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"name":"my-laptop","scopes":["tools:exec","chat:read"]}'
# Returns: { "id": "...", "key": "mgn_live_...", "prefix": "mgn_live_abc123" }
# SAVE THE 'key' FIELD NOW — it will not be shown again
```

**List your keys (no secrets shown):**
```bash
curl https://api.migancore.com/v1/api-keys -H "Authorization: Bearer $JWT"
```

**Revoke a key (idempotent, sub-1s propagation):**
```bash
curl -X DELETE https://api.migancore.com/v1/api-keys/{key_id} \
  -H "Authorization: Bearer $JWT"
```

**API key format:** `mgn_live_<8hex_id>_<43char_secret>`
- Total length: ~64 chars
- Entropy: 256 bits (brute force infeasible)
- Hashed in DB via HMAC-SHA256(server_pepper, key)
- Same security model as Stripe/OpenAI/Anthropic API keys

---

## 7b. MCP Resources (Day 27)

In addition to **Tools** (action functions), MiganCore exposes **Resources** (attachable context):

| Resource URI | Returns |
|--------------|---------|
| `migancore://workspace` | Workspace root listing |
| `migancore://workspace/{path}` | File contents (sandboxed, 50KB cap) |
| `migancore://soul` | Mighan-Core SOUL.md persona |
| `migancore://memory/help` | Memory tier reference |

In Claude Code, mention with `@migancore:<resource>` syntax (auto-completes).

---

## 7. Troubleshooting

**"missing_bearer_token" 401**
- Add `Authorization: Bearer <jwt>` header

**"invalid_token" 401**
- Token expired — re-login (15 min lifetime)

**"Invalid Host header" or 502**
- DNS rebinding protection. Hostname must be `api.migancore.com`.

**500 "Task group not initialized"**
- API container restart needed (lifespan didn't start MCP session manager)

**Tools call returns success=false**
- Check tool policy. Some tools require pro/enterprise plan (e.g., `python_repl` enterprise-only)
- Check daily quota — `tools.max_calls_per_day` in DB

---

## 8. Security Notes

- All tools execute under the authenticated tenant's plan tier
- File operations are sandboxed to `/app/workspace` — no path traversal possible
- `python_repl` runs in subprocess isolation with import blacklist
- `generate_image` cost-controlled by `max_calls_per_day` (no rate-bypass via MCP)
- JWT must be regenerated every 15 minutes — no long-lived API keys yet (Day 27 TODO)

---

## 9. Roadmap

- **Day 27**: Add `text_to_speech` (ElevenLabs), MCP `resources` capability (expose conversations/agents as readable resources)
- **Day 28**: API key alternative to short-lived JWT for long-running clients
- **Week 4**: OAuth 2.1 dynamic client registration for marketplace deployments
