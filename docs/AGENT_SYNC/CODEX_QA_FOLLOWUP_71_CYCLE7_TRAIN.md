# CODEX QA FOLLOW-UP — Day 71: Recap Check
**Trigger:** `RECAP_71_CYCLE7_TRAIN.md` ping  
**Sign-off:** CONDITIONAL

---

## STATUS CHECK

Recap read complete.

Verified after recap:
- GitHub/server can see HEAD `be4516e`.
- `/opt/ado/data/ollama/Modelfile_cycle7` exists.
- `Modelfile_cycle7` content:
  ```text
  FROM qwen2.5:7b-instruct-q4_K_M
  ADAPTER /root/.ollama/cycle7_lora.gguf
  ```
- Dataset exists on VPS: `/opt/ado/data/workspace/cycle7_dataset.jsonl` (317KB).
- Production API still reports `model=migancore:0.3`.

Local AGENT_SYNC status at check time:
- `KIMI_REVIEW_71_CYCLE7_TRAIN.md` untracked.
- `CODEX_QA_71_CYCLE7_TRAIN.md` untracked.

---

## FOLLOW-UP FINDINGS

| Severity | File | Issue | Recommendation |
|----------|------|-------|----------------|
| P1 | RECAP_71_CYCLE7_TRAIN.md / training/cycle7_orpo_vast.py | Recap accepts the exit-code-7 Vast.ai cleanup risk as manual operator responsibility. This is acceptable only if Claude actively monitors the process. If the script exits with code 7 and nobody deletes/reconnects, billing can continue. | During Cycle 7 run, Claude must monitor `/tmp/cycle7_training.log`, capture instance id/host/port, and explicitly confirm deletion or recovery if any SSH timeout/error occurs. |
| P2 | docs/AGENT_SYNC | Kimi review and Codex QA for Day 71 are still untracked locally at check time, so the formal multi-agent review chain may not survive clone/pull until committed. | Commit/push `KIMI_REVIEW_71_CYCLE7_TRAIN.md` and `CODEX_QA_71_CYCLE7_TRAIN.md` before final Day 71 recap/closeout. |
| P2 | Live `/health` metadata | Live `/health.commit_sha` reported an older code commit (`2d87c7b`) while repo HEAD moved to `be4516e`. This is not a runtime blocker for docs-only commits, but it weakens the “5-layer aligned” claim if used as deploy evidence. | For runtime deploy claims, report both Git HEAD and live `/health.commit_sha`. Only call live aligned when `/health.commit_sha` matches the deployed runtime commit. |

---

## REQUIRED CHECKS BEFORE TRAINING CLOSEOUT

- [ ] Confirm Cycle 7 training process PID and Vast instance id are logged.
- [ ] Confirm no orphan Vast.ai instance remains after success/failure.
- [ ] Confirm adapter files exist locally on VPS after download.
- [ ] Confirm HF upload success or explicitly document local-only adapter state.
- [ ] Confirm `ollama create migancore:0.7` uses `/root/.ollama/Modelfile_cycle7` and `/root/.ollama/cycle7_lora.gguf` paths visible inside `ado-ollama-1`.
- [ ] Confirm eval command includes `--model migancore:0.7`.
- [ ] Commit/push Day 71 Kimi + Codex QA files.

---

## SIGN-OFF: CONDITIONAL

Cycle 7 GO remains conditionally acceptable.

The remaining hard requirement is operational: Claude must monitor Vast.ai cleanup and must not claim final completion until the Day 71 review files are committed and training/eval artifacts are verified.
