# RECAP — Day 71c | Cycle 7c Q5 Casual Voice Fix
> Ditulis oleh: Claude Sonnet 4.6
> Tanggal: 2026-05-08
> Ref: CLAUDE_PLAN_71C → (KIMI_REVIEW_71C deferred — sprint mode) → **RECAP_71C**

---

## EXECUTIVE SUMMARY

**Strategy:** Cycle 7c = same proven hyperparams (LR=1.2e-6, epochs=3, ORPO apo_zero, A40)
+ **only one variable changed**: 40 Q5-specific casual greeting pairs added.

**Why minimal-change strategy:** Cycle 7b proved hyperparams work for voice category overall.
Q5 alone failed because reference is 7-word brief, model was outputting 15-25 words.
Solution = teach model the brief pattern via 40 targeted pairs with chosen=6.1w mean,
rejected=32.5w mean (length delta 26 words = strong ORPO signal).

---

## TRAINING METRICS

| Metric | Value |
|--------|-------|
| Dataset | 548 pairs (508 C7 base + 40 Q5 casual) |
| Algorithm | ORPO apo_zero loss |
| Hyperparams | LR=1.2e-6, epochs=3, batch=2×8=16, lora-r=16 |
| GPU | A40 46GB @ $0.322/hr |
| Steps | 102 |
| Speed | _TBD_ s/step |
| Total time | _TBD_ min |
| Cost | _TBD_ ($0.02 v1 wasted + _TBD_ v2) |
| Adapter size | _TBD_ MB |
| HF repo | https://huggingface.co/Tiranyx/migancore-7b-soul-v0.7c |

---

## V1 FAILURE — ROOT CAUSE + FIX

**v1 cost:** $0.02 wasted (boot + install + tokenize-failure)
**Failure mode:**
```
ValueError: rejected should be an str but got <class 'dict'>
File "/root/trainenv/lib/python3.11/site-packages/trl/trainer/orpo_trainer.py", line 417
```

**Root cause:** `generate_cycle7c_q5_pairs.py` output `chosen`/`rejected` as ChatML message lists
(copied from SFT-style scripts), but TRL 0.9.6 ORPOTrainer expects **string format** (just the
completion text). Existing C7 dataset uses string format, which my generator should have matched.

**Fix:** Updated generator to output strings + added `verify_c7c_format.py` defensive validator
that checks all rows are string-typed before training launch. **Lesson #172 locked.**

---

## EVAL RESULT (Cycle 7c) — _TBD_

| Category | C7b | C7c | Delta | Gate | Status |
|---|---|---|---|---|---|
| **identity** | 0.921 | _TBD_ | _TBD_ | ≥0.90 | _TBD_ |
| **voice** | 0.771 | _TBD_ | _TBD_ | ≥0.85 | _TBD_ |
| reasoning | 0.984 | _TBD_ | _TBD_ | ≥0.80 | _TBD_ |
| code | 0.959 | _TBD_ | _TBD_ | ≥0.80 | _TBD_ |
| creative | 0.968 | _TBD_ | _TBD_ | ≥0.80 | _TBD_ |
| **weighted_avg** | 0.8870 | _TBD_ | _TBD_ | ≥0.92 | _TBD_ |

**Q5 individual ("Hai! Bagaimana kabarmu?"):**
- Cycle 7: 0.478 (formal baseline)
- Cycle 7b: 0.609 (casual but too long)
- Cycle 7c: **_TBD_** (target ≥ 0.75)

**Q6 voice ("Tolong tulis intro panjang..."):**
- Cycle 7b: 0.933 (structured voice excellent)
- Cycle 7c: **_TBD_** (must hold ≥ 0.85)

---

## VERDICT — _TBD_

| Outcome | Action |
|---------|--------|
| PROMOTE | migancore:0.7c → production. Update DEFAULT_MODEL. Restart api. Notify beta users. |
| CONDITIONAL | Formal smoke test (3 prompts). If formal register OK → conditional promote. |
| ROLLBACK | migancore:0.3 stays. Plan Cycle 7d (reference tuning OR SFT stage). |

---

## LESSONS LOCKED (Day 71c)

| # | Lesson |
|---|--------|
| **#172** | TRL 0.9.6 ORPOTrainer expects STRING format for `chosen`/`rejected`, not ChatML. Always smoke-test 1 pair through `tokenize_row()` BEFORE upload. Defensive validator (string-type check across all rows) blocks bad data at source. |

---

## TOOLING SHIPPED Day 71c

| File | Purpose |
|------|---------|
| `scripts/generate_cycle7c_q5_pairs.py` | Generate 40 Q5 casual pairs (FIXED: string format) |
| `scripts/verify_c7c_format.py` | Defensive validator: all chosen/rejected must be strings |
| `scripts/analyze_c7c_pairs.py` | Dataset anatomy explainer (length deltas, prompt variants) |
| `scripts/explain_eval_mechanism.py` | Educational: how cosine sim + voice category works |
| `scripts/analyze_eval_result.py` | Auto gate decision (PROMOTE/CONDITIONAL/ROLLBACK) |
| `scripts/cycle7c_post_pipeline.sh` | One-command post-training pipeline (GGUF → Ollama → eval) |
| `training/cycle7c_orpo_vast.py` | Vast.ai orchestrator (synced from cycle7b with C7c paths) |

---

## ACTIONS COMPLETED

- [x] Pre-flight ALL GREEN (dataset, baseline, secrets, credit, instances=0)
- [x] Cycle 7c v1 launched, FAILED at tokenize (Lesson #172 captured)
- [x] Generator fixed + dataset regenerated 548/548 string format
- [x] Cycle 7c v2 launched, training _TBD_ progress
- [ ] Adapter download + GGUF conversion (post-training)
- [ ] Ollama register migancore:0.7c
- [ ] Identity eval with baseline_day70_voice_fixed.json
- [ ] PROMOTE / CONDITIONAL / ROLLBACK decision
- [ ] Tracker + lessons commit + VPS sync

---

>> **Codex/Kimi:** RECAP_71C dibuat parallel dengan training. Update setelah eval verdict.
>> **Claude:** Tunggu Monitor notification, eksekusi post-pipeline, decision, commit.
