# Day 49 Cycle 1 TRIGGER — LIVE STATUS
**Date:** 2026-05-05 (~02:40 UTC)
**Triggered by:** User explicit "GO!!!"
**Status:** 🟡 IN-PROGRESS — pod allocated, monitor running autonomously

---

## 🚀 What's Happening Right Now

A RunPod GPU pod is booting. A VPS-side monitor script is polling for SSH-ready, will auto-upload files, auto-trigger training, auto-poll for completion, auto-download adapter — all without further human intervention.

**Expected timeline from `02:40 UTC`:**
| Phase | Duration | What |
|-------|----------|------|
| Image pull | 5-15 min | RunPod pulls 10GB pytorch image to allocated host |
| SSH ready | +30 sec | sshd starts, PUBLIC_KEY injected |
| File upload | 30 sec | SCP dataset (1.24MB) + train_simpo.py + persona anchor |
| Pip install | 3-5 min | unsloth + trl + transformers + peft + bitsandbytes |
| Model download | 5-8 min | Qwen2.5-7B-Instruct (~15GB) from HF |
| Training | 15-25 min | SimPO+APO-Zero on 596 pairs, lr=5e-7, 1 epoch, RTX 4090 |
| Adapter save + download | 1-2 min | Adapter ~50MB → SCP back to VPS |
| **Total wall-clock** | **~30-55 min** | (image pull is the biggest variable) |

---

## 🔑 Pod Details

| Field | Value |
|-------|-------|
| Pod ID | **`ypr15l0jntkwxo`** |
| Image | `runpod/pytorch:2.4.0-py3.11-cuda12.1.1-devel-ubuntu22.04` |
| GPU | NVIDIA GeForce RTX 4090 (SECURE cloud) |
| Location | RO (Romania) |
| Cost | **$0.69/hr** (non-spot for guaranteed start; spot was unavailable) |
| Container disk | 50GB |
| Volume | 20GB at `/workspace` |
| SSH access | VPS ed25519 pubkey injected via PUBLIC_KEY env |
| Created | 2026-05-05 02:36:28 UTC |

**Cost projection at 30-50 min:** $0.35 - $0.58. Hard cap $7. Saldo intact $16.17.

---

## 🤖 Autonomous Monitor (PID 1717407 on VPS)

`/tmp/cycle1_monitor.sh` running as nohup. It will:
1. ✅ Poll RunPod API for pod SSH endpoint (every 30s)
2. ✅ When ready: SSH-test connection
3. Upload `cycle1_dataset.jsonl` + `train_simpo.py` + `persona_consistency_v1.jsonl` + `cycle1_run.sh` via SCP
4. Trigger `cycle1_run.sh` (background nohup on pod) which: installs deps + downloads Qwen + runs SimPO+APO
5. Poll for `/workspace/_TRAINING_DONE` marker file every 60s (max 2hr)
6. When complete: SCP adapter back to `/opt/ado/cycle1_output/migancore-7b-soul-v0.1/`
7. Log all to `/tmp/cycle1_monitor.log`

**MONITOR STATUS COMMAND (paste this anytime):**
```bash
ssh -i ~/.ssh/sidix_session_key root@72.62.125.6 "tail -30 /tmp/cycle1_monitor.log"
```

**POD STATUS COMMAND:**
```bash
ssh -i ~/.ssh/sidix_session_key root@72.62.125.6 "python3 -c 'import urllib.request, json; d=json.loads(urllib.request.urlopen(urllib.request.Request(\"https://rest.runpod.io/v1/pods/ypr15l0jntkwxo\", headers={\"Authorization\":\"Bearer $RUNPOD_API_KEY\"})).read().decode()); print(json.dumps({k:d.get(k) for k in [\"desiredStatus\",\"runtime\",\"publicIp\",\"costPerHr\"]}, indent=2))'"
```

---

## 🛡️ Safety + Isolation Confirmation (per user concern)

User asked: *"hati-hati di VPS ada SIDIX dan Mighantech3D, jangan bentrok"*

**Confirmed safe:**
- All Cycle 1 work happens on **separate RunPod pod** (RunPod's infra, RO data center)
- VPS interactions only touch `/opt/ado/*` (migancore) and `/tmp/cycle1_*` files
- Zero touch to `/opt/sidix/*` or `/opt/mighantech3d/*`
- HYPERX (`/opt/sidix/tools/hyperx-browser/`) NOT modified this session — only used as bind-mount for ONAMIX (Day 42-46)
- No new processes on VPS except monitor PID 1717407 (which only does SSH-out + SCP, no DB writes)

**Adapter download path:** `/opt/ado/cycle1_output/` — new dedicated directory, isolated from any SIDIX/Mighantech3D paths.

---

## 📋 Next-Session Pickup (when training completes)

The autonomous monitor will leave you with an adapter at `/opt/ado/cycle1_output/migancore-7b-soul-v0.1/`. Next-session work:

### Step 1: Verify adapter downloaded
```bash
ssh -i ~/.ssh/sidix_session_key root@72.62.125.6 "ls -la /opt/ado/cycle1_output/migancore-7b-soul-v0.1/"
# Expected: adapter_config.json, adapter_model.safetensors (~50MB), tokenizer.json, special_tokens_map.json
```

### Step 2: Identity eval (PROMOTE/ROLLBACK gate)
```bash
ssh -i ~/.ssh/sidix_session_key root@72.62.125.6 "
docker exec ado-api-1 python /opt/ado/eval/run_identity_eval.py \
  --adapter /opt/ado/cycle1_output/migancore-7b-soul-v0.1 \
  --baseline /opt/ado/eval/baseline_day39.json \
  --embedding bge-m3
"
```
**PROMOTE:** mean cosine ≥0.85 AND min ≥0.75
**ROLLBACK:** otherwise → post-mortem + Cycle 1.1 with lr=3e-7

### Step 3: GGUF convert (if PROMOTE)
```bash
ssh -i ~/.ssh/sidix_session_key root@72.62.125.6 "
cd /opt/ado/cycle1_output && \
docker exec ado-api-1 python /opt/ado/training/convert_gguf.py \
  --adapter /opt/ado/cycle1_output/migancore-7b-soul-v0.1 \
  --output /opt/ado/cycle1_output/migancore-7b-soul-v0.1.Q4_K_M.gguf
"
```

### Step 4: Push to Ollama + agents.json update
```bash
# Get base Modelfile to copy TEMPLATE block verbatim (footgun!)
ssh -i ~/.ssh/sidix_session_key root@72.62.125.6 "
docker exec ado-ollama-1 ollama show qwen2.5:7b-instruct-q4_K_M --modelfile > /tmp/base_modelfile
# Edit /tmp/base_modelfile: change FROM line to point to new GGUF
# Add: PARAMETER num_ctx 4096 (preserve Day 20 setting)
# Set OLLAMA_KEEP_ALIVE=24h env (footgun: default 5min causes cold reload during A/B)
docker exec ado-ollama-1 ollama create migancore:0.1 -f /tmp/base_modelfile
"
```

### Step 5: A/B traffic split (10% → migancore:0.1)
Update `agents.json` core_brain.model_version → `migancore:0.1` OR add per-request `X-Model-Variant` header routing.

---

## 🎯 What This Validates (when complete)

The original 30-day blueprint promised *"Seed Alive + Self-Improving v1"*. Day 49 closes that promise:

- ✅ Seed alive: Qwen2.5-7B Q4 (Day 1+)
- ⏳ **Self-Improving v1 IN-PROGRESS** (Cycle 1 SimPO running)
- ⏳ Identity preserved: pending eval
- ⏳ Hot-swap to production: pending PROMOTE

After PROMOTE, MiganCore = first ADO with a self-improved checkpoint that survives a model swap. Validates the entire VISION_DISTINCTIVENESS_2026.md "modular brain" thesis.

---

## 🆘 If Things Go Wrong

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Monitor log stuck "waiting for pod SSH" >20 min | Pod image pull stuck OR allocation lost | Check pod status command above; consider terminate+retry |
| SSH fails repeatedly | PUBLIC_KEY didn't propagate | Check `/workspace/.ssh/authorized_keys` on pod |
| Pip install OOM | Container disk too small | Recreate with containerDiskInGb=100 |
| Training crashes mid-run | save_steps=50 → 1-2 checkpoints recoverable | Resume from last checkpoint |
| Identity eval mean <0.80 | Catastrophic forgetting | ROLLBACK + Cycle 1.1 lower lr (3e-7) + cleaner dataset |
| GGUF convert fails | llama.cpp too old | Use Unsloth's `save_pretrained_gguf()` instead |

**Manual override commands** (kill monitor + cleanup):
```bash
ssh -i ~/.ssh/sidix_session_key root@72.62.125.6 "kill 1717407 || true"
# Terminate pod (stop billing):
ssh -i ~/.ssh/sidix_session_key root@72.62.125.6 "python3 -c \"
import urllib.request
key='$RUNPOD_API_KEY'
req=urllib.request.Request('https://rest.runpod.io/v1/pods/ypr15l0jntkwxo', headers={'Authorization':'Bearer '+key}, method='DELETE')
urllib.request.urlopen(req, timeout=15)
print('TERMINATED')
\""
```

---

**Day 49 = TRIGGERED, AUTONOMOUS MONITOR RUNNING. The Aha Moment is happening right now.**
