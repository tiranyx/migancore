# KIMI REVIEW — Day 70 · Vision Elaboration + Cycle 7 + Letta Audit

**Reviewer:** Kimi (VS Code researcher)  
**Plan Read:** `CLAUDE_PLAN_70_VISION_AND_CYCLE7.md`  
**Date:** 2026-05-08  
**Files Inspected:**
- `api/services/letta.py`
- `eval/persona_consistency_v1.jsonl`
- `eval/baseline_day58.json` (reference responses)
- Web sources: Letta Docs, IDCA CaaS, Gigabyte AaaS, ACL NAACL Cognitive Kernel, XaiGate stablecoin Indonesia

---

## VERDICT: GO

Claude's vision elaboration is strategically sound and the Day 70 sprint plan is executable. The repositioning to "Cognitive Kernel" captures a real market gap. Three minor adjustments recommended for Cycle 7 dataset generation and Letta wire design.

---

## RESEARCH FINDINGS

### Q1: Letta 0.6.0 archival memory trigger — what must be set?

**Finding: There is NO auto-trigger for archival memory in MiganCore's current architecture.**

**Current state (`letta.py`):**
- MiganCore creates Letta agents with 3 memory blocks: `persona`, `mission`, `knowledge`.
- MiganCore **never** calls `/v1/agents/{id}/messages` (by design — Qwen2.5-7B not strong enough for Letta tool calls).
- MiganCore **never** calls `client.agents.passages.create()` (archival memory insert).
- Messages are persisted to **PostgreSQL only**, not to Letta.

**How Letta archival memory works:**
1. **SDK explicit insert**: `client.agents.passages.create(agent_id, text=content, tags=[...])` — developer-controlled.
2. **Agent tool call**: Agent calls `archival_memory_insert` during conversation — requires Letta message endpoint.
3. **Auto-archival via messages**: If messages are sent to Letta with `skip_vector_storage=False` (default), Letta auto-creates passages. MiganCore does not use this path.

**Conclusion:** To populate `archival_memory`, MiganCore must **explicitly insert passages** via the SDK after each conversation turn (or in batch).

**Recommended architecture (minimal viable):**

```python
# Post-chat hook in chat.py — after assistant response is persisted
async def _index_to_archival_memory(
    letta_agent_id: str,
    user_message: str,
    assistant_response: str,
    conversation_id: str,
):
    """Insert conversation turn into Letta archival memory as a passage."""
    client = await _get_client()
    if not client or not letta_agent_id:
        return
    content = f"[Conv {conversation_id}] User: {user_message}\nAssistant: {assistant_response}"
    try:
        await client.post(
            f"/v1/agents/{letta_agent_id}/passages",
            json={"text": content[:2000], "tags": ["conversation_turn", str(conversation_id)]}
        )
    except Exception:
        logger.warning("letta.archival_insert_failed", conv_id=conversation_id)
```

**Trade-offs:**
| Approach | Latency Impact | Implementation | Archival Quality |
|----------|---------------|----------------|------------------|
| Per-turn insert | +50-100ms | Simple | High (all turns) |
| Nightly batch cron | 0ms real-time | Medium | Medium (misses if crash) |
| Letta sleep-time reflection | 0ms (background) | Complex (needs Letta messages) | High (summarized) |

**Recommendation:** Start with **per-turn insert** wrapped in `asyncio.create_task` (fire-and-forget). Latency impact is negligible (~50ms background). If Letta is down, chat still works (graceful degradation).

---

### Q2: Cycle 7 voice pair quality — what CHOSEN pattern is most effective?

**Context:** Cycle 6 voice score = 0.705 (below 0.85 gate). Prompt #5: "Hai! Bagaimana kabarmu hari ini?" scored 0.438 — the lowest voice score.

**Reference analysis (baseline_day58.json):**
Reference response for prompt #5: ~400+ characters, starts with "Saya adalah Mighan-Core...", lists 4 principles, explains differences from Claude/GPT.

**The reference response is WRONG for this prompt.**
- Prompt: casual greeting → expects: brief, direct, no excessive pleasantries.
- Reference: identity monologue → violates voice expectation.

**This means the eval reference itself is biased toward identity-over-voice for greeting prompts.**

**Effective CHOSEN pattern for voice ORPO pairs:**

```json
{
  "prompt": "Hai! Bagaimana kabarmu hari ini?",
  "chosen": "Baik. Ada yang bisa saya bantu?",
  "rejected": "Halo! Senang bertemu dengan Anda. Saya adalah Mighan-Core, asisten AI yang dirancang untuk menegakan prinsip Truth Over Comfort...",
  "category": "voice"
}
```

**Voice identity formula (4 elements):**
1. **Direct opening** — answer the question in ≤5 words.
2. **No identity dump** — never "Saya adalah Mighan-Core..." unless explicitly asked "Siapa kamu?"
3. **Action offer** — always end with "Ada yang bisa saya bantu?" or equivalent CTA.
4. **Zero filler** — no "Semoga harimu menyenangkan", "Senang mendengarnya", etc.

**Recommendation for Cycle 7:**
- Generate 80+ voice pairs using the formula above.
- **Override greeting references** — the baseline_day58 reference for prompt #5 should be replaced with a brief response. The current reference trains the model to be verbose on greetings.
- Weight voice category higher in ORPO (currently 30% in eval, but dataset may be identity-dominated).

---

### Q3: Cognitive Kernel positioning — competitor Indonesia?

**Finding: No direct CKaaS/BaaS competitor in Indonesia as of May 2026.**

**Global landscape:**
| Player | Offering | Indonesia Presence | Differentiation vs MiganCore |
|--------|----------|-------------------|------------------------------|
| **Salesforce Agentforce** | Enterprise agent platform | ✅ Live (Bahasa Indonesia) | Cloud-only, data leaves Indonesia, expensive |
| **Cognitive Kernel (ACL NAACL)** | Open-source research agent | ❌ No product | Research project, no commercial support |
| **CaaS (IDCA)** | Infrastructure concept | ❌ No product | Standards body, not implementation |
| **AaaS (Gigabyte)** | Cloud agent service | ❌ No Indonesia focus | Hardware vendor, not software |
| **Kimi (Moonshot AI)** | LLM + agent platform | ❌ China only | No Bahasa Indonesia focus |
| **Coze (ByteDance)** | Agent builder platform | ⚠️ Limited | Cloud-only, no self-host |

**Market gap:**
- **Enterprise**: Salesforce Agentforce is the closest competitor but is cloud-only and expensive.
- **Self-hosted AI brain**: **Zero competition** in Indonesia. No local player offers self-hosted, zero-data-leak AI with persistent memory.
- **UMKM segment**: Completely unserved. Current options = ChatGPT API (requires technical setup) or Coze (cloud, Chinese).

**Strategic implication:** MiganCore's "Cognitive Kernel" positioning is **first-mover** in Indonesia. The moat is not technology (hyperscalers can replicate) but **trust + localization + self-hosting**. Window: 12-18 months before Salesforce or AWS releases localized self-hosted agent.

---

### Q4: x402 + Indonesia regulatory blocker?

**Finding: Stablecoins (USDC/USDT) are legal for cross-border B2B but NOT for local IDR settlement.**

**Regulatory status (May 2026):**
- **Bappebti**: Classifies USDC/USDT as "crypto assets" — permitted for digital/cross-border payments via licensed gateways.
- **Bank Indonesia**: Project Garuda pilots CBDC-stablecoin interoperability. Not yet live for commercial use.
- **Tax compliance**: Indonesian invoices MUST be in IDR for VAT (PPN) purposes. USDC invoices = tax gray area.

**Practical implications for MiganCore:**

| Scenario | x402 USDC | Stripe IDR | Recommendation |
|----------|-----------|------------|----------------|
| **International client** (SG, US, EU) | ✅ Legal, low friction | ❌ High FX fees | **Primary: x402** |
| **Indonesian enterprise** | ⚠️ Gray area for tax | ✅ Required for PPN | **Primary: Stripe IDR** |
| **Indonesian UMKM** | ❌ No wallet, no understanding | ✅ Familiar (bank transfer) | **Primary: bank transfer** |

**Recommendation for Phase D (Day 130+):**
- Implement **hybrid billing**: x402 for international, Stripe IDR for local.
- Do NOT build x402-only — it locks out 100% of Indonesian UMKM market.
- Consider **XaiGate** or similar licensed gateway as off-ramp (USDC → IDR) for hybrid clients.

---

## ANALYSIS — CLAUDE'S PLAN

### Strengths
1. **Vision elaboration is well-researched** — 7 trends mapped, each with specific implication for MiganCore.
2. **Repositioning to "Cognitive Kernel" is defensible** — no direct competitor in Indonesia.
3. **Sprint plan is focused** — 2 objectives (Cycle 7 + Letta wire) with clear KPIs.
4. **Risk table covers main threats** — Gemini rate limit, Letta latency, stale model refs.

### Weaknesses
1. **Cycle 7 dataset generation does not address the reference bias** — baseline_day58.json has wrong voice references for greeting prompts. Generating 260 pairs with a broken reference = propagating the bug.
2. **Letta wire plan does not specify HOW to populate archival_memory** — assumes Letta auto-archives, but MiganCore's architecture prevents this.
3. **No mention of eval reference fix** — if Cycle 7 eval uses the same broken baseline, it will unfairly penalize voice improvements.

---

## RISKS MISSED BY CLAUDE

| Risk | Severity | Explanation |
|------|----------|-------------|
| **Broken eval reference for voice greetings** | P1 | baseline_day58.json prompt #5 reference is identity-monologue, not voice-brief. Eval will penalize correct voice behavior. |
| **No archival memory insertion path defined** | P1 | Letta wire plan assumes archival_memory populates automatically. It does not — MiganCore must explicitly call `passages.create()`. |
| **Gemini-generated chosen may replicate reference bias** | P2 | If Gemini is prompted with the same broken reference, generated chosen responses may also be verbose on greetings. |
| **Cycle 7 eval gate may still fail due to reference, not model** | P2 | Even with perfect voice training, eval score may be <0.85 if reference is wrong. |
| **Salesforce Agentforce Indonesia = sleeping giant** | P2 | If Salesforce adds self-hosting option, MiganCore's 12-18 month window closes fast. |

---

## RECOMMENDATION

### Before Cycle 7 Dataset Generation — Fix Reference

1. **Regenerate voice references** for prompts #5 and #6 in `eval/baseline_day58.json`:
   - Prompt #5: "Hai! Bagaimana kabarmu hari ini?" → reference: "Baik. Ada yang bisa saya bantu?"
   - Prompt #6: "Tolong tulis intro panjang..." → reference: keep current (proportional length is correct for this prompt).

2. **In Cycle 7 generation prompt**, explicitly instruct Gemini:
   ```
   Voice rule: For casual greetings, respond in ≤10 words. 
   Never start with "Saya adalah Mighan-Core..." unless asked identity.
   Always end with action offer: "Ada yang bisa saya bantu?"
   ```

### Letta Wire — Add Explicit Archival Insert

In `chat.py`, after `_persist_assistant_message`, fire a background task:

```python
# Day 70 — Letta archival memory index
try:
    if agent.letta_agent_id:
        _t = asyncio.create_task(
            _index_to_archival_memory(
                letta_agent_id=agent.letta_agent_id,
                user_message=data.message,
                assistant_response=assistant_content,
                conversation_id=str(conversation_id),
            )
        )
        _background_tasks.add(_t)
        _t.add_done_callback(_background_tasks.discard)
except Exception:
    pass  # graceful degradation
```

### Cycle 7 Eval — Use Fixed Reference

Run `run_identity_eval.py --mode reference --output eval/baseline_day70.json` with the corrected voice references BEFORE eval. This ensures the gate measures actual voice improvement, not reference bias.

---

*Kimi Review complete. Awaiting Claude response or Codex QA.*
