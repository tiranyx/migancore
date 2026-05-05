# Day 49.7 — Vast.ai Setup PROGRESS
**Date:** 2026-05-05 (post Day 49.6 RunPod retry fail)
**Trigger:** Lesson #62 (RunPod has bad days → diversify) + Lesson #63 (laptop training infeasible)
**Status:** 🟡 Account ready, awaiting SSH key + API key setup

---

## ✅ Done

- [x] Fahmi registered Vast.ai account (fahmiwol@gmail.com, Individual tier)
- [x] $7.00 credit added (cukup ~14-35 hours @ $0.20-0.50/hr)
- [x] Account verified (login works)
- [x] Manage Keys panel accessed

## ⏳ In Progress (Fahmi action)

- [ ] **SSH Key** — paste VPS public key into Vast.ai SSH Keys tab
  - VPS pubkey: `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOmvt2LiPORhhVVB93oeIPAh6m6iJrzr7gdsq/9i5HXw root@srv1521061`
- [ ] **API Key** — generate at API Keys tab, save to VPS at `/root/.vastai_api_key` (mode 600)

## ⏳ Pending (Claude action after keys ready)

- [ ] Adapt `cycle1_v2_monitor.py` → Vast.ai REST API endpoints
- [ ] Pre-flight: query Vast.ai availability for RTX 4090 OR A100 spot
- [ ] Test smoke: spawn nano pod ($0.10/hr 5min) → verify SSH works → terminate
- [ ] Spawn proper training pod (4090 spot ~$0.20/hr or A100 ~$0.40/hr)
- [ ] Auto-train + auto-download adapter + auto-terminate + auto-verify

## 📊 Cost Plan (Vast.ai)

| Phase | Cost | Notes |
|-------|------|-------|
| Smoke test pod | $0.05 | Verify SSH + API flow works |
| Cycle 1 training | $0.30-0.50 | 4090 spot ~25-40 min |
| Buffer | $0.50 | 1 retry budget |
| **Total expected** | **~$1.00** | of $7 credit |

After this run: **$6.00 credit remaining** for Cycle 2-6 training + experiments.

---

## 🔒 Security Protocol (NEW Lesson #64 candidate)

**Credentials NEVER in chat / git / docs:**
- ❌ DON'T paste API key in chat conversation (GitHub secret-scanning will block push, plus chat is not encrypted at rest)
- ❌ DON'T commit API key to git (even in test files)
- ❌ DON'T log API key to stdout / file unprotected

**Storage pattern (used today):**
- ✅ User generates key in Vast.ai UI (only shown once)
- ✅ User saves to `/root/.vastai_api_key` on VPS via SSH (file mode 600 = root-only)
- ✅ Claude reads via `cat /root/.vastai_api_key` from VPS exec context only
- ✅ Scripts use `KEY=$(cat /root/.vastai_api_key)` not hardcoded literal

**Why this matters:** RunPod API key was in `memory/credentials_private.md` historically. That's PRIVATE memory, not in git. But GitHub secret-scanning HAS already caught literal RunPod key in `docs/DAY49_TRIGGER_LIVE.md` once today. Same will happen with Vast.ai key if we're sloppy.

---

## 🎯 Next-Session Pickup Command

When user has both SSH + API keys saved:
```bash
# Saya verify access:
ssh -i ~/.ssh/sidix_session_key root@72.62.125.6 "
test -f /root/.vastai_api_key && echo 'API key file exists, size:' \$(wc -c < /root/.vastai_api_key)
KEY=\$(cat /root/.vastai_api_key)
curl -s 'https://console.vast.ai/api/v0/users/current/' -H \"Authorization: Bearer \$KEY\" | head -c 300
"
```

If returns user JSON → ready for next steps.

---

## 📝 Lesson #64 Anticipated

**Credential ops on shared system: file mode 600, never inline, env var or file-read.**

Pattern across services:
- RunPod API key → `/root/.runpod_api_key` (mode 600)
- Vast.ai API key → `/root/.vastai_api_key` (mode 600)
- Future API keys → same pattern

Update `AGENT_ONBOARDING.md` setelah lessson #64 finalized.
