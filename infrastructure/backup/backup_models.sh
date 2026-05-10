#!/bin/bash
set -euo pipefail

BACKUP_DIR=/opt/ado/backup
REMOTE=migan-backup
REMOTE_PATH=migan-backup:models
TIMESTAMP=$(date -u +%Y%m%d_%H%M%S)
ARCHIVE=${BACKUP_DIR}/migancore_models_${TIMESTAMP}.tar.gz

mkdir -p $BACKUP_DIR

echo [$(date -u +%Y-%m-%dT%H:%M:%SZ)] Backup starting...

cd /opt/ado/models || exit 1

COMPRESSOR=gzip
if command -v pigz >/dev/null 2>&1; then COMPRESSOR=pigz; fi

tar -cf - \
    identity_adapter_v0.4/ \
    migancore_0.4_q4_k_m.gguf \
    migancore_0.4_f16.gguf \
    adapter_pkg.tar.gz \
    Modelfile* \
  | $COMPRESSOR > $ARCHIVE

ARCHIVE_SIZE=$(du -sh $ARCHIVE | cut -f1)
echo [$(date -u +%Y-%m-%dT%H:%M:%SZ)] Archive created: $ARCHIVE ($ARCHIVE_SIZE)

find $BACKUP_DIR -name migancore_models_*.tar.gz -mtime +7 -delete 2>/dev/null || true
echo [$(date -u +%Y-%m-%dT%H:%M:%SZ)] Local retention: kept last 7 days

if rclone listremotes 2>/dev/null | grep -q ^${REMOTE}: ; then
    echo [$(date -u +%Y-%m-%dT%H:%M:%SZ)] Uploading to $REMOTE_PATH ...
    rclone copy $ARCHIVE $REMOTE_PATH/
    echo [$(date -u +%Y-%m-%dT%H:%M:%SZ)] Upload complete.
else
    echo [$(date -u +%Y-%m-%dT%H:%M:%SZ)] WARNING: rclone remote not configured. Local only.
fi

cd /opt/ado || exit 1
docker compose exec -T postgres pg_dump -U ado -d ado \
    --data-only \
    --table=users --table=agents --table=conversations --table=messages --table=preference_pairs \
  | gzip > ${BACKUP_DIR}/db_snapshot_${TIMESTAMP}.sql.gz

DB_SIZE=$(du -sh ${BACKUP_DIR}/db_snapshot_${TIMESTAMP}.sql.gz | cut -f1)
echo [$(date -u +%Y-%m-%dT%H:%M:%SZ)] DB snapshot: ${BACKUP_DIR}/db_snapshot_${TIMESTAMP}.sql.gz ($DB_SIZE)

echo [$(date -u +%Y-%m-%dT%H:%M:%SZ)] Backup complete.
