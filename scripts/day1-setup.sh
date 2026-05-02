#!/bin/bash
# ============================================================
# MIGANCORE — Day 1 VPS Provisioning Script
# Run as root on VPS 72.62.125.6
# ============================================================
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; exit 1; }

echo "=========================================="
echo "  MIGANCORE — Day 1 VPS Provisioning"
echo "  IP: 72.62.125.6"
echo "  Domain: migancore.com"
echo "=========================================="

# --- Step 1: System Update ---
echo ""
echo "[1/8] Updating system..."
apt-get update -qq && apt-get upgrade -y -qq
log "System updated"

# --- Step 2: Install Essentials ---
echo ""
echo "[2/8] Installing essentials..."
apt-get install -y -qq curl wget git ufw fail2ban htop nano unzip
log "Essentials installed"

# --- Step 3: UFW Firewall ---
echo ""
echo "[3/8] Configuring UFW firewall..."
ufw default deny incoming >/dev/null 2>&1
ufw default allow outgoing >/dev/null 2>&1
ufw allow 22/tcp >/dev/null 2>&1
ufw allow 80/tcp >/dev/null 2>&1
ufw allow 443/tcp >/dev/null 2>&1
ufw allow 443/udp >/dev/null 2>&1
ufw --force enable >/dev/null 2>&1
log "UFW configured (22, 80, 443 allowed)"

# --- Step 4: Fail2ban ---
echo ""
echo "[4/8] Enabling fail2ban..."
systemctl enable fail2ban >/dev/null 2>&1
systemctl start fail2ban >/dev/null 2>&1
log "Fail2ban active"

# --- Step 5: Swap 8GB ---
echo ""
echo "[5/8] Creating 8GB swap file..."
if [ ! -f /swapfile ]; then
    fallocate -l 8G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile >/dev/null 2>&1
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    log "Swap 8GB created and mounted"
else
    warn "Swap file already exists, skipping"
fi

# --- Step 6: Docker + Compose ---
echo ""
echo "[6/8] Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh >/dev/null 2>&1
    systemctl enable docker >/dev/null 2>&1
    systemctl start docker >/dev/null 2>&1
    log "Docker installed"
else
    warn "Docker already installed, skipping"
fi

DOCKER_COMPOSE_VERSION=$(docker compose version 2>/dev/null || echo "not found")
log "Docker Compose: $DOCKER_COMPOSE_VERSION"

# --- Step 7: Clone Repo ---
echo ""
echo "[7/8] Cloning migancore repo..."
mkdir -p /opt/ado
cd /opt/ado
if [ ! -d ".git" ]; then
    git clone https://github.com/tiranyx/migancore.git . >/dev/null 2>&1
    log "Repo cloned to /opt/ado/"
else
    warn "Repo already exists, pulling latest..."
    git pull origin main >/dev/null 2>&1
fi

# --- Step 8: JWT Keys ---
echo ""
echo "[8/8] Generating JWT RS256 keypair..."
mkdir -p /etc/ado/keys
chmod 700 /etc/ado/keys

if [ ! -f /etc/ado/keys/private.pem ]; then
    openssl genrsa -out /etc/ado/keys/private.pem 2048 >/dev/null 2>&1
    openssl rsa -in /etc/ado/keys/private.pem -pubout -out /etc/ado/keys/public.pem >/dev/null 2>&1
    chmod 600 /etc/ado/keys/*
    log "JWT keypair generated at /etc/ado/keys/"
else
    warn "JWT keys already exist, skipping"
fi

# --- Verification ---
echo ""
echo "=========================================="
echo "           VERIFICATION"
echo "=========================================="

PASS=0
FAIL=0

check() {
    if eval "$2" >/dev/null 2>&1; then
        echo -e "${GREEN}[PASS]${NC} $1"
        ((PASS++))
    else
        echo -e "${RED}[FAIL]${NC} $1"
        ((FAIL++))
    fi
}

check "SSH port open" "ss -tlnp | grep -q ':22'"
check "Docker running" "docker info"
check "Docker Compose available" "docker compose version"
check "Swap active" "swapon --show | grep -q '/swapfile'"
check "UFW active" "ufw status | grep -q 'Status: active'"
check "Fail2ban running" "systemctl is-active --quiet fail2ban"
check "Repo cloned" "test -d /opt/ado/.git"
check "JWT private key" "test -f /etc/ado/keys/private.pem"
check "JWT public key" "test -f /etc/ado/keys/public.pem"

echo ""
echo "=========================================="
echo "  Results: $PASS passed, $FAIL failed"
echo "=========================================="

if [ $FAIL -gt 0 ]; then
    error "Some checks failed. Please review."
fi

echo ""
echo "Next steps:"
echo "  1. cd /opt/ado && cp .env.example .env"
echo "  2. nano .env  (fill in all passwords)"
echo "  3. docker compose up -d  (do this AFTER DNS propagates)"
echo "  4. ollama pull qwen2.5:7b-instruct-q4_K_M"
echo ""
log "Day 1 provisioning complete!"
