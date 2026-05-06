# ADO License System — Design Document
**Day 61 | 2026-05-07 | Author: Claude Code**
**Inspiration: Ixonomic bank-tiranyx coin minting pipeline**

---

## 1. KONSEP INTI: LICENSE SEBAGAI "KOIN"

Ixonomic (proyek Tiranyx di VPS yang sama) mencetak koin digital dengan identitas
kriptografis: setiap koin punya SHA-256 hash + HMAC-SHA256 signature, tidak bisa dipalsukan,
bisa diverifikasi offline. Pola yang sama kita pakai untuk ADO license.

```
Ixonomic Coin     ←→   ADO License
────────────────────────────────────────────
coinId (UUID)     ←→   license_id (UUID)
denomination      ←→   tier (BERLIAN/EMAS/PERAK/PERUNGGU)
quranRef+ayahText ←→   client_name + entropy (identity anchor)
identityHash      ←→   identity_hash = SHA-256(semua field)
signature         ←→   signature = HMAC-SHA256(LICENSE_SECRET_KEY, identity_hash)
state machine     ←→   ISSUED → ACTIVE → SUSPENDED → REVOKED
supply ceiling    ←→   max_instances per tier
batch mint        ←→   batch_mint() untuk reseller program
offline verify    ←→   load_and_validate() tanpa phone-home
```

**Prinsip: license = koin yang tidak bisa dipalsukan, bisa diverifikasi kapanpun tanpa internet.**

---

## 2. TIER SYSTEM (Nusantara Cultural Encoding — parallel dengan Ixonomic denominations)

| Tier | IDR/bulan | USD/bulan | Max Instances | Durasi Default | Target Segmen |
|------|-----------|-----------|---------------|----------------|---------------|
| **BERLIAN** 💎 | Custom | $2,000+ | 999 (unlimited) | 120 bulan (10 thn) | Government, BUMN, Air-Gapped |
| **EMAS** 🥇 | Rp 8–15 jt | $500–1,000 | 50 | 12 bulan | Enterprise, Multi-dept |
| **PERAK** 🥈 | Rp 3–5 jt | $200–350 | 5 | 1 bulan | Pro, Agency Reseller |
| **PERUNGGU** 🥉 | Rp 1–2 jt | $75–150 | 1 | 1 bulan | Basic, SME |

*Naming rationale: BERLIAN (diamond) = rarest, paling valuable. EMAS (gold) = enterprise.
PERAK (silver) = mid-tier. PERUNGGU (bronze) = entry. Menggunakan bahasa Melayu/Indonesia
— konsisten dengan brand "Built by practitioner, trilingual native."*

---

## 3. MINTING PIPELINE (4 Stages)

```
MANIFES     → license request diterima (client_name, tier, display_name, language_pack)
    ↓
IDENTITAS   → assign license_id (UUID) + entropy (16-byte random)
              identity_hash = SHA-256(license_id:client_name:tier:issued:expiry:entropy)
    ↓
STEMPEL     → signature = HMAC-SHA256(LICENSE_SECRET_KEY, identity_hash)
              LICENSE_SECRET_KEY TIDAK PERNAH disimpan di license file
    ↓
SEGEL       → serialize ke license.json (siap di-embed ke Docker image client)
```

**Analogi Ixonomic:**
```
TIBR     ↔  MANIFES   (raw blank coin ↔ raw license request)
NAQQASH  ↔  IDENTITAS (identity assignment ↔ SHA-256 + entropy)
VALIDATUR ↔ STEMPEL   (HMAC signature ↔ HMAC signature)
BANK     ↔  SEGEL     (final encoding ↔ license.json serialization)
```

---

## 4. VALIDATION PIPELINE (Offline, di ADO Instance)

```python
# Di ADO instance startup (main.py lifespan step 10):
lic = load_and_validate(
    license_path="/opt/ado/license.json",   # Dari env LICENSE_PATH
    secret_key=settings.LICENSE_SECRET_KEY, # Validator key (beda dari minter key?)
    demo_mode_allowed=settings.LICENSE_DEMO_MODE,
)
```

**Validation steps:**
```
1. Baca license.json dari disk
2. Recompute identity_hash dari semua field (tanpa signature)
3. Bandingkan dengan stored identity_hash → jika beda: TAMPERED
4. Verify HMAC-SHA256(LICENSE_SECRET_KEY, recomputed_hash) == stored signature
5. Cek state (REVOKED → INVALID, SUSPENDED → READ_ONLY)
6. Cek expiry date (+ 7 hari grace period)
7. Return LicenseValidationResult(mode, reason, days_remaining, ...)
```

**Modes:**
```
FULL      → License valid + aktif + belum expired → semua fitur available
READ_ONLY → Expired > 7 hari atau SUSPENDED → respond tapi tidak bisa training baru
DEMO      → Tidak ada license.json (beta instances seperti app.migancore.com)
INVALID   → Signature tidak cocok atau REVOKED → log error, tetap DEMO jika flag aktif
```

---

## 5. LICENSE FILE STRUCTURE (license.json)

```json
{
  "license_id":       "550e8400-e29b-41d4-a716-446655440000",
  "client_name":      "PT Rumah Sakit Sari Husada",
  "ado_display_name": "SARI",
  "issued_by":        "PT Tiranyx Digitalis Nusantara",
  "product":          "Migancore ADO Engine v0.5",
  "powered_by":       "Migancore × PT Tiranyx Digitalis Nusantara",
  "issued_date":      "2026-05-07T00:00:00+00:00",
  "expiry_date":      "2026-06-07T00:00:00+00:00",
  "tier":             "PERAK",
  "max_instances":    5,
  "language_pack":    ["id", "en"],
  "state":            "ISSUED",
  "entropy":          "a3f7b2c1d0e9f8a7b6c5d4e3",
  "identity_hash":    "sha256hex...",
  "signature":        "hmac_sha256hex..."
}
```

**Catatan:**
- `entropy` = 16-byte random (hex encoded) → mencegah preimage attack
- `identity_hash` = SHA-256(license_id:client_name:tier:issued:expiry:entropy)
- `signature` = HMAC-SHA256(LICENSE_SECRET_KEY, identity_hash)
- `powered_by` = non-removable brand attribution (tetap ada di config meski UI white-label)

---

## 6. DEPLOYMENT FLOW (Per Client)

```
[Migancore Platform]                     [Client VPS]
       │                                      │
       ├─ POST /license/mint                  │
       │  x-internal-key: INTERNAL_KEY        │
       │  body: {client_name, tier, ...}      │
       │                                      │
       ├─ Receive license.json                │
       │                                      │
       ├─ Bake ke Docker image:               │
       │  COPY license.json /opt/ado/         │
       │                                      │
       ├─ Set env LICENSE_SECRET_KEY          │
       │                                      │
       └──── Deploy Docker image ────────────►│
                                              │
                                              ├─ Startup: load_and_validate()
                                              │  (offline, tidak perlu internet)
                                              │
                                              └─ Log: license.ok, mode=FULL
```

---

## 7. ENFORCEMENT MATRIX

| Kondisi | Mode | Response |
|---------|------|----------|
| License valid, aktif | FULL | Semua fitur |
| License valid, dalam 7 hari expiry | FULL + WARNING | Semua fitur + peringatan |
| License expired < 7 hari | FULL + WARNING | Semua fitur + urgent renewal warning |
| License expired > 7 hari | READ_ONLY | Respond, tidak bisa training/import |
| License suspended | READ_ONLY | Respond, tidak bisa training/import |
| Signature tidak cocok | INVALID | Log error, fallback DEMO jika allowed |
| License revoked | INVALID | Log error, fallback DEMO jika allowed |
| Tidak ada license.json | DEMO | Semua fitur tapi display "Demo Mode" |
| No LICENSE_SECRET_KEY | DEMO | Semua fitur, log warning |

---

## 8. RESELLER / BATCH MINTING

Mirip Ixonomic mintBatch() untuk mencetak banyak koin sekaligus:

```python
# Agensi digital beli lisensi → jual ke 3 klien sekaligus
licenses = batch_mint([
    {"client_name": "RS Sari", "ado_display_name": "SARI", "tier": "PERAK", "language_pack": ["id"]},
    {"client_name": "Lexindo", "ado_display_name": "LEX",  "tier": "PERUNGGU", "language_pack": ["id", "en"]},
    {"client_name": "PT Maju",  "ado_display_name": "AVA",  "tier": "PERAK", "language_pack": ["id"]},
], secret_key=LICENSE_SECRET_KEY)
# → 3 license.json files, siap di-embed ke 3 Docker images
```

**Revenue share:** 30-40% ke Migancore (per brief Section 5.1 Stream 4)

---

## 9. ROADMAP LANJUTAN

| Feature | Timeline | Deskripsi |
|---------|----------|-----------|
| Hardware fingerprint binding | Day 76-80 | BERLIAN tier: license terikat ke CPU serial / MAC address |
| License renewal flow | Day 76-80 | API endpoint untuk generate license.json baru (renew) |
| Revocation server (optional) | Day 81-90 | Cache revocation list untuk BERLIAN tier (police fraud) |
| Billing integration | Phase 3 | Midtrans/Stripe → auto-generate license on payment |
| Multi-language license UI | Phase 3 | Dashboard trilingual untuk client self-service |

---

## 10. SECURITY NOTES

- **LICENSE_SECRET_KEY**: Gunakan key berbeda untuk minting (platform) dan validation (instance).
  Atau satu key dengan strict access control. NEVER commit ke git.
- **LICENSE_INTERNAL_KEY**: Protects `/license/mint` endpoint — only Migancore platform knows this.
- **HMAC vs asymmetric (RSA/Ed25519)**: HMAC dipilih karena: (1) offline-capable, (2) simpler deploy,
  (3) matches Ixonomic pattern. RSA would allow public-key verification without distributing secret —
  upgrade path for BERLIAN tier.
- **Entropy**: 128-bit random per license → each license is cryptographically unique even if
  all other fields are identical.
- **Timing attack**: `hmac.compare_digest()` digunakan (bukan `==`) → constant-time comparison.

---

*Dokumen ini dibuat Day 61 berdasarkan analisis Ixonomic coin minting pipeline (bank-tiranyx)
dan research enterprise license enforcement best practices.*
*File implementasi: `api/services/license.py` + `api/routers/license.py`*
