# CODEX QA — Day 70: Vision Elaboration + Cycle 7 + Letta Audit
**Sign-off:** CONDITIONAL

---

## SECURITY FINDINGS

| Severity | File | Issue | Recommendation |
|----------|------|-------|----------------|
| P1 | api/routers/chat.py / api/services/letta.py | Letta archival memory insertion can become a cross-tenant leak if passages are inserted or later queried without strict `tenant_id + agent_id + conversation_id/message_id` scoping. Claude/Kimi propose archival insert, but the plan does not define isolation keys, idempotency, or retrieval filters. | Before wiring, require per-agent Letta ID ownership check, tenant-scoped tags/metadata, and retrieval limited to the current authenticated tenant/agent only. Add a cross-tenant negative test. |
| P1 | training/Cycle 7 generation script | Gemini-generated chosen responses can poison the training set if they include prompt-injection text, identity drift, secret requests, or tool-use instructions that should never be learned as model behavior. The plan mentions generation but not validation/filtering. | Add a dataset QA gate before DB insert/export: schema validation, banned phrase scan, identity consistency check, max length bounds, and manual sample review per category. |
| P2 | eval/baseline_day58.json / eval baseline update | Kimi is right that a broken voice reference can distort eval, but directly mutating the existing baseline would damage comparability across cycles. | Create a new versioned baseline, e.g. `baseline_day70_voice_fixed.json`, and document exactly which prompts changed. Never overwrite Day58 baseline silently. |
| P2 | Ollama model cleanup | Removing `migancore:0.1`, `migancore:0.4`, `migancore:0.5` is probably safe, but the plan must verify no env/config/docs/scripts/rollback path still references them before deletion. | Grep local + server `.env`, compose, scripts, docs, and Ollama Modelfiles. Keep at least current prod `migancore:0.3` and candidate `migancore:0.6` until Cycle 7 decisions are stable. |
| P2 | Letta archival memory content | Per-turn archival insert may store raw user messages. For the ADO zero-data-leak promise, this is okay inside the same tenant instance, but unsafe if later reused for Hafidz/parent contribution without anonymization. | Mark archival memory as tenant-local by default. Any parent/Hafidz export must be opt-in and anonymized separately. |

---

## LOGIC BUGS

1. **Letta KPI ambiguity:** `archival_memory > 0` proves data is being inserted, but not that memory is useful or safely retrieved. Add a functional KPI: “ask a follow-up in a new session and verify the answer uses prior memory from the same tenant only.”
2. **Fire-and-forget insert risk:** Kimi recommends background insertion. If the task fails silently, KPI may remain zero without surfacing to Claude. It needs structured log + counter/metric, even if chat degrades gracefully.
3. **Duplicate memory risk:** If chat persistence or retry runs twice, archival insert can duplicate the same conversation turn unless tagged by stable `message_id` and made idempotent.
4. **Cycle 7 reference bias fix can overfit eval:** If dataset generation and eval reference are both changed with the same rule, Cycle 7 may optimize for the eval prompt rather than general voice behavior. Keep held-out greeting prompts not used in training generation.
5. **BUILD_DAY update is not enough deploy proof:** `/health` showing Day 70 only proves API env updated. It does not verify frontend feedback, Letta archival insert, or dataset quality.

---

## MISSING TESTS

Sebelum ship, harus ditest:
- [ ] Letta archival insert writes a passage for the current agent after one completed chat turn.
- [ ] Cross-tenant test: Tenant B cannot retrieve or influence Tenant A archival memory.
- [ ] Duplicate/idempotency test: same `message_id` inserted twice does not create duplicate usable memory.
- [ ] Letta down test: chat still succeeds and logs `letta.archival_insert_failed` or equivalent.
- [ ] New-session memory test: prior tenant-local fact is recalled only for the same user/agent context.
- [ ] Cycle 7 dataset QA: no malformed JSONL, no empty chosen/rejected, no identity drift, no prompt-injection phrases in chosen.
- [ ] Eval baseline versioning test: Day58 baseline remains unchanged; Day70 fixed baseline is separately named and documented.
- [ ] Ollama cleanup dry run: grep proves removed model names are not referenced by live env/config/rollback path.
- [ ] After model cleanup, `/health` still reports `migancore:0.3` and `/ready` still sees required models.

---

## SIGN-OFF: CONDITIONAL

Claude may proceed with:
- Vision documentation.
- Cycle 7 dataset generation **only if** dataset QA/filtering is added before use.
- Letta audit/design.
- Ollama cleanup **only after** reference grep confirms no live dependency on deleted models.

Claude must not ship Letta archival wiring to production until:
- Tenant/agent isolation and retrieval filters are explicit.
- Failure logging/metrics exist.
- Cross-tenant and Letta-down tests pass.

Claude must not mutate existing eval baselines silently. Use a new Day70 baseline file and document changed references.
