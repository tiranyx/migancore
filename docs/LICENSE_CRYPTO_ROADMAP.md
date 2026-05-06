# ADO License — Cryptographic Roadmap
**Day 62 | Author: Claude Code + Codex Review**

---

## Posisi Saat Ini: HMAC-SHA256 (Symmetric)

### Cara kerjanya sekarang
```
Migancore (issuer) → memegang LICENSE_SECRET_KEY
ADO child (validator) → memegang LICENSE_SECRET_KEY yang SAMA

validate_license():
  recompute identity_hash = SHA-256(license_id:client_name:tier:issued:expiry:entropy)
  verify: HMAC-SHA256(LICENSE_SECRET_KEY, identity_hash) == stored_signature
```

### Kenapa HMAC dipakai (valid untuk Phase 1)
- **Offline-capable**: tidak butuh internet saat validasi
- **Sederhana**: satu key, dua fungsi (mint + validate)
- **Battle-tested**: sama persis dengan Ixonomic coin minting yang sudah live di produksi
- **Phase 1 threat model**: Migancore memegang kedua key secara internal, belum distribute key ke client

### Limitation HMAC (Codex flag — valid concern)
Kalau `LICENSE_SECRET_KEY` terdistribusi ke client machine:
1. Client yang nakal bisa **forge license sendiri**: edit JSON → recompute hash → re-sign dengan key yang sama
2. HMAC = symmetric → siapa yang bisa verify, bisa juga sign
3. Untuk BERLIAN tier (key ada di client's air-gapped machine) → ini jadi real risk

---

## Phase 2: Ed25519 Asymmetric (Planned — Day 76-80, BERLIAN Tier)

### Cara kerja target
```
Migancore (issuer) → memegang ed25519_PRIVATE_KEY (NEVER leaves Migancore)
ADO child (validator) → memegang ed25519_PUBLIC_KEY saja

Minting (Migancore only):
  signature = ed25519_sign(PRIVATE_KEY, identity_hash)

Validation (ADO child, offline):
  ed25519_verify(PUBLIC_KEY, identity_hash, signature) → True/False
  ✓ Client bisa verify, tapi TIDAK BISA forge (no private key)
```

### Keunggulan Ed25519 untuk license client
- **Asymmetric**: public key bisa distribute bebas → client tidak bisa forge
- **Offline**: verify tanpa internet (public key baked ke image)
- **Fast**: Ed25519 = ~10x faster than RSA-2048
- **Modern**: dipakai oleh SSH keys, GitHub signing, JWT ES256

### Migration Plan (non-breaking)

```python
# Backward compatible migration strategy:
def validate_license(license_data: dict, public_key: Optional[str] = None, secret_key: Optional[str] = None):
    """
    If license has 'signature_algorithm': 'ed25519' → use public_key verify
    If legacy (no algorithm field) → fallback to HMAC-SHA256 with secret_key
    """
    algo = license_data.get("signature_algorithm", "hmac_sha256")
    
    if algo == "ed25519":
        return _validate_ed25519(license_data, public_key)
    else:
        return _validate_hmac(license_data, secret_key)  # legacy path
```

### New License Fields (Ed25519 era)
```json
{
  "license_id": "...",
  "signature_algorithm": "ed25519",
  "public_key_fingerprint": "SHA-256 of public key used to sign",
  "signature": "ed25519_signature_hex",
  ...
}
```

---

## Tier Mapping: Crypto Strategy per Tier

| Tier | Crypto | Rationale |
|------|--------|-----------|
| **PERUNGGU** | HMAC-SHA256 | Migancore controls deployment → key tidak pernah di tangan client |
| **PERAK** | HMAC-SHA256 | Same — Migancore manages VPS |
| **EMAS** | HMAC-SHA256 + optional Ed25519 | Client-managed infra, upgrade path available |
| **BERLIAN** | **Ed25519 WAJIB** | Air-gapped, client-controlled, private key NEVER leaves Migancore |

---

## Timeline

| Milestone | Target | Status |
|-----------|--------|--------|
| HMAC-SHA256 live (Phase 1) | Day 61-62 | ✅ DONE |
| LICENSE_ISSUER_MODE gate | Day 62 | ✅ DONE |
| Ed25519 key generation tooling | Day 76-80 | ⏳ Planned |
| Ed25519 mint + verify implementation | Day 76-80 | ⏳ Planned |
| Backward-compat migration (HMAC + Ed25519 parallel) | Day 76-80 | ⏳ Planned |
| BERLIAN tier: Ed25519 enforced | Day 81+ | ⏳ Planned |

---

## Untuk Agent Berikutnya (Day 76-80)

Implementasi Ed25519:
```python
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization

# Key generation (run once on Migancore platform):
private_key = Ed25519PrivateKey.generate()
public_key = private_key.public_key()

# Mint (Migancore only — private key):
signature = private_key.sign(identity_hash.encode())

# Validate (ADO child — public key only):
public_key.verify(signature, identity_hash.encode())  # raises InvalidSignature if forged
```

Dependencies: `pip install cryptography` (already likely in requirements.txt)

---

*Dokumen ini ditulis sebagai response terhadap Codex review Day 62.*
*Red flag #4: "HMAC tidak cocok untuk offline license client" — valid concern, migration path documented.*
*HMAC tetap dipakai sampai BERLIAN tier dan air-gapped deployment diimplementasikan.*
