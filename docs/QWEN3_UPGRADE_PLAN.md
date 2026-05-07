# Qwen3-8B Upgrade Plan — Day 67
**Status:** P1 — Plan ready, execute after Cycle 6 PROMOTE  
**Target:** Upgrade base model Qwen2.5-7B → Qwen3-8B untuk Cycle 7+

---

## Konteks

### Mengapa Qwen3-8B?
Research 2026 (Apache 2.0, April 2026):
- Qwen3-8B **beats Qwen2.5-14B** pada >50% benchmarks
- **Hybrid thinking mode**: toggle `enable_thinking=True/False` dalam 1 model
  - `no-think` mode: fast response, persona consistency → ideal untuk produk default
  - `think` mode: deep reasoning, CoT chains → ideal untuk analytic tasks
- Parameter 8B = hardware sama dengan Qwen2.5-7B (VRAM ≈ 5GB Q4_K_M)
- **Product differentiator untuk Migancore ADO:**
  - Demo mode (fast, no-think) → klien merasakan ADO yang responsif
  - Analytic mode (think) → ADO yang bisa reasoning mendalam

### Kapan Upgrade?
- **JANGAN sekarang** — tunggu Cycle 6 PROMOTE
- Setelah Cycle 6 PROMOTE: base model Cycle 7+ = Qwen3-8B
- Cycle 7 target = identity + voice pairs di atas Qwen3-8B (karena model baru)
- Re-baseline eval dengan Qwen3-8B sebelum training Cycle 7

---

## Migration Steps

### Step 1: Download Qwen3-8B Q4_K_M ke Ollama
```bash
# Di VPS (via docker exec)
docker exec ado-ollama-1 ollama pull qwen3:8b-q4_K_M
# Expected: ~4.8GB download, ~5min pada koneksi stabil
# Verify:
docker exec ado-ollama-1 ollama list | grep qwen3
```

### Step 2: Test Hybrid Thinking Mode
```bash
# no-think mode (default, fast)
curl http://localhost:11434/api/generate -d '{
  "model": "qwen3:8b-q4_K_M",
  "prompt": "Siapa kamu?",
  "stream": false,
  "options": {"temperature": 0.7}
}'

# think mode (reasoning, tambahkan /no_think atau /think di prompt)
# Qwen3 menggunakan special tokens untuk toggle thinking
curl http://localhost:11434/api/generate -d '{
  "model": "qwen3:8b-q4_K_M",
  "prompt": "<|im_start|>user\nAnalisa keuntungan dan kerugian penggunaan AI di perusahaan manufaktur Indonesia.<|im_end|>\n<|im_start|>assistant\n",
  "stream": false
}'
```

### Step 3: Modelfile untuk Qwen3-8B (no-think default)
```modelfile
# Modelfile_cycle7_qwen3 — no-think mode default
FROM qwen3:8b-q4_K_M
ADAPTER /opt/ado/cycle7_output/cycle7_lora_q4.gguf  # Setelah Cycle 7 training

# ADO persona injection
SYSTEM """Kamu adalah {ADO_DISPLAY_NAME}, asisten AI yang dikembangkan oleh Migancore.
Kamu membantu {CLIENT_NAME} dengan kebutuhan operasional mereka.
Berkomunikasilah dengan profesional, hangat, dan informatif.
Gunakan bahasa Indonesia sebagai default, kecuali diminta bahasa lain."""

# No-think mode: append /no_think untuk disable reasoning chain
# Think mode: user append /think atau set via API parameter

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER num_ctx 4096
PARAMETER stop "<|im_end|>"
PARAMETER stop "<|endoftext|>"
```

### Step 4: Eval Baseline Qwen3-8B (BEFORE training)
```bash
# Jalankan eval dengan model baru SEBELUM training Cycle 7
# Ini menjadi baseline baru (baseline_qwen3.json)
docker compose exec -T api python /app/workspace/run_identity_eval.py \
    --model qwen3:8b-q4_K_M \
    --reference /app/eval/baseline_day58.json \
    --retry 3 \
    --output /app/workspace/baseline_qwen3.json
```

### Step 5: Update Training Script untuk Cycle 7
```python
# Di cycle7_orpo_vast.py:
BASE_MODEL = "Qwen/Qwen3-8B"           # Ganti dari Qwen2.5-7B-Instruct
BASE_MODEL_OLLAMA = "qwen3:8b-q4_K_M"  # Untuk GGUF LoRA
HF_REPO = "Tiranyx/migancore-7b-soul-v0.7"  # Masih 7b untuk konsistensi naming
```

---

## Thinking Mode Integration — API Level

Qwen3 hybrid thinking = product differentiator. Perlu API support:

### Option A: Header Toggle (Recommended)
```python
# Di api/routers/chat.py
# X-ADO-Mode: fast | analytic
mode = request.headers.get("X-ADO-Mode", "fast")
if mode == "analytic":
    prompt = f"{user_message}\n/think"  # Trigger Qwen3 thinking
else:
    prompt = f"{user_message}\n/no_think"  # Fast mode
```

### Option B: Automatic Mode Detection
```python
# Detect analytical queries automatically
ANALYTICAL_KEYWORDS = ["analisa", "bandingkan", "pros cons", "jelaskan detail"]
if any(kw in user_message.lower() for kw in ANALYTICAL_KEYWORDS):
    prompt += "\n/think"
```

---

## Cost & Performance Estimate

| Metric | Qwen2.5-7B | Qwen3-8B | Delta |
|--------|-----------|---------|-------|
| VRAM (Q4_K_M) | ~4.5GB | ~4.8GB | +300MB |
| Inference speed | ~22 tok/s | ~20 tok/s est. | -10% |
| Benchmark (MMLU) | 71.3% | 75.4% est. | +5.7% |
| Reasoning | Fair | Good (think mode) | ↑↑ |
| Price delta | $0 | $0 | same infra |
| Cycle 7 training (Vast.ai) | $0.15 | ~$0.17 est. | +13% |

---

## Risk Assessment

| Risk | Probability | Mitigation |
|------|-------------|-----------|
| Qwen3-8B OOM di VPS lama | Low | Q4_K_M = 4.8GB, same as Qwen2.5 |
| Persona drift (new base) | Medium | Cycle 7 identity pairs + re-baseline |
| GGUF LoRA format change | Low | Test dengan llama.cpp nightly build |
| Ollama Qwen3 support lag | Low | Qwen3 already available: `ollama pull qwen3:8b` |

---

## Decision Gate: Proceed ke Qwen3-8B Upgrade?

✅ Proceed jika:
- Cycle 6 PROMOTE sukses (weighted >= 0.92)
- Qwen3-8B pull berhasil (verify dengan test prompt)
- Baseline eval Qwen3 bare ≥ 0.75 (pre-training baseline)

⚠️ Tunda jika:
- Cycle 6 ROLLBACK → fix Cycle 7 dulu dengan Qwen2.5
- Qwen3 Ollama support issues
- VPS RAM < 8GB (tidak cukup untuk Qwen3 + API overhead)

---

*Dibuat: Day 67, Claude Code*  
*Target implementasi: Day 68-70 (setelah Cycle 6 PROMOTE)*
