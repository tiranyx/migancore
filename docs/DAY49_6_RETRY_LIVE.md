# Day 49.6 — CYCLE 1 RETRY LIVE (lessons #55-61 applied)
**Date:** 2026-05-05 (~13:45 UTC)
**Trigger:** User: "Jalankan protokol, cek timing dan kesiapan, kalo sudah saatnya pake pod. GO aja!"
**Status:** 🟢 IN PROGRESS — pod booting, monitor live with auto-abort

---

## ✅ Pre-flight ALL GREEN (full protocol applied)

| Check | Result |
|-------|--------|
| Dataset 596 pairs intact at `/tmp/cycle1_dataset.jsonl` | ✅ 1.24MB |
| SSH pubkey ready | ✅ `~/.ssh/id_ed25519.pub` |
| API v0.5.16 healthy | ✅ |
| DPO pool | **801** (grew from 596 — synth gen auto-resumed) |
| All 6 containers UP | ✅ |
| **tiranyx webpack DONE** (no CPU competition) | ✅ confirmed |
| 0 active pods (no orphan billing) | ✅ |
| Saldo RunPod | $9.41 (cukup ~21 jam @ $0.44/hr) |

---

## 🚀 Pod Spawned (with hari ini's lessons applied)

| Field | Value | Why |
|-------|-------|-----|
| Pod ID | **`qd4wodagps0acb`** | new pod, replaces failed ypr15l0jntkwxo |
| GPU | **NVIDIA A40** | 48GB VRAM (vs 4090's 24GB) — more headroom for QLoRA |
| Cost | **$0.44/hr** | cheaper than 4090 ($0.69/hr) |
| Location | CA (California) | US west, low latency |
| Image | **`runpod/pytorch:2.4.0-py3.11-cuda12.1.1-runtime-ubuntu22.04`** | RUNTIME variant (~3GB) bukan DEVEL (~10GB) — **3x faster boot** |
| Cloud type | SECURE non-spot | reliable allocation (Lesson #55: spot tight today) |
| Container disk | 50GB | enough for model + adapter |
| Volume | 20GB at /workspace | workspace persistence |
| SSH | port 22, ed25519 pubkey injected via PUBLIC_KEY env | so monitor can SCP |

**Cost projection:**
- Boot phase ~5 min: $0.04
- Pip install + Qwen download ~10 min: $0.07
- Training ~25 min on A40: $0.18
- Total successful run: **~$0.30**
- 5-min abort worst case: **$0.04**

---

## 🤖 Autonomous Monitor (PID 2637391)

`/tmp/cycle1_v2_monitor.py` running on VPS — Python (cleaner than nested bash heredocs).

**Applied lessons (#55, #59, #60, #61):**

```
Phase 1: Wait for SSH-ready (max 5 min, Lesson #60)
  ├─ poll /v1/pods/{id} every 20s
  ├─ log cost telemetry to /tmp/cycle1_v2_cost.log
  └─ if elapsed > 300s: TERMINATE + VERIFY (Lessons #59 #60)

Phase 2: SSH test → upload dataset + train_simpo.py + persona anchor

Phase 3: Trigger training in background (nohup)
  - python /workspace/train_simpo.py
    --use-apo --padding-free --use-liger-kernel
    (lr=5e-7 default per Day 49 refinement)

Phase 4: Poll /workspace/_TRAINING_DONE every 60s (max 90 min)
  - Cost log per minute (Lesson #61)
  - Tail of cycle1.log per iteration

Phase 5: SCP adapter → /opt/ado/cycle1_output/migancore-7b-soul-v0.1/

Phase 6: TERMINATE + VERIFY (Lesson #59)
  - DELETE /v1/pods/{id}
  - GET /v1/pods/{id} → expect 404
  - Retry DELETE if verify fails
```

**MONITORING COMMANDS (paste anytime):**
```bash
# Monitor log (most useful)
ssh -i ~/.ssh/sidix_session_key root@72.62.125.6 "tail -30 /tmp/cycle1_v2_monitor.log"

# Cost telemetry
ssh -i ~/.ssh/sidix_session_key root@72.62.125.6 "cat /tmp/cycle1_v2_cost.log"

# Adapter check (when complete)
ssh -i ~/.ssh/sidix_session_key root@72.62.125.6 "ls -la /opt/ado/cycle1_output/migancore-7b-soul-v0.1/ 2>/dev/null"

# Monitor process
ssh -i ~/.ssh/sidix_session_key root@72.62.125.6 "ps -p 2637391 -o pid,etime,stat"
```

**EMERGENCY KILL:**
```bash
ssh -i ~/.ssh/sidix_session_key root@72.62.125.6 "kill 2637391"
# Then manually terminate pod via API if needed:
ssh -i ~/.ssh/sidix_session_key root@72.62.125.6 "python3 -c \"
import urllib.request
req=urllib.request.Request('https://rest.runpod.io/v1/pods/qd4wodagps0acb', headers={'Authorization':'Bearer \$RUNPOD_API_KEY'}, method='DELETE')
print('DELETE:', urllib.request.urlopen(req, timeout=15).status)\""
```

---

## 📊 Why this attempt should succeed (vs Day 49 fail)

| Dimension | Day 49 (failed) | Day 49.6 (live) |
|-----------|-----------------|-----------------|
| Image size | 10GB devel | **3GB runtime (3x faster boot)** |
| GPU choice | RTX 4090 only | A40 fallback (better availability) |
| GPU cost | $0.69/hr | **$0.44/hr (36% cheaper)** |
| Boot timeout | (none — stuck 10hr = $6.76) | **5-min hard abort** (Lesson #60) |
| DELETE verify | trust HTTP 204 | **GET /pods/{id} expect 404** (Lesson #59) |
| Cost telemetry | manual check | **auto-poll per minute → cost log** (Lesson #61) |
| Pre-flight check | none | **GPU availability via API** (Lesson #55) |
| Synth gen contention | competing | n/a (training on RunPod, not VPS) |
| tiranyx CPU contention | 657% peak | **DONE — no contention** |

---

## 🎯 Expected Outcomes

### If SUCCESS (~30-50 min total wall-clock):
- `/opt/ado/cycle1_output/migancore-7b-soul-v0.1/` ~50MB safetensors
- Cost: ~$0.30
- Pod auto-terminated + verified
- Next: identity eval (PROMOTE gate cosine ≥0.85 mean + ≥0.75 min)

### If 5-MIN BOOT FAIL:
- Pod auto-terminated within 5:30 min
- Cost: ~$0.04
- Next: investigate (different image? different GPU? Vast.ai?)

### If TRAINING FAIL:
- Pod auto-terminated after max 90 min
- Cost: ~$0.66
- Adapter NOT downloaded (no _TRAINING_DONE marker)
- Next: SSH manually to inspect training error

---

## 📝 Next-Session Pickup

When monitor completes (success OR fail), verify with single command:
```bash
ssh -i ~/.ssh/sidix_session_key root@72.62.125.6 "
tail -30 /tmp/cycle1_v2_monitor.log
echo ---
ls -la /opt/ado/cycle1_output/ 2>/dev/null
"
```

If adapter exists at `/opt/ado/cycle1_output/migancore-7b-soul-v0.1/`:
1. Run identity eval
2. PROMOTE/ROLLBACK decision (cosine ≥0.85/0.75)
3. GGUF convert if PROMOTE
4. Ollama push `migancore:0.1`
5. agents.json model_version update + A/B routing

---

## 🛡️ Safety re-check

- All training on RunPod (separate from VPS) ✅
- VPS access limited to `/opt/ado/*` and `/tmp/cycle1_*` ✅
- Zero touch ke `/opt/sidix/`, `/opt/mighantect3d/`, `/var/www/ixonomic/`, `/www/wwwroot/tiranyx.co.id/` ✅
- Production user chat (api.migancore.com) tidak terpengaruh ✅
- Monitor PID 2637391 only does SSH-out + SCP, no DB writes ✅

---

**Day 49.6 = retry dengan disiplin. 5-min abort rule + cost telemetry + verify-DELETE = tidak akan bocor lagi seperti hari ini pagi.**
