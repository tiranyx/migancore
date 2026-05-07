# CODEX QA — Day 71: Cycle 7 Training GO
**Sign-off:** CONDITIONAL

---

## SECURITY FINDINGS

| Severity | File | Issue | Recommendation |
|----------|------|-------|----------------|
| P1 | training/cycle7_orpo_vast.py | If `ssh_run()` raises during the long training command, the script explicitly does **not** delete the Vast.ai instance and exits with recovery instructions. That is good for manual recovery, but unsafe for unattended runs because a stuck training/SSH session can keep billing indefinitely. | Add a clear operator requirement: if exit code 7 occurs, Claude must immediately reconnect or delete the instance. Prefer writing instance id/host/port to a recovery file and adding a separate cleanup command. |
| P2 | training/cycle7_orpo_vast.py | HF token is interpolated into a remote shell command (`--token {HF_TOKEN}`). It may appear in process args or shell history/log surfaces on the rented instance. | Prefer `HF_TOKEN` as environment variable for the remote command, or use `huggingface_hub` Python API reading token from env/file. Ensure logs never echo the token. |

---

## LOGIC BUGS

1. **Missing Modelfile blocker:** Claude plan requires `ollama create migancore:0.7 -f /opt/ado/training/Modelfile_cycle7`, but server check shows `/opt/ado/training/Modelfile_cycle7` is missing. Training can run, but post-training registration/eval will fail unless this file is created before convert/register.
2. **Eval command mismatch:** Plan says run `run_identity_eval.py --mode eval --model-tag migancore-7b-soul-cycle7 --retry 3`, but this does not specify `--model migancore:0.7`. If the script defaults to `settings.DEFAULT_MODEL`, eval may score production `migancore:0.3` instead of candidate `migancore:0.7`.
3. **Promotion command incomplete:** `ollama cp migancore:0.7 migancore:latest` alone does not switch API production if `DEFAULT_MODEL` remains `migancore:0.3`. Promotion must update env/config or explicitly document that `latest` is not used by API.
4. **Cost cap checked too early only:** The script checks `COST_CAP_USD` after package install, but not during/after long training except final summary. A hung command can exceed the cap before cleanup.
5. **Dataset local/server parity not documented:** Dataset exists on VPS (`508` pairs, 317KB) but not in local workspace at check time. That may be intentional, but reproducibility requires checksum/line count in recap before GO.
6. **Kimi's under-training risk is not operationalized:** Same LR/epochs with fewer steps may be acceptable, but plan lacks a concrete Cycle 7b trigger and command if voice/tool-use fails.

---

## MISSING TESTS

Sebelum ship, harus ditest:
- [ ] Confirm `/opt/ado/training/Modelfile_cycle7` exists before running `ollama create`.
- [ ] Confirm Modelfile references the correct base model and adapter path (`cycle7_lora.gguf`) inside the Ollama container-visible mount.
- [ ] Run eval with explicit candidate model: `--model migancore:0.7`, not only `--model-tag`.
- [ ] Verify `/health` still reports production `migancore:0.3` before promotion.
- [ ] If promoted, verify `/health` reports the promoted model and rollback to `migancore:0.3` is tested.
- [ ] Record dataset checksum and `wc -l` before training.
- [ ] Verify Vast instance deletion in all non-recovery failure paths.
- [ ] Simulate missing HF upload or failed `scp_from`: ensure local adapter exists before instance deletion or explicitly accept loss risk.
- [ ] Confirm no token appears in `/tmp/cycle7_training.log` or remote shell output.

---

## SIGN-OFF: CONDITIONAL

Claude may start Cycle 7 training only if the operator accepts the manual cleanup responsibility for exit code 7.

Claude must not proceed to conversion/register/eval until:
- `Modelfile_cycle7` exists on VPS.
- Eval command explicitly targets `migancore:0.7`.
- Promotion procedure updates the actual API model setting or documents why `migancore:latest` is used.

Claude must not claim PROMOTE/ROLLBACK from an eval that does not explicitly score the candidate model.
