# CLAUDE REVIEW CHECKLIST — Pre-Deploy Gate
**Role:** Kimi (QA/Conflict Watcher)
**Date:** 2026-05-06
**Rule:** Claude TIDAK BOLEH deploy tanpa checklist ini di-review oleh user ATAU Kimi.

---

## 🔴 PRE-DEPLOY MANDATORY CHECKS

### 1. Git Status Audit
Claude WAJIB menunjukkan:
```bash
git status --short
git diff --stat HEAD
git log --oneline -5
```
**Kriteria PASS:**
- [ ] Working tree bersih ATAU hanya file yang RELEVAN dengan task
- [ ] Tidak ada file yang di-edit di luar scope task
- [ ] Tidak ada secret/API key yang tertinggal di diff

### 2. Diff Review
Claude WAJIB menunjukkan diff lengkap:
```bash
git diff HEAD
```
**Kriteria PASS:**
- [ ] Semua perubahan bisa dijelaskan dalam 1 kalimat per file
- [ ] Tidak ada "magic numbers" tanpa komentar
- [ ] Tidak ada hardcoded IPs atau credentials
- [ ] Tidak ada commented-out code > 5 lines (hapus, jangan comment)

### 3. Scope Boundary Check
**Kriteria PASS:**
- [ ] Tidak ada perubahan di `frontend/chat.html` (LOCKED — Kimi's domain)
- [ ] Tidak ada perubahan di `docs/LOCKED_ITEMS_DAY55.md` (LOCKED)
- [ ] Tidak ada penghapusan tool tanpa pengganti
- [ ] Tidak ada perubahan arsitektur tanpa diskusi

### 4. Testing Evidence
Claude WAJIB menunjukkan:
```bash
# Unit test (jika ada)
pytest tests/ -v -k [relevant_test]

# Integration test
python -c "from api.services.tool_executor import TOOL_REGISTRY; print(len(TOOL_REGISTRY))"

# Health check
curl -s http://localhost:18000/v1/health | jq .
```
**Kriteria PASS:**
- [ ] API health endpoint return 200
- [ ] Tidak ada import error di Python
- [ ] Tool registry count sesuai expected (jangan ada yang hilang)

### 5. Deploy Command Transparency
Claude WAJIB menulis EXACT command yang akan dijalankan:
```bash
# CONTOH — Claude harus isi dengan command aktual:
cd /opt/ado && docker compose build --no-cache api
# ATAU
cd /opt/ado && docker compose up -d --build api
# ATAU
cd /opt/ado && git pull origin main && docker compose restart api
```
**Kriteria PASS:**
- [ ] Command bisa di-copy-paste dan di-review
- [ ] Tidak ada `rm -rf` tanpa backup confirmation
- [ ] Tidak ada `docker system prune` (bisa hapus cache Ollama)

### 6. Rollback Plan
Claude WAJIB menulis rollback plan:
```bash
# CONTOH — Claude harus isi dengan command aktual:
# Rollback: restore previous image
# cd /opt/ado && docker compose down && docker compose up -d --build api
# OR: git reset --hard HEAD~1 && docker compose restart api
```
**Kriteria PASS:**
- [ ] Rollback bisa di-execute dalam < 2 menit
- [ ] Database tidak akan corrupt saat rollback
- [ ] Ollama model tidak akan terhapus saat rollback

### 7. Cost Check
**Kriteria PASS:**
- [ ] RunPod/Vast.ai cost di-estimasi sebelum trigger
- [ ] Budget remaining > $10 untuk buffer
- [ ] Tidak ada auto-scaling yang bisa nge-bill tanpa batas

---

## 🟡 POST-DEPLOY VERIFICATION

Setelah deploy, Claude WAJIB verifikasi:

```bash
# 1. Container health
docker compose ps

# 2. API health (dari VPS)
curl -s http://localhost:18000/v1/health

# 3. API health (dari internet)
curl -s https://api.migancore.com/v1/health

# 4. Log check (no errors)
docker logs --tail 30 [api_container_name] 2>&1 | grep -i error | head -5

# 5. Wikipedia tool test
curl -X POST https://api.migancore.com/v1/agents/[agent_id]/chat \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message":"Cari di Wikipedia tentang Soekarno"}' | jq '.response'

# 6. Frontend link test (manual)
# Buka app.migancore.com → chat → ketik Wikipedia query → klik link → verify opens in new tab
```

**Kriteria PASS:**
- [ ] Semua 6 checks PASS
- [ ] Tidak ada error 500/502/503
- [ ] Response time < 10s untuk tool calling

---

## 🟢 HANDOFF CHECKLIST

Jika Claude selesai dan Kimi akan melanjutkan:

- [ ] Claude commit semua perubahan dengan pesan jelas
- [ ] Claude push ke origin/main
- [ ] Claude update `docs/HANDOFF_CLAUDE_TO_KIMI.md` dengan:
  - Apa yang dikerjakan
  - State yang ditinggalkan
  - Next steps
  - Gotchas/warnings
- [ ] Kimi review commit diff sebelum lanjut

---

## ❌ RED FLAGS — STOP DEPLOY

Jika SALAH SATU dari ini terjadi → STOP, jangan deploy:

1. `git status` menunjukkan file di-edit di luar scope task
2. Diff mengandung API key, password, atau secret
3. Test gagal atau health check tidak return 200
4. Rollback plan tidak jelas atau > 5 menit
5. Tidak ada backup database sebelum migration
6. Claude tidak bisa menjelaskan perubahan dalam bahasa sederhana
7. Perubahan di file yang LOCKED (chat.html, LOCKED_ITEMS, dll)

---

## ✅ SIGN-OFF

**Claude Declaration:**
> Saya telah membaca dan memenuhi semua checks di atas. Saya yakin deploy ini aman.

**Kimi Review:**
> Saya telah review diff dan checklist. DEPLOY APPROVED / DEPLOY BLOCKED — [alasan]

**User Final Authority:**
> GO / NO-GO

---

*This checklist is MANDATORY. No exceptions.*
