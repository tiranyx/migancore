#!/usr/bin/env python3
"""
MiganCore Cycle 5 ORPO Training — Vast.ai Orchestration
=========================================================
Day 64 | 2026-05-07

Dataset  : 877 pairs (554 curated + 323 new domain + targeted voice/evo-aware)
           Curated: identity×194 + tool_use×160 + code×180 + cai×16 + distill×10
           New domain: umkm×67 + engineering×60 + legalitas×56 + creative_id×50 + adaptive×40
           Cycle 4 ROLLBACK fixes: voice×31 (targeted) + evo_aware×19 (targeted)
Algorithm: ORPO — SFT + odds-ratio preference, beta=0.1, lr=6e-7, 2 epochs
Target   : A40/A100 40-80GB @ ~$0.27-0.60/hr | ~25-35 min total
Output   : Tiranyx/migancore-7b-soul-v0.5 (ORPO Cycle 5 adapter)

Cycle 5 OKRs (fix Cycle 4 ROLLBACK):
  weighted_avg >= 0.92   (Cycle 4: 0.891 ROLLBACK)
  voice >= 0.85          (Cycle 4: 0.739 CRITICAL — 31 targeted pairs + MIGAN_VOICE_PRINCIPLES)
  evo-aware >= 0.80      (Cycle 4: 0.537 CRITICAL — 19 targeted pairs + architecture description)
  tool-use >= 0.85       (Cycle 4: 0.768 — 160 tool_use curated pairs)
  creative >= 0.80       (Cycle 4: 0.829 ✅ — preserve)
  identity >= 0.90       (Cycle 4: 0.963 ✅ — preserve, 194 identity-anchor pairs)

Lessons applied (cumulative Cycle 1–4):
  #59  — verify instance DELETE (not just 204 — list again after)
  #60  — 10-min auto-abort if no SSH
  #61  — cost telemetry per-minute logged to file
  #62  — never >2hr same vendor same fail mode
  #63  — Vast.ai API key stored in /opt/secrets/migancore/vastai_api_key
  #110 — TRL 0.9.6 has CPOTrainer/ORPOTrainer, NOT SimPOTrainer
  #111 — era-pin: trl==0.9.6 + transformers==4.44.2 + peft==0.12.0 + accelerate==0.34.0
  #113 — SSH ping before install (status=running != sshd ready)
  #114 — Qwen2.5 bos_token_id=None fix in train_simpo_standard.py
  #116 — Gemini model: use gemini-2.5-flash (not 2.0-flash which is 404)
  #131 — voice/evo dedup: 80 stored → 31 unique prompts (30 seeds × 4 repeats)
"""

import os
import sys
import json
import time
import subprocess
import requests
from pathlib import Path
from datetime import datetime, timezone

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
VAST_KEY_PATH = "/opt/secrets/migancore/vastai_api_key"
HF_TOKEN_PATH = "/opt/secrets/migancore/hf_token"
DATASET_PATH  = "/opt/ado/data/workspace/cycle5_combined_dataset.jsonl"
TRAIN_SCRIPT  = "/opt/ado/training/train_simpo_standard.py"
OUTPUT_DIR    = "/opt/ado/cycle5_output"
LOG_PATH      = "/tmp/cycle5_training.log"

HF_REPO       = "Tiranyx/migancore-7b-soul-v0.5"
BASE_MODEL    = "Qwen/Qwen2.5-7B-Instruct"

# GPU requirements
MIN_GPU_RAM_MB = 40_000   # 40 GB minimum (A40/A100)
MAX_PRICE_HR   = 0.65     # USD hard cap per hour
MIN_DISK_GB    = 65       # base 15GB + training overhead

# Timing (Lesson #60, #62)
MAX_BOOT_WAIT_SEC = 600   # 10 min — abort if SSH not up
COST_CAP_USD      = 5.00  # hard stop

# Training hyperparams — identical to Cycle 3/4 proven config
# Only change: dataset size 723 → 877 (more domain + targeted voice/evo)
SIMPO_ARGS = [
    "--dataset",       "/root/cycle5_combined_dataset.jsonl",
    "--output-dir",    "/root/cycle5_adapter",
    "--base-model",    BASE_MODEL,
    "--epochs",        "2",          # same as Cycle 3/4 (2 epochs converged well)
    "--learning-rate", "6e-7",       # same as Cycle 3/4
    "--simpo-beta",    "2.5",
    "--simpo-gamma",   "1.0",
    "--loss-type",     "apo_zero",
    "--lora-r",        "16",
    "--lora-alpha",    "16",
    "--batch-size",    "2",
    "--grad-accum",    "8",
    "--max-seq-length","2048",
]

VAST_API = "https://console.vast.ai/api/v0"
SSH_KEY  = "/root/.ssh/id_ed25519"

# ─────────────────────────────────────────
# HELPERS (identical to Cycle 4)
# ─────────────────────────────────────────
VAST_KEY = ""
HF_TOKEN = ""


def log(msg: str):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")


def load_secret(path: str) -> str:
    try:
        val = Path(path).read_text().strip()
        if not val:
            raise ValueError("empty")
        return val
    except Exception as e:
        log(f"FATAL: cannot read {path}: {e}")
        sys.exit(1)


def vast(method: str, path: str, **kwargs) -> dict:
    """Vast.ai API wrapper — always injects api_key as query param."""
    url = f"{VAST_API}{path}"
    params = kwargs.pop("params", {})
    params["api_key"] = VAST_KEY
    resp = getattr(requests, method)(url, params=params, timeout=30, **kwargs)
    try:
        data = resp.json()
    except Exception:
        data = {}
    if resp.status_code not in (200, 201):
        log(f"Vast API {method.upper()} {path} → {resp.status_code}: {resp.text[:200]}")
        return {}
    return data


def search_offers() -> list:
    """Find cheapest A40/A100-class offers meeting our requirements."""
    query = {
        "verified": {"eq": True},
        "rentable": {"eq": True},
        "gpu_ram":  {"gte": MIN_GPU_RAM_MB},
        "disk_space": {"gte": MIN_DISK_GB},
        "dph_total":  {"lte": MAX_PRICE_HR},
        "type": "ask",
        "order": [["dph_total", "asc"]],
        "limit": 20,
    }
    result = vast("get", "/bundles/", params={"q": json.dumps(query)})
    return result.get("offers", [])


def create_instance(offer_id: int) -> int | None:
    """Rent an instance from offer_id. Returns instance_id or None."""
    payload = {
        "client_id":       "me",
        "image":           "pytorch/pytorch:2.5.1-cuda12.4-cudnn9-devel",
        "disk":            MIN_DISK_GB,
        "runtype":         "ssh",
        "use_jupyter_lab": False,
        "label":           "migancore-cycle5-orpo",
        "ssh_key_ids":     [808896],  # VPS id_ed25519 registered in Vast.ai
    }
    result = vast("put", f"/asks/{offer_id}/", json=payload)
    inst_id = (result.get("new_contract") or
               result.get("contract_id") or
               result.get("id"))
    if not inst_id:
        log(f"create_instance: no id in response: {result}")
    return inst_id


def get_instance(inst_id: int) -> dict:
    """GET /instances/{id}/ returns {"instances": <dict>}."""
    result = vast("get", f"/instances/{inst_id}/")
    if not result:
        return {}
    instances = result.get("instances", result)
    if isinstance(instances, dict):
        return instances
    if isinstance(instances, list):
        for inst in instances:
            if isinstance(inst, dict) and inst.get("id") == inst_id:
                return inst
    return {}


def delete_instance(inst_id: int) -> bool:
    """Delete + verify gone (Lesson #59)."""
    log(f"Deleting instance {inst_id}...")
    vast("delete", f"/instances/{inst_id}/")
    time.sleep(5)
    remaining_inst = get_instance(inst_id)
    status = remaining_inst.get("actual_status", "")
    if remaining_inst and status not in ("exited", "deleted", ""):
        log(f"WARNING: instance {inst_id} still present (status={status}). Retrying delete...")
        time.sleep(10)
        vast("delete", f"/instances/{inst_id}/")
        time.sleep(10)
        remaining_inst2 = get_instance(inst_id)
        status2 = remaining_inst2.get("actual_status", "")
        if remaining_inst2 and status2 not in ("exited", "deleted", ""):
            log(f"ERROR: instance {inst_id} still alive (status={status2}) after 2 deletes! Manual cleanup required.")
            return False
    log(f"Instance {inst_id} CONFIRMED DELETED ✓  (Lesson #59)")
    return True


def wait_for_ssh(inst_id: int, deadline: float) -> tuple[str, int] | tuple[None, None]:
    """Poll until instance is running with SSH, or deadline reached."""
    log(f"Waiting for SSH (max {int(deadline - time.time())}s remaining)...")
    while time.time() < deadline:
        inst = get_instance(inst_id)
        status = inst.get("actual_status", "unknown")
        ssh_host = inst.get("ssh_host", "")
        ssh_port = inst.get("ssh_port", 0)
        log(f"  status={status} ssh_host={ssh_host} ssh_port={ssh_port}")
        if status == "running" and ssh_host and ssh_port:
            log(f"SSH ready: {ssh_host}:{ssh_port}")
            return ssh_host, int(ssh_port)
        if status in ("exited", "error", "failed"):
            log(f"Instance entered terminal state: {status}")
            return None, None
        time.sleep(20)
    log(f"ABORT: no SSH within {MAX_BOOT_WAIT_SEC}s (Lesson #60)")
    return None, None


def ssh(host: str, port: int, cmd: str, timeout: int = 600) -> tuple[int, str, str]:
    """Run a command on the instance via SSH."""
    result = subprocess.run(
        ["ssh",
         "-i", SSH_KEY,
         "-o", "StrictHostKeyChecking=no",
         "-o", "BatchMode=yes",
         "-o", "ConnectTimeout=15",
         "-p", str(port),
         f"root@{host}",
         cmd],
        capture_output=True, text=True, timeout=timeout
    )
    return result.returncode, result.stdout, result.stderr


def scp_to(local: str, host: str, port: int, remote: str, timeout: int = 300) -> bool:
    result = subprocess.run(
        ["scp",
         "-i", SSH_KEY,
         "-o", "StrictHostKeyChecking=no",
         "-P", str(port),
         local,
         f"root@{host}:{remote}"],
        capture_output=True, text=True, timeout=timeout
    )
    if result.returncode != 0:
        log(f"SCP failed: {result.stderr[:200]}")
        return False
    return True


def scp_from(host: str, port: int, remote: str, local: str, timeout: int = 600) -> bool:
    """SCP a single file (NOT -r) to avoid downloading checkpoints. Lesson #132."""
    Path(local).parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["scp",           # NO -r flag: only copy exact file specified
         "-i", SSH_KEY,
         "-o", "StrictHostKeyChecking=no",
         "-P", str(port),
         f"root@{host}:{remote}",
         local],
        capture_output=True, text=True, timeout=timeout
    )
    if result.returncode != 0:
        log(f"SCP-from failed: {result.stderr[:300]}")
        return False
    return True


def cost_so_far(inst_id: int, start_ts: float, price_hr: float = 0.35) -> float:
    """Rough cost estimate: elapsed_hours × price_per_hour."""
    elapsed_h = (time.time() - start_ts) / 3600
    try:
        inst = get_instance(inst_id)
        price_hr = inst.get("dph_total", price_hr)
    except Exception:
        pass
    return round(elapsed_h * price_hr, 4)


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
def main():
    global VAST_KEY, HF_TOKEN

    log("=" * 60)
    log("MIGANCORE CYCLE 5 — ORPO Training (Vast.ai)")
    log(f"Dataset: {DATASET_PATH}")
    log(f"Pairs  : 877 (554 curated + 323 new domain)")
    log(f"  Curated: identity×194 + tool_use×160 + code×180 + cai×16 + distill×10")
    log(f"  New domain: umkm×67 + engineering×60 + legalitas×56 + creative_id×50 + adaptive×40")
    log(f"  C4 ROLLBACK fixes: voice×31 (targeted) + evo_aware×19 (targeted)")
    log(f"Epochs : 2 (same as Cycle 3/4)")
    log(f"LR     : 6e-7 (same as Cycle 3/4)")
    log(f"Target : {HF_REPO}")
    log(f"Goal   : voice >= 0.85 (C4: 0.739), evo-aware >= 0.80 (C4: 0.537)")
    log(f"         weighted_avg >= 0.92 (C4: 0.891), identity >= 0.90 (PRESERVE)")
    log("=" * 60)

    # Load secrets
    VAST_KEY = load_secret(VAST_KEY_PATH)
    HF_TOKEN = load_secret(HF_TOKEN_PATH)
    log(f"Vast.ai key loaded ({len(VAST_KEY)} chars)")
    log(f"HF token loaded: {HF_TOKEN[:10]}...")

    # Pre-flight: check dataset
    if not Path(DATASET_PATH).exists():
        log(f"FATAL: dataset not found at {DATASET_PATH}")
        log(f"Run export_cycle5_dataset.py first:")
        log(f"  cp /opt/ado/training/export_cycle5_dataset.py /opt/ado/data/workspace/")
        log(f"  docker compose exec -T api python /app/workspace/export_cycle5_dataset.py \\")
        log(f"    --output /app/workspace/cycle5_combined_dataset.jsonl")
        sys.exit(1)
    dataset_lines = len(Path(DATASET_PATH).read_text().splitlines())
    log(f"Dataset: {dataset_lines} pairs ✓")
    if dataset_lines < 700:
        log(f"WARNING: only {dataset_lines} pairs — expected ~877. Proceed anyway? (will continue)")

    # Pre-flight: check train script
    if not Path(TRAIN_SCRIPT).exists():
        log(f"FATAL: train_simpo_standard.py not at {TRAIN_SCRIPT}")
        sys.exit(1)
    log(f"Training script: {TRAIN_SCRIPT} ✓")

    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    # ── 1. Search offers ──────────────────────────────────────
    log("\n[1/8] Searching Vast.ai for GPU offers...")
    offers = search_offers()
    if not offers:
        log("No offers found with current criteria.")
        log("Try relaxing: MAX_PRICE_HR or MIN_GPU_RAM_MB in this script.")
        sys.exit(1)

    log(f"Found {len(offers)} offers. Top 5:")
    for o in offers[:5]:
        log(f"  #{o['id']} {o.get('gpu_name','?')} {o.get('num_gpus',1)}× "
            f"RAM={o.get('gpu_ram',0)//1000}GB "
            f"${o.get('dph_total',0):.3f}/hr "
            f"disk={o.get('disk_space',0):.0f}GB "
            f"cuda={o.get('cuda_vers','?')}")

    best = offers[0]
    offer_id = best["id"]
    price_hr = best.get("dph_total", 0.35)
    log(f"\nSelected offer #{offer_id}: {best.get('gpu_name','?')} @ ${price_hr:.3f}/hr")

    # ── 2. Create instance ────────────────────────────────────
    log("\n[2/8] Creating instance...")
    inst_id = create_instance(offer_id)
    if not inst_id:
        log("FATAL: could not create instance.")
        sys.exit(1)
    log(f"Instance {inst_id} created.")
    start_ts = time.time()

    # ── 3. Wait for SSH (Lesson #60) ─────────────────────────
    log(f"\n[3/8] Waiting for SSH (abort deadline: {MAX_BOOT_WAIT_SEC}s)...")
    deadline = start_ts + MAX_BOOT_WAIT_SEC
    ssh_host, ssh_port = wait_for_ssh(inst_id, deadline)

    if not ssh_host:
        log("No SSH within abort window. Cleaning up...")
        delete_instance(inst_id)
        elapsed_min = (time.time() - start_ts) / 60
        wasted = cost_so_far(inst_id, start_ts, price_hr)
        log(f"Cost: ${wasted:.4f} for {elapsed_min:.1f} min (Lesson #60 abort works)")
        sys.exit(2)

    # ── 3b. SSH readiness ping (Lesson #113) ─────────────────
    log("Verifying SSH is command-ready...")
    for _ping_attempt in range(12):
        rc_ping, _, _ = ssh(ssh_host, ssh_port, "echo PING_OK", timeout=15)
        if rc_ping == 0:
            log("SSH command-ready ✓")
            break
        log(f"  SSH ping attempt {_ping_attempt+1}/12 failed (rc={rc_ping}) — retrying in 5s...")
        time.sleep(5)
    else:
        log("SSH not command-ready after 60s. Aborting.")
        delete_instance(inst_id)
        sys.exit(2)

    # ── 4. Install dependencies (era-pinned, Lessons #110-111) ──
    log(f"\n[4/8] Installing ML packages on {ssh_host}:{ssh_port}...")
    install_cmd = (
        "python -m venv /root/trainenv --system-site-packages && "
        "/root/trainenv/bin/pip install -q "
        "'trl==0.9.6' 'transformers==4.44.2' 'peft==0.12.0' "
        "'accelerate==0.34.0' datasets huggingface_hub rich && "
        "/root/trainenv/bin/python -c '"
        "import trl, transformers, peft, accelerate; "
        "from trl import ORPOTrainer, ORPOConfig; "
        "print(\"DEPS OK — trl\", trl.__version__, "
        "\"transformers\", transformers.__version__, "
        "\"peft\", peft.__version__, "
        "\"accelerate\", accelerate.__version__)'"
    )
    rc, out, err = ssh(ssh_host, ssh_port, install_cmd, timeout=900)
    log(f"Install exit={rc}")
    if out.strip():
        log(f"  stdout: {out.strip()[-600:]}")
    if rc != 0:
        log(f"  stderr: {err[-400:]}")
        log("Install FAILED (rc != 0). Aborting — venv not ready for training.")
        delete_instance(inst_id)
        sys.exit(6)

    # Cost check post-install
    cost = cost_so_far(inst_id, start_ts, price_hr)
    log(f"Cost so far: ${cost:.4f}  (cap: ${COST_CAP_USD})")
    if cost > COST_CAP_USD:
        log("COST CAP EXCEEDED. Aborting.")
        delete_instance(inst_id)
        sys.exit(3)

    # ── 5. Upload dataset + script ────────────────────────────
    log("\n[5/8] Uploading dataset + training script...")

    ok1 = scp_to(DATASET_PATH, ssh_host, ssh_port, "/root/cycle5_combined_dataset.jsonl")
    ok2 = scp_to(TRAIN_SCRIPT, ssh_host, ssh_port, "/root/train_simpo_standard.py")

    if not (ok1 and ok2):
        log("Upload failed. Aborting.")
        delete_instance(inst_id)
        sys.exit(4)
    log("Upload complete ✓")

    rc, out, _ = ssh(ssh_host, ssh_port,
                     "wc -l /root/cycle5_combined_dataset.jsonl /root/train_simpo_standard.py")
    log(f"Remote file check: {out.strip()}")

    # ── 6. Train ──────────────────────────────────────────────
    log("\n[6/8] Starting ORPO training (Cycle 5: 2 epochs, LR=6e-7, 877 pairs)...")
    log(f"Args: {' '.join(SIMPO_ARGS)}")

    train_cmd = (
        f"/root/trainenv/bin/python /root/train_simpo_standard.py "
        f"{' '.join(SIMPO_ARGS)} "
        f"> /root/train_log.txt 2>&1"
    )
    log("Training started. Estimated 25-40 min for 877 pairs × 2 epochs on A40/A100...")

    train_start = time.time()
    rc, out, err = ssh(ssh_host, ssh_port, train_cmd, timeout=7200)  # 2hr hard timeout

    train_elapsed = time.time() - train_start
    log(f"Training exit={rc} | elapsed={train_elapsed:.0f}s ({train_elapsed/60:.1f}min)")

    # Always read training log for diagnosis
    _, train_log_tail, _ = ssh(ssh_host, ssh_port, "tail -200 /root/train_log.txt 2>/dev/null", timeout=30)
    if train_log_tail:
        log("Training log (tail 200):")
        for line in train_log_tail.strip().splitlines():
            log(f"  {line}")

    if rc != 0:
        log(f"Training FAILED (rc={rc})")
        log("Manual recovery commands:")
        log(f"  ssh -i {SSH_KEY} -p {ssh_port} root@{ssh_host}")
        log(f"  cat /root/train_log.txt")
        delete_instance(inst_id)
        sys.exit(5)

    log("Training COMPLETE ✓")

    cost = cost_so_far(inst_id, start_ts, price_hr)
    log(f"Cost so far: ${cost:.4f}")

    # ── 7. Download adapter + upload to HF ───────────────────
    log("\n[7/8] Downloading adapter to VPS...")

    rc, out, _ = ssh(ssh_host, ssh_port,
                     "ls -lh /root/cycle5_adapter/ 2>/dev/null | head -20")
    log(f"Adapter contents:\n{out}")

    # Lesson #132: NEVER scp -r the full adapter dir (checkpoints = 700MB+, causes timeout).
    # Only download the 2 essential files: adapter_model.safetensors + adapter_config.json
    adapter_local = f"{OUTPUT_DIR}/cycle5_adapter"
    Path(adapter_local).mkdir(parents=True, exist_ok=True)
    files_to_download = ["adapter_model.safetensors", "adapter_config.json"]
    ok = True
    for fname in files_to_download:
        file_ok = scp_from(ssh_host, ssh_port,
                           f"/root/cycle5_adapter/{fname}",
                           f"{adapter_local}/{fname}",
                           timeout=300)
        if not file_ok:
            log(f"  Failed to download {fname}")
            ok = False
        else:
            log(f"  {fname} downloaded ✓")
    if not ok:
        log("Partial adapter download. Manual SCP for missing files:")
        log(f"  scp -i {SSH_KEY} -P {ssh_port} root@{ssh_host}:/root/cycle5_adapter/adapter_model.safetensors {adapter_local}/")
    else:
        log(f"Adapter saved to {adapter_local} ✓")

        log("Uploading adapter to HuggingFace...")
        hf_cmd = (
            f"cd /root/cycle5_adapter && "
            f"pip install -q huggingface_hub && "
            f"huggingface-cli upload {HF_REPO} . "
            f"--token {HF_TOKEN} "
            f"--commit-message 'Day 64: ORPO Cycle 5 (877 pairs, 2ep, lr=6e-7, voice+evo+domain fix)' "
            f"2>&1 | tail -10"
        )
        rc_hf, out_hf, _ = ssh(ssh_host, ssh_port, hf_cmd, timeout=600)
        log(f"HF upload exit={rc_hf}: {out_hf.strip()[-300:]}")

        if rc_hf == 0:
            log(f"Adapter live at: https://huggingface.co/{HF_REPO} ✓")
        else:
            log(f"HF upload failed (rc={rc_hf}). Adapter is in {adapter_local} — upload manually later.")

    # ── 8. Cleanup (Lesson #59) ───────────────────────────────
    log("\n[8/8] Deleting instance (Lesson #59 — verify gone)...")
    deleted = delete_instance(inst_id)

    total_elapsed = time.time() - start_ts
    total_cost = round((total_elapsed / 3600) * price_hr, 4)
    log("\n" + "=" * 60)
    log("CYCLE 5 TRAINING SUMMARY")
    log("=" * 60)
    log(f"Instance     : {inst_id}")
    log(f"GPU          : {best.get('gpu_name','?')}")
    log(f"Total time   : {total_elapsed/60:.1f} min")
    log(f"Train time   : {train_elapsed/60:.1f} min")
    log(f"Cost         : ${total_cost:.4f} @ ${price_hr:.3f}/hr")
    log(f"Instance gone: {'YES ✓' if deleted else 'WARNING — check Vast.ai console!'}")
    log(f"Adapter (VPS): {adapter_local}")
    log(f"Adapter (HF) : https://huggingface.co/{HF_REPO}")
    log(f"Log          : {LOG_PATH}")
    log("=" * 60)
    log("")
    log("Next steps: GGUF conversion + Eval + PROMOTE to Ollama")
    log("")
    log("  # 1. Convert to GGUF LoRA")
    log(f"  python3 /opt/llama.cpp/convert_lora_to_gguf.py {adapter_local}/ \\")
    log(f"    --outfile {OUTPUT_DIR}/cycle5_lora.gguf --outtype f16")
    log("")
    log("  # 2. Copy into Ollama volume")
    log(f"  cp {OUTPUT_DIR}/cycle5_lora.gguf /opt/ado/data/ollama/cycle5_lora.gguf")
    log("")
    log("  # 3. Create Modelfile in Ollama volume")
    log("  echo 'FROM qwen2.5:7b-instruct-q4_K_M' > /opt/ado/data/ollama/Modelfile_cycle5")
    log("  echo 'ADAPTER /root/.ollama/cycle5_lora.gguf' >> /opt/ado/data/ollama/Modelfile_cycle5")
    log("")
    log("  # 4. Register in Ollama")
    log("  docker exec ado-ollama-1 ollama create migancore:0.5 -f /root/.ollama/Modelfile_cycle5")
    log("")
    log("  # 5. Run eval (PROMOTE gates: weighted_avg>=0.92, voice>=0.85, evo-aware>=0.80)")
    log("  cp /opt/ado/eval/run_identity_eval.py /opt/ado/data/workspace/")
    log("  docker compose exec -T api python /app/workspace/run_identity_eval.py \\")
    log("    --model migancore:0.5 --reference /app/eval/baseline_day58.json")
    log("")
    log("  # 6. If PROMOTE: update DEFAULT_MODEL → migancore:0.5 in .env → restart api")
    log("  # If ROLLBACK: investigate + more targeted pairs for failing categories")
    log("")


if __name__ == "__main__":
    main()
