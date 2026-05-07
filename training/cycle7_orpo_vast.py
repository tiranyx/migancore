#!/usr/bin/env python3
"""
MiganCore Cycle 7 ORPO Training — Vast.ai Orchestration
=========================================================
Day 70 | 2026-05-08

CYCLE 7 PHILOSOPHY — VOICE FIRST, ZERO DOMAIN PAIRS:
Root cause of Cycle 6 ROLLBACK: 300 domain pairs diluted voice (0.705).
Rule: EXCLUDE all domain/engineering/UMKM/legalitas/adaptive pairs this cycle.

Dataset  : 508 pairs (~210 pillar + ~298 targeted cycle7)
           - identity_anchor_v2:*  194  (pillar — WHO Migan is)
           - cai_pipeline           18  (authentic real convs)
           - voice_anchor_v1:c7     80  (casual voice recovery)
           - voice_style_v1:c7      40  (style/tagline voice)
           - tool_use_v2:c7        107  (write+image confirm patterns)
           - creative_v3:c7         39  (creative voice anchored)
           - honesty_v1:c7          40  (epistemic humility)

Algorithm: ORPO (apo_zero loss) — proven Cycle 3/4/5 config
Target   : A40/A100 40-80GB @ ~$0.27-0.60/hr | ~15-25 min (508 pairs)
Output   : Tiranyx/migancore-7b-soul-v0.7

Gate targets (PROMOTE requires ALL):
  weighted_avg >= 0.92   (Cycle 6 ROLLBACK: 0.891 — need +0.029)
  voice        >= 0.85   (Cycle 6 ROLLBACK: 0.705 — need +0.145 ← HARDEST)
  tool-use     >= 0.85   (Cycle 6 ROLLBACK: 0.733 — need +0.117)
  identity     >= 0.90   (Cycle 6: 0.9334 — already passing, maintain)
  evo-aware    >= 0.80   (Cycle 6: 0.8856 — already passing, not trained this cycle)
  creative     >= 0.80   (Cycle 6: 0.771  — need +0.029)

Lessons applied: #59 #60 #61 #63 #110 #111 #113 #114 #129 #130 #132 #137 #143
"""

import os
import sys
import json
import time
import subprocess
import requests
from pathlib import Path
from datetime import datetime, timezone

VAST_KEY_PATH = "/opt/secrets/migancore/vastai_api_key"
HF_TOKEN_PATH = "/opt/secrets/migancore/hf_token"
DATASET_PATH  = "/opt/ado/data/workspace/cycle7_dataset.jsonl"
TRAIN_SCRIPT  = "/opt/ado/training/train_simpo_standard.py"
OUTPUT_DIR    = "/opt/ado/cycle7_output"
LOG_PATH      = "/tmp/cycle7_training.log"

HF_REPO       = "Tiranyx/migancore-7b-soul-v0.7"
BASE_MODEL    = "Qwen/Qwen2.5-7B-Instruct"

MIN_GPU_RAM_MB    = 40_000
MAX_PRICE_HR      = 0.65
MIN_DISK_GB       = 65
MAX_BOOT_WAIT_SEC = 600
COST_CAP_USD      = 5.00

# Cycle 7: same proven ORPO hyperparams as Cycle 5 (which hit weighted_avg 0.8453 on smaller dataset)
# Cycle 6 ROLLBACK was content issue (domain pairs), not hyperparam issue — keep same config
# Lesson #129: voice=30% weight dominates gate — fix high-weight first (done: 80+40=120 voice pairs)
# Lesson #130: targeted 50 pairs → +0.134 creative — proven pattern, 120 voice pairs should move needle
SIMPO_ARGS = [
    "--dataset",       "/root/cycle7_dataset.jsonl",
    "--output-dir",    "/root/cycle7_adapter",
    "--base-model",    BASE_MODEL,
    "--epochs",        "2",
    "--learning-rate", "6e-7",
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
    url = f"{VAST_API}{path}"
    params = kwargs.pop("params", {})
    params["api_key"] = VAST_KEY
    resp = getattr(requests, method)(url, params=params, timeout=30, **kwargs)
    try:
        data = resp.json()
    except Exception:
        data = {}
    if resp.status_code not in (200, 201):
        log(f"Vast API {method.upper()} {path} -> {resp.status_code}: {resp.text[:200]}")
        return {}
    return data


def search_offers() -> list:
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


def create_instance(offer_id: int):
    payload = {
        "client_id":       "me",
        "image":           "pytorch/pytorch:2.5.1-cuda12.4-cudnn9-devel",
        "disk":            MIN_DISK_GB,
        "runtype":         "ssh",
        "use_jupyter_lab": False,
        "label":           "migancore-cycle7-orpo",
        "ssh_key_ids":     [808896],
    }
    result = vast("put", f"/asks/{offer_id}/", json=payload)
    inst_id = (result.get("new_contract") or result.get("contract_id") or result.get("id"))
    if not inst_id:
        log(f"create_instance: no id in response: {result}")
    return inst_id


def get_instance(inst_id: int) -> dict:
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
    log(f"Deleting instance {inst_id}...")
    vast("delete", f"/instances/{inst_id}/")
    time.sleep(5)
    remaining = get_instance(inst_id)
    status = remaining.get("actual_status", "")
    if remaining and status not in ("exited", "deleted", ""):
        log(f"WARNING: instance still present (status={status}). Retrying...")
        time.sleep(10)
        vast("delete", f"/instances/{inst_id}/")
        time.sleep(10)
        remaining2 = get_instance(inst_id)
        status2 = remaining2.get("actual_status", "")
        if remaining2 and status2 not in ("exited", "deleted", ""):
            log(f"ERROR: instance still alive (status={status2}) after 2 deletes!")
            return False
    log(f"Instance {inst_id} CONFIRMED DELETED (Lesson #59)")
    return True


def wait_for_ssh(inst_id: int, deadline: float):
    log(f"Waiting for SSH (max {int(deadline - time.time())}s)...")
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


def ssh_run(host: str, port: int, cmd: str, timeout: int = 600):
    result = subprocess.run(
        ["ssh", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no",
         "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
         "-p", str(port), f"root@{host}", cmd],
        capture_output=True, text=True, timeout=timeout
    )
    return result.returncode, result.stdout, result.stderr


def scp_to(local: str, host: str, port: int, remote: str, timeout: int = 300) -> bool:
    result = subprocess.run(
        ["scp", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no",
         "-P", str(port), local, f"root@{host}:{remote}"],
        capture_output=True, text=True, timeout=timeout
    )
    if result.returncode != 0:
        log(f"SCP failed: {result.stderr[:200]}")
        return False
    return True


def scp_from(host: str, port: int, remote: str, local: str, timeout: int = 600) -> bool:
    """NO -r flag (Lesson #132)."""
    Path(local).parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["scp", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no",
         "-P", str(port), f"root@{host}:{remote}", local],
        capture_output=True, text=True, timeout=timeout
    )
    if result.returncode != 0:
        log(f"SCP-from failed: {result.stderr[:300]}")
        return False
    return True


def cost_so_far(inst_id: int, start_ts: float, price_hr: float = 0.35) -> float:
    elapsed_h = (time.time() - start_ts) / 3600
    try:
        inst = get_instance(inst_id)
        price_hr = inst.get("dph_total", price_hr)
    except Exception:
        pass
    return round(elapsed_h * price_hr, 4)


def main():
    global VAST_KEY, HF_TOKEN

    log("=" * 60)
    log("MIGANCORE CYCLE 7 — ORPO Training (Vast.ai)")
    log("PHILOSOPHY: Voice First, Zero Domain Pairs")
    log(f"Dataset: {DATASET_PATH}")
    log("Pairs  : 508 (194 identity pillar + 18 cai + 296 cycle7 targeted)")
    log("Epochs : 2 | LR: 6e-7 | Loss: apo_zero | Beta: 2.5")
    log(f"Target : {HF_REPO}")
    log("Gates  : voice>=0.85, tool-use>=0.85, weighted_avg>=0.92")
    log("=" * 60)

    VAST_KEY = load_secret(VAST_KEY_PATH)
    HF_TOKEN = load_secret(HF_TOKEN_PATH)
    log("Secrets loaded OK")

    if not Path(DATASET_PATH).exists():
        log(f"FATAL: dataset not found at {DATASET_PATH}")
        log(f"Run: docker compose exec -T api python /app/workspace/export_cycle7_dataset.py --output /app/workspace/cycle7_dataset.jsonl")
        sys.exit(1)
    dataset_lines = len(Path(DATASET_PATH).read_text().splitlines())
    log(f"Dataset: {dataset_lines} pairs")
    if dataset_lines < 400:
        log(f"WARNING: only {dataset_lines} pairs (expected ~508)")
    elif dataset_lines < 500:
        log(f"WARNING: only {dataset_lines} pairs (some cycle7 pairs may be missing)")

    if not Path(TRAIN_SCRIPT).exists():
        log(f"FATAL: train script not at {TRAIN_SCRIPT}")
        sys.exit(1)
    log("Training script OK")
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    log("\n[1/8] Searching Vast.ai offers...")
    offers = search_offers()
    if not offers:
        log("No offers found. Relax MAX_PRICE_HR or MIN_GPU_RAM_MB.")
        sys.exit(1)
    log(f"Found {len(offers)} offers. Top 5:")
    for o in offers[:5]:
        log(f"  #{o['id']} {o.get('gpu_name','?')} RAM={o.get('gpu_ram',0)//1000}GB ${o.get('dph_total',0):.3f}/hr")

    best = offers[0]
    offer_id = best["id"]
    price_hr = best.get("dph_total", 0.35)
    log(f"Selected: #{offer_id} {best.get('gpu_name','?')} @ ${price_hr:.3f}/hr")

    log("\n[2/8] Creating instance...")
    inst_id = create_instance(offer_id)
    if not inst_id:
        log("FATAL: could not create instance.")
        sys.exit(1)
    log(f"Instance {inst_id} created.")
    start_ts = time.time()

    log(f"\n[3/8] Waiting for SSH (abort in {MAX_BOOT_WAIT_SEC}s)...")
    ssh_host, ssh_port = wait_for_ssh(inst_id, start_ts + MAX_BOOT_WAIT_SEC)

    if not ssh_host:
        delete_instance(inst_id)
        wasted = cost_so_far(inst_id, start_ts, price_hr)
        log(f"Aborted. Cost: ${wasted:.4f} (Lesson #60)")
        sys.exit(2)

    log("Verifying SSH command-ready (Lesson #113)...")
    for attempt in range(12):
        rc, _, _ = ssh_run(ssh_host, ssh_port, "echo PING_OK", timeout=15)
        if rc == 0:
            log("SSH OK")
            break
        log(f"  Ping {attempt+1}/12 failed, retrying in 5s...")
        time.sleep(5)
    else:
        log("SSH not ready. Aborting.")
        delete_instance(inst_id)
        sys.exit(2)

    log(f"\n[4/8] Installing ML packages (era-pinned, Lessons #110-111)...")
    install_cmd = (
        "python -m venv /root/trainenv --system-site-packages && "
        "/root/trainenv/bin/pip install -q "
        "trl==0.9.6 transformers==4.44.2 peft==0.12.0 "
        "accelerate==0.34.0 datasets huggingface_hub rich && "
        '/root/trainenv/bin/python -c "import trl, transformers, peft, accelerate; '
        'from trl import ORPOTrainer, ORPOConfig; '
        'print(chr(68)+chr(69)+chr(80)+chr(83)+chr(32)+chr(79)+chr(75))"'
    )
    rc, out, err = ssh_run(ssh_host, ssh_port, install_cmd, timeout=900)
    log(f"Install exit={rc} | {out.strip()[-400:]}")
    if rc != 0:
        log(f"STDERR: {err[-300:]}")
        log("Install FAILED. Aborting.")
        delete_instance(inst_id)
        sys.exit(6)

    cost = cost_so_far(inst_id, start_ts, price_hr)
    log(f"Cost so far: ${cost:.4f}")
    if cost > COST_CAP_USD:
        log("COST CAP hit. Aborting.")
        delete_instance(inst_id)
        sys.exit(3)

    log("\n[5/8] Uploading dataset + training script...")
    ok1 = scp_to(DATASET_PATH, ssh_host, ssh_port, "/root/cycle7_dataset.jsonl")
    ok2 = scp_to(TRAIN_SCRIPT, ssh_host, ssh_port, "/root/train_simpo_standard.py")
    if not (ok1 and ok2):
        log("Upload failed. Aborting.")
        delete_instance(inst_id)
        sys.exit(4)
    log("Upload complete")
    rc, out, _ = ssh_run(ssh_host, ssh_port, "wc -l /root/cycle7_dataset.jsonl /root/train_simpo_standard.py")
    log(f"Remote check: {out.strip()}")

    log("\n[6/8] Starting ORPO training (508 pairs, 2 epochs, LR=6e-7)...")
    train_cmd = (
        "/root/trainenv/bin/python /root/train_simpo_standard.py "
        + " ".join(SIMPO_ARGS)
        + " > /root/train_log.txt 2>&1"
    )
    log("Training started. Estimated 15-25 min (508 pairs, A40/A100)...")
    train_start = time.time()
    # Lesson #143: timeout must exceed actual training time
    # 508 pairs × 2 epochs ÷ (batch_size=2, grad_accum=8) ≈ 63 steps × ~15s/step ≈ ~15 min
    # Add buffer for install + safety margin → 10800s (3hr) cap
    try:
        rc, out, err = ssh_run(ssh_host, ssh_port, train_cmd, timeout=10800)
    except Exception as e:
        log(f"Training SSH timeout/error: {e}")
        log("Instance NOT deleted — training may still be running on Vast.ai")
        log(f"Recovery: ssh -i {SSH_KEY} -p {ssh_port} root@{ssh_host}")
        log("  tail -f /root/train_log.txt")
        sys.exit(7)
    train_elapsed = time.time() - train_start
    log(f"Training exit={rc} | elapsed={train_elapsed:.0f}s ({train_elapsed/60:.1f}min)")

    _, train_tail, _ = ssh_run(ssh_host, ssh_port, "tail -200 /root/train_log.txt 2>/dev/null", timeout=30)
    if train_tail:
        log("Training log (tail 200):")
        for line in train_tail.strip().splitlines():
            log(f"  {line}")

    if rc != 0:
        log(f"Training FAILED (rc={rc}). Manual recovery:")
        log(f"  ssh -i {SSH_KEY} -p {ssh_port} root@{ssh_host}")
        log("  cat /root/train_log.txt")
        delete_instance(inst_id)
        sys.exit(5)
    log("Training COMPLETE")

    log("\n[7/8] Downloading adapter (Lesson #132 — no -r flag)...")
    rc, out, _ = ssh_run(ssh_host, ssh_port, "ls -lh /root/cycle7_adapter/ 2>/dev/null | head -20")
    log(f"Adapter dir:\n{out}")

    adapter_local = f"{OUTPUT_DIR}/cycle7_adapter"
    Path(adapter_local).mkdir(parents=True, exist_ok=True)
    ok = True
    for fname in ["adapter_model.safetensors", "adapter_config.json"]:
        fok = scp_from(ssh_host, ssh_port,
                       f"/root/cycle7_adapter/{fname}",
                       f"{adapter_local}/{fname}", timeout=300)
        if not fok:
            log(f"  Failed: {fname}")
            ok = False
        else:
            log(f"  {fname} OK")

    if ok:
        log("Uploading to HuggingFace...")
        hf_cmd = (
            f"cd /root/cycle7_adapter && "
            f"/root/trainenv/bin/pip install -q huggingface_hub && "
            f"/root/trainenv/bin/huggingface-cli upload {HF_REPO} . "
            f"--token {HF_TOKEN} "
            f"--commit-message 'Day 70: ORPO Cycle 7 voice-first (508 pairs, 2ep, lr=6e-7, zero domain)' "
            f"2>&1 | tail -10"
        )
        rc_hf, out_hf, _ = ssh_run(ssh_host, ssh_port, hf_cmd, timeout=600)
        log(f"HF upload exit={rc_hf}: {out_hf.strip()[-300:]}")
        if rc_hf == 0:
            log(f"Adapter live: https://huggingface.co/{HF_REPO}")

    log("\n[8/8] Deleting instance (Lesson #59)...")
    deleted = delete_instance(inst_id)
    total_elapsed = time.time() - start_ts
    total_cost = round((total_elapsed / 3600) * price_hr, 4)

    log("\n" + "=" * 60)
    log("CYCLE 7 TRAINING SUMMARY")
    log("=" * 60)
    log(f"GPU      : {best.get('gpu_name','?')}")
    log(f"Time     : {total_elapsed/60:.1f} min (train: {train_elapsed/60:.1f} min)")
    log(f"Cost     : ${total_cost:.4f} @ ${price_hr:.3f}/hr")
    log(f"Deleted  : {'YES' if deleted else 'WARNING - check Vast.ai!'}")
    log(f"Adapter  : {adapter_local}")
    log(f"HF repo  : https://huggingface.co/{HF_REPO}")
    log("=" * 60)
    log("")
    log("NEXT STEPS (run on VPS after training):")
    log(f"  1. Convert to GGUF:")
    log(f"     python3 /opt/llama.cpp/convert_lora_to_gguf.py {adapter_local}/ \\")
    log(f"       --outfile {OUTPUT_DIR}/cycle7_lora.gguf --outtype f16")
    log(f"  2. Copy GGUF:")
    log(f"     cp {OUTPUT_DIR}/cycle7_lora.gguf /opt/ado/data/ollama/cycle7_lora.gguf")
    log("  3. Create Modelfile and register (Lesson #137 — use --retry 3 in eval):")
    log("     ollama create migancore:0.7 -f /opt/ado/training/Modelfile_cycle7")
    log("  4. Run identity eval WITH --retry 3:")
    log("     docker compose exec -T api python /app/eval/run_identity_eval.py \\")
    log("       --mode eval --model-tag migancore-7b-soul-cycle7")
    log("  5. Gates: weighted_avg>=0.92 AND voice>=0.85 AND tool-use>=0.85")
    log("  6. If PROMOTE: ollama cp migancore:0.7 migancore:latest && restart")
    log("")


if __name__ == "__main__":
    main()
