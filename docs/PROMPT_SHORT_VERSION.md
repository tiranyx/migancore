# SHORT PROMPT — For ChatGPT / Claude (character limit)
**Copy-paste ini kalau yang panjang kepotong.**

---

## KONTEKS
MiganCore = Autonomous Digital Organism (ADO). Multi-tenant AI agent platform. Owner: Fahmi Wol (non-technical designer). AI agents do 99% coding.

Stack: FastAPI + Postgres 16 + Redis + Qdrant + Ollama (Qwen2.5-7B) + Letta + LangGraph. VPS 32GB RAM + $50 RunPod budget.

Day 0-5 built: Auth (RS256 JWT, Argon2id, refresh rotation), RLS multi-tenant isolation, Ollama running, audit logging. Code coverage vs architecture: ~15%.

Missing: Agent CRUD, chat, LangGraph, Letta integration, Qdrant usage, Celery, tools, training pipeline.

## PROYEK INTERNAL DI VPS (ANALISIS READ-ONLY)
1. **SIDIX** — Production AI agent dengan 7-pillar self-awareness (Nafs/Aql/Qalb/Ruh/Hayat/Ilm/Hikmah), 35+ tools, 5 cognitive personas, CQF quality filter, Sanad provenance, Raudah multi-agent orchestration.
2. **Ixonomic** — Tokenization system dengan individual coin identity, supply integrity, two-step mint confirmation, multi-app monorepo.
3. **Mighantect3D** — 3D agent world dengan world.json (declarative agent config), lazy-loaded skill-registry.json, MCP-style execution, approval gate.

## 7 PERTANYAAN UNTUK KAMU

1. **Architecture Review:** Apakah stack (LangGraph + Letta + Qdrant + Ollama) appropriate untuk 32GB VPS + $50 RunPod? Adakah yang harus diganti?

2. **Code Review:** Review kode di github.com/tiranyx/migancore — apa top 3 code quality issues, top 3 security vulnerabilities, dan apakah RLS implementation robust untuk production multi-tenant SaaS?

3. **Internal Project Mapping:** Dari SIDIX (7-pillar, CQF, personas, skills), Ixonomic (supply integrity, approval gate), Mighantect3D (world.json, skill-registry, MCP execution) — mana yang harus diadopsi MiganCore segera, mana yang di-ignore, dan ada risiko over-engineering?

4. **2026 Trend Alignment:** Riset trend agentic AI 2026. Apa 3 trend paling penting yang MiganCore lewatkan? Apa 3 trend yang sudah aligned? Apakah self-improvement loop (weekly SimPO) masih genuine differentiator atau sudah table stakes?

5. **Fastest Path to "Aha Moment":** Fahmi butuh lihat agent berkarakter (bukan ChatGPT clone), agent yang ingat, agent yang bisa spawn. Dari state kode saat ini (15% built), apa path TERCEPAT ke demo? Day 6 harus fokus personality+chat atau infrastructure fixes? Apa yang harus dipotong dari 30-day sprint?

6. **Competitive Positioning:** CrewAI, AutoGen, Letta, Mem0, Replit Agent, Character.AI. Dimana MiganCore harus differentiate? Multi-tenant SaaS? Self-improving? Agent spawning? Indonesian-first?

7. **Risk Assessment:** Cross-tenant leak ✅ mitigated. Function calling <80% 🔴 not implemented. Agent feels generic 🔴 not addressed. Risiko baru apa yang kamu lihat? Risiko mana yang overblown?

## FORMAT JAWABAN
Untuk setiap pertanyaan, berikan:
- Analisis kritis (jangan setuju kalau memang salah)
- Verdict: [APPROPRIATE/OVER-ENGINEERED/UNDER-ENGINEERED] untuk architecture, [PRODUCTION-READY/NEEDS WORK] untuk code, dll.
- Rekomendasi actionable (apa yang harus dilakukan, bukan cuma "perlu diperbaiki")

## FINAL RECOMMENDATION
1 paragraf summary: top 3 actionable recommendations yang paling penting untuk Fahmi lakukan minggu ini.

---
**Be critical. Be specific. Be actionable. Truth over comfort.**
