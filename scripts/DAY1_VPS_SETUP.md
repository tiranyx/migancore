# Day 1 — VPS Provisioning Checklist
**Target:** Dari VPS kosong → Docker jalan, swap 8GB, JWT keys generated
**VPS IP:** `72.62.125.6`
**Domain:** `migancore.com`

---

## Pre-Flight: Tambah DNS Record (di Hostinger)

Sebelum mulai, tambah satu record lagi di Hostinger DNS:

| Tipe | Nama | Konten | TTL |
|---|---|---|---|
| A | `studio` | `72.62.125.6` | 14400 |

Ini untuk training studio / MLflow nanti.

---

## Step 1: SSH ke VPS

```bash
ssh root@72.62.125.6
# atau user yang Anda buat saat setup VPS
```

---

## Step 2: System Update & Hardening

```bash
# Update sistem
apt update && apt upgrade -y

# Install essentials
apt install -y curl wget git ufw fail2ban htop nano unzip

# UFW Firewall — hanya izinkan port yang dibutuhkan
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp      # SSH
ufw allow 80/tcp      # HTTP (Caddy redirect ke HTTPS)
ufw allow 443/tcp     # HTTPS
ufw allow 443/udp     # HTTPS/3 (HTTP/3 via QUIC)
ufw --force enable
ufw status

# Fail2ban — cegah brute force
systemctl enable fail2ban && systemctl start fail2ban
```

---

## Step 3: Swap 8GB (KRITIS untuk 32GB RAM)

```bash
fallocate -l 8G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile

# Persist di /etc/fstab
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# Verifikasi
free -h
swapon --show
```

**Output yang diharapkan:** `Swap: 8.0G`

---

## Step 4: Docker + Docker Compose v2

```bash
# Install Docker
curl -fsSL https://get.docker.com | sh

# Enable Docker
systemctl enable docker && systemctl start docker

# Docker Compose v2 (sudah bundled dengan Docker modern)
docker compose version
# Output: Docker Compose version v2.x.x

# Test Docker
docker run hello-world
```

---

## Step 5: Clone Repo & Setup Environment

```bash
# Buat direktori
mkdir -p /opt/ado && cd /opt/ado

# Clone repo
git clone https://github.com/tiranyx/migancore.git .

# Setup .env
cp .env.example .env
nano .env
# Isi semua password dengan value yang kuat!
```

**Isi `.env` (minimal):**
```
PG_PASSWORD=YOUR_STRONG_PASSWORD_HERE
REDIS_PASSWORD=YOUR_STRONG_PASSWORD_HERE
QDRANT_API_KEY=YOUR_STRONG_PASSWORD_HERE
LETTA_PASSWORD=YOUR_STRONG_PASSWORD_HERE
LANGFUSE_SECRET=RANDOM_STRING_32CHAR
LANGFUSE_SALT=RANDOM_STRING_32CHAR
SECRET_KEY=RANDOM_STRING_32CHAR
```

---

## Step 6: Generate JWT RS256 Keypair

```bash
mkdir -p /etc/ado/keys
chmod 700 /etc/ado/keys

openssl genrsa -out /etc/ado/keys/private.pem 2048
openssl rsa -in /etc/ado/keys/private.pem -pubout -out /etc/ado/keys/public.pem

chmod 600 /etc/ado/keys/*
ls -la /etc/ado/keys/
```

**Output yang diharapkan:**
```
-rw------- 1 root root 1679 ... private.pem
-rw------- 1 root root  451 ... public.pem
```

---

## Step 7: Day 1 Done Criteria Check

```bash
# Cek semua
ssh root@72.62.125.6 "echo '=== SSH OK ==='"
docker --version
docker compose version
free -h | grep Swap
ls -la /etc/ado/keys/
ufw status | grep -E '(22|80|443)'
```

**Semua harus PASS:**
- [ ] SSH works
- [ ] Docker hello-world runs
- [ ] Swap 8GB active
- [ ] UFW configured (22, 80, 443 allowed)
- [ ] JWT keys exist di `/etc/ado/keys/`
- [ ] Repo cloned di `/opt/ado/`

---

## Day 2 Preview

```bash
# Pull Ollama model
ollama pull qwen2.5:7b-instruct-q4_K_M

# Benchmark
# time curl -X POST http://localhost:11434/api/generate \
#   -d '{"model":"qwen2.5:7b-instruct-q4_K_M","prompt":"Hello","stream":false}'
```

---

> **Catatan:** Jangan jalankan `docker compose up -d` di Day 1. Itu Day 2 setelah DNS propagate (bisa butuh 1–24 jam).
