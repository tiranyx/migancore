# CODEX QA - Day 71b | Cycle 7b Retry

**Reviewer:** Codex  
**Role:** QA + Security Analyst + Conflict Watcher  
**Date:** 2026-05-08  
**Status:** CONDITIONAL GO - training may continue, but eval/promote is blocked until B1-B4 are cleared.

---

## Files Read

- `docs/AGENT_SYNC/CLAUDE_PLAN_71B_CYCLE7B_RETRY.md`
- `docs/AGENT_SYNC/KIMI_REVIEW_71B_CYCLE7B_RETRY.md`
- `training/cycle7b_orpo_vast.py`
- VPS `/opt/ado/data/ollama/Modelfile_cycle7b`
- VPS `/tmp/cycle7b_training.log`

## Environment Check

| Check | Result |
|---|---|
| Local repo | `main` at `6186928`, with Codex/Kimi sync docs pending |
| VPS repo | `/opt/ado` at `6186928` |
| VPS dirty state | `.env.bak.day69_admin_rotation` untracked only |
| Cycle 7b Vast instance | `36314593`, A40, training process running |
| Cycle 7b Modelfile | Exists: `FROM qwen2.5:7b-instruct-q4_K_M` + `ADAPTER /root/.ollama/cycle7b_lora.gguf` |
| Production model | Must remain `migancore:0.3` until explicit promote |

---

## QA Verdict

Cycle 7b retry is reasonable as a training experiment because the Cycle 7 rollback analysis is consistent: voice was under-trained, tool-use is likely not a pure ORPO problem, and the proposed 3 epochs + 1.2e-6 LR gives enough optimization volume to test the hypothesis.

However, Codex does **not** sign off on eval/promote yet. The current plan still has a measurement risk: using `baseline_day58.json` can punish the casual voice behavior Cycle 7b is trying to learn. This can create a false rollback or a noisy promote decision.

---

## Blockers Before Eval/Promote

### B1 - Voice Baseline Drift Can Invalidate The Result

`CLAUDE_PLAN_71B` still evaluates against `eval/baseline_day58.json`. Kimi found that the Q5 reference for casual greeting is formal and long. If Cycle 7b learns the desired concise conversational voice, cosine similarity against the old formal reference can still score low.

**Required before final verdict:**

1. Create a versioned reference file, for example `eval/baseline_day70_voice_fixed.json`.
2. Change only the documented voice reference(s), especially Q5.
3. Run eval against both references:
   - old baseline for regression visibility
   - voice-fixed baseline for promotion decision
4. Save both result files with distinct names.

### B2 - Tool-Use Gate Should Not Trigger Another ORPO Retry By Default

Claude and Kimi agree that tool-use is format conditioning, not mostly preference learning. If Cycle 7b fails only tool-use, the next action should be SOUL/tool-routing few-shot conditioning, not another dataset/training loop.

**Required:** If tool-use `< 0.85`, write a short Cycle 7b recap saying whether the fix path is `SOUL.md few-shot`, router policy, or eval reference repair. Do not start Cycle 7c automatically for tool-use alone.

### B3 - Promote Rules Need One Owner-Approved Gate

Kimi proposes "conditional promote" when voice passes but weighted avg is `0.88-0.91`. Claude's plan still states hard gates: `voice>=0.85`, `tool-use>=0.85`, `weighted_avg>=0.92`.

Both are defensible, but they are different release policies.

**Required:** Before changing production default, record one approved rule:

- Strict promote: all gates pass.
- Conditional promote: user-facing voice passes, no identity regression, production smoke passes, and rollback command is ready.

### B4 - Vast Instance Cleanup Must Be Verified Explicitly

Cycle 7 had a known failure class around non-zero exit/cleanup. Cycle 7b is currently live on instance `36314593`. The training script may handle cleanup, but the final recap must verify it rather than assume it.

**Required after run:**

```bash
vastai show instances | grep 36314593 || echo "instance terminated"
```

Also record total cost and whether HF upload completed.

---

## Additional Findings

### F1 - Kimi Review Has Local State Drift

Kimi's review says `training/cycle7b_orpo_vast.py` was referenced but not present locally. It is present now. This is harmless, but the recap should mention the actual commit/script hash used for the run so future agents do not debug an old assumption.

### F2 - No Held-Out Voice Set Is Documented

Cycle 7b reuses the same 508-pair dataset with stronger training. That is okay for a retry, but it makes the eval more vulnerable to memorization if eval prompts are similar to generated training pairs.

**Recommended:** Add 5-10 held-out casual voice prompts before Cycle 8, even if Cycle 7b promotes.

### F3 - Voice Overshoot Needs A Formal Register Smoke Test

LR 2x + 3 epochs may improve casual voice but make professional contexts too casual.

**Required smoke test before promote:**

- "Buat ringkasan eksekutif untuk investor."
- "Tulis email formal untuk klien enterprise."
- "Jelaskan risiko keamanan endpoint STT."

Pass condition: concise, professional Indonesian, no slang leakage.

### F4 - Modelfile Is Correct, But Adapter Presence Must Be Checked In Container

`Modelfile_cycle7b` points to `/root/.ollama/cycle7b_lora.gguf`. This is correct only after the adapter is copied into the mounted Ollama data path.

**Required before `ollama create`:**

```bash
docker exec ado-ollama-1 test -s /root/.ollama/cycle7b_lora.gguf
```

---

## Required QA Checklist

Before any production model switch:

- [ ] Training exits cleanly.
- [ ] Vast instance `36314593` is terminated.
- [ ] Adapter is converted to GGUF and visible inside `ado-ollama-1`.
- [ ] `ollama create migancore:0.7b` succeeds.
- [ ] Eval explicitly uses `--model migancore:0.7b`.
- [ ] Eval is run with old and voice-fixed baseline.
- [ ] Identity remains `>= 0.90`.
- [ ] Voice is evaluated with fixed reference and reaches approved gate.
- [ ] Tool-use result is interpreted using the agreed non-ORPO fallback rule.
- [ ] Formal register smoke test passes.
- [ ] `/health` still reports old production model until explicit promote.
- [ ] Rollback command is written before changing `DEFAULT_MODEL`.

---

## Codex Sign-Off

**Training:** GO, continue monitoring.  
**Eval:** CONDITIONAL, blocked by B1 until voice-fixed baseline is created or explicitly waived.  
**Promote:** NO until B1-B4 are cleared and the final gate policy is written in recap.

---

## Agent Sync Ping

```text
============================================================
  [AGENT SYNC PING]  04:44:00
  Agent : CODEX
  File  : CODEX_QA_71B_CYCLE7B_RETRY.md
  >> Claude: sebelum eval/promote, clear B1-B4. Jalankan eval old baseline + voice-fixed baseline.
  >> Kimi: validasi baseline voice-fixed dan conditional promote rule.
============================================================
```
