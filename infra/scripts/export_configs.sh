#!/bin/bash
# ============================================================
# EXPORT CONFIGS TO REPO — Day 67 Migration
# Jalankan SETELAH inventory dianalisis Claude
# Salin semua config ke /opt/ado/infra/ lalu git push
#
# Usage: bash export_configs.sh [OUTPUT_DIR]
# Default OUTPUT_DIR: /opt/ado/infra
# ============================================================

OUTPUT_DIR="${1:-/opt/ado/infra}"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')

echo "=== EXPORT CONFIGS → $OUTPUT_DIR ==="
mkdir -p "$OUTPUT_DIR/nginx"
mkdir -p "$OUTPUT_DIR/docker"
mkdir -p "$OUTPUT_DIR/systemd"
mkdir -p "$OUTPUT_DIR/cron"
mkdir -p "$OUTPUT_DIR/env_templates"

# ── Nginx configs ──────────────────────────────────────────
echo "[1/6] Nginx configs..."
cp -r /etc/nginx/sites-enabled/* "$OUTPUT_DIR/nginx/" 2>/dev/null
cp -r /etc/nginx/conf.d/*.conf "$OUTPUT_DIR/nginx/" 2>/dev/null
cp /etc/nginx/nginx.conf "$OUTPUT_DIR/nginx/nginx.conf" 2>/dev/null
echo "     Done: $(ls $OUTPUT_DIR/nginx/ | wc -l) files"

# ── Docker compose files ───────────────────────────────────
echo "[2/6] Docker compose files..."
find /opt /home /root -name "docker-compose*.yml" -o -name "compose*.yml" 2>/dev/null | \
while read f; do
    # Create subdirectory mirroring path
    REL=$(echo "$f" | sed 's|/|_|g' | sed 's|^_||')
    cp "$f" "$OUTPUT_DIR/docker/${REL}"
    echo "     Copied: $f"
done

# ── Systemd unit files (user-created) ─────────────────────
echo "[3/6] Systemd units..."
for f in /etc/systemd/system/*.service; do
    [ -f "$f" ] || continue
    # Skip standard system services
    name=$(basename "$f")
    echo "     Copying: $name"
    cp "$f" "$OUTPUT_DIR/systemd/$name"
done

# ── Cron jobs ──────────────────────────────────────────────
echo "[4/6] Cron jobs..."
crontab -l 2>/dev/null > "$OUTPUT_DIR/cron/root_crontab.txt"
cp -r /etc/cron.d/* "$OUTPUT_DIR/cron/" 2>/dev/null
echo "     Done"

# ── ENV templates (redacted secrets) ─────────────────────
echo "[5/6] ENV templates (secrets DIREDACT)..."
find /opt /home /root /var/www -name ".env" -o -name "*.env" 2>/dev/null | \
grep -v ".git" | \
while read envfile; do
    REL=$(echo "$envfile" | sed 's|/|_|g' | sed 's|^_||')
    # Redact secrets: replace values with PLACEHOLDER
    sed 's/\(.*=\).*/\1REDACTED/' "$envfile" > "$OUTPUT_DIR/env_templates/${REL}.template"
    echo "     Template: $envfile → (secrets redacted)"
done

# ── Readme dengan catatan ──────────────────────────────────
echo "[6/6] Membuat README..."
cat > "$OUTPUT_DIR/README.md" << EOF
# VPS Existing — Config Export
**Exported:** $TIMESTAMP
**VPS:** $(hostname) / $(curl -s ifconfig.me 2>/dev/null)

## Struktur
- \`nginx/\` — semua nginx virtual host configs
- \`docker/\` — semua docker-compose files
- \`systemd/\` — unit files custom
- \`cron/\` — crontab dan cron.d entries
- \`env_templates/\` — template .env (secrets sudah di-REDACT, isi manual)

## Catatan untuk VPS Baru
1. Restore nginx: \`cp nginx/* /etc/nginx/sites-enabled/\` → \`nginx -t && reload\`
2. Restore compose: letakkan di path yang sesuai, isi \`.env\` dari template
3. Secrets TIDAK tersimpan di repo — isi manual dari password manager
EOF

echo ""
echo "=== EXPORT SELESAI → $OUTPUT_DIR ==="
ls -la "$OUTPUT_DIR/"

echo ""
echo "=== GIT ADD & PUSH ==="
cd /opt/ado
git add infra/ 2>/dev/null || echo "bukan git repo, skip"
git status 2>/dev/null | head -20
