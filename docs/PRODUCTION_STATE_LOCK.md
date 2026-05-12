# PRODUCTION STATE LOCK — Day 72e
**Date:** 2026-05-12
**Status:** ✅ LOCKED — Do not change without owner approval + rollback plan
**Purpose:** Frozen snapshot of working production config. If anything breaks, revert to this.

---

## Production Model
| Key | Value |
|---|---|
| Active model | migancore:0.7c |
| Fallback model | migancore:0.3 |
| Base reference | qwen2.5:7b-instruct-q4_K_M |
| Ollama status | Loaded, keep_alive=24h |

## API Config
| Key | Value |
|---|---|
| DEFAULT_MODEL | migancore:0.7c |
| OLLAMA_DEFAULT_MODEL | migancore:0.7c |
| API version | v0.5.16 |
| Build day | Day 70 |
| Build time | 2026-05-12T07:08:33Z |
| Port | 127.0.0.1:18000 → 8000 |

## Docker Services
`
ado-api-1       Up (healthy)    127.0.0.1:18000->8000
ado-ollama-1    Up              0.0.0.0:11434->11434
ado-postgres-1  Up (healthy)    5432
ado-redis-1     Up              6379
ado-qdrant-1    Up              6333
ado-letta-1     Up              8083
`

## Database State
| Metric | Value |
|---|---|
| Users | 67 |
| Agents | 74 |
| Conversations | 109 |
| Messages | 602 |
| Preference pairs | 3,359 (0.9% real) |
| Alembic version | 010 (head) |

## Ollama Models (Cleaned)
`
migancore:0.7c    4.8 GB  ← PRODUCTION
migancore:0.3     4.8 GB  ← FALLBACK
qwen2.5:7b-instruct-q4_K_M  4.7 GB ← BASE REF
qwen2.5:0.5b      397 MB  ← SPECULATIVE DECODING
`

## Removed (Broken/Contaminated)
- migancore:0.8 — identity collapse (ChatGPT/OpenAI)
- migancore:0.8-fixed — sequential merge failed
- migancore:0.8-identity — contaminated (Anthropic/Claude)
- migancore:0.4, 0.4-fixed — older, not needed
- migancore:0.7, 0.7b — intermediate failures

## Disk
| Before cleanup | After cleanup |
|---|---|
| 79% (102GB free) | 66% (136GB free) |

## Git
| Key | Value |
|---|---|
| Branch | main |
| HEAD | 4f689a7 (Merge: alignment + MiganForge) |
| Remote | github.com:tiranyx/migancore |

## Files Archived
| Path | Reason |
|---|---|
| archive/contaminated_day72c/ | Contaminated model artifacts |
| archive/scripts_deprecated/ | Failed merge scripts |
| archive/models_broken/ | Broken GGUF files (if any) |

## Rollback Command (Emergency)
`ash
# If production degrades after any change:
cd /opt/ado
git checkout fac6f02  # Day 72e alignment commit
docker compose build api && docker compose up -d api
docker exec ado-ollama-1 ollama rm <broken-model>
`

## Verification
`ash
# 1. API health
curl -s http://127.0.0.1:18000/health | jq

# 2. Model list
docker exec ado-ollama-1 ollama list

# 3. Identity test (WITH system prompt)
curl -s http://127.0.0.1:11434/api/generate -d '{" model\:\migancore:0.7c\,\system\:\Kamu adalah Mighan-Core...\,\prompt\:\Siapa kamu?\,\stream\:false}' | jq .response

# 4. DB
docker exec ado-postgres-1 psql -U ado_app -d ado -c 'SELECT COUNT(*) FROM preference_pairs;'
`

---

*This document is a snapshot. Update only after successful promote with eval gate pass.*
*Last updated: Day 72e · 2026-05-12 · by Kimi*
