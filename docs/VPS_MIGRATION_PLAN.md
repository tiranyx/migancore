# VPS MIGRATION PLAN — 2-VPS Architecture
**Dibuat:** 2026-05-08 (Day 67)
**Status:** PENDING — Menunggu user order KVM 4
**Eksekutor:** Agent berikutnya setelah VPS baru siap

---

## KEPUTUSAN FINAL

**Beli KVM 4** ($12.99/mo promo, $28.99/mo renewal, 2 tahun)
- Platform: Hostinger
- Promo: [hpanel.hostinger.com](https://hpanel.hostinger.com)
- Alasan KVM 4 bukan KVM 2: Ollama 7B butuh 4-6GB RAM, KVM 2 (8GB) terlalu tight → swap risk

---

## ARSITEKTUR TARGET

```
┌─────────────────────────────────────────┐
│  VPS LAMA — "MiganCore VPS"             │
│  IP: 72.62.125.6 (Hostinger, existing)  │
│  Spec: 8 vCPU / 32GB RAM               │
│                                         │
│  🧠 MiganCore Stack (TETAP):            │
│     • ado-api-1 (uvicorn FastAPI)       │
│     • ado-ollama-1 (migancore:0.x)      │
│     • ado-qdrant-1 (vector DB)          │
│     • ado-letta-1 (memory)              │
│     • ado-redis-1                       │
│     • ado-postgres-1                    │
│                                         │
│  🌐 Services yang TETAP di sini:        │
│     • Ixonomic (Node.js bank server)    │
│     • MighanWorld (Three.js gateway)    │
│                                         │
│  ✅ Setelah SIDIX pindah: MiganCore     │
│     dapat full resource untuk training  │
└─────────────────────────────────────────┘
                    │ (dipisah)
                    ▼
┌─────────────────────────────────────────┐
│  VPS BARU — "SIDIX VPS"                 │
│  IP: [TBD setelah order]                │
│  Spec: 4 vCPU / 16GB RAM (KVM 4)       │
│  OS: Ubuntu 22.04 LTS                   │
│                                         │
│  🤖 SIDIX Stack (PINDAH ke sini):       │
│     • Ollama (qwen2.5:7b + sidix-lora)  │
│     • SIDIX API/backend                 │
│     • SIDIX frontend (jika ada)         │
│                                         │
│  🌐 Web Apps (PINDAH ke sini):          │
│     • tiranyx.com (landing page)        │
│     • tiranyx.id (landing page)         │
│     • sidixlab.com                      │
│     • Web statis/dinamis lainnya        │
│                                         │
│  💾 Database:                           │
│     • PostgreSQL kecil (SIDIX data)     │
│     • Redis (jika butuh)               │
└─────────────────────────────────────────┘
```

---

## PRE-REQUISITES (User harus selesaikan dulu)

- [ ] **Order KVM 4** dari Hostinger (~$12.99/mo, pilih Ubuntu 22.04)
- [ ] **Catat IP baru** VPS → isi di bawah ini: `IP_VPS_BARU = ___________`
- [ ] **Share SSH access** ke VPS baru (root password atau SSH key)
- [ ] **Konfirmasi** service apa saja yang ada di SIDIX saat ini (path di VPS lama)

---

## MIGRATION STEPS (Untuk Agent Eksekutor)

### FASE 1: Setup VPS Baru (±30 menit)

```bash
# 1. SSH ke VPS baru
ssh root@[IP_VPS_BARU]

# 2. Update OS
apt update && apt upgrade -y

# 3. Install Docker
curl -fsSL https://get.docker.com | sh
systemctl enable docker && systemctl start docker

# 4. Install Docker Compose
apt install docker-compose-plugin -y

# 5. Install tools
apt install -y nginx certbot python3-certbot-nginx git curl jq

# 6. Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh
systemctl enable ollama

# 7. Setup swap (safety net)
fallocate -l 4G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
sysctl vm.swappiness=10
echo 'vm.swappiness=10' >> /etc/sysctl.conf
```

### FASE 2: Pull Model Ollama di VPS Baru

```bash
# Pull base model (ini yang berat, ~4.5GB)
ollama pull qwen2.5:7b-instruct-q4_K_M

# Verifikasi
ollama list
```

**PENTING:** Jika SIDIX punya LoRA adapter sendiri, perlu:
1. Copy adapter dari VPS lama ke VPS baru
2. Buat Modelfile dan register: `ollama create sidix:0.x -f /path/Modelfile_sidix`

### FASE 3: Migrate SIDIX Stack

```bash
# Di VPS LAMA — cari path SIDIX
ssh root@72.62.125.6
find /opt /home -name "sidix*" -type d 2>/dev/null
docker ps | grep -i sidix

# Backup SIDIX data
tar czf /tmp/sidix_backup_$(date +%Y%m%d).tar.gz /path/to/sidix/
# Transfer ke VPS baru
scp /tmp/sidix_backup_*.tar.gz root@[IP_VPS_BARU]:/opt/
```

### FASE 4: Migrate Web Apps

```bash
# Di VPS LAMA — backup web apps
# Tiranyx sites (biasanya di /opt/tiranyx atau /var/www/)
find /opt /var/www -name "tiranyx*" -type d 2>/dev/null

# Tar & scp ke VPS baru
tar czf /tmp/webapps_backup.tar.gz /path/to/webapps/
scp /tmp/webapps_backup.tar.gz root@[IP_VPS_BARU]:/var/www/
```

### FASE 5: Setup Nginx + SSL di VPS Baru

```bash
# Di VPS BARU
# Setup nginx config untuk tiap domain
cat > /etc/nginx/sites-available/tiranyx << 'EOF'
server {
    listen 80;
    server_name tiranyx.com www.tiranyx.com tiranyx.id;
    root /var/www/tiranyx;
    index index.html;
    location / { try_files $uri $uri/ =404; }
}
EOF

ln -s /etc/nginx/sites-available/tiranyx /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# SSL (setelah DNS dipindah)
certbot --nginx -d tiranyx.com -d www.tiranyx.com -d tiranyx.id
```

### FASE 6: Update DNS

**Dilakukan oleh user di Hostinger DNS panel:**
- `tiranyx.com` A record → [IP_VPS_BARU]
- `tiranyx.id` A record → [IP_VPS_BARU]
- `sidixlab.com` A record → [IP_VPS_BARU]
- TTL: set ke 300 (5 menit) sebelum migrasi, kembalikan ke 3600 setelah

### FASE 7: Verifikasi & Cleanup

```bash
# Test dari luar
curl -I https://tiranyx.com
curl -I https://sidixlab.com

# Jika semua OK — hapus SIDIX dari VPS lama
ssh root@72.62.125.6
# Hentikan SIDIX containers/processes
docker stop [sidix containers] 2>/dev/null
# Hapus web app files dari VPS lama (setelah konfirmasi)
# rm -rf /path/to/old/sidix (HATI-HATI)
```

### FASE 8: Resource Cleanup di VPS Lama

```bash
# Setelah SIDIX pindah — optimize VPS lama untuk MiganCore
ssh root@72.62.125.6

# Restart MiganCore stack
cd /opt/ado
docker compose restart

# Verifikasi semua container UP
docker ps

# Cek resource freed up
free -h
top -bn1 | head -5
```

---

## COST ANALYSIS

| Item | Promo | Renewal (2yr) |
|------|-------|---------------|
| VPS Lama (existing) | Sudah berjalan | ~$50.99/mo (KVM 8 equivalent) |
| VPS Baru KVM 4 | $12.99/mo | $28.99/mo |
| **Total baru** | **~$64/mo** | **~$80/mo** |

**Manfaat:** MiganCore training Cycle 6+ tidak lagi bersaing CPU/RAM dengan SIDIX web apps.

---

## CATATAN PENTING UNTUK AGENT EKSEKUTOR

1. **VPS lama JANGAN direstart/dimatikan** — semua MiganCore production ada di sana
2. **Backup dulu** sebelum hapus apa pun dari VPS lama
3. **DNS propagation** butuh 5-60 menit setelah update — tunggu dulu sebelum matiin service lama
4. **Ollama di VPS baru** — set `OLLAMA_NUM_THREADS=4` (sesuai jumlah vCPU)
5. **Jika SIDIX punya DB PostgreSQL** — dump dulu: `pg_dump sidix_db > /tmp/sidix_db.sql`, restore di VPS baru
6. **Hostinger API token** yang dipakai user sudah exposed di chat — minta user buat token baru sebelum eksekusi via Hostinger MCP

---

## TRIGGER UNTUK AGENT EKSEKUTOR

Agent bisa mulai eksekusi Fase 1-2 segera setelah user:
1. Berikan IP VPS baru
2. Konfirmasi SSH access tersedia
3. Konfirmasi path SIDIX di VPS lama

Kata trigger dari user: **"VPS baru siap, IP: xxx.xxx.xxx.xxx"** atau **"GO migrate"**

---

## STATUS TRACKING

| Fase | Status | Catatan |
|------|--------|---------|
| Pre-req: Order KVM 4 | ⏳ User | Menunggu |
| Fase 1: Setup VPS Baru | ⏳ Pending | |
| Fase 2: Pull Ollama model | ⏳ Pending | ~4.5GB download |
| Fase 3: Migrate SIDIX | ⏳ Pending | Perlu konfirmasi path |
| Fase 4: Migrate Web Apps | ⏳ Pending | Perlu konfirmasi domains |
| Fase 5: Nginx + SSL | ⏳ Pending | Setelah DNS |
| Fase 6: Update DNS | ⏳ User | User yang kerjakan di panel |
| Fase 7: Verifikasi | ⏳ Pending | |
| Fase 8: Cleanup VPS Lama | ⏳ Pending | Setelah verify semua OK |
