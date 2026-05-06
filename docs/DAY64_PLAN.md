# DAY 64 PLAN — MiganCore
# Date: 2026-05-07
# Status: Cycle 4 ROLLBACK → Cycle 5 supplement DONE → Cycle 5 training NEXT

## KONTEKS: POSISI HARI INI

### What Just Happened (Day 63–64)
- **Cycle 4 ROLLBACK** confirmed: weighted_avg 0.891 (gate 0.92), voice 0.739, evo-aware 0.537, tool-use 0.768 — 4 gates failed
- **migancore:0.3** tetap production (weighted_avg 0.9082)
- **Supplement COMPLETE**: 80 voice pairs + 60 evo-aware pairs = 140 pairs stored di DB
  - source: `voice_anchor_v1:cycle5` (80 pairs)
  - source: `evolution_aware_v2:cycle5` (60 pairs)
- **KB v1.3 COMMITTED** (commit 5388bf1): +10 domain baru, +companion file 47KB
  - Domains: Agama, Mistis/Folklor, Olahraga, Hukum, Kerajaan/Arkeologi, Dasar Negara, Tren Global, Kementerian, Tools Ekosistem, Referensi Riset
- **DB total**: ~2.530 pairs

### Production State
- Brain: `migancore:0.3` (Cycle 3, weighted_avg 0.9082)
- API: v0.5.19 LIVE
- VPS: 72.62.125.6, ADO containers UP
- Vast.ai credit: ~$6.90 remaining (dari $7)

---

## PRIORITY 1 — CYCLE 5 TRAINING (HARI INI)

### Dataset Export
```bash
# Di VPS:
cp /opt/ado/training/export_cycle5_dataset.py /opt/ado/data/workspace/
docker compose exec -T api python /app/workspace/export_cycle5_dataset.py \
  --output /app/workspace/cycle5_combined_dataset.jsonl
```

Target dataset: ~1.000 pairs
- 560 curated (identity/tool/code/cai/distill)
- 300 new domain (engineering/umkm/legalitas/creative_id/adaptive)
- 140 supplement (voice/evo-aware rollback fixes)

### KPI Checks (harus lulus sebelum training)
- Total: 900–1.200 pairs ✅/❌
- voice >= 60 ✅/❌
- evo_aware >= 45 ✅/❌
- Semua 5 domain >= 40 ✅/❌

### Training (Vast.ai)
```bash
# Adapt cycle4_orpo_vast.py → cycle5_orpo_vast.py
# Key changes:
#   DATASET_PATH = "cycle5_combined_dataset.jsonl"
#   run_name = "migancore-cycle5"
#   epochs = 2 (atau 3 kalau dataset ≥ 900)
python3 /opt/ado/training/cycle5_orpo_vast.py
```

Estimated cost: ~$0.15–0.30 (A40 46GB, ~200–300 steps)

### Eval & Gate
```bash
# Post-training:
docker compose exec -T api python /app/workspace/run_cycle5_eval.py \
  --model migancore:0.5
```

Gates Cycle 5:
- weighted_avg >= 0.92
- identity >= 0.90
- voice >= 0.85 (was 0.739, need +0.111)
- evo-aware >= 0.80 (was 0.537, need +0.263)
- tool-use >= 0.85 (was 0.768, need +0.117)
- creative >= 0.80

---

## PRIORITY 2 — VISION EXPANSION (KB & TOOLS)

Fahmi's direction (Day 64): KB harus cover semua aspek Indonesia + global.

### KB Roadmap
| File | Status | Isi |
|------|--------|-----|
| `indonesia_kb_v1.md` | ✅ v1.3 committed | Timeline 1800-2026, Agama, Mistis, Olahraga, Hukum, Kerajaan, Pancasila, Tren Global, Kementerian, Tools |
| `indonesia_comprehensive_v1.md` | ✅ committed | 15 bagian BPS/Kementan/KKP data terverifikasi |
| `global_trends_v1.md` | 🔲 TO DO | Deep-dive per megatren: AI adoption, climate, geopolitics |
| `religious_cultural_v1.md` | 🔲 TO DO | Ritual, festival, kalender adat, kearifan lokal per suku |
| `tools_ecosystem_v1.md` | 🔲 TO DO | Detail tech stack tiap kategori, API, integrasi |
| `indonesia_kb_v2.md` | 🔲 Day 70+ | Update harian dari sumber web (BPS RSS, JDIH, Bank Indonesia) |

### Daily KB Update Mechanism (Day 65–70)
Goal: Migan fetch + update KB otomatis setiap hari.

Approach:
1. Cron job VPS 06:00 WIB: hit endpoint `/api/kb/daily-update`
2. Endpoint hits BPS RSS (bps.go.id/rss), Bank Indonesia (bi.go.id/rss), JDIH (jdih.go.id)
3. New items → summarize via Qwen 7B → append ke `indonesia_kb_v1.md` (versioned)
4. Migan auto-retrieves via Qdrant RAG

### User Input → Training Data (Lesson #131 target)
Goal: Setiap percakapan user = potensi training pair.

Architecture:
- After each conversation: judge score via Gemini teacher
- If judge_score >= 0.85 → insert ke `preference_pairs` sebagai `cai_pipeline` source
- Weekly: batch export + masuk siklus training berikutnya

Status: Partially built (CAI pipeline Day 15). Perlu hook judge otomatis.

---

## PRIORITY 3 — TOOL EXPANSION

### Short-term (Day 64–70)
| Tool | Platform | Tujuan |
|------|----------|--------|
| BPS Data Fetcher | Python + requests | Ambil data statistik terbaru (inflasi, kemiskinan, dll) |
| JDIH Scraper | Playwright/Jina | Scrape regulasi terbaru |
| IDX/Stockbit reader | API/scrape | Ambil data saham, IHSG |
| News aggregator | RSS (Kompas/Detik/Tempo) | Berita harian → training data |
| WhatsApp sender | Twilio/360dialog | Notifikasi ke user |

### Medium-term (Day 71–90)
| Kategori | Tools Target |
|----------|-------------|
| Social Media | Twitter/X API v2, Instagram Graph API, TikTok for Developers |
| Marketplace | Tokopedia Partner API, Shopee Open Platform |
| Enterprise | Google Workspace API (Docs/Sheets), Microsoft Graph API (Office 365) |
| Finance | Midtrans API, Xendit API, IDX data feed |
| AI Orchestration | LangChain agents, n8n webhook → Migan |

---

## PRIORITY 4 — MULTI-BAHASA & PERSONA

### Bahasa Target
1. Bahasa Indonesia (current) ✅
2. Bahasa Inggris ✅ (partial, needs more pairs)
3. Bahasa Jawa (Ngoko/Krama) — 100M+ speakers
4. Bahasa Sunda — 42M speakers
5. Bahasa Minangkabau / Padang — komersial penting
6. Bahasa Bugis/Makassar — Sulawesi commerce hub
7. Melayu Regional — SEA expansion

### Adaptive Persona (sudah ada 55 pairs)
Expand untuk:
- Profil lansia vs Gen Z (sudah)
- Profil pengusaha vs akademisi (sudah)
- Regional dialect adaptation (baru)
- Formal vs casual register switching (baru)

---

## LESSONS (New Day 64)

### Lesson #131 (pending validation): KB depth > KB breadth
- 10 domain baru hari ini, tapi depth tiap domain masih shallow
- Prioritaskan 3 domain paling relevan bisnis (Hukum, Tools, Global Trends) untuk deep-dive

### Lesson #132 (pending): Daily auto-update KB = moat jangka panjang
- Static KB = outdated dalam 3 bulan
- Dynamic KB via RSS/web fetch = keunggulan kompetitif berkelanjutan

---

## CHECKLIST DAY 64

- [x] KB v1.3 committed (+10 domain, +companion file)
- [x] Supplement pairs selesai (80 voice + 60 evo-aware)
- [ ] Export Cycle 5 dataset (run di VPS)
- [ ] Launch Cycle 5 training (Vast.ai)
- [ ] Sync VPS (git pull + pull KB files)
- [ ] MEMORY.md updated
- [ ] DAY64_PLAN.md committed

---

## NEXT MILESTONES

| Target | ETA | KPI |
|--------|-----|-----|
| Cycle 5 PROMOTE | Day 64–65 | weighted_avg ≥ 0.92, voice ≥ 0.85, evo-aware ≥ 0.80 |
| Daily KB updater live | Day 67 | BPS + BI + JDIH RSS auto-fetch |
| 3 new tools deployed | Day 68 | BPS fetcher, news aggregator, IDX reader |
| Clone mechanism v1 | Day 70 | GAP-01 closed (per-client ADO deployment) |
| Multi-language beta | Day 75 | Javanese + English pairs 100 each |
| Cycle 6 training | Day 75 | Incorporate user conversation pairs |
