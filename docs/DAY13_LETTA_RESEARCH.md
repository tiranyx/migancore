# DAY 13 — Letta Tier 3 Research & Architecture Decision
**Date:** 2026-05-03  
**Author:** Claude Sonnet 4.6  
**Status:** Research Complete → Implementation In Progress

---

## 1. VPS Ecosystem Map (Temuan Baru)

Sebelum Day 13, VPS audit mengungkap ekosistem yang lebih besar dari yang terdokumentasi:

```
/opt/ado/            → MiganCore (current sprint)
/opt/sidix/          → Sidix Brain + AI workspace
                       (Qwen2.5-7B + LoRA, own corpus, brain pack)
/root/mighantect-3d/ → Mighantech3D platform
                       (Node.js + Prisma, 3D/image gen via RunPod)
/root/mighan-ops/    → Mighan ops tooling
/var/www/ixonomic/   → Ixonomic web platform
/root/brain/         → Mighan-brain-1 public corpus
```

**RunPod Serverless Endpoints (dari screenshot):**
| Endpoint | VRAM | Queue | Use Case |
|----------|------|-------|----------|
| `vLLM v2.14.0` | 80GB | Based | LLM inference (Sidix brain / OpenAI-compat) |
| `mighan-media-worker` | 48GB | Based | Media/3D generation (Mighantech3D) |

**Implikasi:** MiganCore bukan proyek isolat — ia hidup di ekosistem multi-proyek. Arsitektur Letta harus dirancang dengan kesadaran ini.

---

## 2. Letta Status (Verified via Docker Probe)

| Aspek | Nilai |
|-------|-------|
| Container | `ado-letta-1` (Up 12 hours) |
| Internal port | 8283 (uvicorn) — bukan 8083 (EXPOSE mismatch di Dockerfile) |
| Host binding | TIDAK ADA — hanya accessible dari Docker network |
| URL dari API container | `http://letta:8283` ✅ |
| Auth | `Bearer {LETTA_PASSWORD}` |
| Database | `letta_db` (Postgres), 9 Alembic migrations ✅ |
| Agents saat ini | 0 — fresh installation |
| API version | 1.0.0 (Letta 0.6.0) |
| Total endpoints | 72 |

**Port mismatch note:** Letta Dockerfile menggunakan `EXPOSE 8083` tapi server berjalan di 8283.
`LETTA_URL: http://letta:8283` di config.py sudah BENAR. Bukan bug — EXPOSE hanya metadata, actual listen di 8283.

---

## 3. Letta API Surface (Relevant untuk Day 13)

```
POST   /v1/agents/                          → Create agent with memory blocks
GET    /v1/agents/{id}                      → Get agent info
GET    /v1/agents/{id}/memory               → Get full memory state
GET    /v1/agents/{id}/memory/block         → List all blocks
GET    /v1/agents/{id}/memory/block/{label} → Get specific block
PATCH  /v1/agents/{id}/memory/block/{label} → Update specific block
POST   /v1/blocks/                          → Create standalone block
POST   /v1/blocks/{id}/attach               → Attach block to agent
```

**Agent types:** `memgpt_agent` | `split_thread_agent` | `o1_agent`
→ Gunakan `memgpt_agent` (original MemGPT architecture, full block support)

**LLMConfig supports:** `openai` | `ollama` | `vllm` | `anthropic` | `groq` | ...
→ Day 13: `ollama` | Day 14+: `vllm` (RunPod endpoint) ← fondasi sudah siap

---

## 4. Arsitektur Decision: Multi-Block Pattern (vs Simple Single Block)

### ❌ Pendekatan Sederhana: Single Persona Block
```
Letta Agent
  └── persona block: [everything dumped here]
```
**Masalah:** Identitas + misi + pengetahuan tercampur → susah di-update secara selektif.

### ✅ Pendekatan Dipilih: Structured Multi-Block
```
MiganCore Agent (Postgres: agents.letta_agent_id → )
                                                      ↓
                                              Letta Agent
                                                ├── persona block [STABIL]
                                                │     Identitas inti, voice, values
                                                │     Diisi dari soul_text + overrides
                                                │     Limit: 2000 chars
                                                │
                                                ├── mission block [EVOLVES]  
                                                │     Tujuan & konteks saat ini
                                                │     Diupdate manual atau by owner
                                                │     Limit: 1000 chars
                                                │
                                                └── knowledge block [GROWS]
                                                      Fakta tentang owner/tenant
                                                      Auto-grow dari conversation (Day 14+)
                                                      Limit: 4000 chars
```

**Keunggulan jangka panjang:**
- `persona` stabil — identitas tidak berubah tiap chat
- `mission` dapat di-update per project/task
- `knowledge` tumbuh otomatis (Day 14+) tanpa merusak persona
- Setiap block independent → partial update, partial inject
- LLMConfig menunjuk Ollama sekarang → siap switch ke RunPod vLLM (Day 14)

---

## 5. System Prompt Injection Strategy

### Before (Day 12):
```python
parts = [soul_text.strip()]  # static file
if agent_cfg:
    persona = agent_cfg.get("persona_overrides", {})
    parts.append(f"Voice: {persona['voice']}")
    ...
```

### After (Day 13):
```python
# Tier 3: Letta blocks (evolved, persistent)
if agent.letta_agent_id:
    blocks = await letta_client.get_blocks(agent.letta_agent_id)
    if blocks.get("persona"):
        parts = [blocks["persona"]]  # override soul_text with evolved persona
    if blocks.get("mission"):
        parts.append(f"\n[MISI AKTIF]\n{blocks['mission']}")
    if blocks.get("knowledge") and "Belum ada" not in blocks["knowledge"]:
        parts.append(f"\n[KONTEKS DIKETAHUI]\n{blocks['knowledge']}")
else:
    # Graceful fallback: soul_text + overrides (existing behavior)
    ...
```

**Graceful degradation:** Jika Letta unavailable → fallback ke soul_text (Tier 0). Never blocks chat.

---

## 6. Future-Proofing: RunPod vLLM Integration (Day 14+)

RunPod vLLM endpoint (80GB) sudah tersedia. LettaClient dan OllamaClient harus:
1. LettaClient: LLMConfig menggunakan `model_endpoint_type: "ollama"` sekarang
   → Mudah diubah ke `"vllm"` + `model_endpoint: "{runpod_url}"` di masa depan
2. OllamaClient: Tambahkan abstraksi `InferenceBackend` untuk support multiple providers

**Tidak diimplementasi Day 13, tapi fondasi tidak akan perlu dirombak.**

---

## 7. Implementation Plan

### New File: `services/letta.py`
- `LettaClient` — async httpx client, singleton, auth dengan Bearer
- `ensure_letta_agent()` — get or create, returns `letta_agent_id`
- `get_blocks()` — fetch all blocks, returns `dict[str, str]`
- `update_block()` — PATCH specific block, silent fail on error
- `format_persona_block()` — build persona text dari soul + overrides
- Graceful degradation: semua methods return empty/None on Letta failure

### Modified: `routers/agents.py`
- `create_agent()` → after DB commit, `ensure_letta_agent` → save `letta_agent_id`
- `spawn_agent()` → child inherits parent's `persona` block content (clone)

### Modified: `routers/chat.py`
- `_build_system_prompt()` → async, fetches Letta blocks before building prompt
- Day 14+ hook: `# asyncio.create_task(maybe_update_knowledge_block(...))`

### Migration
- Tidak ada DB migration — `letta_agent_id` sudah ada di schema (Day 10) ✅

---

## 8. Constraint Log (JANGAN DILANGGAR)

| Constraint | Reason |
|------------|--------|
| JANGAN call `/v1/agents/{id}/messages` | Qwen2.5-7B tidak cukup kuat untuk Letta tool calls |
| JANGAN set tools di Letta agent | Sama — Letta as storage only |
| BOLEH: read/write blocks langsung | Via PATCH /memory/block/{label} |
| BOLEH: create agent baru | Saat MiganCore agent dibuat |
| Letta failure = log warning, NOT error | Graceful degradation wajib |

---

*Research lengkap. Implementasi dimulai setelah dokumen ini disimpan.*
