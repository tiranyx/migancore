#!/usr/bin/env python3
"""
MiganCore Cycle 6 ORPO Training — Vast.ai Orchestration
=========================================================
Day 67 | 2026-05-07

Dataset  : 954 pairs (554 curated + 323 C5 domain carry-over + 77 C6 supplement)
Algorithm: ORPO (apo_zero loss) — same as Cycle 5 proven config
Target   : A40/A100 40-80GB @ ~$0.27-0.60/hr | ~25-35 min total
Output   : Tiranyx/migancore-7b-soul-v0.6

Cycle 6 OKRs (fix Cycle 5 ROLLBACK):
  weighted_avg >= 0.92   (Cycle 5: 0.8453 — 3 Ollama 500 errors cost -0.099)
  tool-use     >= 0.85   (Cycle 5: 0.7439 fix — 29 write_file confirm pairs)
  creative     >= 0.80   (Cycle 5: 0.7278 fix — 28 creative voice pairs)
  evo-aware    >= 0.80   (Cycle 5: 0.7502 fix — 20 additional pairs)
  identity     >= 0.90   (Cycle 5: 0.9376 maintain)
  voice        >= 0.85   (Cycle 5: 0.8946 maintain)

Lessons applied: #59 #60 #61 #63 #110 #111 #113 #114 #132 #137
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
DATASET_PATH  = "/opt/ado/data/workspace/cycle6_combined_dataset.jsonl"
TRAIN_SCRIPT  = "/opt/ado/training/train_simpo_standard.py"
OUTPUT_DIR    = "/opt/ado/cycle6_output"
LOG_PATH      = "/tmp/cycle6_training.log"

HF_REPO       = "Tiranyx/migancore-7b-soul-v0.6"
BASE_MODEL    = "Qwen/Qwen2.5-7B-Instruct"

MIN_GPU_RAM_MB    = 40_000
MAX_PRICE_HR      = 0.65
MIN_DISK_GB       = 65
MAX_BOOT_WAIT_SEC = 600
COST_CAP_USD      = 5.00

SIMPO_ARGS = [
    "--dataset",       "/root/cycle6_combined_dataset.jsonl",
    "--output-dir",    "/root/cycle6_adapter",
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
        "label":           "migancore-cycle6-orpo",
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
    log("MIGANCORE CYCLE 6 — ORPO Training (Vast.ai)")
    log(f"Dataset: {DATASET_PATH}")
    log("Pairs  : 954 (554 curated + 323 C5 domain + 77 C6 supplement)")
    log("Epochs : 2 | LR: 6e-7 | Loss: apo_zero | Beta: 2.5")
    log(f"Target : {HF_REPO}")
    log("Goal   : tool-use>=0.85, creative>=0.80, evo-aware>=0.80, weighted_avg>=0.92")
    log("=" * 60)

    VAST_KEY = load_secret(VAST_KEY_PATH)
    HF_TOKEN = load_secret(HF_TOKEN_PATH)
    log(f"Secrets loaded OK")

    if not Path(DATASET_PATH).exists():
        log(f"FATAL: dataset not found at {DATASET_PATH}")
        sys.exit(1)
    dataset_lines = len(Path(DATASET_PATH).read_text().splitlines())
    log(f"Dataset: {dataset_lines} pairs")
    if dataset_lines < 800:
        log(f"WARNING: only {dataset_lines} pairs (expected ~954)")

    if not Path(TRAIN_SCRIPT).exists():
        log(f"FATAL: train script not at {TRAIN_SCRIPT}")
        sys.exit(1)
    log(f"Training script OK")
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
    ok1 = scp_to(DATASET_PATH, ssh_host, ssh_port, "/root/cycle6_combined_dataset.jsonl")
    ok2 = scp_to(TRAIN_SCRIPT, ssh_host, ssh_port, "/root/train_simpo_standard.py")
    if not (ok1 and ok2):
        log("Upload failed. Aborting.")
        delete_instance(inst_id)
        sys.exit(4)
    log("Upload complete")
    rc, out, _ = ssh_run(ssh_host, ssh_port, "wc -l /root/cycle6_combined_dataset.jsonl /root/train_simpo_standard.py")
    log(f"Remote check: {out.strip()}")

    log("\n[6/8] Starting ORPO training (954 pairs, 2 epochs, LR=6e-7)...")
    train_cmd = (
        "/root/trainenv/bin/python /root/train_simpo_standard.py "
        + " ".join(SIMPO_ARGS)
        + " > /root/train_log.txt 2>&1"
    )
    log("Training started. Estimated 25-40 min...")
    train_start = time.time()
    # Lesson #143: timeout must exceed actual training time (Q RTX 8000 ~3.5hr for 954 pairs)
    try:
        rc, out, err = ssh_run(ssh_host, ssh_port, train_cmd, timeout=14400)
    except Exception as e:
        log(f"Training SSH timeout/error: {e}")
        log("Instance NOT deleted — training may still be running on Vast.ai")
        log("Recovery: bash /opt/ado/scripts/vast_recovery.sh")
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
    rc, out, _ = ssh_run(ssh_host, ssh_port, "ls -lh /root/cycle6_adapter/ 2>/dev/null | head -20")
    log(f"Adapter dir:\n{out}")

    adapter_local = f"{OUTPUT_DIR}/cycle6_adapter"
    Path(adapter_local).mkdir(parents=True, exist_ok=True)
    ok = True
    for fname in ["adapter_model.safetensors", "adapter_config.json"]:
        fok = scp_from(ssh_host, ssh_port,
                       f"/root/cycle6_adapter/{fname}",
                       f"{adapter_local}/{fname}", timeout=300)
        if not fok:
            log(f"  Failed: {fname}")
            ok = False
        else:
            log(f"  {fname} OK")

    if ok:
        log("Uploading to HuggingFace...")
        hf_cmd = (
            f"cd /root/cycle6_adapter && "
            f"pip install -q huggingface_hub && "
            f"huggingface-cli upload {HF_REPO} . "
            f"--token {HF_TOKEN} "
            f"--commit-message 'Day 67: ORPO Cycle 6 (954 pairs, 2ep, lr=6e-7, tool+creative+evo fix)' "
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
    log("CYCLE 6 TRAINING SUMMARY")
    log("=" * 60)
    log(f"GPU      : {best.get('gpu_name','?')}")
    log(f"Time     : {total_elapsed/60:.1f} min (train: {train_elapsed/60:.1f} min)")
    log(f"Cost     : ${total_cost:.4f} @ ${price_hr:.3f}/hr")
    log(f"Deleted  : {'YES' if deleted else 'WARNING - check Vast.ai!'}")
    log(f"Adapter  : {adapter_local}")
    log(f"HF repo  : https://huggingface.co/{HF_REPO}")
    log("=" * 60)
    log("")
    log("NEXT STEPS (after training):")
    log(f"  1. python3 /opt/llama.cpp/convert_lora_to_gguf.py {adapter_local}/ \\")
    log(f"       --outfile {OUTPUT_DIR}/cycle6_lora.gguf --outtype f16")
    log(f"  2. cp {OUTPUT_DIR}/cycle6_lora.gguf /opt/ado/data/ollama/cycle6_lora.gguf")
    log("  3. Create Modelfile_cycle6 and register: ollama create migancore:0.6 ...")
    log("  4. Run eval WITH --retry 3 (Lesson #137)")
    log("  5. PROMOTE if all gates pass")
    log("")


if __name__ == "__main__":
    main()
