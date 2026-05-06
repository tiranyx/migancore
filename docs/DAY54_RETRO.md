# Day 54 Retrospective — CYCLE 1 ADAPTER LANDED 🏆
**Date:** 2026-05-06 (05:00–08:13 WIB Jakarta = 22:00 UTC May 5 → 01:13 UTC May 6)
**Outcome:** 🟢 First MiganCore-branded LoRA adapter trained from own DPO data on Qwen2.5-7B-Instruct.

---

## 🎯 ACHIEVEMENT (the moat is real)

**Adapter:** `migancore-7b-soul-v0.1`
- HF live: https://huggingface.co/Tiranyx/migancore-7b-soul-v0.1
- VPS local: `/opt/ado/cycle1_output/migancore-7b-soul-v0.1/` (166MB)
- Base: Qwen/Qwen2.5-7B-Instruct
- Method: DPO + LoRA (r=16, α=32, all 7 Qwen2 linear layers)
- Dataset: `Tiranyx/migancore-cycle1-dpo-v1` (596 pairs UltraFeedback format)
- Hyperparams: lr=5e-7, num_epochs=1, batch=2 grad_accum=4, bf16, warmup 0.1
- Train runtime: 597s (~10 min on A100 SXM 80GB)

**ADO core mechanic (own data → own training → own adapter) E2E VALIDATED.**

---

## 📊 TRAINING METRICS (honest read)

| Metric | Start | End | Delta |
|--------|-------|-----|-------|
| train_loss | 0.6931 (=ln 2) | 0.6879 | -0.0052 (marginal) |
| mean_token_accuracy | 0.7121 | 0.777 | **+5.6%** ✅ |
| rewards/margins | 0.0 | +0.011 | **positive DPO direction** ✅ |
| entropy | 0.88 | 0.84 | model still confident |

**Honest assessment:** Conservative hyperparams (lr 5e-7, 1 epoch on 596 pairs) intentionally minimize catastrophic forgetting. Adapter delta is small but in the **right direction**. Cycle 2+ with aggressive params (lr 1e-6, num_epochs 3) will iterate quality.

Proof-of-concept SUCCESS, not "adapter that beats baseline." Expected.

---

## 🛠️ WORKING CONFIG (proven Day 54 r9 manual install)

```yaml
# /workspace/cycle1_r9.yaml (ran on dedicated A100 SXM RunPod pod)
base_model: Qwen/Qwen2.5-7B-Instruct
model_type: AutoModelForCausalLM
tokenizer_type: AutoTokenizer
is_qwen_derived_model: false   # CRITICAL — bypass Qwen1 eod_id bug
load_in_4bit: false
strict: false

rl: dpo
rl_beta: 0.1
chat_template: qwen_25         # CRITICAL — required for Qwen+DPO

datasets:
  - path: Tiranyx/migancore-cycle1-dpo-v1
    split: train
    type: chatml.ultra         # CRITICAL — UltraFeedback {prompt, chosen[msgs], rejected[msgs]}

dataset_prepared_path: /workspace/prepared
val_set_size: 0.0
output_dir: /root/r9_manual    # CRITICAL — container disk, NOT volume (avoid quota mid-save)

sequence_len: 2048
sample_packing: false
pad_to_sequence_len: false

adapter: lora
lora_r: 16
lora_alpha: 32
lora_dropout: 0.05
lora_target_modules: [q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj]

gradient_accumulation_steps: 4
micro_batch_size: 2
num_epochs: 1
optimizer: adamw_torch
lr_scheduler: cosine
learning_rate: 5e-7
warmup_ratio: 0.1
weight_decay: 0.0

bf16: auto
flash_attention: false         # SDPA fallback, skip flash-attn compile
gradient_checkpointing: true

logging_steps: 1
saves_per_epoch: 1
save_safetensors: true
# NO hub_model_id, NO hub_strategy — Axolotl push_to_hub broken (TRL/Transformers version mismatch)
```

### Pre-flight commands (Axolotl 0.16.0 manual install fix-up)

```bash
# After pip install axolotl==0.16.0:
pip uninstall -y torchvision           # Fix: torchvision::nms operator missing
mkdir -p /usr/local/lib/python3.11/dist-packages/axolotl/telemetry
cat > /usr/local/lib/python3.11/dist-packages/axolotl/telemetry/whitelist.yaml << 'EOF'
models: []
datasets: []
EOF
export AXOLOTL_DO_NOT_TRACK=1
export DO_NOT_TRACK=1
```

---

## 🛣️ TIMELINE Day 54 (3 hours active 05:00-08:13 WIB)

| Time WIB | Event | Cost |
|----------|-------|------|
| 05:00 | RunPod top-up $19.20, defer dedicated VPS Day 53 | — |
| 05:30 | 5x direct pod boot timeouts (4090, A5000, 4090 runtime, H100 SXM, Vast A100) | $0.46 |
| 06:00 | Pivot Axolotl Hub Serverless via UI → endpoint `7vzxc02ek2on0r` deployed | $0 |
| 06:08 | v1-v8 silent fails (eod_id, auto-detect, wrong type, wrong schema, push_to_hub bug) | $1.50 |
| 06:35 | Network volume `42hjavzigv` US-MO-1 30GB created + attached | $2.10/mo |
| 06:50 | CPU pod via UI — confirm volume mount + Axolotl handler doesn't write output_dir to volume | $0.10 |
| 07:15 | PIVOT 2: A100 SXM dedicated pod via UI + manual Axolotl install | — |
| 07:25 | Axolotl install pitfalls: torchvision broken, telemetry whitelist missing | — |
| 07:36 | Training run #1: 75/75 succeed but disk quota exceeded mid-save (14GB partial) | $1.37 (running) |
| 07:55 | Cleanup volume + retarget output_dir → /root/r9_manual (container 30GB) | — |
| 08:07 | Training run #2: 75/75 succeed + saved 162MB adapter to /root/ ✅ | (continued) |
| 08:11 | Upload to HF: 16.1GB total (162MB net), commit `9637f04b` | — |
| 08:12 | STOP A100 + CPU pods, download adapter to VPS | — |
| **TOTAL** | **3h 13min active** | **~$3.40** |

---

## 💰 COST ACTUAL Day 54

| Item | Cost |
|------|------|
| 5x direct pod boot timeouts | ~$0.42 |
| Vast.ai host self-stop | ~$0.04 |
| 8x Axolotl serverless jobs | ~$1.50 |
| CPU pod retrieve | ~$0.10 |
| A100 SXM dedicated training (~55 min @ $1.49/hr) | ~$1.37 |
| Network volume (one-off creation, ongoing $2.10/mo) | $0 today |
| **Day 54 total spent** | **~$3.43** |

Saldo RunPod: **$19.20 → ~$15.77** sisa. Vast credit $7 untouched. DigitalOcean AMD $100 credit untouched. Cumulative project cost: $8.36 + $3.43 = **$11.79 / $44 budget (~27%)**.

---

## 🎓 NEW LESSONS Day 54 (8 lessons, **83 cumulative**)

### #75 — Audit vendor's first-class features BEFORE building custom from raw REST
RunPod has Pod Templates, Network Volumes, runpodctl CLI, Hub Serverless, Fine-tuning UI. We jumped to raw REST (250 LOC custom script) and burned hours on infrastructure that higher-tier features would have avoided. Rule: spend 15 min reading vendor's table-of-contents BEFORE writing custom integration.

### #76 — Explicit timezone discipline in mixed-locale teams
Server logs UTC, Fahmi reads Jakarta WIB (UTC+7). All operational reports MUST include both: `22:37 UTC (05:37 WIB Jakarta)`. Reduces cognitive load for founder reading retros at 5 AM.

### #77 — RunPod Serverless needs network volume FROM DAY ONE
Endpoint without `networkVolumeId` = `/runpod-volume/` is worker ephemeral storage, idleTimeout 5s = adapter LOST despite logs claiming "saved". Pre-flight: create volume in target GPU region → attach to endpoint → THEN submit jobs. We trained successfully twice (v5+v6 + v7) on serverless but lost ALL three adapters. Cost: ~$1.50 + 24 min training time.

### #78 — When blocked at vendor abstraction tier, try NEXT HIGHER tier before debugging current
Day 54 timeline: stuck on direct REST API pod (5x boot timeout) → moved up to Hub Serverless (worked but had different bugs) → hit handler bug → moved back DOWN to dedicated pod via UI (combined: UI deploy reliability + manual training control). Tier ladder for RunPod: Direct REST → Pod Templates → runpodctl → Hub Serverless repos → Fine-tuning UI. Pair with #75 (audit) and #57 (STOP).

### #79 — Diversify vendor stack EARLY when training is the moat
Day 54: RunPod direct boot 5/5 fail + Vast.ai marketplace flake same day. Single-vendor dependency = blocking. Free credits cover diversification: $19.20 RunPod + $7 Vast + $100 DigitalOcean AMD MI300X. Stock 2-3 accounts BEFORE blocking. Operational hygiene, not feature creep.

### #80 — Axolotl Hub Serverless `output_dir` doesn't persist to user network volume despite logs claiming saved
RunPod's `axolotl-ai-cloud` Hub serverless repo writes cache (`/runpod-volume/prepared/`, `/runpod-volume/huggingface-cache/`) to volume but NOT `output_dir` (`/runpod-volume/fine-tuning/<run_id>`). Empirical Day 54: 8 training runs claimed success in logs ("Model successfully saved to..."), 0 adapters retrievable from volume after worker scale-down. Workaround: dedicated pod with manual Axolotl install + explicit volume mount + `output_dir: /workspace/...`.

### #81 — UI-deploy via console is more reliable than direct REST API spawn on RunPod (Day 54 empirical)
Day 54 empirical: 5/5 direct REST API pod spawn = boot timeout 5min. 4/4 UI-deploy via console = succeeded (endpoint serverless deploy + CPU pod retrieve + A100 GPU pod train + checkpoint pod). Hypothesis: UI uses different scheduler path that handles network/SSH provisioning better. When REST blocks, switch to UI.

### #82 — Axolotl 0.16.0 install pitfalls (3 sequential gotchas)
Manual `pip install axolotl==0.16.0` triggers chain of issues:
1. **torchvision::nms operator missing** (torchvision pre-installed in pytorch:2.4.0 image incompatible with new torch from axolotl deps) → `pip uninstall -y torchvision`
2. **`whitelist.yaml` missing** in `axolotl/telemetry/` (packaging bug) → `mkdir -p .../telemetry && echo "models: []\ndatasets: []" > .../whitelist.yaml`
3. **Auto-detected `is_qwen_derived_model: true`** triggers Qwen1 `eod_id` AttributeError → force `is_qwen_derived_model: false` in YAML
Plus `export AXOLOTL_DO_NOT_TRACK=1 DO_NOT_TRACK=1` to disable telemetry.

### #83 — Save adapter to container disk if network volume tight (avoid disk quota mid-save)
Day 54 r9 first attempt: training succeeded 75/75, save to `/workspace/r9_manual` started, hit "Disk quota exceeded (os error 122)" mid-write after 14GB partial (volume 30GB filled by HF cache 15GB + checkpoint 14GB). Lesson: estimate save footprint = LoRA adapter (150MB) + merged_model (`save_only_model: false` default = +15GB Qwen 7B) + checkpoint (~325MB) + tokenizer (11MB). Budget volume accordingly OR set `output_dir: /root/...` (container ephemeral 30GB plenty) and upload to HF before pod stop.

---

## 🛡️ ASSETS NOW AVAILABLE (post Day 54)

| Asset | Where | Notes |
|-------|-------|-------|
| HF dataset | `Tiranyx/migancore-cycle1-dpo-v1` | 596 DPO pairs UltraFeedback format |
| HF adapter | `Tiranyx/migancore-7b-soul-v0.1` | LoRA r=16 + merged 15GB model |
| Adapter local | `/opt/ado/cycle1_output/migancore-7b-soul-v0.1/` (VPS) | 166MB ready for identity eval |
| RunPod network volume | `42hjavzigv` (US-MO-1, 30GB) | Qwen 7B base + dataset cached, reusable Cycle 2+ |
| RunPod endpoint | `7vzxc02ek2on0r` (scale-to-zero, $0/s idle) | Axolotl Fine-Tuning Hub serverless |
| RunPod API key | `/opt/secrets/migancore/runpod_api_key` | Mode 600 |
| HF token | `/opt/secrets/migancore/hf_token` | **EXPOSED IN CHAT — ROTATE** |
| Vast.ai credit | $7 untouched | Backup vendor |
| DigitalOcean AMD credit | $100 free, 30 day expiry | MI300X $1.99/hr — Cycle 2+ alternative |

---

## 🔭 DAY 55+ ROADMAP

### Day 55 — Validate adapter quality
1. **Identity eval** — `/opt/ado/eval/run_identity_eval.py` baseline vs adapter. Gate: cosine ≥ baseline.
2. **A/B test** — 5 fingerprint prompts side-by-side (baseline Qwen vs migancore:0.1).
3. **Decision gate**:
   - PROMOTE if identity stable + at least 1 prompt shows preferred behavior
   - REJECT if regression on persona anchors (rare with conservative lr 5e-7)
4. **Hot-swap demo** — register `migancore:0.1` to Ollama if PROMOTE
5. **Document** in `BETA_LAUNCHED_DAY51.md` baseline snapshot update

### Day 56 — Cycle 2 with aggressive params
Cycle 2 hyperparams (research-validated for stronger learning):
- lr: 5e-7 → **1e-6** (2x stronger)
- num_epochs: 1 → **3** (more passes through small dataset)
- Add APO custom override (`use_apo: true` + anchor_dataset)
- Add SimPO (Axolotl supports `rl: simpo`)
- Same dataset OR add 200 fresh pairs from Day 54+ chat data
- Save BOTH adapter + merged → easier deployment

### Day 57+ — Strategic options (Fahmi picks)
- **Path A: Open beta scaling** — invite 20 more users, stress-test infrastructure
- **Path B: Try DigitalOcean AMD MI300X** — vendor diversification + free $100
- **Path C: Distill Qwen 7B → 3B own model** — speed for production (Lesson #70)
- **Path D: Spec dec verdict** — kill or tune (Lesson #71 follow-up)

---

## 🚦 EXIT CRITERIA — Day 54 Status

Must-have:
- [x] Cycle 1 adapter trained
- [x] Adapter on HF Hub (Tiranyx/migancore-7b-soul-v0.1)
- [x] Adapter on VPS (`/opt/ado/cycle1_output/`)
- [x] All pods STOPPED (no leak)
- [x] Volume + endpoint preserved (Cycle 2 reuse)
- [x] DAY54_RETRO documented (this file)
- [x] Lessons #75-83 documented in AGENT_ONBOARDING

Stretch (deferred Day 55):
- [ ] Identity eval cosine measurement
- [ ] PROMOTE/REJECT decision
- [ ] Hot-swap to Ollama as `migancore:0.1`
- [ ] Update BETA_LAUNCHED snapshot

---

## ⚠️ CRITICAL — Token Rotation (do FIRST in Day 55)

HF token `hf_<REDACTED_DAY54>****` exposed in chat history during Day 54 session.

**Action:**
1. Login https://huggingface.co/settings/tokens
2. Find token named `migancore` (FINEGRAINED)
3. **Revoke** that specific token
4. Generate new token with same scopes (write to user repos)
5. Save to `/opt/ado/data/secrets/migancore/hf_token` mode 600 on VPS:
   ```bash
   ssh root@vps 'echo "<new_token>" > /opt/secrets/migancore/hf_token && chmod 600 /opt/secrets/migancore/hf_token'
   ```
6. Verify: `hf auth whoami --token "$(cat /opt/secrets/migancore/hf_token)"`

---

## 📝 META — Process learnings (not coded as #lessons but worth noting)

1. **Engineer mode vs Researcher mode**: Day 54 morning I panic-iterated 5 silent-fail attempts in 10 min before doing proper research. After research-agent delegation found `chat_template: qwen_25` missing field, problem solved in 1 attempt. **Ratio: 1 hour research saves 5 hours iteration.**

2. **Vendor dependency = vendor risk**: spent ~50% of Day 54 fighting RunPod-specific bugs. Diversified vendor stack (Lesson #79) is operational hygiene we should have done Day 49.

3. **UI vs API reliability gap**: Day 54 empirical 5/5 REST direct fail vs 4/4 UI deploy succeed (Lesson #81). Surprising finding — API-first dogma not always correct for new vendors.

4. **Honest reporting >>> shipping**: Lessons #80 and #82 only emerged because we kept logs of EACH failure. Without honest documentation, Day 55 would repeat all 8 silent-fail iterations.

5. **3 hours active session limit**: Fahmi up since 5 AM, productive until 8 AM. After that = diminishing returns. Per Lesson #65: verify-end-to-end before deep-diving applies to founder energy too.

---

**Day 54 = HISTORIC. The MOAT is real. Cycle 1 proven. ADO core mechanic E2E validated.** 🌱

Selamat istirahat Fahmi. Day 55 starts fresh with PROMOTE/REJECT decision pada adapter `migancore-7b-soul-v0.1` setelah identity eval.
