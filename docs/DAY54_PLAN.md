# Day 54 Plan — Cycle 1 Training (THE MOAT)
**Date:** 2026-05-06 (Day 54)
**Trigger:** Fahmi top-up RunPod $19.20, defer dedicated VPS, GO Cycle 1.
**Vision check:** ALL 5 principles pass — own model, own data, closed loop, modular adapter, mentor (teacher data already collected).

---

## 🎯 SINGLE GOAL TODAY: Adapter v0.1 lands + identity eval ≥ baseline

No spec dec experiments, no platform scaffold, no frontend modularize. Per `DAY53_REVIEW_SYNTHESIS.md`: until adapter exists, MiganCore is "chatbot with memory" — not ADO.

---

## 🛫 Pre-flight (DONE)
- [x] DPO dataset present at `/opt/ado/data/workspace/cycle1_dataset.jsonl` (596 pairs, schema `{prompt, chosen, rejected}`)
- [x] RunPod API key saved centralized at `/opt/secrets/migancore/runpod_api_key` (mode 600)
- [x] Synthetic gen pipeline paused (`redis SET synthetic:paused 1`) — frees Ollama CPU during training
- [x] Zero orphan pods on RunPod (verified via REST API)
- [x] Train assets verified: `train_simpo.py`, `persona_consistency_v1.jsonl`, `baseline_day39.json` all present at `/opt/ado/training/` and `/opt/ado/eval/`

## 🛠️ Script: `/tmp/cycle1_runpod.py`
- Spawn: REST POST `/v1/pods` with body schema `{ports: ["22/tcp"], cloudType: SECURE, gpuTypeIds: [...]}`
- Boot wait: max 300s (Lesson #60 — SECURE pods bill from allocation, not boot)
- GPU candidate fallback: 4090 → A5000 → L40S → A40
- Train: `python train_simpo.py --use-apo --anchor-dataset persona_consistency_v1.jsonl` (defaults: lr=5e-7, simpo-beta=2.5, apo-lambda=0.05, loss=apo_zero, 1 epoch — research-validated for <700 pairs no overfit)
- Wait: poll `/workspace/_TRAINING_DONE` marker every 60s, max 90 min
- Download: `scp -r /workspace/migancore-7b-soul-v0.1` → `/opt/ado/cycle1_output/`
- Cleanup: Lesson #59 DELETE+VERIFY (404 expected, retry once on failure)
- Cost telemetry: per-poll write to `/tmp/cycle1_runpod_cost.log` per Lesson #61

## 💰 Cost projection
- Successful run: ~$0.34-0.69/hr × 1hr = **$0.34-0.69**
- Boot timeout abort: ~5 min × $0.69/hr = **~$0.06**
- Hard ceiling: **$2.00** (covers retry + buffer)

## 📊 KPIs Day 54
| Goal | Target | Pass condition |
|------|--------|----------------|
| Pod allocation | succeed in <30s | spawn returns 200/201 |
| Boot to SSH | <300s | Lesson #60 |
| Training completes | <90 min | `_TRAINING_DONE` marker |
| Adapter downloaded | files present at `/opt/ado/cycle1_output/migancore-7b-soul-v0.1/adapter_*.safetensors` | `ls` confirms |
| DELETE + VERIFY | clean (404) | Lesson #59 |
| Identity eval delta | ≥ 0 vs baseline | run `eval/run_identity_eval.py` |
| Total cost | < $2.00 | sum from cost log |

## 🚦 Exit criteria
- [ ] Adapter v0.1 lands at `/opt/ado/cycle1_output/migancore-7b-soul-v0.1/`
- [ ] Identity eval ≥ baseline (no degradation on persona anchors)
- [ ] DELETE + VERIFY clean — 0 orphan pod billing
- [ ] DAY54_RETRO with honest training-loss curve + cost
- [ ] Memory updated + commit
- [ ] Synthetic gen resumed (`redis SET synthetic:paused 0` then DEL or just delete the key)

## 📝 If training fails
- **Spawn fails (HTTP 4xx)**: log full error, fix schema, retry. Cost = $0.
- **Boot timeout**: Lesson #60 auto-abort, try next GPU candidate. Cost ≤ $0.06 per attempt.
- **Training crash mid-run**: Lesson #59 DELETE+VERIFY still fires via `finally`, save partial log to `cycle1_failed_attempts/`. Investigate before retry.
- **Identity eval degrades**: DO NOT promote. Document, re-tune hyperparameters, retry next day.

---

## 🔄 Post-training (Sprint B + C)
1. **If PROMOTE:** copy adapter to Ollama models dir, register `migancore:0.1`, A/B test 5 fingerprint prompts
2. **If REJECT:** keep adapter as `_v0.1-rejected/`, document why, plan tuning for Cycle 1.1
3. **Resume synthetic gen:** `redis-cli DEL synthetic:paused`
4. **Write `DAY54_RETRO.md`** with: training loss curve, time, cost, identity scores, GO/NO-GO decision
5. **Update memory + AGENT_ONBOARDING with Lesson #75 (TBD based on learning)**
6. **First "Otak Belajar Apa Minggu Ini" thread** if PROMOTE — Indonesia narrative tactic per Lesson #66
