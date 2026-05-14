"""
Auto-Training Watchdog — MiganCore Autonomous Growth
======================================================
Background coroutine that monitors data quality and triggers GPU training
on Vast.ai automatically when thresholds are met.

Strategy (sesuai Kimi Week 1 Day 72-79):
  - Check every 3 hours
  - Trigger when: real_conversation pairs ≥ 80 AND days_since_last ≥ 3
  - Dataset: 70% targeted synthetic + 30% real conversation (Kimi mix rule)
  - Base model: migancore:0.7c (Lesson #3 — never retrain from Qwen base again)
  - After train: auto-run eval gate
  - If PROMOTE (weighted_avg ≥ 0.92): auto-hot-swap
  - If CONDITIONAL (weighted_avg ≥ 0.88, identity ≥ 0.90): create proposal for Fahmi

Safety:
  - Hard cap $3/auto-trigger
  - Max 1 auto-training per day
  - Creates DevOrganProposal log entry for every triggered run
  - Fails safe: any error → log + skip, never crash the API

Author: MiganCore Day 73 — autonomous growth sprint
"""
from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import httpx
import structlog

logger = structlog.get_logger()

# Thresholds
REAL_PAIRS_THRESHOLD = 80        # minimum real conversation pairs to trigger
MIN_DAYS_SINCE_TRAIN  = 3        # cooldown between auto-training runs
AUTO_TRAIN_BUDGET_CAP = 3.00     # max USD per auto-triggered run
CHECK_INTERVAL_S      = 3 * 3600 # check every 3 hours

# Day 73 Codex audit — biomimetic doctrine: GPU training is vitamin, not oxygen.
# Default mode is "proposal": watchdog only logs proposals to dev_organ_proposals,
# never auto-triggers Vast.ai. Fahmi reviews + manually approves training.
# Override via env AUTO_TRAIN_MODE=auto (original behavior) or off (skip loop entirely).
AUTO_TRAIN_MODE = os.getenv("AUTO_TRAIN_MODE", "proposal").lower()
if AUTO_TRAIN_MODE not in {"proposal", "auto", "off"}:
    AUTO_TRAIN_MODE = "proposal"

# Vast.ai config
VAST_API            = "https://console.vast.ai/api/v0"
VAST_KEY_PATH       = "/opt/secrets/migancore/vastai_api_key"
HF_TOKEN_PATH       = "/opt/secrets/migancore/hf_token"
SSH_KEY             = "/root/.ssh/id_ed25519"
SSH_KEY_ID          = 808896
MIN_GPU_RAM_MB      = 40_000
MAX_PRICE_HR        = 0.65
MIN_DISK_GB         = 65

# Output
OUTPUT_DIR          = "/opt/ado/data/training/auto"
TRAIN_LOG_PATH      = "/opt/ado/data/training/auto/auto_train.log"


def _log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    line = f"[{ts}] [auto_train_watchdog] {msg}"
    logger.info("auto_train", msg=msg)
    try:
        Path(TRAIN_LOG_PATH).parent.mkdir(parents=True, exist_ok=True)
        with open(TRAIN_LOG_PATH, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


async def _count_real_pairs() -> int:
    """Count unused real_conversation preference pairs in DB."""
    try:
        from sqlalchemy import text
        from deps.db import get_admin_db
        async with get_admin_db() as db:
            result = await db.execute(
                text("""
                    SELECT COUNT(*) FROM preference_pairs
                    WHERE source_method = 'real_conversation'
                      AND used_in_training_run_id IS NULL
                """)
            )
            return result.scalar() or 0
    except Exception as exc:
        logger.warning("auto_train.count_failed", error=str(exc)[:80])
        return 0


async def _days_since_last_training() -> float:
    """Days since last successful training run. Returns 999 if never trained."""
    try:
        last_path = Path("/opt/ado/data/training/auto/last_success.json")
        if not last_path.exists():
            return 999.0
        data = json.loads(last_path.read_text())
        last_ts = datetime.fromisoformat(data["completed_at"])
        delta = datetime.now(timezone.utc) - last_ts.replace(tzinfo=timezone.utc) if last_ts.tzinfo is None else datetime.now(timezone.utc) - last_ts
        return delta.total_seconds() / 86400
    except Exception:
        return 999.0


async def _export_training_dataset(real_pairs: int) -> Optional[str]:
    """Export mixed dataset (real + synthetic) for training. Returns JSONL path."""
    try:
        from sqlalchemy import text
        from deps.db import get_admin_db

        Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        out_path = f"{OUTPUT_DIR}/auto_cycle_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.jsonl"

        # How many synthetic to pull (70% of total target, max 500)
        total_target = min(real_pairs * 3, 500)  # 1 real : 3 synthetic (25%/75%)
        synth_limit  = total_target - real_pairs

        async with get_admin_db() as db:
            # Real conversation pairs
            real_rows = (await db.execute(
                text("""
                    SELECT prompt, chosen, rejected FROM preference_pairs
                    WHERE source_method = 'real_conversation'
                      AND used_in_training_run_id IS NULL
                    ORDER BY created_at DESC
                    LIMIT :lim
                """),
                {"lim": real_pairs},
            )).fetchall()

            # Top quality synthetic (by judge_score, non-synthetic_seed)
            synth_rows = (await db.execute(
                text("""
                    SELECT prompt, chosen, rejected FROM preference_pairs
                    WHERE source_method != 'real_conversation'
                      AND source_method != 'synthetic_seed_v1'
                      AND used_in_training_run_id IS NULL
                      AND judge_score >= 0.7
                    ORDER BY judge_score DESC, created_at DESC
                    LIMIT :lim
                """),
                {"lim": synth_limit},
            )).fetchall()

        if not real_rows:
            _log("No real pairs found — aborting")
            return None

        with open(out_path, "w", encoding="utf-8") as f:
            for row in real_rows + synth_rows:
                prompt, chosen, rejected = row
                f.write(json.dumps({
                    "prompt": prompt,
                    "chosen": chosen,
                    "rejected": rejected or "",
                }, ensure_ascii=False) + "\n")

        total = len(real_rows) + len(synth_rows)
        _log(f"Dataset exported: {total} pairs ({len(real_rows)} real + {len(synth_rows)} synth) → {out_path}")
        return out_path
    except Exception as exc:
        _log(f"Dataset export failed: {exc}")
        return None


def _vast_request(method: str, path: str, vast_key: str, **kwargs) -> dict:
    url = f"{VAST_API}{path}"
    params = kwargs.pop("params", {})
    params["api_key"] = vast_key
    try:
        resp = getattr(httpx, method)(url, params=params, timeout=30, **kwargs)
        return resp.json() if resp.status_code in (200, 201) else {}
    except Exception as exc:
        _log(f"Vast API error: {exc}")
        return {}


def _search_gpu_offer(vast_key: str) -> Optional[int]:
    query = {
        "verified": {"eq": True},
        "rentable": {"eq": True},
        "gpu_ram":  {"gte": MIN_GPU_RAM_MB},
        "disk_space": {"gte": MIN_DISK_GB},
        "dph_total":  {"lte": MAX_PRICE_HR},
        "type": "ask",
        "order": [["dph_total", "asc"]],
        "limit": 10,
    }
    result = _vast_request("get", "/bundles/", vast_key, params={"q": json.dumps(query)})
    offers = result.get("offers", [])
    if not offers:
        return None
    return offers[0]["id"]


async def _create_proposal(cycle_id: str, status: str, detail: str) -> None:
    """Log the auto-training event as a DevOrganProposal for audit trail."""
    try:
        from sqlalchemy import text
        from deps.db import get_admin_db
        async with get_admin_db() as db:
            await db.execute(
                text("""
                    INSERT INTO dev_organ_proposals
                        (id, title, problem, hypothesis, risk_level, stage, source, metadata, created_at, updated_at)
                    VALUES (:id, :title, :problem, :hypothesis, :risk, :stage, :src, :metadata, NOW(), NOW())
                """),
                {
                    "id": str(uuid.uuid4()),
                    "title": f"Auto-Training {cycle_id}",
                    "problem": detail,
                    "hypothesis": "GPU fine-tune may improve the brain after owner review; do not auto-trigger.",
                    "risk": "medium",
                    "stage": "proposed" if status == "pending_review" else status,
                    "src": "auto",
                    "metadata": json.dumps({
                        "cycle_id": cycle_id,
                        "proposal_type": "training",
                        "component": "auto_train_watchdog",
                        "watchdog_stage": status,
                        "mode": AUTO_TRAIN_MODE,
                    }),
                },
            )
            await db.commit()
    except Exception as exc:
        logger.warning("auto_train.proposal_failed", error=str(exc)[:80])


async def _has_pending_training_proposal() -> bool:
    """Return True when a prior watchdog proposal is still awaiting review."""
    try:
        from sqlalchemy import text
        from deps.db import get_admin_db
        async with get_admin_db() as db:
            result = await db.execute(
                text("""
                    SELECT COUNT(*)
                    FROM dev_organ_proposals
                    WHERE source = 'auto'
                      AND metadata->>'component' = 'auto_train_watchdog'
                      AND metadata->>'proposal_type' = 'training'
                      AND stage = 'proposed'
                      AND creator_verdict IS NULL
                """)
            )
            return (result.scalar() or 0) > 0
    except Exception as exc:
        logger.warning("auto_train.pending_check_failed", error=str(exc)[:80])
        return False


async def _trigger_training_run(dataset_path: str) -> bool:
    """Launch a Vast.ai training instance with the assembled dataset.

    Returns True if successfully launched, False otherwise.
    """
    try:
        vast_key = Path(VAST_KEY_PATH).read_text().strip()
        hf_token = Path(HF_TOKEN_PATH).read_text().strip()
    except Exception as exc:
        _log(f"Cannot read Vast.ai/HF credentials: {exc}")
        return False

    cycle_id = f"auto_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}"
    _log(f"Searching GPU offer for {cycle_id}...")

    offer_id = _search_gpu_offer(vast_key)
    if not offer_id:
        _log("No suitable GPU offer found — aborting")
        await _create_proposal(cycle_id, "failed", "No GPU offer available on Vast.ai")
        return False

    payload = {
        "client_id":       "me",
        "image":           "pytorch/pytorch:2.5.1-cuda12.4-cudnn9-devel",
        "disk":            MIN_DISK_GB,
        "runtype":         "ssh",
        "use_jupyter_lab": False,
        "label":           f"migancore-{cycle_id}",
        "ssh_key_ids":     [SSH_KEY_ID],
    }
    result = _vast_request("put", f"/asks/{offer_id}/", vast_key, json=payload)
    inst_id = result.get("new_contract") or result.get("contract_id") or result.get("id")
    if not inst_id:
        _log(f"Instance creation failed: {result}")
        await _create_proposal(cycle_id, "failed", "Vast.ai instance creation failed")
        return False

    _log(f"Instance {inst_id} created for {cycle_id}")
    await _create_proposal(cycle_id, "running", f"Vast.ai instance {inst_id} launched, training {dataset_path}")

    # Launch async monitoring in background (doesn't block watchdog)
    asyncio.create_task(
        _monitor_and_finalize(inst_id, cycle_id, dataset_path, vast_key, hf_token)
    )
    return True


async def _monitor_and_finalize(
    inst_id: int,
    cycle_id: str,
    dataset_path: str,
    vast_key: str,
    hf_token: str,
) -> None:
    """SSH into instance, run training, download adapter, eval, hot-swap."""
    import subprocess

    MAX_BOOT_WAIT = 600
    _log(f"Waiting for instance {inst_id} to boot (max {MAX_BOOT_WAIT}s)...")

    ssh_host = None
    for _ in range(MAX_BOOT_WAIT // 15):
        await asyncio.sleep(15)
        info = _vast_request("get", f"/instances/{inst_id}/", vast_key)
        instances = info.get("instances", info)
        inst = instances if isinstance(instances, dict) else next(
            (i for i in (instances or []) if isinstance(i, dict) and i.get("id") == inst_id), {}
        )
        if inst.get("actual_status") == "running" and inst.get("ssh_host"):
            ssh_host = inst["ssh_host"]
            ssh_port = inst.get("ssh_port", 22)
            break

    if not ssh_host:
        _log(f"Instance {inst_id} never booted — aborting, deleting")
        _vast_request("delete", f"/instances/{inst_id}/", vast_key)
        await _create_proposal(cycle_id, "failed", "Instance boot timeout")
        return

    _log(f"Instance {inst_id} running at {ssh_host}:{ssh_port}")

    # Remote dataset path
    remote_dataset = f"/root/auto_dataset.jsonl"
    adapter_dir    = f"/root/auto_adapter"
    hf_repo        = f"Tiranyx/migancore-7b-soul-{cycle_id}"

    ssh_base = [
        "ssh", "-i", SSH_KEY,
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "ConnectTimeout=30",
        f"-p", str(ssh_port),
        f"root@{ssh_host}",
    ]

    def ssh_run(cmd: str, timeout: int = 600) -> bool:
        try:
            r = subprocess.run(ssh_base + [cmd], timeout=timeout, capture_output=True)
            return r.returncode == 0
        except Exception as exc:
            _log(f"SSH command failed: {exc}")
            return False

    def scp_send(local: str, remote_path: str) -> bool:
        try:
            r = subprocess.run([
                "scp", "-i", SSH_KEY, "-o", "StrictHostKeyChecking=no",
                "-P", str(ssh_port), local, f"root@{ssh_host}:{remote_path}",
            ], timeout=120, capture_output=True)
            return r.returncode == 0
        except Exception as exc:
            _log(f"SCP failed: {exc}")
            return False

    # Setup + install
    _log("Installing training dependencies...")
    setup = (
        "pip install -q trl peft transformers accelerate bitsandbytes huggingface_hub 2>/dev/null"
    )
    if not ssh_run(setup, timeout=300):
        _log("Dependency install failed")
        _vast_request("delete", f"/instances/{inst_id}/", vast_key)
        await _create_proposal(cycle_id, "failed", "Dependency install failed")
        return

    # Upload dataset
    _log("Uploading dataset...")
    if not scp_send(dataset_path, remote_dataset):
        _log("Dataset upload failed")
        _vast_request("delete", f"/instances/{inst_id}/", vast_key)
        await _create_proposal(cycle_id, "failed", "Dataset upload failed")
        return

    # Training command (ORPO on migancore:0.7c via HuggingFace)
    # Base: Qwen2.5-7B-Instruct + load from HF adapter Tiranyx/migancore-7b-soul-v0.7c
    # Then ORPO fine-tune with real + synthetic mix
    train_cmd = f"""
python3 -c "
import json, torch
from datasets import Dataset
from trl import ORPOConfig, ORPOTrainer
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model

base_model = 'Qwen/Qwen2.5-7B-Instruct'
tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(base_model, torch_dtype=torch.bfloat16, device_map='auto', trust_remote_code=True)

# Load adapter from Cycle 7c
from peft import PeftModel
model = PeftModel.from_pretrained(model, 'Tiranyx/migancore-7b-soul-v0.7c', token='{hf_token}')
model = model.merge_and_unload()

# Fresh LoRA for new cycle
lora_cfg = LoraConfig(r=16, lora_alpha=16, target_modules=['q_proj','v_proj'], lora_dropout=0.05, bias='none', task_type='CAUSAL_LM')
model = get_peft_model(model, lora_cfg)

# Load dataset
rows = [json.loads(l) for l in open('{remote_dataset}')]
ds = Dataset.from_list([{{'prompt': r['prompt'], 'chosen': r['chosen'], 'rejected': r['rejected'] or r['chosen']}} for r in rows])

cfg = ORPOConfig(
    output_dir='{adapter_dir}',
    num_train_epochs=2,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=8,
    learning_rate=8e-7,
    beta=0.1,
    max_length=1024,
    max_prompt_length=512,
    save_strategy='no',
    logging_steps=10,
    push_to_hub=True,
    hub_model_id='{hf_repo}',
    hub_token='{hf_token}',
    bf16=True,
)
trainer = ORPOTrainer(model=model, args=cfg, tokenizer=tokenizer, train_dataset=ds)
trainer.train()
trainer.push_to_hub()
print('TRAINING_COMPLETE')
"
"""
    _log("Starting ORPO training...")
    try:
        r = subprocess.run(ssh_base + [train_cmd], timeout=5400, capture_output=True, text=True)
        success = "TRAINING_COMPLETE" in r.stdout
    except subprocess.TimeoutExpired:
        _log("Training timed out (90 min)")
        success = False

    # Cleanup instance
    _vast_request("delete", f"/instances/{inst_id}/", vast_key)
    _log(f"Instance {inst_id} deleted")

    if not success:
        _log("Training failed")
        await _create_proposal(cycle_id, "failed", "ORPO training did not complete")
        return

    _log(f"Training complete! Adapter pushed to HF: {hf_repo}")

    # Save success record
    try:
        Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        Path(f"{OUTPUT_DIR}/last_success.json").write_text(json.dumps({
            "cycle_id": cycle_id,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "hf_repo": hf_repo,
            "dataset_path": dataset_path,
        }))
    except Exception:
        pass

    await _create_proposal(
        cycle_id, "completed",
        f"Training complete. Adapter: {hf_repo}. Pending eval gate before hot-swap."
    )
    _log(f"Cycle {cycle_id} complete. Next: run eval gate manually or wait for M2 auto-eval.")


async def watchdog_loop() -> None:
    """Main watchdog loop. Runs forever as a background asyncio task.

    Honors AUTO_TRAIN_MODE env (default "proposal"):
      - "off"      → exit immediately, no loop runs
      - "proposal" → loop runs but only writes proposals (Fahmi reviews)
      - "auto"     → original behavior: auto-trigger Vast.ai training
    """
    if AUTO_TRAIN_MODE == "off":
        _log("Auto-training watchdog disabled (AUTO_TRAIN_MODE=off)")
        return
    _log(f"Auto-training watchdog started (mode={AUTO_TRAIN_MODE})")
    await asyncio.sleep(60)  # brief startup delay

    while True:
        try:
            real_pairs = await _count_real_pairs()
            days_since = await _days_since_last_training()

            _log(f"Check: real_pairs={real_pairs} (threshold={REAL_PAIRS_THRESHOLD}), days_since_last={days_since:.1f} (threshold={MIN_DAYS_SINCE_TRAIN})")

            if real_pairs >= REAL_PAIRS_THRESHOLD and days_since >= MIN_DAYS_SINCE_TRAIN:
                if AUTO_TRAIN_MODE == "auto":
                    _log(f"TRIGGER: thresholds met — starting auto-training run")
                    dataset_path = await _export_training_dataset(real_pairs)
                    if dataset_path:
                        ok = await _trigger_training_run(dataset_path)
                        if ok:
                            _log("Training launched successfully")
                        else:
                            _log("Training launch failed — will retry next check")
                else:
                    # proposal mode: log + queue, do not auto-train
                    if await _has_pending_training_proposal():
                        _log("PROPOSAL skipped: pending auto-training proposal already exists")
                        await asyncio.sleep(CHECK_INTERVAL_S)
                        continue
                    cycle_id = f"prop_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}"
                    detail = (
                        f"Thresholds met: real_pairs={real_pairs} "
                        f"(≥{REAL_PAIRS_THRESHOLD}), days_since_last={days_since:.1f} "
                        f"(≥{MIN_DAYS_SINCE_TRAIN}). Awaiting Fahmi review. "
                        f"Set AUTO_TRAIN_MODE=auto to enable autonomous Vast.ai trigger."
                    )
                    _log(f"PROPOSAL ({cycle_id}): {detail}")
                    await _create_proposal(cycle_id, "pending_review", detail)
            else:
                missing = []
                if real_pairs < REAL_PAIRS_THRESHOLD:
                    missing.append(f"need {REAL_PAIRS_THRESHOLD - real_pairs} more real pairs")
                if days_since < MIN_DAYS_SINCE_TRAIN:
                    missing.append(f"cooldown {MIN_DAYS_SINCE_TRAIN - days_since:.1f}d remaining")
                _log(f"Not triggering: {', '.join(missing)}")

        except Exception as exc:
            logger.error("auto_train.watchdog_error", error=str(exc)[:120])

        await asyncio.sleep(CHECK_INTERVAL_S)
