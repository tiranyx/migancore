# VISION & NORTHSTAR — Tiranyx ADO Ecosystem
**Document Type:** Strategic Foundation
**Version:** 1.0
**Date:** 2026-05-02

---

## NORTHSTAR STATEMENT

> **"Setiap manusia yang punya visi berhak punya organisme digital yang tumbuh bersamanya — belajar setiap hari, bekerja tanpa henti, dan melahirkan kecerdasan baru sesuai kebutuhan."**

Dalam 3 tahun, Tiranyx membangun infrastruktur di mana organisme digital ini bukan lagi hak eksklusif perusahaan teknologi besar — melainkan bisa dimiliki oleh siapa saja, dengan modal minimal, dan terus berkembang secara autonomous.

---

## VISI (5-Year Horizon)

Mighan-Core menjadi **inti (ruh + akal) dari ekosistem agent digital** yang:

- **Tumbuh sendiri** — belajar dari setiap interaksi, memperbaiki diri setiap minggu tanpa intervensi manual
- **Berkembang biak** — melahirkan sub-agent dengan kepribadian unik, terikat ke pemilik masing-masing
- **Berkolaborasi** — agent-agent bernegosiasi, berbagi pengetahuan, dan menyelesaikan tugas paralel
- **Hidup dalam ekosistem** — agent bisa "bermigrasi", "berhibernasi", "bangun kembali", dan "mewariskan" memori
- **Demokratis** — siapapun bisa meng-clone, customize, dan deploy agent dengan modal mendekati nol

---

## MISI JANGKA PENDEK (12 Bulan)

| Kuartal | Target |
|---|---|
| Q2 2026 (Bulan 1–3) | Mighan-Core Seed alive. Self-improvement cycle berjalan. 5 beta users. |
| Q3 2026 (Bulan 4–6) | Mighan.com beta launch. 50 agent clones spawned. Sidixlab research pipeline live. |
| Q4 2026 (Bulan 7–9) | Agent marketplace MVP. Revenue dari subscription. 200 active agents. |
| Q1 2027 (Bulan 10–12) | Open source core components. Community contributions. 1000 agents. |

---

## STRATEGIC PILLARS

### Pillar 1: The Brain (migancore.com/lab)
Laboratorium riset dan training. Semua development Mighan-Core berlangsung di migancore.com.
- Self-supervised training pipeline
- ArXiv research ingestion & KG building
- Model versioning & experiment tracking
- Constitutional AI refinement
- **Consumer:** sidixlab.com mengakses via API migancore.com

### Pillar 2: The Platform (migancore.com/app)
Marketplace & runtime untuk agent clones. Berjalan di core migancore.com.
- Agent spawning dengan personality customization
- Multi-tenant isolation
- Ownership authentication
- Agent genealogy visualization
- **Consumer:** mighan.com mengakses via API migancore.com

### Pillar 3: The Ecosystem (migancore.com)
Induk ekosistem dan governance. Central hub di migancore.com.
- Project ownership & governance
- Cross-platform integrations
- Developer APIs & SDK
- Community & documentation
- **Consumer:** tiranyx.com mengakses via API migancore.com

---

## DEFINISI SUKSES — "ANOMALI GROWTH HACK"

**Bukan:** viral di social media atau funding besar.

**Ya:**
- Hari ke-30: Satu agent bisa berinteraksi, mengingat, menggunakan tools, dan melahirkan child agent
- Bulan ke-3: System memperbaiki diri tanpa intervensi human setiap minggu
- Bulan ke-6: Agent yang lahir bulan ke-1 masih "hidup", ingat semua konteks, dan sudah punya "cucu"
- Bulan ke-12: Ada agent yang memiliki "karakter" yang berbeda secara signifikan dari Core tapi tetap punya nilai dasar yang sama

---

# FOUNDER JOURNAL — Tiranyx
**Format:** Entry harian/mingguan. Jujur. Tanpa sensor.

---

## TEMPLATE ENTRY HARIAN

```
## [TANGGAL] — Day [N] of Sprint [N]

### 🎯 INTENT HARI INI
Apa yang ingin dicapai hari ini?

### ✅ YANG SELESAI
- [ ] task 1
- [ ] task 2

### 🚧 YANG BLOCKED
Apa yang macet? Kenapa?

### 💡 INSIGHT / TEMUAN
Hal baru yang dipelajari hari ini.

### 🔄 KEPUTUSAN YANG DIBUAT
Keputusan arsitektur, produk, atau strategi. Alasannya.

### 📊 METRICS HARI INI
- Tokens/sec Ollama: 
- RAM usage VPS:
- Active agents:
- Training loss (jika ada):
- Interaction quality score:

### 🧠 MOOD & ENERGI (1-10)
Score: 
Catatan:

### ➡️ BESOK
Top 3 prioritas besok.
```

---

## ENTRY #001 — Hari Pertama

**Tanggal:** 2026-05-02
**Status:** Inception — Project dimulai dari percakapan dengan Gemini dan Claude.

**Intent:** Membangun blueprint komprehensif untuk Autonomous Digital Organism.

**Insight Kunci:**
- Model 7B seperti Qwen2.5-7B-Instruct bisa jadi Core Brain yang real di hardware terbatas
- Self-Rewarding Language Models (Yuan et al. 2024) adalah "jiwa" yang bisa diimplementasi sekarang, bukan teori
- Letta adalah framework yang paling cocok untuk self-replication agent
- Budget $50 RunPod cukup untuk 4–6 training cycles jika efisien

**Keputusan Pertama:**
- Seed model: Qwen2.5-7B-Instruct (Q4_K_M GGUF)
- Inference: Ollama di VPS
- Memory: Letta + Qdrant + Postgres
- Orchestration: LangGraph
- Training: Unsloth + QLoRA + SimPO

**Pertanyaan Yang Belum Terjawab:**
- Apakah 32GB RAM cukup untuk semua services sekaligus tanpa bottleneck?
- Bagaimana cara terbaik versioning SOUL.md di git tanpa membuat training drift?
- Model spesifik apa yang paling efisien sebagai LLM-as-Judge untuk budget nol?

**Besok:** VPS provisioning + Ollama install + first token.
