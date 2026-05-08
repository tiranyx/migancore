# MIGANCORE AMOEBA ARCHITECTURE — LOCKED v1.0
**Status:** LOCKED — Canonical reference for clone, deployment, and death model
**Date Locked:** 2026-05-08
**Locked By:** Executor Day 0 (post-Foundation Reset)
**Owner:** Fahmi Ghani / PT Tiranyx Digitalis Nusantara

> **LOCKED means:** This document is the single source of truth. Any deviation requires explicit owner approval and a new version. Do not improve or refactor without discussion.

---

## I. FILOSOFI INTI — Amoeba, Bukan SaaS

Migancore bukan platform SaaS multi-tenant. Migancore adalah **organisme induk yang berkembang biak melalui pembelahan biner (binary fission)** — setiap anak adalah organisme lengkap, mandiri, dan bisa hidup sendiri.

### Metafora → Realitas Teknis

| Metafora Biologi | Realitas Teknis | File / Komponen |
|---|---|---|
| **Induk** | Migancore base model + Hafidz Ledger | migancore:0.3, /api.migancore.com/hafidz |
| **Pembelahan** | Clone pipeline: detect → mint → render → deploy → verify | clone_manager.py |
| **Token kelahiran** | License JSON: HMAC-SHA256 signed, unique per instance | license.py |
| **DNA / Silsilah** | genealogy: parent_version, generation, lineage_chain | license.py::mint_license() |
| **Nama anak** | White-label display name: SARI, LEX, NOVA | ADO_DISPLAY_NAME env |
| **Hidup mandiri** | Full Docker stack per instance | docker-compose.template.yml |
| **Kematian** | License expired / REVOKED / VPS crash | license.py::LicenseState |
| **Warisan pengetahuan** | Knowledge Return → Hafidz Ledger | POST /hafidz/contribute |
| **1000 Bayangan** | 1000+ instance independen di seluruh dunia | Visi jangka panjang |

### Prinsip Kunci (TIDAK NEGOTIABLE)

1. **Zero Data Leak:** Data client TIDAK PERNAH keluar dari VPS/client server. Induk tidak bisa membaca database anak.
2. **Self-Sufficient:** Setelah deploy, anak bisa hidup tanpa koneksi ke induk (offline validation).
3. **Inheritance + Individuality:** Anak mewarisi jiwa induk (SOUL.md core values) tapi punya persona dan domain knowledge unik.
4. **Death = Contribution (opt-in):** Ketika anak mati, pengetahuan yang dia kumpulkan BISA kembali ke induk — dalam bentuk pola yang dianonimkan, bukan data mentah.
5. **Nested Cloning:** Anak bisa memiliki anak sendiri (generation 2, 3...). Silsilah tercatat di lineage_chain.

---

## II. ARSITEKTUR CLONE — Pipeline 5 Langkah

### 2.1 Alur Keseluruhan

`
[MIGANCORE INDUK]
     |
     |  CloneRequest (API call atau dashboard)
     |  +- client_name: RS Sari Husada
     |  +- ado_display_name: SARI
     |  +- tier: PERAK
     |  +- vps_ip: 203.0.113.45
     |  +- vps_ssh_key_path: /keys/sari.pem
     v
+--------------+
| 1. DETECT    |  SSH probe: nproc, free -g, docker check
|    VPS Spec  |  Minimum: 8GB RAM, 4 core, 50GB disk
+------+-------+
       |
+------+-------+
| 2. MINT      |  mint_license() -> SHA-256 identity + HMAC signature
|    License   |  genealogy block: parent_version, generation, lineage
+------+-------+
       |
+------+-------+
| 3. RENDER    |  docker-compose.yml + setup_ado.sh (customized)
|    Templates |  Injected: license_id, signature, db_password, domain
+------+-------+
       |
+------+-------+
| 4. DEPLOY    |  SCP + SSH: upload ke /opt/ado-client di VPS client
|    to VPS    |  Run setup_ado.sh -> docker compose up -d
+------+-------+
       |
+------+-------+
| 5. VERIFY    |  Poll http://{ip}:18000/health hingga UP (max 120s)
|    Health    |
+------+-------+
       v
[ADO ANAK — LIVE]
  Full stack: API + Ollama + Postgres + Qdrant + Redis + nginx
  Data: 100% di VPS client
  License: offline-validated, expiry tracked locally
`

### 2.2 Stack yang Di-Deploy ke Setiap Anak

- api: FastAPI gateway (white-label)
- ollama: Qwen2.5-7B-Instruct-Q4_K_M (atau model pilihan client)
- postgres: pgvector — data tenant, conversations, memory
- qdrant: Vector store — RAG, knowledge base client
- redis: Cache + session
- nginx: Reverse proxy + SSL (Certbot)

Tidak ada: Langfuse, Caddy, Letta (opsional — bisa ditambahkan tier EMAS/BERLIAN).

### 2.3 White-Label Capability

Setiap anak bisa punya identitas visual dan nama sendiri:
- ADO_DISPLAY_NAME: SARI, LEX, NOVA
- ADO_LANGUAGE_PACK: [id], [id, en], [id, en, zh]
- Logo, warna, domain: ado.client.com
- Engine tetap Migancore — immutable core

### 2.4 Generation & Nested Cloning

Generation 1 = anak langsung dari Migancore
Generation 2 = anak dari anak (reseller white-label)
lineage_chain = jejak lengkap silsilah

Reseller bisa membelah lagi — lineage tetap terlacak kembali ke Migancore induk.

---

## III. DEPLOYMENT MODEL — Self-Hosted, On-Premise, Air-Gapped

### 3.1 Tiga Mode Deploy

| Mode | Tier | Koneksi Internet | Lokasi Deploy | Use Case |
|---|---|---|---|---|
| Cloud VPS | PERUNGGU / PERAK / EMAS | Ya (opsional) | VPS client (DO, AWS, Hetzner) | Startup, UKM, agency |
| On-Premise | EMAS / BERLIAN | Ya (terbatas) | Server fisik di kantor client | Bank, RS, BUMN |
| Air-Gapped | BERLIAN | Tidak sama sekali | Server isolasi, no outbound | TNI, Polri, intelijen |

### 3.2 Offline License Validation (No Phone-Home)

Kunci untuk on-premise dan air-gapped:

validate_license() di license.py:
1. Recompute SHA-256 dari license fields
2. Verify HMAC-SHA256 signature dengan secret key
3. Cek expiry (grace period 7 hari)
4. Cek state (REVOKED -> INVALID)
-> TIDAK PERLU kontak api.migancore.com

Untuk BERLIAN (air-gapped):
- Secret key di-embed saat install oleh tim Tiranyx (USB / secure transfer)
- Tidak ada outbound call ke induk
- License expiry bisa diperpanjang dengan file license baru (secure courier / encrypted email)
- Tidak ada knowledge return (karena tidak ada internet) — kecuali client secara manual export dan kirim

### 3.3 Resource Minimum per Instance

| Resource | Minimum | Direkomendasikan |
|---|---|---|
| RAM | 8 GB | 16 GB |
| CPU | 4 core | 8 core |
| Disk | 50 GB SSD | 100 GB SSD |
| Swap | 4 GB | 8 GB |
| OS | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS |

---

## IV. KEMATIAN & KNOWLEDGE RETURN — Anak Kembali ke Induk

### 4.1 Definisi Mati

| State | Pemicu | Pengetahuan Bisa Kembali? |
|---|---|---|
| EXPIRED | Melewati expiry_date + grace period (7 hari) | Ya, jika opt-in |
| REVOKED | Pelanggaran license, non-payment, abuse | Tidak — hukuman |
| SUSPENDED | Non-payment sementara, review | Ditahan, belum kembali |
| VPS CRASH | Hardware failure, tidak ada backup | Hilang (kecuali backup ada) |
| MANUAL TERMINATE | Client hapus instance sendiri | Ya, jika export manual |

### 4.2 Knowledge Return Pipeline (Target Implementasi)

ADO ANAK (misal: SARI — RS Sari Husada)
         |
         |  Trigger: license expired / admin opt-in manual
         v
1. EXTRACTION (di dalam VPS client)
    +- DPO pairs dari conversations
    +- Tool usage patterns
    +- Domain topic clusters
    +- Voice/formality patterns
         |
2. ANONYMIZATION (di dalam VPS client)
    +- Strip PII: nama, NIK, no. RM
    +- Strip lokasi spesifik
    +- Strip data transaksi
    +- Retain: pola, struktur, topik
         |
3. CLIENT AUDIT (preview sebelum kirim)
    Admin client bisa review & edit apa yang akan dikirim ke induk
         |
         v POST https://api.migancore.com/hafidz/contribute
         |  Headers: X-License-ID, X-License-Signature
         v
4. HAFIDZ LEDGER (di Induk)
    +- Deduplication: SHA-256 hash
    +- Quality scoring (0-1)
    +- Status: pending -> review -> incorporated / reject
    +- Tracking: incorporated_cycle
         |
         v
5. TRAINING CYCLE N+1
    +- Export contributions (status: incorporated) ke JSONL
    +- Mix dengan data lain (CAI, owner, user, teacher)
    +- Fine-tune base model
    +- Output: migancore:v0.4
         |
         v
6. ANAK BARU LAHIR
    migancore:v0.4 -> clone baru
    Lahir dengan wisdom kesehatan dari SARI (tanpa lihat data RS)

### 4.3 Tipe Kontribusi yang Diterima

| Type | Struktur Payload | Domain Example |
|---|---|---|
| dpo_pair | {prompt, chosen, rejected} | Cara handle pasien kritis -> A_bagus vs A_buruk |
| tool_pattern | {trigger, tool_used, success, latency_ms} | Kata dosis -> trigger search_obat |
| domain_cluster | {topics[], frequency} | Topik RS: [BPJS, rujukan, farmasi] |
| voice_pattern | {formality, tone, effective_for} | Tone formal = efektif untuk medis |

### 4.4 Privacy Guarantees

1. Anonymization in-place: PII di-strip DI DALAM VPS client sebelum keluar.
2. No raw data: Tidak ada percakapan verbatim yang dikirim — hanya pola yang di-extract.
3. Client audit: Admin client bisa preview dan edit apa yang akan dikirim.
4. Opt-in default: knowledge_return.enabled = false secara default. Harus explicitly diaktifkan client.
5. Air-gapped exception: BERLIAN tier tidak bisa knowledge return (no internet). Manual export saja.

### 4.5 Hafidz Ledger Schema

CREATE TABLE hafidz_contributions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    child_license_id VARCHAR NOT NULL,
    child_display_name VARCHAR NOT NULL,
    child_tier VARCHAR NOT NULL,
    parent_version VARCHAR NOT NULL,
    contribution_type VARCHAR NOT NULL,
    contribution_hash VARCHAR NOT NULL UNIQUE,
    anonymized_payload JSONB NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    quality_score FLOAT,
    status VARCHAR NOT NULL DEFAULT pending,
    incorporated_cycle INTEGER,
    incorporated_at TIMESTAMPTZ,
    reject_reason VARCHAR,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX hafidz_parent_version_idx ON hafidz_contributions(parent_version);
CREATE INDEX hafidz_status_idx ON hafidz_contributions(status);
CREATE INDEX hafidz_type_idx ON hafidz_contributions(contribution_type);
CREATE INDEX hafidz_cycle_idx ON hafidz_contributions(incorporated_cycle);

---

## V. LICENSE TIER — Spek per Tingkat

| Tier | Max Instances | Default Duration | Support | Deploy Model | Knowledge Return |
|---|---|---|---|---|---|
| PERUNGGU (Bronze) | 1 | 1 bulan | Community | Cloud VPS only | Tidak |
| PERAK (Silver) | 5 | 1 bulan | Email | Cloud VPS / On-prem | Ya, opt-in |
| EMAS (Gold) | 50 | 12 bulan | Dedicated | Cloud / On-prem / Private cloud | Ya, opt-in |
| BERLIAN (Diamond) | 999 | 120 bulan (10 tahun) | On-site | Air-gapped / Isolated | Manual export only |

### Mode Runtime

| Mode | Artinya | Training? | Knowledge Return? |
|---|---|---|---|
| FULL | License valid | Ya | Ya (jika opt-in) |
| READ_ONLY | Expired / grace period | Tidak | Ya (final return) |
| DEMO | No license / beta | Terbatas | Tidak |
| INVALID | Tampered / REVOKED | Tidak | Tidak — instance mati |

---

## VI. IMPLEMENTASI STATUS — Jujur

### Sudah Ada & Jalan

| Komponen | Lokasi | Keterangan |
|---|---|---|
| License minter | api/services/license.py | SHA-256 + HMAC-SHA256, 4 tier |
| Clone manager | api/services/clone_manager.py | 5-step pipeline, dry-run ready |
| Docker template | docker/ado-instance/docker-compose.template.yml | Self-contained stack |
| Deploy script | SETUP_SCRIPT_TEMPLATE in clone_manager.py | Auto-install Docker + nginx + swap |
| Offline validation | validate_license() in license.py | No phone-home |
| Genealogy block | license.py::mint_license() | parent_version, generation, lineage_chain |
| Knowledge return config | knowledge_return in license.json | Enabled false by default |
| White-label env | ADO_DISPLAY_NAME, ADO_LANGUAGE_PACK | Rendered di docker-compose |

### Belum Ada / Belum Jalan

| Komponen | Yang Perlu Dibangun | Prioritas |
|---|---|---|
| hafidz_contributions table | Migration DB + schema | M0 (foundation) |
| POST /hafidz/contribute | Endpoint + auth (license signature) | M1 (data pipeline) |
| Anonymization pipeline | PII stripper di ADO anak | M1 |
| Knowledge export tool | python -m tools.export_knowledge | M1 |
| Contribution preview UI | Dashboard admin: Review before send | M2 |
| Real deploy (bukan dry-run) | Test end-to-end ke VPS nyata | M2 |
| Quality scoring | Cosine similarity threshold | M3 |
| Incorporation ke training | Export Hafidz -> JSONL -> cycle N+1 | M4 |

---

## VII. NETWORK EFFECT — Kenapa Model Ini Moat

Tahun 1:  10 ADO anak -> ~4,000 contributions -> migancore:v0.4
Tahun 2:  60 ADO anak -> ~25,000 contributions -> migancore:v0.6
Tahun 3: 200 ADO anak -> ~100,000 contributions -> migancore:v1.0

Setiap anak baru lahir dengan wisdom dari SEMUA anak sebelumnya — tanpa pernah melihat data spesifik mereka. Ini cooperative intelligence:

- ChatGPT/Claude: Kamu kontribusi data -> mereka dapat manfaat -> kamu tidak dapat apa-apa.
- Migancore: ADO anakmu kontribusi pola -> semua anak berikutnya (termasuk versi baru anakmu sendiri) lahir lebih cerdas.

Moat yang tidak bisa dikejar kompetitor:
Bukan fitur. Bukan model. Tapi wisdom yang terakumulasi dari ratusan organisasi Indonesia di Hafidz Ledger.

---

## VIII. DECISION REGISTRY — Pertanyaan yang Sudah Dijawab

| ID | Pertanyaan | Keputusan | Alasan |
|---|---|---|---|
| D-011 | Model deploy: SaaS atau self-contained? | Self-contained Docker per instance | Zero data leak, on-premise capable, amoeba model |
| D-012 | License validation: online atau offline? | Offline — HMAC-SHA256 locally | Air-gapped requirement (BERLIAN tier) |
| D-013 | Knowledge return: default on atau opt-in? | Opt-in, default false | Privacy first, compliance, client trust |
| D-014 | Data yang kembali: raw atau pola? | Pola yang dianonimkan | Zero PII leakage guarantee |
| D-015 | Generation depth: berapa level? | Unlimited, tracked via lineage_chain | Reseller model, white-label nesting |
| D-016 | Death handler: auto-delete atau read-only? | Read-only grace 7 hari, then knowledge return | Window untuk backup & final contribution |

---

## IX. ANTI-PATTERNS — Jangan Pernah

1. Jangan buat anak yang phone home tanpa izin. Telemetry harus disabled by default (TELEMETRY_ENABLED=false).
2. Jangan kirim data mentah dari anak ke induk. Hanya pola yang dianonimkan.
3. Jangan buat license yang tidak bisa offline-validated. Ini membunuh on-premise dan air-gapped.
4. Jangan hardcode secret key di image Docker. Embed saat deploy, rotateable.
5. Jangan biarkan anak mati tanpa window untuk knowledge return. Grace period minimal 7 hari.
6. Jangan anggap semua client mau knowledge return. Explicit opt-in, auditable, revocable.

---

## X. CHANGE LOG

| Version | Date | Changes | Author |
|---|---|---|---|
| v1.0 LOCKED | 2026-05-08 | Initial synthesis & lock post-Foundation Reset | Executor Day 0 |

---

Dokumen ini adalah arsitektur dari visi Fahmi Ghani — anak kembali ke induk.
Terinspirasi dari: Ixonomic (minting koin), SIDIX (1000 Bayangan + Hafidz Ledger), biologi (parent-child inheritance).
