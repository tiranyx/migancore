#!/usr/bin/env python3
"""
MiganCore Cycle 2 SimPO Training — Vast.ai Orchestration
=========================================================
Day 59 | 2026-05-06

Dataset  : 613 pairs (identity 194 + tool-use 200 + code 200 + cai 16 + distill 10)
Algorithm: SimPO — apo_zero loss, beta=2.5, gamma=1.0, lr=5e-7
Target   : A100 PCIE 40GB @ ~$0.27-0.40/hr | ~90-120 min total
Output   : Tiranyx/migancore-7b-soul-v0.2 (SimPO Cycle 2 adapter)

Lessons applied
  #59 — verify instance DELETE (not just 204 — list again after)
  #60 — 10-min auto-abort if no SSH (was 5-min for smoke, 10-min proven for prod)
  #61 — cost telemetry per-minute logged to file
  #62 — never >2hr same vendor same fail mode; fall-through: print manual SCP cmds
  #63 — Vast.ai API key stored in /opt/secrets/migancore/vastai_api_key
  #66 — use base PyTorch image (install unsloth from pip); runtime images pull fast
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
DATASET_PATH  = "/opt/ado/data/workspace/cycle2_dataset.jsonl"
TRAIN_SCRIPT  = "/opt/ado/training/train_simpo_standard.py"  # no-unsloth version (Lesson #103)
OUTPUT_DIR    = "/opt/ado/cycle2_output"
LOG_PATH      = "/tmp/cycle2_training.log"

HF_REPO       = "Tiranyx/migancore-7b-soul-v0.2"
BASE_MODEL    = "Qwen/Qwen2.5-7B-Instruct"  # official — unsloth handles quantization

# GPU requirements
MIN_GPU_RAM_MB = 40_000   # 40 GB
MAX_PRICE_HR   = 0.60     # USD hard cap per hour
MIN_DISK_GB    = 65       # base 15GB + training overhead

# Timing (Lesson #60, #62)
MAX_BOOT_WAIT_SEC = 600   # 10 min — abort if SSH not up
COST_CAP_USD      = 4.00  # hard stop

# Training hyperparams (train_simpo.py CLI)
SIMPO_ARGS = [
    "--dataset",       "/root/cycle2_dataset.jsonl",
    "--output-dir",    "/root/cycle2_adapter",
    "--base-model",    BASE_MODEL,
    "--epochs",        "1",
    "--learning-rate", "5e-7",
    "--simpo-beta",    "2.5",
    "--simpo-gamma",   "1.0",
    "--loss-type",     "apo_zero",
    "--lora-r",        "16",
    "--lora-alpha",    "16",
    "--batch-size",    "2",
    "--grad-accum",    "8",
    "--max-seq-length","2048",
    # --padding-free and --use-liger-kernel removed: liger-kernel conflicts with unsloth.
    # apo_zero loss + lr=5e-7 is the key optimization; liger is optional speed-up only.
]

VAST_API = "https://console.vast.ai/api/v0"
SSH_KEY  = "/root/.ssh/id_ed25519"

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────
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
    """Find cheapest A100-class offers meeting our requirements."""
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
        # Lesson #108: pytorch:2.4.0 (Aug 2024) is incompatible with modern TRL/transformers.
        # TRL 1.x+ (2026) requires PyTorch>=2.5 for torch.library.custom_op API.
        # Use 2.5.1 image — fixes moe.py infer_schema error, supports current packages.
        "image":           "pytorch/pytorch:2.5.1-cuda12.4-cudnn9-devel",
        "disk":            MIN_DISK_GB,
        "runtype":         "ssh",
        "use_jupyter_lab": False,
        "label":           "migancore-cycle2-simpo",
        "ssh_key_ids":     [808896],  # VPS id_ed25519 registered in Vast.ai account
    }
    result = vast("put", f"/asks/{offer_id}/", json=payload)
    # Vast.ai returns new_contract (older API) or contract_id / id
    inst_id = (result.get("new_contract") or
               result.get("contract_id") or
               result.get("id"))
    if not inst_id:
        log(f"create_instance: no id in response: {result}")
    return inst_id


def get_instance(inst_id: int) -> dict:
    """GET /instances/{id}/ returns {"instances": <dict>} (single instance as dict, NOT list)."""
    result = vast("get", f"/instances/{inst_id}/")
    if not result:
        return {}
    instances = result.get("instances", result)
    # Vast.ai: single-instance endpoint returns instances as a dict
    if isinstance(instances, dict):
        return instances
    # List format (GET /instances/ all-list endpoint — shouldn't happen here but handle it)
    if isinstance(instances, list):
        for inst in instances:
            if isinstance(inst, dict) and inst.get("id") == inst_id:
                return inst
    return {}


def delete_instance(inst_id: int) -> bool:
    """Delete + verify gone (Lesson #59). GET /instances/ returns {"instances": [list]}."""
    log(f"Deleting instance {inst_id}...")
    vast("delete", f"/instances/{inst_id}/")
    time.sleep(5)
    # Verify: get single instance — if 404/empty it's gone
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
         "-o", f"ConnectTimeout=15",
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
    Path(local).parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["scp", "-r",
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


def cost_so_far(inst_id: int, start_ts: float) -> float:
    """Rough cost estimate: elapsed_hours × price_per_hour."""
    elapsed_h = (time.time() - start_ts) / 3600
    inst = get_instance(inst_id)
    dph = inst.get("dph_total", 0.30)
    return round(elapsed_h * dph, 4)


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
def main():
    global VAST_KEY, HF_TOKEN

    log("=" * 60)
    log("MIGANCORE CYCLE 2 — SimPO Training (Vast.ai)")
    log(f"Dataset: {DATASET_PATH}")
    log(f"Pairs  : 613 (identity 194 + tool 200 + code 200 + cai 16 + distill 10)")
    log(f"Target : {HF_REPO}")
    log("=" * 60)

    # Load secrets
    VAST_KEY = load_secret(VAST_KEY_PATH)
    HF_TOKEN = load_secret(HF_TOKEN_PATH)
    log(f"Vast.ai key loaded ({len(VAST_KEY)} chars)")
    log(f"HF token loaded: {HF_TOKEN[:10]}...")

    # Pre-flight
    if not Path(DATASET_PATH).exists():
        log(f"FATAL: dataset not found at {DATASET_PATH}")
        sys.exit(1)
    dataset_lines = len(Path(DATASET_PATH).read_text().splitlines())
    log(f"Dataset: {dataset_lines} pairs ✓")

    if not Path(TRAIN_SCRIPT).exists():
        log(f"FATAL: train_simpo_standard.py not at {TRAIN_SCRIPT}")
        sys.exit(1)
    log(f"Training script: {TRAIN_SCRIPT} ✓ (no-unsloth standard version)")

    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    # ── 1. Search offers ──────────────────────────────────────
    log("\n[1/8] Searching Vast.ai for GPU offers...")
    offers = search_offers()
    if not offers:
        log("No offers found with current criteria. Try relaxing GPU RAM or price cap.")
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
    price_hr = best.get("dph_total", 0.30)
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
        wasted = cost_so_far(inst_id, start_ts)
        log(f"Cost: ${wasted:.4f} for {elapsed_min:.1f} min (Lesson #60 abort works)")
        sys.exit(2)

    # ── 4. Install dependencies ───────────────────────────────
    log(f"\n[4/8] Installing ML packages on {ssh_host}:{ssh_port}...")
    # Lesson #108: pytorch:2.4.0 image incompatible with TRL 1.x+. Fixed: use 2.5.1.
    # Lesson #109: pytorch:2.5.1 conda base has OLD TRL pre-installed.
    #   `pip install --upgrade trl` installs new TRL to user-site (~/.local) BUT
    #   Python sys.path puts conda site-packages BEFORE user site-packages on this
    #   image, so old conda TRL wins at import time regardless of the pip upgrade.
    # Fix: venv --system-site-packages inherits conda torch/CUDA, but venv
    #   site-packages (/root/trainenv/lib/python3.11/site-packages/) comes FIRST
    #   in sys.path, so newly installed TRL always wins over old conda TRL.
    #   With PyTorch 2.5.1 there is no transformers 4.47+ compat issue, so no
    #   version pins needed — plain `pip install trl` gets latest 1.x+.
    # Lesson #110: SimPOTrainer never existed in TRL 0.9.6 OR 0.29.1.
    # TRL 0.9.6 (Aug 2024): CPOTrainer with loss_type="simpo" = CPO-SimPO ≡ SimPO.
    # TRL 0.29.1 (latest 0.x 2026): DPOTrainer/GRPOTrainer/KTOTrainer — no SimPO.
    # Solution: pin trl==0.9.6, use CPOTrainer (train_simpo_standard.py 3-tier fallback).
    # Lesson #111: peft>=0.13 added DTensor LoRA (torch.distributed.tensor) not in conda
    # pytorch:2.5.1. Pin peft==0.12.0 (Sep 2024) to avoid AttributeError: module
    # 'torch.distributed' has no attribute 'tensor' during LoRA injection.
    # Era-consistent: trl==0.9.6 + transformers==4.44.2 + peft==0.12.0 + accelerate==0.34.0
    install_cmd = (
        "python -m venv /root/trainenv --system-site-packages && "
        "/root/trainenv/bin/pip install -q "
        "'trl==0.9.6' 'transformers==4.44.2' 'peft==0.12.0' "
        "'accelerate==0.34.0' datasets huggingface_hub rich && "
        # All pinned to Sep-Oct 2024 era: compatible with each other + PyTorch 2.5.1
        # peft>=0.13 added DTensor LoRA that uses torch.distributed.tensor not
        # available in conda pytorch:2.5.1 image (Lesson #111)
        # Verify: TRL 0.9.6 has CPOTrainer (not SimPOTrainer — that was removed).
        # train_simpo_standard.py handles 3-tier fallback: simpo→cpo_simpo→orpo
        "/root/trainenv/bin/python -c '"
        "import trl, transformers, peft, accelerate; "
        "from trl import CPOTrainer, CPOConfig; "
        "print(\"DEPS OK — trl\", trl.__version__, "
        "\"transformers\", transformers.__version__, "
        "\"peft\", peft.__version__, "
        "\"accelerate\", accelerate.__version__)'"
    )
    rc, out, err = ssh(ssh_host, ssh_port, install_cmd, timeout=900)
    log(f"Install exit={rc}")
    if out.strip():
        log(f"  stdout: {out.strip()[-600:]}")  # 600 chars to capture TRL diagnostic
    if rc != 0:
        log(f"  stderr: {err[-400:]}")
        # Non-fatal — continue and see if unsloth is available
        log("Install had errors — continuing (unsloth may be partial)")

    # Cost check
    cost = cost_so_far(inst_id, start_ts)
    log(f"Cost so far: ${cost:.4f}  (cap: ${COST_CAP_USD})")
    if cost > COST_CAP_USD:
        log("COST CAP EXCEEDED. Aborting.")
        delete_instance(inst_id)
        sys.exit(3)

    # ── 5. Upload dataset + script ────────────────────────────
    log("\n[5/8] Uploading dataset + training script...")

    ok1 = scp_to(DATASET_PATH, ssh_host, ssh_port, "/root/cycle2_dataset.jsonl")
    ok2 = scp_to(TRAIN_SCRIPT, ssh_host, ssh_port, "/root/train_simpo_standard.py")

    if not (ok1 and ok2):
        log("Upload failed. Aborting.")
        delete_instance(inst_id)
        sys.exit(4)
    log("Upload complete ✓")

    # Verify upload
    rc, out, _ = ssh(ssh_host, ssh_port, "wc -l /root/cycle2_dataset.jsonl /root/train_simpo_standard.py")
    log(f"Remote file check: {out.strip()}")

    # ── 6. Train ──────────────────────────────────────────────
    log("\n[6/8] Starting SimPO training...")
    log(f"Args: {' '.join(SIMPO_ARGS)}")

    # Use trainenv python (has new TRL from venv install) — NOT conda base python.
    # Redirect output to file (no tee pipe) to preserve real exit code — Lesson #102.
    train_cmd = f"/root/trainenv/bin/python /root/train_simpo_standard.py {' '.join(SIMPO_ARGS)} > /root/train_log.txt 2>&1"
    log("Training started. Estimated 15-45 min for 613 pairs × 1 epoch on A100...")

    train_start = time.time()
    rc, out, err = ssh(ssh_host, ssh_port, train_cmd, timeout=7200)  # 2hr hard timeout

    train_elapsed = time.time() - train_start
    log(f"Training exit={rc} | elapsed={train_elapsed:.0f}s ({train_elapsed/60:.1f}min)")

    # Read training log (output was redirected to file, not in stdout)
    _, train_log_tail, _ = ssh(ssh_host, ssh_port, "tail -30 /root/train_log.txt 2>/dev/null", timeout=30)
    if train_log_tail:
        log("Training log (tail 30):")
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

    # Cost check again
    cost = cost_so_far(inst_id, start_ts)
    log(f"Cost so far: ${cost:.4f}")

    # ── 7. Download adapter + upload to HF ───────────────────
    log("\n[7/8] Downloading adapter to VPS...")

    # Check adapter exists on instance
    rc, out, _ = ssh(ssh_host, ssh_port,
                     "ls -lh /root/cycle2_adapter/ 2>/dev/null | head -20")
    log(f"Adapter contents:\n{out}")

    adapter_local = f"{OUTPUT_DIR}/cycle2_adapter"
    ok = scp_from(ssh_host, ssh_port, "/root/cycle2_adapter", adapter_local, timeout=600)
    if not ok:
        log("Adapter download failed. Manual SCP:")
        log(f"  scp -i {SSH_KEY} -r -P {ssh_port} root@{ssh_host}:/root/cycle2_adapter {adapter_local}")
    else:
        log(f"Adapter saved to {adapter_local} ✓")

        # Upload adapter to HuggingFace
        log("Uploading adapter to HuggingFace...")
        hf_cmd = (
            f"cd /root/cycle2_adapter && "
            f"pip install -q huggingface_hub && "
            f"huggingface-cli upload {HF_REPO} . "
            f"--token {HF_TOKEN} "
            f"--commit-message 'Day 59: SimPO Cycle 2 adapter (613 pairs, apo_zero, lr=5e-7)' "
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

    # Final cost telemetry (Lesson #61)
    total_elapsed = time.time() - start_ts
    total_cost = round((total_elapsed / 3600) * price_hr, 4)
    log("\n" + "=" * 60)
    log("CYCLE 2 TRAINING SUMMARY")
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
    log("\nNext step: run eval vs baseline_day58.json")
    log("  docker exec ado-api python eval/run_identity_eval.py --mode eval "
        "--reference /app/eval/baseline_day58.json "
        "--adapter-path /app/workspace/cycle2_adapter")
    log("")


if __name__ == "__main__":
    main()
