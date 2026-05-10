# MIGANCORE — Backup & Recovery Procedures
**Version:** 1.0 | **Date:** 2026-05-10

---

## 📦 BACKUP INVENTORY

### What Gets Backed Up
| Component | Frequency | Retention | Location |
|-----------|-----------|-----------|----------|
| Model artifacts | Daily 03:00 UTC | 7 days local, 30 days remote | Hetzner Storage Box |
| DB snapshot (data-only) | Daily 03:00 UTC | 7 days local, 30 days remote | Hetzner Storage Box |

### Model Artifacts Included
- `identity_adapter_v0.4/` — LoRA adapter (323MB)
- `migancore_0.4_q4_k_m.gguf` — Production GGUF (4.4GB)
- `migancore_0.4_f16.gguf` — Full precision GGUF (15GB)
- `adapter_pkg.tar.gz` — Packaged adapter
- `Modelfile*` — Ollama model definitions

### DB Snapshot Included
- `users`, `agents`, `conversations`, `messages`, `preference_pairs`
- Data-only (schema managed by Alembic)

---

## 🔄 BACKUP AUTOMATION

### Cron Schedule
```
0 3 * * * /opt/ado/scripts/backup_models.sh >> /opt/ado/logs/backup_cron.log 2>&1
```

### Manual Trigger
```bash
cd /opt/ado
/opt/ado/scripts/backup_models.sh
```

### Verify Last Backup
```bash
# Local
cd /opt/ado/backup && ls -lt *.tar.gz *.sql.gz | head -5

# Remote (Hetzner Storage Box)
rclone ls migan-backup:models | sort -k2
```

---

## 🚨 DISASTER RECOVERY

### Scenario 1: Model Corruption / Accidental Deletion

```bash
# 1. Stop API to prevent inference on bad model
cd /opt/ado && docker compose stop api

# 2. List available backups on remote
rclone ls migan-backup:models

# 3. Download specific backup
REMOTE_ARCHIVE="migancore_models_20260510_081658.tar.gz"
rclone copy migan-backup:models/$REMOTE_ARCHIVE /opt/ado/backup/

# 4. Extract to models directory
cd /opt/ado/models
tar -xzf /opt/ado/backup/$REMOTE_ARCHIVE

# 5. Restart API
cd /opt/ado && docker compose up -d api

# 6. Verify model loads
curl -s http://localhost:18000/health | jq .model
```

### Scenario 2: Database Corruption / Data Loss

```bash
# 1. Stop API
cd /opt/ado && docker compose stop api

# 2. Download DB snapshot
REMOTE_DB="db_snapshot_20260510_081658.sql.gz"
rclone copy migan-backup:models/$REMOTE_DB /opt/ado/backup/

# 3. Drop and recreate database (CAUTION: destructive)
docker compose exec postgres psql -U ado -c "DROP DATABASE ado;"
docker compose exec postgres psql -U ado -c "CREATE DATABASE ado;"

# 4. Apply Alembic schema
cd /opt/ado/api
docker compose exec api alembic upgrade head

# 5. Restore data
gunzip -c /opt/ado/backup/$REMOTE_DB | docker compose exec -T postgres psql -U ado -d ado

# 6. Restart API
cd /opt/ado && docker compose up -d api

# 7. Verify
curl -s http://localhost:18000/health | jq .status
```

### Scenario 3: Complete VPS Rebuild

```bash
# 1. Provision new VPS, install Docker, clone repo
git clone https://github.com/tiranyx/migancore.git /opt/ado
cd /opt/ado

# 2. Restore .env from secure backup (keepass/vault)
cp /secure/location/.env /opt/ado/.env

# 3. Download latest backup
rclone copy migan-backup:models/migancore_models_20260510_081658.tar.gz /opt/ado/backup/
rclone copy migan-backup:models/db_snapshot_20260510_081658.sql.gz /opt/ado/backup/

# 4. Extract models
cd /opt/ado/models && tar -xzf /opt/ado/backup/migancore_models_*.tar.gz

# 5. Start infrastructure
cd /opt/ado && docker compose up -d postgres redis qdrant ollama

# 6. Apply schema and restore data
docker compose exec api alembic upgrade head
gunzip -c /opt/ado/backup/db_snapshot_*.sql.gz | docker compose exec -T postgres psql -U ado -d ado

# 7. Start API
docker compose up -d api

# 8. Verify
curl -s http://localhost:18000/health
```

---

## 📋 BACKUP VERIFICATION CHECKLIST

- [ ] `rclone ls migan-backup:models` shows expected files
- [ ] Local archive size ≈ remote archive size (±1%)
- [ ] DB snapshot < 10MB (data-only, compressed)
- [ ] Can download and extract a backup successfully
- [ ] Can restore DB snapshot to test database

---

## 🔧 STORAGE BOX CONFIGURATION

**Provider:** Hetzner Storage Box BX11 (500GB)  
**Location:** Falkenstein, Germany  
**Protocol:** SFTP (port 23)  
**Remote name:** `migan-backup` (rclone)  

### rclone Config
```ini
[migan-backup]
type = sftp
host = u591338.your-storagebox.de
user = u591338
port = 23
key_file = /root/.ssh/id_rsa_hetzner_storage
```

### Test Connection
```bash
rclone ls migan-backup:models
```

---

## 📞 ESCALATION

| Issue | Contact | SLA |
|-------|---------|-----|
| Storage Box unreachable | Hetzner Support | 24h |
| Backup script failure | Check logs + cron | Self-service |
| Data corruption | Immediate restore from remote | 2h RTO |

---

*Document updated: 2026-05-10 (Day 72c)*
