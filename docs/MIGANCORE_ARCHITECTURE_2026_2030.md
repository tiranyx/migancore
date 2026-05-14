# MiganCore — Architecture Vision 2026 → 2030

**Date:** 2026-05-14 (Day 73)
**Status:** Foundational architecture reference. Living document.
**Owner:** Fahmi Ghani / PT Tiranyx Digitalis Nusantara

## I. VISION HORIZON

> **"Migan harus bisa kembang seperti Claude Code, OpenClaw, ChatGPT Canvas, dengan inline artifacts, multi-modal, akses sistem, basic-basic semua disiplin — lalu belajar sendiri spesifik per domain."**

5-year horizon mengarahkan Migan dari **assistant** → **collaborator** → **autonomous specialist** per organization.

---

## II. KAPABILITAS — Mapping ke Sprint Roadmap

### A. ALREADY IN ROADMAP (existing sprints)

| Kapabilitas (Fahmi minta) | Existing sprint | Status |
|---------------------------|-----------------|--------|
| Code execution + iterate (ala Claude Code) | Sprint 2 Code Lab | ✅ MVP done |
| Multi-modal inline (image/audio/video) | Sprint 4 (canvas+image edit), Sprint 9 (video) | planned |
| 3D modeling | Sprint 9 (Blender CLI) | planned |
| MCP connector | Day 26 + Sprint 8 federated | ✅ live |
| Coding katas / practice | Sprint 7 | planned |
| VSCode IDE in browser | Sprint 6 (code-server) | planned |
| PowerShell CLI bridge | Sprint 9 (security-careful) | planned |
| Self-modify code (Evolusi) | Sprint X | future |
| Camera + screen share | Sprint 3 + Sprint 6 | planned |
| Voice tone | Sprint 2 ✅ done | shipped |

### B. NEW — Need to add as Sprint 10+

| Kapabilitas | Effort | Sprint slot |
|-------------|--------|-------------|
| **Inline Artifact Rendering** (chart, PDF, slide displayed IN chat, not external link) | medium | **Sprint 10** |
| **Python rendering inline** (Plotly, matplotlib output → SVG/PNG inline) | small | Sprint 10 |
| **Data analysis runtime** (CSV/Excel ingest + analysis + viz) | medium | Sprint 10 |
| **Web builder** (HTML/CSS/JS scaffold + sandbox preview iframe) | medium | Sprint 11 |
| **PDF generator inline** (WeasyPrint already exists, surface in chat) | small | Sprint 10 |
| **Slide generator inline** (Marp exists, surface as carousel) | small | Sprint 10 |
| **Video generation** (fal.ai Kling/Minimax, or OpenRouter video models) | medium | Sprint 12 |
| **Image gen inline** (FLUX already, ensure displayed in chat) | ✅ done | tweaks Sprint 4 |
| **Web scraping** (onamix exists, extend) | ✅ partial | extend Sprint 3 |
| **Connector API generator** (brain reads OpenAPI spec → wraps as tool) | medium | Sprint 11 |
| **Cowork (multi-user shared session)** | LARGE | Sprint 15+ (defer — no signal yet) |
| **Desktop apps integration** (computer-use style) | large | Sprint 14 |

### C. DOMAIN KNOWLEDGE LAYER (later sprints)

| Domain | Approach | Sprint |
|--------|----------|--------|
| Accounting & Finance | RAG ingest curated books + tax regs | Sprint 13 |
| Trading & Crypto | Realtime API connector + KG | Sprint 13 |
| Carbon Tax & Sustainability | Indonesia ESG regs RAG + calculator tools | Sprint 13 |
| Legal & Contract | Doc parsing + clause library | Sprint 14 |
| Engineering (mech/elec/civil) | Calculation libs + STEM RAG | Sprint 14 |
| Game Design | Asset gen + scripting helpers | Sprint 15 |
| Bahasa Pemrograman foundation | SIDIX inherit (12 roadmap docs) | ✅ Sprint 1 done |
| API / Server / DevOps basics | SIDIX inherit + extends | ✅ + Sprint 7 |

**Approach: "Provide foundation, let Migan learn organically"** — sesuai instruksi kamu. Tiap domain tidak pre-build expert agent; Migan tumbuh per kebutuhan beta user real.

---

## III. FOUNDATIONAL ARCHITECTURE PRIMITIVES

Yang dibutuhkan SEKARANG biar Migan bisa ekspansi ke kapabilitas atas:

### Primitive 1: **Artifact System** (Sprint 10 priority)

Inspirasi: Claude Artifacts, ChatGPT Canvas.

```
User: "buatkan chart sales 6 bulan terakhir"
   ↓
Brain → run_python code → generates Plotly chart
   ↓
Code Lab returns: {type: 'chart', mime: 'image/svg+xml', data: '<svg>...</svg>'}
   ↓
Chat UI: render INLINE <img> bubble (BUKAN external link)
   ↓
Persist: artifact stored di artifacts table, fingerprint = sha256
   ↓
Future recall: "tampilkan chart kemarin" → query artifacts by recent
```

Schema baru:
```sql
CREATE TABLE artifacts (
  id UUID PRIMARY KEY,
  conversation_id UUID NOT NULL,
  tenant_id UUID NOT NULL,
  kind TEXT NOT NULL,   -- 'chart' | 'pdf' | 'slide' | 'image' | 'video' | 'audio' | 'html' | 'code'
  mime_type TEXT NOT NULL,
  data BYTEA OR url TEXT,  -- inline binary or storage ref
  metadata JSONB,        -- prompt, source, params
  created_at TIMESTAMPTZ DEFAULT now()
);
```

API:
- `POST /v1/artifacts` (auto from tool output)
- `GET /v1/artifacts/{id}` (render inline)
- `GET /v1/conversations/{id}/artifacts` (timeline)

Frontend:
- Chat bubble detects artifact ref → render inline (img/svg/pdf-embed/video tag)
- Tidak external link kecuali asset > 10MB

### Primitive 2: **Sandbox Hub** (Sprint 10)

Multi-language execution sandbox:
- **Python** — current `run_python` tool ✅
- **JavaScript** — Node.js subprocess (already wired for hyperx-mcp)
- **Bash** — restricted subset (existing tool_executor)
- **R** — future (Sprint 13 for finance/stats)

Pattern: thin wrapper, NOT framework. Each language: single-purpose subprocess executor.

### Primitive 3: **System Access Bridge** (Sprint 9 — security-careful)

Whitelist-based RPC dari brain ke host system:
- `POST /v1/system/cmd` — whitelisted commands only (ls, git status, npm test, etc)
- `POST /v1/system/file_read` — sandbox file read with path validation
- `POST /v1/system/file_write` — sandbox file write
- NEVER: arbitrary shell, sudo, network without explicit allow

### Primitive 4: **API Connector Generator** (Sprint 11)

Brain consumes OpenAPI/Swagger spec:
```
User uploads stripe-openapi.json
   ↓
Brain parses spec → generates wrapper tool:
  - tool_id: stripe_create_payment
  - schema: from spec
  - handler: HTTP call to api.stripe.com
   ↓
Auto-register to TOOL_REGISTRY (sandboxed, owner-approval)
```

This is **Tool Autonomy MVP++** — extends Sprint 3.

### Primitive 5: **Multi-Modal Output Channel** (Sprint 10-12)

Tool response shape standardization:
```python
@dataclass
class ToolOutput:
    text: str                  # always present (markdown ok)
    artifacts: list[Artifact]  # inline display items
    actions: list[Action]      # suggested follow-up
```

UI: progressive disclosure — text first, artifact below, action chips at bottom.

### Primitive 6: **Domain Knowledge Pluggable Buckets** (Sprint 13+)

Extend bucket system (`ilm:coding`, etc) dengan domain-specific:
- `ilm:accounting` — PSAK, IFRS basics
- `ilm:trading` — crypto regs, technical analysis
- `ilm:legal` — Indonesia legal frameworks
- `ilm:engineering` — STEM foundations

Ingest source: curated open datasets (HuggingFace) + Tiranyx-specific corpus.

---

## IV. EVOLUSI ROADMAP — Sprint 10-20

| Sprint | Days | Theme | Deliverables |
|--------|------|-------|--------------|
| **10** | 201-220 | **Artifact System** | artifacts table + API + inline rendering (chart, PDF, slide, image) |
| **11** | 221-240 | **Web Builder + API Connector** | HTML scaffold + sandbox preview iframe, OpenAPI-to-tool generator |
| **12** | 241-260 | **Video Generation** | fal.ai Kling/Minimax integration, inline video bubble |
| **13** | 261-300 | **Domain: Finance/Sustainability** | accounting/trading/carbon tax RAG ingest + calculator tools |
| **14** | 301-340 | **Legal + Engineering Domain** | doc parsing, contract clause library, STEM foundations |
| **15** | 341-380 | **Desktop Apps Integration** | computer-use style hooks (extends Sprint 9 PowerShell relay) |
| **16+** | 381+ | **Cowork (multi-user)** | shared session, real-time collab — IF signal from beta |

---

## V. PRINCIPLE-DRIVEN — Per Selective Adoption Doctrine

**JANGAN adopt:**
- Frameworks (LangChain artifacts, ChatUI frameworks) — build thin custom
- Cloud-only artifact stores (S3, CDN) — local first, cloud later
- LLM-as-code-executor (use real subprocess sandbox)

**ADOPT (selective):**
- Plotly Python (chart inline, pure-python, no extra runtime)
- WeasyPrint (PDF — sudah ada)
- Marp (slide — sudah ada)
- fal.ai SDK (video — sudah ada)
- Pyodide (Sprint 2 — sandbox Python in browser if needed)
- code-server (Sprint 6)
- Blender headless (Sprint 9)

---

## VI. VISION 2030 — North Star

**Migan at Day 1825 (Year 5):**

User scenario:
> Fahmi: "Mig, audit Q4 2030 keuangan Tiranyx — find anomaly, suggest tax optimization sesuai carbon tax 2029."
>
> Migan:
> 1. Pulls Q4 transactions dari connected accounting API (auto-spawn data connector saat onboarding 2 tahun lalu)
> 2. Runs Python analysis in Code Lab → generates anomaly chart
> 3. Cross-reference Indonesia carbon tax law 2029 (RAG from ilm:legal:tax)
> 4. Proposes 3 optimization scenarios → artifact: comparison table inline
> 5. Generates PDF report → inline preview + download
> 6. Save lessons learned ke hikmah bucket → next audit faster
> 7. Recall: "Last quarter Fahmi prefer optimization conservative" — adjust recommendation
>
> All in 1 conversation. Inline. No external links. Tabayyun multi-source verified. Pencipta bond strong.

This requires:
- ✅ Foundation knowledge (Sprint 1 done, extends per domain)
- ✅ Code Lab + reflection (Sprint 2 ✓)
- 🚧 Artifact system (Sprint 10)
- 🚧 Multi-tenant memory (Sprint 4)
- 🚧 Connector API generator (Sprint 11)
- 🚧 Per-domain RAG buckets (Sprint 13+)
- 🚧 Multi-modal inline rendering (Sprint 10-12)
- 🚧 Tool autonomy with sandbox approval (Sprint 3 MVP)
- 🚧 Drift detection (Sprint 5)
- 🚧 Saksi audit log (Sprint 8)

**Path clear. No magic.** Sprint per sprint, vision arrives.

---

## VII. ANTI-OVERBUILD GUARDRAILS

Setiap sprint baru cek:
1. Apakah ini extends primitive existing atau bangun framework baru? Extend > build
2. Apakah ada user signal real (beta user, Fahmi spesifik)? OR speculative?
3. Apakah ada thin-wrapper path 200 LOC? Atau force adopt heavy lib?
4. Apakah teach Migan ATAU ship feature? Vision = teach > ship

**Lebih baik 1 capability dengan 6-bulan retention dibanding 10 capabilities yang lapuk.**

---

## VIII. FOR AGENT LAIN

Saat baca doc ini:
- Setiap capability map ke sprint specific (lihat tabel)
- Update doc ini saat sprint complete (rotate ✅)
- Jangan duplicate ke arsitektur lain — SSOT principle
- Tagging convention: principle (Mizan/Hafidz/Akal/etc) + facility area (INDERA/TANGAN/OTAK/JIWA/PERTUMBUHAN)
