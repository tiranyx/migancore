#!/usr/bin/env bash
#
# MiganCore — One-line MCP setup for Claude Code CLI
#
# Usage:
#   curl -sL https://raw.githubusercontent.com/tiranyx/migancore/main/scripts/migan-setup.sh | bash
#
# Or manually:
#   ./migan-setup.sh
#
# What it does:
#   1. Prompts for MiganCore email + password (or reads $MIGAN_EMAIL/$MIGAN_PASSWORD env)
#   2. Logs in to obtain a short-lived JWT
#   3. Uses the JWT to create a long-lived API key (named "claude-code-<hostname>")
#   4. Registers the API key with `claude mcp add` so MiganCore tools are
#      available in every Claude Code session forever (until revoked).
#
# Requires: curl, jq, claude (Claude Code CLI)

set -euo pipefail

API_BASE="${MIGAN_API:-https://api.migancore.com}"
SERVER_NAME="${MIGAN_SERVER_NAME:-migancore}"
KEY_NAME="${MIGAN_KEY_NAME:-claude-code-$(hostname -s 2>/dev/null || echo laptop)}"

# ----- Pretty print helpers -----
B="\033[1m"; G="\033[32m"; Y="\033[33m"; R="\033[31m"; D="\033[2m"; X="\033[0m"

say()  { printf "${B}▸${X} %s\n" "$*"; }
ok()   { printf "  ${G}✓${X} %s\n" "$*"; }
warn() { printf "  ${Y}⚠${X} %s\n" "$*"; }
fail() { printf "  ${R}✗${X} %s\n" "$*" >&2; exit 1; }

# ----- Pre-flight checks -----
say "MiganCore — One-line MCP setup"
echo

command -v curl >/dev/null || fail "curl required"
command -v jq >/dev/null || fail "jq required (install: brew/apt install jq)"

if ! command -v claude >/dev/null; then
  warn "Claude Code CLI ('claude') not found in PATH"
  warn "Install: https://docs.claude.com/en/docs/claude-code"
  warn "Or proceed manually using the API key shown at the end."
  CLAUDE_OK=0
else
  CLAUDE_OK=1
  ok "Claude Code CLI found: $(command -v claude)"
fi

# ----- Get credentials -----
EMAIL="${MIGAN_EMAIL:-}"
PASSWORD="${MIGAN_PASSWORD:-}"

if [ -z "$EMAIL" ]; then
  printf "MiganCore email: "
  read -r EMAIL </dev/tty
fi

if [ -z "$PASSWORD" ]; then
  printf "MiganCore password: "
  stty -echo
  read -r PASSWORD </dev/tty
  stty echo
  echo
fi

[ -z "$EMAIL" ] && fail "Email is required"
[ -z "$PASSWORD" ] && fail "Password is required"

# ----- Login -----
say "Logging in as $EMAIL..."

LOGIN_RESP=$(curl -sf -X POST "$API_BASE/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg email "$EMAIL" --arg pwd "$PASSWORD" '{email:$email,password:$pwd}')") \
  || fail "Login failed. Check email/password."

TOKEN=$(echo "$LOGIN_RESP" | jq -r '.access_token // empty')
[ -z "$TOKEN" ] && fail "Login response missing access_token: $LOGIN_RESP"
ok "JWT obtained"

# ----- Create API key -----
say "Creating long-lived API key '$KEY_NAME'..."

KEY_RESP=$(curl -sf -X POST "$API_BASE/v1/api-keys" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg name "$KEY_NAME" '{name:$name}')") \
  || fail "Failed to create API key"

API_KEY=$(echo "$KEY_RESP" | jq -r '.key // empty')
KEY_ID=$(echo "$KEY_RESP" | jq -r '.id // empty')
PREFIX=$(echo "$KEY_RESP" | jq -r '.prefix // empty')

[ -z "$API_KEY" ] && fail "API key response missing 'key': $KEY_RESP"
ok "API key created: $PREFIX..."

# ----- Register with Claude Code -----
if [ "$CLAUDE_OK" = "1" ]; then
  say "Registering with Claude Code..."

  # Remove existing registration if present (idempotent)
  claude mcp remove "$SERVER_NAME" 2>/dev/null || true

  if claude mcp add --transport http "$SERVER_NAME" "$API_BASE/mcp/" \
       --header "Authorization: Bearer $API_KEY" 2>/dev/null; then
    ok "Registered as '$SERVER_NAME' in Claude Code"
  else
    warn "Auto-registration failed. Run manually:"
    echo "    claude mcp add --transport http $SERVER_NAME $API_BASE/mcp/ \\"
    echo "      --header \"Authorization: Bearer $API_KEY\""
  fi
fi

# ----- Final report -----
echo
printf "${G}═══════════════════════════════════════════════════════════════${X}\n"
printf "${B}  Setup complete${X}\n"
printf "${G}═══════════════════════════════════════════════════════════════${X}\n"
echo
echo "  API key (save this if you want to use elsewhere):"
echo "    $API_KEY"
echo
echo "  Manage keys at: $API_BASE/v1/api-keys"
echo "  Revoke this key:"
echo "    curl -X DELETE $API_BASE/v1/api-keys/$KEY_ID \\"
echo "      -H \"Authorization: Bearer <login-jwt>\""
echo
if [ "$CLAUDE_OK" = "1" ]; then
  echo "  Try it: open Claude Code and ask"
  echo "    \"buatkan gambar logo MiganCore\""
  echo "    \"tulis file todo.md isinya belajar React\""
  echo
fi
printf "${G}═══════════════════════════════════════════════════════════════${X}\n"
