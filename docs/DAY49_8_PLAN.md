# Day 49.8 Plan — Cycle 1 di Vast.ai (lessons #54-64 applied)
**Date:** 2026-05-05
**Trigger:** User: "GO!" (after Vast.ai key saved + verified)
**Pre-flight ALL GREEN per AGENT_ONBOARDING.md protocol**

---

## 🧭 1. CONTEXT (state before execute)

| Item | Value | Source |
|------|-------|--------|
| Vast.ai API key | ✅ saved `/opt/secrets/migancore/vastai_api_key` mode 600 | Day 49.7 setup |
| Vast.ai credit | $7.00 | API verified |
| 4090 availability | 3 offers, cheapest $0.136/hr | Vast.ai bundles API |
| 3090 availability | 2 offers, cheapest $0.069/hr (24GB cukup utk 7B) | Vast.ai bundles API |
| Dataset | 596 DPO pairs `/tmp/cycle1_dataset.jsonl` (1.24MB) | Day 49 export |
| API health | v0.5.16 ✅ | curl /health |
| DPO pool | 801 (growing autonomous) | /v1/public/stats |
| All containers | 6/6 UP | docker compose ps |
| tiranyx CPU | DONE (no contention) | ps aux |
| RunPod cap | $6.80/$7 spent — **DO NOT TOUCH** until Vast verified | Day 49.5/49.6 |
| Lessons | 63 cumulative (#54-63 hari ini) | AGENT_ONBOARDING |

---

## 🔬 2. RESEARCH SYNTHESIS (Vast.ai vs RunPod operational)

| Aspect | RunPod (today's experience) | Vast.ai (target) |
|--------|----------------------------|-------------------|
| GPU pricing 4090 | $0.69/hr (SECURE non-spot) | **$0.136/hr** (5x cheaper) |
| Allocation reliability | 2x stuck today (10hr + 5min abort) | unknown — first attempt today |
| API style | REST `/v1/pods` | REST `/api/v0/{asks,instances,bundles}` |
| Pod creation | POST `/v1/pods` body | **POST `/asks/{offer_id}/`** (rent specific offer) |
| SSH key | `PUBLIC_KEY` env var → auto-inject | **`onstart` script writes to `~/.ssh/authorized_keys`** |
| Termination | DELETE `/pods/{id}` | DELETE `/instances/{id}/` |
| Status field | `desiredStatus` + `runtime` | `actual_status` + `intended_status` |
| SSH endpoint | from `runtime.ports[]` | from `ssh_host` + `ssh_port` direct fields |
| Cost telemetry | from pod object `costPerHr` | from instance `dph_total` |
| Image format | full Docker tag | full Docker tag (compatible) |

---

## 📐 3. TASK LIST — H/R/B FRAMEWORK

### A1 — Adapt cycle1_v2_monitor.py → cycle1_vast.py (~30 min)
**Hipotesis:** Same flow (poll → SSH → train → terminate), different endpoints. Reuse 80% code.
**Risk:** LOW — Python rewrite, no infra change.
**Benefit:** Tested abstraction for future cloud vendors.
**KPI:** Syntax OK + dry-run exec (no spawn) shows correct API call shapes.

### A2 — Pre-flight: select cheapest reliable offer
**Hipotesis:** Sort 4090/3090 offers by `dph_total ASC` filtered by `reliability >= 0.95`.
**Risk:** LOW — read-only API call.
**Benefit:** Avoid unreliable hosts (Vast marketplace = host quality varies).
**KPI:** Returns offer_id with reliability ≥0.95 AND price ≤$0.20/hr.

### A3 — Smoke test ($0.05, 5 min)
**Hipotesis:** Spawn cheapest 3090 (or any) for 5 min. Verify: rent succeeds, instance reaches running, SSH works, terminate works.
**Risk:** LOW — capped at $0.05 worst case. If fails, learn vendor-specific quirks before $$ spend.
**Benefit:** De-risk full training run.
**KPI:** SSH ping succeeds within 5 min, terminate verified gone.

### A4 — Production training (~$0.10, 30-50 min)
**Hipotesis:** Spawn 4090, upload dataset+script+anchor, run train_simpo.py with apo_zero+padding_free+liger_kernel, download adapter.
**Risk:** MED — training itself may fail (model collapse, OOM, etc.) but bounded by 90-min monitor cap.
**Benefit:** First MiganCore-branded adapter (`migancore-7b-soul-v0.1`).
**KPI:** Adapter saved to `/opt/ado/cycle1_output/migancore-7b-soul-v0.1/` ~50MB safetensors.

### A5 — Identity eval + PROMOTE/ROLLBACK
**Gate:** cosine ≥0.85 mean AND ≥0.75 min (BGE-M3 embeddings).
**Risk:** MED — small dataset, identity drift possible.
**Benefit:** Validate "Self-Improving v1" claim.

### A6 — Cleanup + key rotate
**Hipotesis:** ALWAYS terminate + verify (Lesson #59). ROTATE Vast.ai key after Cycle 1 (chat exposure mitigation).
**Risk:** LOW — guard rails enforced.

---

## 📊 4. KPI Day 49.8

| Item | Target | Verifikasi |
|------|--------|------------|
| Monitor adapt | syntax OK + 0 errors on dry-run | python -m ast |
| Smoke pod | SSH succeeds, terminated, verified 404 | log inspection |
| Production train | adapter ~50MB, log shows TRAINING_DONE | ls -la output |
| Cost actual | <$0.20 total (smoke + production) | Vast.ai instance billing |
| Identity eval | cosine ≥0.85/0.75 | run_identity_eval.py output |
| Pod cleanup | 0 active instances at end | API /instances/ list |
| Documentation | DAY49_8_RETRO + day49_8_progress + MEMORY.md | git log |
| **Lessons learned** | +1 lesson minimum | AGENT_ONBOARDING update |

---

## 💰 5. BUDGET PROJECTION

| Item | Estimate |
|------|----------|
| Smoke test (5min @ $0.07/hr) | $0.01 |
| Production training (40min @ $0.14/hr) | $0.10 |
| Buffer (1 retry) | $0.10 |
| **Day 49.8 total** | **~$0.21** |
| Vast.ai credit remaining after | **$6.79** of $7 |

vs RunPod yang sudah $6.80 spent untuk 0 success = **infinite ROI improvement** kalau Vast.ai works.

---

## 🚦 6. EXIT CRITERIA — Day 49.8

Must-have:
- [ ] cycle1_vast.py adapted + syntax OK
- [ ] Smoke test 5-min successful (SSH + terminate verified)
- [ ] Production pod spawned + training started
- [ ] Adapter downloaded to /opt/ado/cycle1_output/
- [ ] All instances terminated + verified gone
- [ ] DAY49_8_RETRO.md committed

Stretch:
- [ ] Identity eval result (PROMOTE/ROLLBACK)
- [ ] GGUF convert + Ollama push if PROMOTE
- [ ] Vast.ai key rotated (chat exposure)

---

## 🛡️ 7. SCOPE BOUNDARIES

❌ **DON'T DO Day 49.8:**
- Touch RunPod ($0.20 cap remaining, save for emergency)
- Add new tools (STOP per VISION compass — Lesson #57)
- Trigger Cycle 2 (validate Cycle 1 success first)
- Modify production API code (training is separate)

✅ **DO STAY FOCUSED:**
- Reuse cycle1_v2_monitor.py structure (80% code reuse)
- Apply ALL lessons #54-64 (5-min abort, DELETE+VERIFY, cost telemetry, secret hygiene)
- Smoke test BEFORE production training (de-risk)
- Document everything as we go

---

## 🎓 8. LESSONS APPLIED + ANTICIPATED

Applied today (already in code/protocol):
- #55 pre-flight availability check ✅
- #59 DELETE + VERIFY ✅
- #60 5-min boot abort ✅
- #61 cost telemetry per-min ✅
- #62 vendor diversification (now using Vast.ai) ✅
- #63 hardware feasibility check ✅
- #64 (anticipated) secret centralized at /opt/secrets/<project>/ ✅

Anticipated NEW from Day 49.8:
- #65 (anticipated) Vast.ai-specific quirks (TBD discovered)
- #66 (anticipated) smoke-test-before-production for any new vendor

---

## 🔭 POST-DAY-49.8 LOOKAHEAD

**If Cycle 1 PROMOTE:**
- Day 50: GGUF convert + Ollama push `migancore:0.1` + A/B 10% traffic
- Day 51-52: 24h A/B win-rate eval
- Day 53-55: Hot-swap public eval demo (DD-2 from VISION compass)

**If Cycle 1 ROLLBACK:**
- Day 50: post-mortem + Cycle 1.1 with lr=3e-7 + cleaner dataset (drop synthetic <2 score)

**Either way (parallel):**
- Synth gen rate-limit fix (Day 50, prevent today's outage class)
- Tool registration sync CI (Lesson #48 systematic)

---

**THIS IS THE COMPASS for Day 49.8. Vast.ai = 5-9x cheaper + first attempt. Smoke test de-risks. All lessons applied operationally.**
