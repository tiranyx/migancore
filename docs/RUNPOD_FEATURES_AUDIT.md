# RunPod Features Audit — What MiganCore Should Use vs Skip
**Created:** Day 54 (2026-05-06, ~05:42 WIB Jakarta = 22:42 UTC)
**Trigger:** Fahmi pointed out RunPod has built-in fine-tuning UI + many features I hadn't explored. Honest gap: I built 250-line custom REST script while higher-level options existed.
**Anti-recurrence:** Pair with Lesson #57 (STOP — don't build what already exists) + Lesson #75 (this doc spawns the lesson).

---

## ⏰ Timezone discipline

ALL server logs use UTC (Docker default, RunPod API default). Fahmi reads Jakarta WIB (UTC+7). Going forward EVERY retro/plan must include both for clarity.

Conversion shortcut: **WIB = UTC + 7h**.

---

## 🔍 Audit matrix — Use, Skip, Defer

### ✅ ALREADY USING (verified in cycle1_runpod.py)

| Feature | What it does | How we use it |
|---------|--------------|---------------|
| REST API `/v1/pods` POST | Spawn pod | Custom script with Lesson #59-#62 guards |
| REST API `/v1/pods/{id}` GET | Poll runtime/status | Boot watcher + cost telemetry |
| REST API DELETE | Terminate | Lesson #59 verify-after-delete |
| SSH via pod port | Code/data transfer | scp + ssh exec |
| SECURE cloud type | Predictable allocation | Lesson #60 (vs spot interruption) |
| `containerDiskInGb` | Ephemeral container disk | 40GB for training scratch |

### 🚀 SHOULD USE NEXT — high-leverage features I missed

| Feature | Why high-leverage | Where it helps | Adoption |
|---------|------------------|----------------|----------|
| **🔥 Axolotl Fine-Tuning Serverless** (Hub: `axolotl-ai-cloud`, 11.8k ⭐) | Submit DPO/SimPO job, get adapter back. **Zero pod management, zero boot timeouts**. Pay per actual GPU-second of training, not allocation. Native HF dataset + base model URLs. | **THE RIGHT ANSWER for Cycle 1+** if APO custom support fits. Bypasses ALL of Day 54's boot-timeout drama. | Day 54.5 / 55 |
| **Network Volumes** (persistent storage across pods, default mount `/workspace` on Pods, `/runpod-volume` on Serverless) | Save Qwen 7B base (15GB) ONCE, mount everywhere. Saves 5-10 min per cycle + bandwidth. Currently 600/1000 GB shown in Fahmi's account. | Cycle 2+ retrain, also Axolotl serverless can reference network volume for cached base weights | Day 55 setup |
| **Pod Templates** (Hub: `Pod Templates` tab — pre-baked images on RunPod's registry, faster than custom Docker Hub pulls) | Pre-baked PyTorch+CUDA, RunPod nodes have these cached → boot 1-2min vs 5min raw image | If Axolotl serverless doesn't fit, fall back to Pod Template here | Day 54.5 fallback |
| **The Hub Public Endpoints** (vLLM, Faster Whisper, SDXL, ComfyUI) | Ready-made inference endpoints — pay per request | Day 70+ when MiganCore needs scaled inference (currently CPU on VPS is fine for beta) | Day 70+ |
| **`runpodctl` CLI** (official) | Wrapper for spawn/SSH/upload/cleanup. Fewer LOC than raw REST. | Replace `cycle1_runpod.py` if we keep pod-based path | Day 56 |
| **Cost Centers** | Multi-project accounting — separate MiganCore from Sidix bills | When Fahmi splits projects | When 2+ projects share key |

### 🟡 SKIP for our use case (with reasoning)

| Feature | Why skip |
|---------|----------|
| **Built-in Fine-tuning UI** (the screenshot Fahmi showed) | Hardcoded to SFT/standard DPO with HF dataset URL input. **Cannot do SimPO + APO + anchor dataset + custom hyperparameters (lr 5e-7, simpo-beta 2.5, apo-lambda 0.05)**. Designed for generic LoRA fine-tuning, not research-grade alignment training. |
| **Serverless endpoints** | For inference (not training). MiganCore inference stays on VPS Ollama — Lesson #68 (standing alone, own infra). |
| **Public endpoints** (deploy model as API) | Wrapper pattern. Violates Vision Principle 1. Use only if we ever sell inference compute. |
| **Spot/Community Cloud** | Cheaper but interruptible. Lesson #60 explicitly says SECURE for training (mid-train kill = wasted money + corrupt checkpoint). |

### 🔮 DEFER (evaluate later)

| Feature | When to revisit |
|---------|----------------|
| **Savings Plans** | When monthly RunPod spend > $30 (committed discount). Currently ~$5-20/cycle = below threshold. |
| **Audit Logs** | When team grows beyond Fahmi alone — solo dev = no audit need. |
| **Create Team / Cost Centers** | When MiganCore separates from Sidix in billing. Today single-account mixing is fine. |
| **Refer & Earn** | After we have a public adapter that works — content angle for "Otak Belajar Apa" thread. |

---

## 🎯 Strategic implication for Day 54 onwards

### Immediate (current pod attempt)
Current A5000 spawn `981i8rnlce3c2v` is using raw `runpod/pytorch:devel` image (heavy, ~5GB+ to pull + warmup). **This is likely why 4090 boot timed out** — image pull contention with co-located training jobs.

If A5000 ALSO times out (next 1min), don't blindly retry — switch strategy:
1. Use a **RunPod Pod Template** with PyTorch+TRL pre-baked (search console for "pytorch trl" or "axolotl")
2. Spec template ID in spawn body instead of `imageName`

### Short-term (Day 55)
- Set up **Network Volume** sized 30GB
- Pre-cache Qwen 7B base + tokenizer to volume (one-time download via warm pod)
- All future cycles mount volume instead of HF download → cuts ~5min off every cycle

### Long-term
- Migrate `cycle1_runpod.py` from raw REST to `runpodctl` CLI calls — less code to maintain
- Build our OWN Pod Template (custom Docker image with TRL+APO+Liger pre-installed, pushed to RunPod template registry) — boots in <60s

---

## 📝 New Lesson candidates

### #75 — Audit vendor's first-class features BEFORE building custom from raw REST
Day 54 morning: I built 250-line cycle1_runpod.py with raw `urllib.request` REST calls. Fahmi pointed at RunPod's console UI showing fine-tuning, pod-templates, network-volumes, runpodctl CLI — features designed exactly to avoid the kind of boilerplate I wrote. The fine-tuning UI doesn't fit our SimPO+APO custom needs, but **Pod Templates** and **Network Volumes** absolutely would have helped Day 49 onwards.

Rule: Before committing to a custom integration, spend 15min reading vendor's docs **table of contents** (not just API reference). Identify high-leverage features that sit ABOVE raw REST. Custom code only if no built-in matches.

Pair with #57 (STOP — don't add tools/cloud when X already enough) and #69 (own tools default — but don't reinvent vendor primitives that ARE already commodity).

### #76 — Explicit timezone discipline in mixed-locale teams
Server logs UTC, Fahmi reads Jakarta WIB. I wrote "22:37" in monitor output without WIB context → cognitive load on Fahmi to mentally convert. Rule: every operational timestamp in user-facing reports = include both UTC and WIB. Format: `22:37 UTC (05:37 WIB Jakarta)`.

---

## 🛠️ Action items (ordered by ROI)

1. **(NOW)** Wait current A5000 attempt (1min until Lesson #60 timeout fires)
2. **(if A5000 fails)** Refactor `cycle1_runpod.py` to use Pod Template ID instead of raw image — search console for ready PyTorch templates
3. **(Day 55)** Create Network Volume + cache Qwen base weights once
4. **(Day 56+)** Migrate spawn logic to `runpodctl`
5. **(Day 60+)** Build custom MiganCore Pod Template (Docker image with all training deps pre-installed) — push to RunPod registry, boot <60s

---

## 💰 Cost impact projection if we adopt Pod Templates + Network Volumes

| Per cycle (Cycle 1, 2, 3...) | Current approach | With templates+volumes |
|------------------------------|------------------|------------------------|
| Boot to SSH ready | 4-7 min | 1-2 min |
| Dep install (`pip install trl ...`) | 2-3 min | 0 (pre-baked) |
| Base model download (15GB Qwen) | 3-5 min | 0 (volume mount) |
| **Total wasted billable boot time** | **9-15 min × $0.34-0.69/hr = $0.05-0.17 burned** | **~1-2 min × rate = $0.01-0.03** |
| **Savings per cycle** | — | **~$0.04-0.14** |

For Cycle 2-10 over next month, that's **$0.40-1.40 saved + 80+ minutes faster iteration**. Bigger than dollar value: faster iteration loop = more cycles = more learning = bigger moat.
