# MIGANCORE — DAILY PROTOCOL
**Dokumen Wajib | Anti Context Loss | Anti Rollback**
**Versi:** 1.0 | **Tanggal:** 2026-05-08

---

## FILOSOFI

> "Memory is sacred. Preserve what matters. Surface it proactively. Forget nothing relevant." — SOUL.md

Claude Code dan AI agent lain punya memory PENDEK. Setiap session baru = context baru. Tanpa protocol ketat, agent akan:
1. Mengulang pekerjaan yang sudah selesai
2. Melupakan keputusan yang sudah dibuat
3. Merusak fitur yang sudah jalan
4. Membuat circular loop (5x training rollback)

**Protocol ini adalah VACCINE untuk context loss.**

---

## PROTOCOL WAJIB MANDATORY

### 1. CATAT YANG SUDAH, CATAT YANG AKAN, CATAT TEMUAN

Setiap hari HARUS ada 3 catatan:
- **DONE:** Apa yang selesai hari ini
- **NEXT:** Apa yang akan dikerjakan besok
- **FOUND:** Temuan, insight, bug, lesson learned

### 2. BACA SELURUH DOKUMEN PENTING SEBELUM EKSEKUSI

Sebelum coding satu baris pun, agent HARUS baca:
1. `CONTEXT.md` — State proyek saat ini
2. `TASK_BOARD.md` — Task yang sedang/sudah/akan dikerjakan
3. `docs/MIGANCORE_ARCHITECTURE_REMAP_v2026.md` — Arsitektur
4. `docs/MIGANCORE_ROADMAP_MILESTONES.md` — Roadmap
5. Daily log hari ini (jika ada)

### 3. ANTI KEHILANGAN ARAH DAN KONTEKS

- Setiap keputusan arsitektural HARUS masuk ke `Decision Registry` di ARCHITECTURE_REMAP
- Setiap bug HARUS masuk ke `Known Issues` di CONTEXT.md
- Setiap lesson learned HARUS masuk ke `Lessons` dengan nomor
- Jangan pernah membuat keputusan tanpa mencatatnya

### 4. WRAP DAY BY DAY

Setiap hari SEBELUM selesai kerja, jalankan ritual wrap:
```
1. Update daily log
2. Update CONTEXT.md (status, decisions, issues)
3. Update TASK_BOARD.md (task status)
4. Commit semua perubahan dengan message yang jelas
5. Push ke GitHub
6. Tulis handoff note jika ada agent lain yang melanjutkan
```

---

## DAILY LOG FORMAT

**File:** `docs/logs/daily/YYYY-MM-DD.md`

```markdown
# Daily Log — [YYYY-MM-DD] — Day [N] of [Phase]

## 🎯 INTENT HARI INI
Apa yang ingin dicapai hari ini? (1-3 target saja)

## ✅ YANG SELESAI
- [HH:MM] [Agent]: [Task] — [commit hash]
- [HH:MM] [Agent]: [Task] — [commit hash]

## 🚧 YANG BLOCKED
- [Task]: [Kenapa blocked] — [Apa yang dibutuhkan untuk unblock]

## 💡 TEMUAN / INSIGHT
- [Temuan 1]: [Deskripsi] — [Implikasi]
- [Lesson #XXX]: [Deskripsi lesson]

## 🔄 KEPUTUSAN YANG DIBUAT
- [Keputusan]: [Alasan] — [Dampak]

## 📊 METRICS HARI INI
- Test pass rate: [XX%]
- Code coverage: [XX%]
- API latency p95: [X.Xs]
- Pairs generated: [X] (self: [X], owner: [X], user: [X], teacher: [X])
- Cost: [$X.XX]
- Mood & energy: [1-10]

## 🧪 TESTING & VALIDASI
- [Test yang dijalankan]: [Hasil]
- [Bug yang ditemukan]: [Status: fixed/pending]
- [QA sign-off]: [YES/NO]

## 📝 DOKUMENTASI
- File yang di-update: [list]
- Keputusan yang di-catat: [list]
- Handoff note: [link jika ada]

## ➡️ BESOK
1. [Task 1] — [Owner]
2. [Task 2] — [Owner]
3. [Task 3] — [Owner]

## 🛑 RITUAL WRAP
- [x] Daily log written
- [x] CONTEXT.md updated
- [x] TASK_BOARD.md updated
- [x] All changes committed
- [x] Pushed to GitHub
- [x] Handoff note written (if needed)
```

---

## AGENT ONBOARDING CHECKLIST

Setiap agent baru HARUS check semua ini sebelum kerja:

```
□ Baca CONTEXT.md (5 menit)
□ Baca TASK_BOARD.md (3 menit)
□ Baca docs/MIGANCORE_ARCHITECTURE_REMAP_v2026.md (10 menit)
□ Cek daily log hari ini (2 menit)
□ Cek git log 10 commit terakhir (2 menit)
□ Cek branch aktif (1 menit)
□ Claim task di TASK_BOARD.md (1 menit)
□ Buat branch: [agent-type]/[task-name]
□ Mulai kerja
```

**Total onboarding time: ~25 menit. Non-negotiable.**

---

## COMMIT MESSAGE CONVENTION

Format wajib:
```
[type]([scope]): [subject] — [WHY, not just WHAT]

[body — explain reasoning, link to issue/task]

Refs: TASK-XXX
```

Type:
- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation
- `test:` tests
- `refactor:` code refactoring
- `infra:` infrastructure
- `train:` training-related

Contoh baik:
```
feat(data): Add owner dataset upload endpoint — enables Pathway B growth

Owner can now upload JSONL/CSV/PDF files which get parsed into
training-compatible pairs. This unblocks real-data collection
from owner corrections and examples.

Refs: TASK-005
```

Contoh buruk:
```
update code
```

---

## HANDOFF PROTOCOL

### Kapan Handoff Diperlukan
- Task tidak selesai dalam satu session
- Ada keputusan penting yang perlu disampaikan
- State environment berubah signifikan
- Ada gotcha / trap yang perlu diwaspadai

### Handoff Note Format
```markdown
## HANDOFF — [Agent Lama] → [Agent Baru]
**Tanggal:** [YYYY-MM-DD HH:MM]
**Branch:** [branch name]
**Commit:** [hash]
**Task:** [TASK-XXX]

### ✅ Selesai
- [task] — [file] — [commit]

### 🏗️ State Sekarang
- [service/file]: [state]
- [service/file]: [state]

### ➡️ Yang Harus Dilanjutkan
1. [task pertama — kenapa penting]
2. [task kedua — dependensi apa]

### ⚠️ Watch Out
- [gotcha 1 — bisa menyebabkan apa]
- [gotcha 2 — workaroundnya apa]

### 🔄 Keputusan Baru
- [decision] — [reasoning]

### 📝 Context Updated
- CONTEXT.md: [apa yang di-update]
- TASK_BOARD.md: [apa yang di-update]
- ARCHITECTURE_REMAP: [apa yang di-update]
```

---

## DECISION REGISTRY PROTOCOL

Setiap keputusan arsitektural HARUS masuk ke registry:

1. **ID format:** D-XXX (sequential)
2. **Tanggal:** Kapan keputusan dibuat
3. **Keputusan:** Apa yang diputuskan
4. **Alternatif:** Apa yang dipertimbangkan tapi ditolak
5. **Alasan:** Kenapa memilih ini
6. **Dampak:** Apa konsekuensinya

**Lokasi:** `docs/MIGANCORE_ARCHITECTURE_REMAP_v2026.md` → Section 11: Decision Registry

**Aturan:** Keputusan tidak boleh diubah tanpa:
1. Review dampak rollback
2. Approval dari owner (untuk keputusan besar)
3. Update registry dengan entry baru (jangan hapus entry lama)

---

## LESSON LEARNED PROTOCOL

Setiap lesson HARUS punya:
1. **Nomor:** #XXX (sequential, permanent)
2. **Konteks:** Kapan dan di mana terjadi
3. **Lesson:** Apa yang dipelajari
4. **Action:** Apa yang harus dilakukan berbeda ke depan
5. **Status:** OPEN / IN PROGRESS / SOLVED

**Lokasi:** `docs/LESSONS_LEARNED.md` (create if not exists)

**Aturan:** Lesson tidak boleh dihapus. Hanya update status. Ini adalah biografi proyek.

---

## ROLLBACK PROTOCOL

### Kapan Rollback
- Eval gate FAIL
- Identity cosine sim < 0.85
- Tool-use accuracy < 80%
- Regression di known-good scenarios
- Production error rate > 5%

### Rollback Steps
1. **STOP** — Jangan panic. Jangan deploy fix tanpa paham root cause.
2. **LOG** — Catat apa yang terjadi, kapan, versi apa.
3. **ROLLBACK** — Hot-swap ke versi sebelumnya (Ollama create dari backup)
4. **INVESTIGATE** — Cari root cause. Jangan asumsi.
5. **FIX** — Fix root cause, bukan symptom.
6. **TEST** — Jalankan eval gate lagi.
7. **DEPLOY** — Baru deploy setelah semua test pass.
8. **DOCUMENT** — Catat sebagai lesson learned.

**Aturan:** Tidak boleh deploy fix production dalam < 2 jam setelah rollback. Investigate dulu.

---

## WEEKLY RITUAL (Setiap Minggu)

### Minggu: Training Cycle Day (02:00 WIB)
1. Trigger training cycle (jika data cukup)
2. Monitor progress
3. Eval gate setelah selesai
4. PASS → A/B deploy 10%
5. FAIL → Rollback, investigate, catat lesson

### Senin: Sprint Planning
1. Review milestone DoD — tercapai atau tidak?
2. Review metrics dashboard
3. Set priorities untuk minggu ini
4. Update TASK_BOARD.md

### Jumat: Review & Deploy
1. Review semua task minggu ini
2. Deploy ke staging
3. Beta user feedback review
4. Update roadmap jika perlu

---

## CONTEXT PRESERVATION TOOLS

### 1. CONTEXT.md
- **Purpose:** RAM proyek — state saat ini
- **Update:** Minimal sekali sehari, atau setiap ada keputusan penting
- **Read:** WAJIB dibaca sebelum kerja

### 2. TASK_BOARD.md
- **Purpose:** What to do now
- **Update:** Setiap claim/complete task
- **Read:** WAJIB dibaca sebelum kerja

### 3. Daily Log
- **Purpose:** History harian
- **Update:** Setiap hari sebelum selesai kerja
- **Read:** Cek log hari ini dan kemarin

### 4. Architecture Remap
- **Purpose:** Arsitektur dan keputusan
- **Update:** Setiap ada keputusan arsitektural
- **Read:** Sebelum membuat keputusan teknis baru

### 5. Roadmap & Milestones
- **Purpose:** Where we're going
- **Update:** Weekly
- **Read:** Sprint planning

### 6. Lessons Learned
- **Purpose:** Don't repeat failures
- **Update:** Setiap ada rollback, bug, atau insight
- **Read:** Sebelum membuat keputusan serupa

---

## ANTI-PATTERNS (NEVER DO)

- ❌ **Commit tanpa message yang jelas**
- ❌ **Deploy tanpa test**
- ❌ **Schema change tanpa migration**
- ❌ **Keputusan tanpa dicatat**
- ❌ **Bug fix tanpa dicatat di Known Issues**
- ❌ **Task selesai tanpa update TASK_BOARD.md**
- ❌ **Session selesai tanpa daily log**
- ❌ **Handoff tanpa handoff note**
- ❌ **Rollback tanpa investigation**
- ❌ **Training cycle tanpa eval gate**
- ❌ **Context.md outdated > 24 jam**

---

## TEMPLATE FILES

### Daily Log Template
```markdown
# Daily Log — YYYY-MM-DD — Day N of Phase

## 🎯 INTENT
1. 
2. 
3. 

## ✅ DONE
- 

## 🚧 BLOCKED
- 

## 💡 INSIGHT
- 

## 🔄 DECISIONS
- 

## 📊 METRICS
- 

## 🧪 TESTING
- 

## 📝 DOCS
- 

## ➡️ TOMORROW
1. 
2. 
3. 

## 🛑 WRAP CHECKLIST
- [ ] Daily log written
- [ ] CONTEXT.md updated
- [ ] TASK_BOARD.md updated
- [ ] Committed
- [ ] Pushed
```

### Handoff Note Template
```markdown
## HANDOFF — [From] → [To]
**Date:** 
**Branch:** 
**Commit:** 
**Task:** 

### ✅ Completed
- 

### 🏗️ State
- 

### ➡️ Next
1. 
2. 

### ⚠️ Watch Out
- 

### 🔄 Decisions
- 

### 📝 Context Updated
- 
```

---

*Protocol ini adalah HUKUM. Tidak boleh dilanggar. Jika dilanggar, context loss akan terjadi. Jika context loss terjadi, rollback akan terjadi. Jika rollback terjadi, waktu terbuang. Jangan buang waktu.*
