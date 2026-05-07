# Infra — VPS Config Repository

Folder ini menyimpan semua konfigurasi infrastruktur VPS untuk keperluan migrasi dan reproducibility.

## Struktur

```
infra/
├── scripts/
│   ├── vps_inventory.sh      # Audit semua service di VPS existing
│   └── export_configs.sh     # Export configs ke repo (secrets redacted)
├── nginx/                    # Nginx virtual host configs (diisi setelah inventory)
├── docker/                   # Docker compose files per service (diisi setelah inventory)
├── systemd/                  # Custom systemd unit files
├── cron/                     # Crontab backups
├── env_templates/            # .env templates (TANPA secrets)
└── README.md                 # Ini
```

## Workflow Migrasi

### Step 1 — Inventory (jalankan di VPS existing)
```bash
curl -o /tmp/vps_inventory.sh https://raw.githubusercontent.com/.../vps_inventory.sh
# ATAU copy manual, lalu:
bash /tmp/vps_inventory.sh 2>&1 | tee /tmp/vps_inventory.txt
# Paste output ke Claude untuk analisis
```

### Step 2 — Export configs ke repo
```bash
bash /tmp/export_configs.sh
cd /opt/ado && git add infra/ && git commit -m "infra: export VPS configs for migration"
git push
```

### Step 3 — Setup VPS baru
```bash
# Di VPS baru:
git clone [repo] /opt/ado
bash /opt/ado/infra/scripts/setup_new_vps.sh   # (akan dibuat setelah analisis inventory)
```

## Status
- [ ] Inventory selesai dijalankan
- [ ] Output inventory dianalisis Claude
- [ ] Configs di-export ke repo
- [ ] VPS baru ordered (KVM 4)
- [ ] Setup VPS baru
- [ ] Migrasi service by service
- [ ] DNS update
- [ ] Cleanup VPS lama
