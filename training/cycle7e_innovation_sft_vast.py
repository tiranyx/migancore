#!/usr/bin/env python3
"""
MiganCore Cycle 7e Innovation Engine SFT — Vast.ai Orchestration
=================================================================
Day 73+ | 2026-05-14 | M1.7 Innovation Engine Phase 2

PHASE 1 (DONE): runtime prompt injection in chat.py [INNOVATION ENGINE - MANDATORY].
                Brain applies OBSERVE→SYNTHESIZE→DIVERGE→RANK→PROTOTYPE→TEST
                →POLISH→TOOLIFY→LEARN loop via prompt. 4/4 QA probe PASS.

PHASE 2 (THIS): teach the doctrine INTO the weights via SFT, so the loop
                survives prompt edits AND frees prompt tokens for content.

STRATEGY (per Lesson #174 no-dilution + Lesson #175 SFT-for-style):
  - Own cycle (NOT bundled with cycle7d voice SFT) — preserves signal density
  - 200 SFT pairs, 5 families × 40 = 100% signal density
  - LR=5e-7 (lower than ORPO 1.2e-6 to avoid catastrophic forgetting)
  - 5 epochs × 200 pairs ÷ batch 16 = ~63 gradient steps
  - LoRA r=8 (focused adaptation, matches cycle7d design)
  - Base: Qwen2.5-7B-Instruct (fresh — innovation is orthogonal to voice/identity)

LESSONS APPLIED:
  #59 verify DELETE not trust 204 | #60 abort < 5min boot wait
  #62 never >2hr same vendor same fail | #110 Q5 baseline alignment
  #113 SSH command-ready ping retry | #129 voice 30% weight dominates gate
  #170 baseline ref must match training target | #173 HF roundtrip not SCP
  #174 no diversity dilution | #175 SFT-for-style not ORPO

DATASET     : /opt/ado/data/workspace/cycle7e_innovation_sft_dataset.jsonl (200 pairs)
ALGORITHM   : SFT (TRL SFTTrainer)
TRAINER     : /opt/ado/training/train_sft_simple.py
TARGET GPU  : A40 or RTX A6000 40GB+ @ ~$0.30-0.65/hr | ~10-15 min
COST PROJ.  : $0.20 success / $0.04 abort (Lesson #60)
OUTPUT REPO : Tiranyx/migancore-7b-soul-v0.7e

EVAL GATES (Codex B3-inspired, innovation-specific):
  PROMOTE      : innovation >= 0.80 AND identity >= 0.90 AND voice >= 0.80
                 AND weighted_avg >= 0.85
  CONDITIONAL  : weighted_avg >= 0.82 AND no category < 0.70
  ROLLBACK     : else — fallback to migancore:0.7c

USAGE:
  Dry-run (Gate 1 — no money spent):
      python3 cycle7e_innovation_sft_vast.py --dry-run
  Live launch (Gate 2 — explicit Fahmi GO, ~$0.30):
      python3 cycle7e_innovation_sft_vast.py --launch
"""

import os
import sys
import json
import time
import subprocess
import requests
from pathlib import Path
from datetime import datetime, timezone

# === Cycle 7e config ===
VAST_KEY_PATH = "/opt/secrets/migancore/vastai_api_key"
HF_TOKEN_PATH = "/opt/secrets/migancore/hf_token"
DATASET_PATH  = "/opt/ado/data/workspace/cycle7e_innovation_sft_dataset.jsonl"
TRAIN_SCRIPT  = "/opt/ado/training/train_sft_simple.py"
OUTPUT_DIR    = "/opt/ado/cycle7e_output"
LOG_PATH      = "/tmp/cycle7e_training.log"

HF_REPO       = "Tiranyx/migancore-7b-soul-v0.7e"
BASE_MODEL    = "Qwen/Qwen2.5-7B-Instruct"

MIN_GPU_RAM_MB    = 40_000
MAX_PRICE_HR      = 0.65
MIN_DISK_GB       = 65
MAX_BOOT_WAIT_SEC = 600     # Lesson #60: abort 10 min boot
COST_CAP_USD      = 3.00    # Tighter cap than C7c (smaller dataset, faster train)

# SFT hyperparams — matches cycle7d guidance + LoRA r=8 focused
SFT_ARGS = [
    "--dataset",       "/root/cycle7e_innovation_sft_dataset.jsonl",
    "--output-dir",    "/root/cycle7e_adapter",
    "--base-model",    BASE_MODEL,
    "--epochs",        "5",
    "--learning-rate", "5e-7",
    "--lora-r",        "8",
    "--lora-alpha",    "16",
    "--batch-size",    "2",
    "--grad-accum",    "8",
    "--max-seq-length", "2048",
]

VAST_API = "https://console.vast.ai/api/v0"
SSH_KEY  = "/root/.ssh/id_ed25519"

VAST_KEY = ""
HF_TOKEN = ""


# ============================================================================
# Helpers (identical pattern to cycle7c_orpo_vast.py for consistency)
# ============================================================================
def log(msg: str):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    Path(LOG_PATH).parent.mkdir(parents=True, exist_ok=True)
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
        log(f"Vast {method.upper()} {path} -> {resp.status_code}: {resp.text[:200]}")
        return {}
    return data


def search_offers() -> list:
    query = {
        "verified":   {"eq": True},
        "rentable":   {"eq": True},
        "gpu_ram":    {"gte": MIN_GPU_RAM_MB},
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
        "label":           "migancore-cycle7e-innovation-sft",
        "ssh_key_ids":     [808896],
    }
    result = vast("put", f"/asks/{offer_id}/", json=payload)
    inst_id = (result.get("new_contract")
               or result.get("contract_id")
               or result.get("id"))
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
    """Lesson #59: verify DELETE, don't trust 204."""
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
            log(f"ERROR: instance alive (status={status2}) after 2 deletes!")
            return False
    log(f"Instance {inst_id} CONFIRMED DELETED")
    return True


def wait_for_ssh(inst_id: int, deadline: float):
    """Lesson #60: abort if no SSH within deadline."""
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
    log(f"ABORT: no SSH within deadline (Lesson #60)")
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


def cost_so_far(inst_id: int, start_ts: float, price_hr: float = 0.35) -> float:
    elapsed_h = (time.time() - start_ts) / 3600
    try:
        inst = get_instance(inst_id)
        price_hr = inst.get("dph_total", price_hr)
    except Exception:
        pass
    return round(elapsed_h * price_hr, 4)


# ============================================================================
# Dry-run validator (Gate 1) — no money spent, no instance spawned
# ============================================================================
def dry_run():
    log("=" * 60)
    log("CYCLE 7e — DRY RUN (Gate 1, zero cost)")
    log("=" * 60)

    issues = []

    # 1. Secrets accessible
    for name, path in [("VAST_KEY", VAST_KEY_PATH), ("HF_TOKEN", HF_TOKEN_PATH)]:
        if not Path(path).exists():
            issues.append(f"Missing secret: {path}")
        else:
            try:
                val = Path(path).read_text().strip()
                if not val:
                    issues.append(f"Empty secret: {path}")
                else:
                    log(f"  [OK] {name} present ({len(val)} chars)")
            except Exception as e:
                issues.append(f"Cannot read {path}: {e}")

    # 2. Dataset exists + valid JSONL + correct schema
    if not Path(DATASET_PATH).exists():
        issues.append(f"Missing dataset: {DATASET_PATH}")
    else:
        lines = Path(DATASET_PATH).read_text().splitlines()
        log(f"  [OK] Dataset: {len(lines)} lines")
        if len(lines) != 200:
            issues.append(f"Expected 200 pairs, got {len(lines)}")
        families = {}
        for i, line in enumerate(lines):
            try:
                d = json.loads(line)
                assert "messages" in d, "missing messages"
                assert "family" in d, "missing family"
                roles = [m["role"] for m in d["messages"]]
                assert roles == ["system", "user", "assistant"], f"bad roles: {roles}"
                families[d["family"]] = families.get(d["family"], 0) + 1
            except Exception as e:
                issues.append(f"Line {i+1} invalid: {e}")
                break
        log(f"  [OK] Families: {dict(families)}")
        expected_families = {"diverge_strategic": 40, "rank_options": 40,
                             "artifact_first": 40, "polish_loop": 40,
                             "toolify_pattern": 40}
        if families != expected_families:
            issues.append(f"Family distribution mismatch — got {families}")

    # 3. Trainer script exists
    if not Path(TRAIN_SCRIPT).exists():
        issues.append(f"Missing trainer: {TRAIN_SCRIPT}")
    else:
        log(f"  [OK] Trainer: {TRAIN_SCRIPT}")
        # Quick check: trainer accepts our args
        rc = subprocess.run(
            ["python3", TRAIN_SCRIPT, "--help"],
            capture_output=True, text=True, timeout=15
        )
        help_text = rc.stdout + rc.stderr
        required_flags = ["--dataset", "--output-dir", "--base-model",
                          "--epochs", "--learning-rate", "--lora-r"]
        missing = [f for f in required_flags if f not in help_text]
        if missing:
            issues.append(f"Trainer missing flags: {missing}")
        else:
            log(f"  [OK] Trainer accepts all required flags")

    # 4. SSH key exists
    if not Path(SSH_KEY).exists():
        issues.append(f"Missing SSH key: {SSH_KEY}")
    else:
        log(f"  [OK] SSH key: {SSH_KEY}")

    # 5. Vast.ai API reachable (read-only) + credit check + orphan instance check
    # Orphan check from Day 49 redux: "exited" instances still incur disk costs
    # until DELETE. Without this, can leak $0.30+/day silently.
    try:
        VAST_KEY_LOCAL = Path(VAST_KEY_PATH).read_text().strip()
        if VAST_KEY_LOCAL:
            r = requests.get(
                f"{VAST_API}/users/current/",
                params={"api_key": VAST_KEY_LOCAL},
                timeout=15
            )
            if r.status_code == 200:
                user = r.json()
                credit = user.get("credit", 0)
                log(f"  [OK] Vast.ai API: credit=${credit:.2f}")
                if credit < COST_CAP_USD:
                    issues.append(
                        f"Vast.ai credit ${credit:.2f} < cost cap ${COST_CAP_USD} — top up needed"
                    )
            else:
                issues.append(f"Vast.ai API: HTTP {r.status_code}")

            # Orphan instance scan (Lesson #59 + Day 49 redux)
            r2 = requests.get(
                f"{VAST_API}/instances/",
                params={"api_key": VAST_KEY_LOCAL},
                timeout=15
            )
            if r2.status_code == 200:
                insts = r2.json().get("instances", [])
                if not insts:
                    log(f"  [OK] No orphan instances")
                else:
                    log(f"  [WARN] {len(insts)} existing instance(s):")
                    for i in insts:
                        status = i.get("actual_status", "?")
                        log(f"    #{i.get('id')} status={status} "
                            f"gpu={i.get('gpu_name','?')} "
                            f"dph={i.get('dph_total',0):.3f}")
                        if status == "exited":
                            issues.append(
                                f"Orphan exited instance #{i.get('id')} — "
                                f"disk cost leaking. DELETE via API before launch."
                            )
    except Exception as e:
        issues.append(f"Vast.ai API unreachable: {e}")

    # 6. Output dir writable
    try:
        Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        test_file = Path(OUTPUT_DIR) / ".write_test"
        test_file.write_text("ok")
        test_file.unlink()
        log(f"  [OK] Output dir writable: {OUTPUT_DIR}")
    except Exception as e:
        issues.append(f"Output dir not writable: {e}")

    # 7. Print full training command that will run
    train_cmd = (
        "/root/trainenv/bin/python /root/train_sft_simple.py "
        + " ".join(SFT_ARGS)
    )
    log(f"\n  Training command (will run on Vast.ai):")
    log(f"  {train_cmd}")

    log("\n" + "=" * 60)
    if issues:
        log("DRY-RUN FAILED:")
        for i in issues:
            log(f"  [FAIL] {i}")
        log("=" * 60)
        sys.exit(1)
    log("DRY-RUN PASS — infrastructure ready for Gate 2 launch")
    log("Estimated cost: $0.20 success / $0.04 abort")
    log("To launch: python3 cycle7e_innovation_sft_vast.py --launch")
    log("=" * 60)
    return 0


# ============================================================================
# Live launch (Gate 2) — requires explicit --launch flag
# ============================================================================
def live_launch():
    global VAST_KEY, HF_TOKEN

    log("=" * 60)
    log("MIGANCORE CYCLE 7e — INNOVATION ENGINE SFT (LIVE)")
    log("Phase 2 of M1.7: teach OBSERVE-SYNTHESIZE-DIVERGE-RANK-PROTOTYPE-")
    log("                 TEST-POLISH-TOOLIFY-LEARN loop into weights.")
    log(f"Dataset: {DATASET_PATH} (200 pairs, 5 families × 40)")
    log(f"Algo   : SFT | LR: 5e-7 | epochs: 5 | LoRA r=8 | ~63 steps")
    log(f"Target : {HF_REPO}")
    log("Gate   : innovation>=0.80 AND identity>=0.90 AND voice>=0.80")
    log("=" * 60)

    VAST_KEY = load_secret(VAST_KEY_PATH)
    HF_TOKEN = load_secret(HF_TOKEN_PATH)
    log("Secrets loaded OK")

    if not Path(DATASET_PATH).exists():
        log(f"FATAL: dataset not found at {DATASET_PATH}")
        sys.exit(1)
    dataset_lines = len(Path(DATASET_PATH).read_text().splitlines())
    log(f"Dataset: {dataset_lines} pairs")

    if not Path(TRAIN_SCRIPT).exists():
        log(f"FATAL: trainer not at {TRAIN_SCRIPT}")
        sys.exit(1)
    log("Trainer OK")
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    log("\n[1/8] Searching Vast.ai offers...")
    offers = search_offers()
    if not offers:
        log("No offers found.")
        sys.exit(1)
    log(f"Found {len(offers)} offers. Top 5:")
    for o in offers[:5]:
        log(f"  #{o['id']} {o.get('gpu_name','?')} "
            f"RAM={o.get('gpu_ram',0)//1000}GB ${o.get('dph_total',0):.3f}/hr")

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

    log("\n[4/8] Installing ML packages...")
    install_cmd = (
        "python -m venv /root/trainenv --system-site-packages && "
        "/root/trainenv/bin/pip install -q "
        "trl==0.9.6 transformers==4.44.2 peft==0.12.0 "
        "accelerate==0.34.0 datasets huggingface_hub bitsandbytes rich && "
        '/root/trainenv/bin/python -c "import trl, transformers, peft, accelerate; '
        'from trl import SFTTrainer, SFTConfig; '
        'print(chr(83)+chr(70)+chr(84)+chr(32)+chr(79)+chr(75))"'
    )
    rc, out, err = ssh_run(ssh_host, ssh_port, install_cmd, timeout=900)
    log(f"Install exit={rc} | {out.strip()[-400:]}")
    if rc != 0:
        log(f"STDERR: {err[-300:]}")
        delete_instance(inst_id)
        sys.exit(6)

    cost = cost_so_far(inst_id, start_ts, price_hr)
    log(f"Cost so far: ${cost:.4f}")
    if cost > COST_CAP_USD:
        log("COST CAP hit. Aborting.")
        delete_instance(inst_id)
        sys.exit(3)

    log("\n[5/8] Uploading dataset + trainer...")
    ok1 = scp_to(DATASET_PATH, ssh_host, ssh_port,
                 "/root/cycle7e_innovation_sft_dataset.jsonl")
    ok2 = scp_to(TRAIN_SCRIPT, ssh_host, ssh_port,
                 "/root/train_sft_simple.py")
    if not (ok1 and ok2):
        log("Upload failed. Aborting.")
        delete_instance(inst_id)
        sys.exit(4)
    log("Upload complete")
    rc, out, _ = ssh_run(ssh_host, ssh_port,
                         "wc -l /root/cycle7e_innovation_sft_dataset.jsonl")
    log(f"Remote check: {out.strip()}")

    log("\n[6/8] Starting SFT training (200 pairs, 5 epochs, LR=5e-7, ~63 steps)...")
    train_cmd = (
        "/root/trainenv/bin/python /root/train_sft_simple.py "
        + " ".join(SFT_ARGS)
        + " > /root/train_log.txt 2>&1"
    )
    log("Training started. Estimated 10-15 min on A40...")
    train_start = time.time()
    try:
        rc, out, err = ssh_run(ssh_host, ssh_port, train_cmd, timeout=3600)
    except Exception as e:
        log(f"Training SSH timeout/error: {e}")
        log(f"Recovery: ssh -i {SSH_KEY} -p {ssh_port} root@{ssh_host}")
        sys.exit(7)
    train_elapsed = time.time() - train_start
    log(f"Training exit={rc} | elapsed={train_elapsed:.0f}s ({train_elapsed/60:.1f}min)")

    _, train_tail, _ = ssh_run(ssh_host, ssh_port,
                               "tail -200 /root/train_log.txt 2>/dev/null",
                               timeout=30)
    if train_tail:
        log("Training log (tail 200):")
        for line in train_tail.strip().splitlines():
            log(f"  {line}")

    if rc != 0:
        log(f"Training FAILED (rc={rc}).")
        delete_instance(inst_id)
        sys.exit(5)
    log("Training COMPLETE")

    log("\n[7/8] HF roundtrip upload (Lesson #173)...")
    # train_sft_simple.py saves to /root/cycle7e_adapter/final_adapter/
    rc, out, _ = ssh_run(ssh_host, ssh_port,
                         "ls -lh /root/cycle7e_adapter/final_adapter/ 2>/dev/null | head -10")
    log(f"Adapter dir:\n{out}")

    hf_cmd = (
        f"cd /root/cycle7e_adapter/final_adapter && "
        f"/root/trainenv/bin/huggingface-cli upload {HF_REPO} . "
        f"--token {HF_TOKEN} "
        f"--commit-message 'Cycle 7e: Innovation Engine SFT (200 pairs, 5 epochs, LR=5e-7, r=8)' "
        f"2>&1 | tail -10"
    )
    rc_hf, out_hf, _ = ssh_run(ssh_host, ssh_port, hf_cmd, timeout=600)
    log(f"HF upload exit={rc_hf}: {out_hf.strip()[-300:]}")
    if rc_hf == 0:
        log(f"Adapter live: https://huggingface.co/{HF_REPO}")
    else:
        log("WARNING: HF upload failed. Will attempt SCP fallback.")
        adapter_local = f"{OUTPUT_DIR}/cycle7e_adapter"
        Path(adapter_local).mkdir(parents=True, exist_ok=True)
        for fname in ["adapter_model.safetensors", "adapter_config.json"]:
            result = subprocess.run(
                ["scp", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no",
                 "-P", str(ssh_port),
                 f"root@{ssh_host}:/root/cycle7e_adapter/final_adapter/{fname}",
                 f"{adapter_local}/{fname}"],
                capture_output=True, text=True, timeout=300
            )
            log(f"  SCP {fname}: rc={result.returncode}")

    log("\n[8/8] Deleting instance (Lesson #59)...")
    deleted = delete_instance(inst_id)
    total_elapsed = time.time() - start_ts
    total_cost = round((total_elapsed / 3600) * price_hr, 4)

    log("\n" + "=" * 60)
    log("CYCLE 7e TRAINING SUMMARY")
    log("=" * 60)
    log(f"GPU      : {best.get('gpu_name','?')}")
    log(f"Time     : {total_elapsed/60:.1f} min (train: {train_elapsed/60:.1f} min)")
    log(f"Cost     : ${total_cost:.4f} @ ${price_hr:.3f}/hr")
    log(f"Deleted  : {'YES' if deleted else 'WARNING - check Vast.ai!'}")
    log(f"HF repo  : https://huggingface.co/{HF_REPO}")
    log("=" * 60)
    log("")
    log("NEXT STEPS (Gate 3 — requires Fahmi GO before hot-swap):")
    log(f"  1. Download adapter from HF:")
    log(f"     huggingface-cli download {HF_REPO} --local-dir {OUTPUT_DIR}/adapter")
    log(f"  2. Convert GGUF:")
    log(f"     python3 /opt/llama.cpp/convert_lora_to_gguf.py {OUTPUT_DIR}/adapter/ \\")
    log(f"       --outfile {OUTPUT_DIR}/cycle7e_lora.gguf --outtype f16")
    log(f"  3. Register in Ollama: docker exec ado-ollama-1 ollama create migancore:0.7e \\")
    log(f"       -f /opt/ado/data/ollama/Modelfile_cycle7e")
    log(f"  4. Run eval: docker compose exec -T api python /app/eval/run_innovation_eval.py \\")
    log(f"       --model migancore:0.7e --baseline eval/baseline_innovation_v1.json")
    log(f"  5. Gate: PROMOTE if innovation>=0.80 AND identity>=0.90 AND voice>=0.80")
    log(f"     ROLLBACK to migancore:0.7c if gate fails")
    log("")


def main():
    if "--dry-run" in sys.argv:
        sys.exit(dry_run())
    if "--launch" in sys.argv:
        live_launch()
        return
    print("Usage:")
    print("  --dry-run  Validate infrastructure (Gate 1, zero cost)")
    print("  --launch   Spawn Vast.ai instance + train (Gate 2, ~$0.30)")
    print()
    print("Recommended: --dry-run first, then --launch after explicit owner GO.")
    sys.exit(0)


if __name__ == "__main__":
    main()
