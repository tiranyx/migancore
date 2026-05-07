# MiganCore — User Guide
**Versi:** Day 69 · **Update:** 2026-05-08 · **Public-safe (secrets removed)**

> **Day 69 SECURITY FIX (Codex P1):** ADMIN_SECRET_KEY rotated. Old key (Day 22 → Day 68) was committed in repo history and is now PERMANENTLY EXPOSED. The new key is stored ONLY in:
> - `/opt/ado/.env` on production VPS (mode 600, gitignored)
> - `/root/.migancore_admin_key` (mode 600 fallback)
> - **Owner's password manager** (Fahmi must store immediately)
>
> **Never** put admin keys, SSH paths, or VPS credentials in `docs/`. Use a separate private vault (1Password, Bitwarden, Notion private).
>
> **Day 68 product changes:** Conversation history E2E (UI fetches `/v1/conversations`, not localStorage), mobile drawer nav (hamburger ☰), feedback buttons per message (👍/👎), build metadata di `/health`.

---

## 🔑 QUICK REFERENCE (public-safe)

| Item | Value |
|------|-------|
| **Chat App** | https://app.migancore.com |
| **API Base URL** | https://api.migancore.com |
| **API Docs** | https://api.migancore.com/docs |
| **GitHub Repo** | https://github.com/tiranyx/migancore |
| **Admin API Key** | _stored in private vault — see Section "Admin Access"_ |
| **SSH credentials** | _stored in private vault_ |

---

## 📱 CARA PAKAI CHAT APP

### Step 1 — Buka app
Buka browser → https://app.migancore.com

Kamu akan lihat boot sequence (animasi startup), setelah itu muncul layar login.

### Step 2 — Buat akun (pertama kali)
1. Klik tab **REGISTER**
2. Isi form:
   - **Display Name:** Nama kamu (opsional) — misal: `Fahmi Wol`
   - **Email:** Email kamu — misal: `tiranyx.id@gmail.com`
   - **Password:** Minimal 8 karakter
   - **Nama Workspace:** Nama organisasi/tim — misal: `ADO Labs`
   - **Workspace ID:** Auto-generate dari nama workspace. Format: huruf kecil + tanda hubung. Misal: `ado-labs`
3. Klik **BUAT AKUN**

Kalau berhasil, langsung masuk ke chat interface.

### Step 3 — Login (kunjungan berikutnya)
Tab **LOGIN** → isi email + password → **LOGIN**

Token disimpan di browser localStorage. Kamu tidak perlu login ulang kecuali logout manual atau hapus data browser.

### Step 4 — Chat dengan MiganCore
1. Agent "MiganCore" otomatis dibuat saat pertama kali login
2. Ketik pesan di kolom bawah
3. **Enter** = kirim · **Shift+Enter** = baris baru
4. Respon streaming real-time (muncul per kata/token)
5. Klik tombol ■ (stop) untuk hentikan streaming di tengah jalan

### Tips:
- Klik hint chip di halaman kosong untuk coba prompt contoh
- **+ NEW CHAT** di sidebar untuk mulai percakapan baru
- Riwayat chat disimpan di **server** (Day 68 fix): klik item di sidebar RIWAYAT CHAT untuk lanjut percakapan lama, atau klik tombol × untuk hapus (soft archive)
- Sidebar di mobile: tap ikon ☰ di header untuk buka drawer (history, NEW CHAT, agents, logout)
- Klik 👍 atau 👎 setelah jawaban Migan — itu jadi training data untuk improvement berikutnya

---

## 🔧 API LANGSUNG — Untuk Developer

Base URL: `https://api.migancore.com`

### Autentikasi

**Register (buat akun baru):**
```bash
curl -X POST https://api.migancore.com/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "kamu@example.com",
    "password": "password123",
    "display_name": "Nama Kamu",
    "tenant_name": "Workspace Kamu",
    "tenant_slug": "workspace-kamu"
  }'
```

**Login:**
```bash
curl -X POST https://api.migancore.com/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "kamu@example.com", "password": "password123"}'
```

Response: `{ "access_token": "...", "refresh_token": "...", "expires_in": 1800 }`

Simpan `access_token` untuk request berikutnya.

**Cek user info:**
```bash
curl https://api.migancore.com/v1/auth/me \
  -H "Authorization: Bearer ACCESS_TOKEN"
```

### Agents

**Buat agent:**
```bash
curl -X POST https://api.migancore.com/v1/agents \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "MiganCore", "visibility": "private"}'
```

Response berisi `"id"` — simpan sebagai `AGENT_ID`.

**Chat (sync):**
```bash
curl -X POST https://api.migancore.com/v1/agents/AGENT_ID/chat \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Halo, siapa kamu?", "conversation_id": null}'
```

**Chat (streaming SSE):**
```bash
curl -X POST https://api.migancore.com/v1/agents/AGENT_ID/chat/stream \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -N \
  -d '{"message": "Ceritakan tentang dirimu", "conversation_id": null}'
```

SSE event format:
```
data: {"type": "start", "conversation_id": "uuid"}
data: {"type": "chunk", "content": "Halo"}
data: {"type": "chunk", "content": " saya"}
data: {"type": "done", "conversation_id": "uuid"}
```

---

## 👑 ADMIN — Monitoring & Control

Semua endpoint admin butuh header `X-Admin-Key: <ADMIN_KEY>` — value tidak ada di repo, simpan di private vault. Untuk perintah di bawah, set env var dulu: `export ADMIN_KEY=$(cat /root/.migancore_admin_key)` (di VPS) atau paste manual dari password manager.

### Cek status sistem
```bash
curl https://api.migancore.com/v1/admin/stats \
  -H "X-Admin-Key: $ADMIN_KEY"   # set ADMIN_KEY=... from your private vault
```

Response berisi: total users, agents, conversations, preference pairs, dll.

### Cek synthetic DPO generation
```bash
curl https://api.migancore.com/v1/admin/synthetic/status \
  -H "X-Admin-Key: $ADMIN_KEY"   # set ADMIN_KEY=... from your private vault
```

Response penting:
- `is_running` — apakah sedang berjalan
- `round` — round ke berapa sekarang
- `cumulative_stored` — total pairs disimpan sesi ini
- `target_pairs` — target total
- `status` — `running` / `done_target_reached` / `error`

### Mulai auto-rerun synthetic (target 1000 pairs)
```bash
curl -X POST https://api.migancore.com/v1/admin/synthetic/start \
  -H "X-Admin-Key: $ADMIN_KEY"   # set ADMIN_KEY=... from your private vault \
  -H "Content-Type: application/json" \
  -d '{"target_pairs": 1000}'
```

### Cek health semua services
```bash
curl https://api.migancore.com/health
```

Response: status Postgres, Redis, Qdrant, Ollama.

### API Docs interaktif
Buka di browser: https://api.migancore.com/docs

---

## 🖥️ AKSES VPS

### SSH
SSH credentials (key path + IP) disimpan di private vault. Format generik:
```bash
ssh -i <path-to-private-key> root@<vps-ip>
```
Untuk owner: lihat password manager entry "MiganCore VPS Production".

### Lihat logs API
```bash
# Di VPS:
cd /opt/ado
docker compose logs -f api --tail=100
```

### Restart API
```bash
cd /opt/ado
docker compose restart api
```

### Cek containers
```bash
cd /opt/ado
docker compose ps
```

### Pull update terbaru + restart
```bash
cd /opt/ado
git pull
docker compose restart api
```

---

## 📁 STRUKTUR REPO

```
migancore/
├── api/                    # FastAPI backend
│   ├── routers/           # Endpoints (auth, agents, chat, admin)
│   ├── services/          # Business logic
│   │   ├── synthetic_pipeline.py  # DPO data generation
│   │   ├── vector_memory.py       # Hybrid search (BM42)
│   │   └── ...
│   ├── models/            # SQLAlchemy models
│   └── main.py            # Entry point (v0.4.1)
├── frontend/
│   └── chat.html          # ← Chat UI (ini file yang kamu pakai)
└── docs/
    ├── CONTEXT.md         # State project saat ini
    ├── CHANGELOG.md       # History semua versi
    └── USER_GUIDE.md      # ← File ini
```

---

## 🗺️ WEEK 3 ROADMAP (Day 22–28)

| Day | Task | Status |
|-----|------|--------|
| 22–23 | Chat UI (ini!) | ✅ Done |
| 24 | Tool expansion: image gen (fal.ai) + file system | Pending |
| 25 | Admin Dashboard frontend | Pending |
| 26–27 | MCP Server (Streamable HTTP) | Pending |
| 28 | TTS (ElevenLabs) + Handoff docs | Pending |

### API yang perlu disiapkan:
- [ ] **fal.ai** — daftar di https://fal.ai, buat API key, kirim ke Claude
- [ ] **ElevenLabs** — daftar di https://elevenlabs.io (free tier cukup)
- [ ] **Firecrawl** — daftar di https://firecrawl.dev (free tier)

---

## 📊 STATUS SAAT INI (Day 22, 2026-05-03)

- **API Version:** v0.4.1
- **Auto-rerun synthetic:** Berjalan otomatis, target 1000 DPO pairs
- **Estimated selesai:** ~30-70 jam dari Day 21
- **Models:** qwen2.5:7b-instruct-q4_K_M (via Ollama)
- **Vector DB:** Qdrant hybrid search (dense + BM42 sparse)

### Cek progress cepat:
```bash
curl https://api.migancore.com/v1/admin/synthetic/status \
  -H "X-Admin-Key: $ADMIN_KEY"   # set ADMIN_KEY=... from your private vault | python -m json.tool
```

---

## ❓ TROUBLESHOOTING

| Problem | Solution |
|---------|----------|
| App tidak bisa dibuka | Cek DNS — A record `app.migancore.com` harus pointing ke production VPS IP (lihat private vault) |
| Login gagal | Cek email/password. Error "Email already registered" = email sudah ada, coba login |
| Chat tidak streaming | Cek koneksi internet. Coba refresh halaman |
| "Agent not found" | Logout → login ulang (agent_id di localStorage mungkin stale) |
| API down | SSH ke VPS → `docker compose ps` → lihat status containers |

---

*Dokumen ini private untuk Fahmi Wol. Jangan share admin key.*
