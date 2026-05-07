# CLAUDE PLAN — Day 71d | Cycle 7d: SFT Pivot for Voice/Casual
> Ditulis oleh: Claude Sonnet 4.6
> Tanggal: 2026-05-08 (sprint extension after Cycle 7c ROLLBACK)
> Status: DRAFT — Awaiting Kimi+Codex review

---

## DECISION FROM USER (Day 71c)

User: "Oke saya ikut saran kamu!" → executes **Option C + Option D parallel**.

**Option C (DONE in this sprint):**
- ✅ migancore:0.3 confirmed as production stable (already live)
- ✅ Q5 reference updated to realistic 17-word natural Indonesian (Lesson #176)
- ✅ baseline_day71_voice_realistic.json created
- 🟡 Re-eval migancore:0.3 against new baseline IN PROGRESS

**Option D (THIS PLAN — Cycle 7d R&D track):**
- 200 voice-only SFT pairs generated (5 families × 40)
- SFT trainer skeleton (cycle7d_sft_vast.py) drafted
- Awaiting agent review before launch

---

## ROOT CAUSE ANALYSIS — Why Cycle 7c Failed

| Factor | Detail | Severity |
|--------|--------|----------|
| Signal density | 40 Q5 pairs / 548 = 7.3% (target ≥15%) | P0 |
| Wrong loss tool | ORPO rewards/margins NEGATIVE throughout | P0 |
| Diversity dilution | C7 base 508 pairs override targeted change | P1 |
| Reference too brief | Q5 ref 7w punishes natural 20-25w response | P0 |

**Therefore Cycle 7d MUST address all 4:**
1. ✅ 100% voice/casual signal density (200/200 pairs)
2. ✅ SFT loss (direct supervised, not preference-based)
3. ✅ No diversity dilution (zero off-topic pairs)
4. ✅ Realistic reference (17w natural casual, Lesson #176)

---

## CYCLE 7d STRATEGY — SFT-First Voice Training

### Dataset (DONE)
- **File**: `/opt/ado/data/workspace/cycle7d_sft_dataset.jsonl`
- **Pairs**: 200 SFT format (messages: system + user + assistant)
- **Families**: 5 × 40 each
  - casual_greeting: "Hai! Bagaimana kabarmu?"
  - casual_check: "Lagi sibuk apa?"
  - casual_intro_request: "Bisa kenalan?"
  - casual_help_request: "Lagi butuh bantuan dikit"
  - casual_thanks_continue: "Makasih ya, lanjut topik lain"
- **Response length**: 3-17 words (natural casual range)
- **Style**: Direct, AI-transparent, action-oriented (founder's voice spec)

### Hyperparams (vs Cycle 7c ORPO)

| Param | Cycle 7c ORPO | Cycle 7d SFT | Why changed |
|---|---|---|---|
| Algorithm | ORPO (apo_zero) | SFT | Direct supervision for length-style targets |
| LR | 1.2e-6 | 5e-7 | Avoid catastrophic forgetting on focused dataset |
| Epochs | 3 | 5 | More passes, smaller data |
| LoRA r | 16 | 8 | Focused adaptation, smaller delta |
| Steps | ~102 | ~63 | 200 pairs × 5 ÷ 16 |
| Pairs | 548 (mixed) | 200 (focused) | 100% voice signal density |

### Cost Estimate
- A40 @ $0.322/hr × ~15 min = **~$0.08 training**
- HF roundtrip: $0
- **Total estimated: ~$0.10**

### HF Roundtrip (Lesson #173 applied)
```
1. Train on Vast → adapter on /root/cycle7d_adapter
2. huggingface-cli upload Tiranyx/migancore-7b-soul-v0.7d (parallel multi-file)
3. DELETE Vast instance immediately (cost containment)
4. hf_hub_download to VPS /opt/ado/cycle7d_output/
5. GGUF conversion + Ollama register migancore:0.7d
```
NO SCP. HF push first, then delete, then HF pull. Defeats Lesson #173 SCP-timeout failure mode.

---

## PRE-LAUNCH BLOCKERS

| # | Blocker | Owner | Status |
|---|---------|-------|--------|
| 1 | Write `train_sft_standard.py` (SFT trainer) | Claude Day 72 | ❌ TODO |
| 2 | Kimi review SFT pivot strategy | Kimi | ⏳ Awaiting |
| 3 | Codex QA gate policy for SFT (different from ORPO) | Codex | ⏳ Awaiting |
| 4 | Re-eval migancore:0.3 vs realistic baseline (Option C) | Claude Day 71c | 🟡 RUNNING |

---

## SUCCESS CRITERIA (Cycle 7d)

| Metric | Target | Current (C7c) | Note |
|--------|--------|---------------|------|
| voice category | ≥ 0.85 | 0.789 | Q5+Q6 average |
| Q5 individual | ≥ 0.80 | 0.625 | Realistic ref makes this easier |
| identity | ≥ 0.90 | 0.925 | Maintain |
| weighted_avg | ≥ 0.92 | 0.8829 | Codex B3 promote gate |
| creative regression | < 0.05 | -0.193 (HUGE) | Risk: SFT may dilute creative — monitor |
| evolution-aware regression | < 0.05 | -0.199 (HUGE) | Same risk |

**Gate decision (Codex B3 reaffirmed):**
- PROMOTE: voice ≥ 0.85 AND weighted_avg ≥ 0.92 AND creative ≥ 0.85 AND evolution-aware ≥ 0.65
- CONDITIONAL: voice ≥ 0.85 AND weighted_avg ≥ 0.88 AND no category < 0.65
- ROLLBACK: else

---

## RISKS

| Risk | Severity | Mitigation |
|------|----------|------------|
| SFT overfits voice → dilutes other categories | P1 | LR 5e-7 (low) + r=8 (small adaptation) |
| Catastrophic forgetting on identity | P2 | Start from Qwen base, not from :0.3 adapter |
| Realistic baseline still too narrow | P2 | Test against multiple sample responses, broaden ref if needed |
| SFT trainer not yet written | P1 | Write Day 72, test on smoke 10 pairs first |

---

## NEXT STEPS

1. **Day 71c FINAL**: Complete this sprint with re-eval :0.3 + commit all
2. **Day 72 morning**: Write `train_sft_standard.py` (SFT trainer wrapper)
3. **Day 72**: Kimi+Codex review CLAUDE_PLAN_71D
4. **Day 72**: Smoke test SFT trainer on 10 pairs (avoid Lesson #172 repeat)
5. **Day 72-73**: Launch Cycle 7d if approved
6. **Day 73**: Eval + decision (PROMOTE :0.7d / KEEP :0.3 / iterate)

---

>> **Kimi:** Review SFT pivot vs ORPO. Confirm Lesson #175 reasoning. Recommend any hyperparam change.
>> **Codex:** QA gate policy for SFT (different gradient dynamics than ORPO). Pre-flight checklist for launch.
>> **Claude:** RECAP_71C reflects current state. Awaiting reviews + Day 72 execution window.
