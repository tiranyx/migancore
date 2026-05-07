#!/bin/bash
# ============================================================
# VPS INVENTORY SCRIPT — Day 67 Migration Audit
# Jalankan di VPS existing: bash vps_inventory.sh 2>&1 | tee /tmp/vps_inventory.txt
# Paste output ke Claude untuk analisis
# ============================================================

SEP="============================================================"

echo "$SEP"
echo "VPS INVENTORY — $(date '+%Y-%m-%d %H:%M:%S')"
echo "Hostname: $(hostname) | IP: $(curl -s ifconfig.me 2>/dev/null)"
echo "$SEP"

echo ""
echo "===== [1] DOCKER CONTAINERS (semua) ====="
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}\t{{.Image}}" 2>/dev/null || echo "Docker not running"

echo ""
echo "===== [2] DOCKER COMPOSE FILES (lokasi & isi) ====="
find /opt /home /root /var -name "docker-compose*.yml" -o -name "compose*.yml" 2>/dev/null | \
while read f; do
    echo ""
    echo "--- FILE: $f ---"
    cat "$f"
done

echo ""
echo "===== [3] PM2 PROCESSES ====="
pm2 list 2>/dev/null || echo "PM2 tidak ditemukan"
pm2 info all 2>/dev/null | grep -E "(name|script|cwd|status|pid)" | head -60

echo ""
echo "===== [4] NGINX — SITES ENABLED ====="
echo "Sites found:"
ls -la /etc/nginx/sites-enabled/ 2>/dev/null || ls -la /etc/nginx/conf.d/ 2>/dev/null || echo "nginx tidak ditemukan"
echo ""
echo "--- Isi setiap config ---"
for f in /etc/nginx/sites-enabled/* /etc/nginx/conf.d/*.conf; do
    [ -f "$f" ] || continue
    echo ""
    echo "=== CONFIG: $f ==="
    cat "$f"
done

echo ""
echo "===== [5] PORTS YANG DIPAKAI ====="
ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null

echo ""
echo "===== [6] DIREKTORI & UKURAN ====="
echo "--- /opt ---"
du -sh /opt/*/ 2>/dev/null | sort -h
echo ""
echo "--- /var/www ---"
du -sh /var/www/*/ 2>/dev/null | sort -h
echo ""
echo "--- /home ---"
du -sh /home/*/ 2>/dev/null | sort -h
echo ""
echo "--- /root (non-hidden, level 1) ---"
du -sh /root/[^.]* 2>/dev/null | sort -h

echo ""
echo "===== [7] CRON JOBS ====="
echo "--- root crontab ---"
crontab -l 2>/dev/null || echo "No crontab for root"
echo ""
echo "--- /etc/cron.d ---"
ls -la /etc/cron.d/ 2>/dev/null
for f in /etc/cron.d/*; do
    [ -f "$f" ] || continue
    echo ""
    echo "=== $f ==="
    cat "$f"
done

echo ""
echo "===== [8] SYSTEMD SERVICES (user-installed) ====="
systemctl list-units --type=service --state=running --no-legend 2>/dev/null | \
grep -vE "(docker|ssh|nginx|cron|rsyslog|systemd|network|dbus|udev|accounts|polkit|apt|snapd|multipathd|irqbalance|lvm)" | \
awk '{print $1, $3, $4}'

echo ""
echo "===== [9] DATABASE CHECK ====="
echo "--- PostgreSQL ---"
psql -U postgres -c "\l" 2>/dev/null || \
docker exec ado-postgres-1 psql -U postgres -c "\l" 2>/dev/null || \
echo "PostgreSQL: tidak bisa query (cek manual)"

echo ""
echo "--- MySQL/MariaDB ---"
mysql -e "SHOW DATABASES;" 2>/dev/null || echo "MySQL/MariaDB: tidak ditemukan"

echo ""
echo "===== [10] DISK USAGE TOTAL ====="
df -h

echo ""
echo "===== [11] ENVIRONMENT FILES (nama saja, bukan isi) ====="
find /opt /home /root /var/www -name ".env" -o -name "*.env" 2>/dev/null | grep -v ".git"

echo ""
echo "===== [12] GIT REPOS DI VPS ====="
find /opt /home /root /var/www -name ".git" -type d 2>/dev/null | sed 's|/.git||' | \
while read repo; do
    echo ""
    echo "--- REPO: $repo ---"
    git -C "$repo" remote -v 2>/dev/null
    git -C "$repo" log --oneline -3 2>/dev/null
done

echo ""
echo "===== [13] TIRANYX / SIDIX SPECIFIC ====="
echo "--- Cari semua 'tiranyx' ---"
find /opt /home /root /var -iname "*tiranyx*" -type d 2>/dev/null
echo ""
echo "--- Cari semua 'sidix' ---"
find /opt /home /root /var -iname "*sidix*" -type d 2>/dev/null
echo ""
echo "--- Cari semua 'mighan' (non-ado) ---"
find /opt /home /root /var -iname "*mighan*" -type d 2>/dev/null | grep -v "/opt/ado"

echo ""
echo "$SEP"
echo "INVENTORY SELESAI — $(date '+%Y-%m-%d %H:%M:%S')"
echo "Output tersimpan di: /tmp/vps_inventory.txt"
echo "$SEP"
