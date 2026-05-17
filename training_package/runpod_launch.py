#!/usr/bin/env python3
"""RunPod launcher for the identity-immunity training path.

Usage:
    RUNPOD_API_KEY=... python -m training_package.runpod_launch --mode smoke
    RUNPOD_API_KEY=... python -m training_package.runpod_launch --mode micro
    RUNPOD_API_KEY=... python -m training_package.runpod_launch --mode full --dpo-data training_data/dpo_export.jsonl

The default smoke mode spends a small amount of GPU time on the immunity data
only. Micro mode is the first behavior-quality run. Full mode requires a real
DPO export and appends the immunity DPO file.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

import runpod


POD_NAME = "migancore-identity-immunity-ssh"
GPU_TYPE_IDS = ("NVIDIA RTX A6000", "NVIDIA A40")
CLOUD_TYPE = "ALL"
IMAGE_NAME = "runpod/pytorch:2.2.0-py3.10-cuda12.1.1-devel-ubuntu22.04"

SSH_KEY_PATH = os.path.expanduser("~/.ssh/runpod_migan")
SSH_PUB_PATH = SSH_KEY_PATH + ".pub"


def run(cmd: list[str], *, capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=not capture, capture_output=capture, text=True)


def get_or_create_ssh_key() -> str:
    if os.path.exists(SSH_KEY_PATH) and os.path.exists(SSH_PUB_PATH):
        with open(SSH_PUB_PATH, encoding="utf-8") as f:
            pub_key = f.read().strip()
        print(f"[SSH] Using existing key: {SSH_KEY_PATH}")
        return pub_key

    print(f"[SSH] Generating ED25519 key pair at {SSH_KEY_PATH}...")
    os.makedirs(os.path.dirname(SSH_KEY_PATH), exist_ok=True)
    run(["ssh-keygen", "-t", "ed25519", "-C", "migan_training", "-f", SSH_KEY_PATH, "-N", ""])
    with open(SSH_PUB_PATH, encoding="utf-8") as f:
        return f.read().strip()


def find_pod() -> dict | None:
    for pod in runpod.get_pods():
        if pod.get("name") == POD_NAME:
            return pod
    return None


def create_pod(pub_key: str) -> str:
    last_error: Exception | None = None
    for gpu_type_id in GPU_TYPE_IDS:
        print(f"[RunPod] Creating pod '{POD_NAME}' with GPU {gpu_type_id}...")
        try:
            pod = runpod.create_pod(
                name=POD_NAME,
                image_name=IMAGE_NAME,
                gpu_type_id=gpu_type_id,
                cloud_type=CLOUD_TYPE,
                gpu_count=1,
                container_disk_in_gb=50,
                volume_in_gb=50,
                ports="22/tcp",
                start_ssh=True,
                support_public_ip=True,
                env={"PUBLIC_KEY": pub_key},
            )
            print(f"[RunPod] Pod created: {pod['id']} ({gpu_type_id})")
            return pod["id"]
        except Exception as exc:
            last_error = exc
            print(f"[RunPod] GPU unavailable ({gpu_type_id}): {exc}")
    raise RuntimeError(f"No configured RunPod GPU type is available. Last error: {last_error}")


def wait_for_ssh(pod_id: str, max_wait_sec: int = 900) -> tuple[str, int]:
    print(f"[RunPod] Waiting up to {max_wait_sec}s for SSH endpoint...")
    for i in range(max_wait_sec // 10):
        pod = runpod.get_pod(pod_id)
        runtime = pod.get("runtime") or {}
        ports = runtime.get("ports", [])
        ssh_ip = None
        ssh_port = None
        for port in ports:
            if port.get("privatePort") == 22:
                ssh_ip = port.get("ip")
                ssh_port = port.get("publicPort")
                break
        status = pod.get("desiredStatus", "unknown")
        print(f"  [{i * 10}s] status={status}, ssh={ssh_ip or 'N/A'}:{ssh_port or 'N/A'}")
        if status == "RUNNING" and ssh_ip and ssh_port:
            return ssh_ip, int(ssh_port)
        time.sleep(10)
    raise TimeoutError(f"SSH endpoint not available after {max_wait_sec}s")


def ssh_cmd(ssh_ip: str, ssh_port: int, command: str, *, capture: bool = False) -> subprocess.CompletedProcess:
    return run(
        [
            "ssh",
            "-i",
            SSH_KEY_PATH,
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-o",
            "ConnectTimeout=15",
            f"root@{ssh_ip}",
            "-p",
            str(ssh_port),
            command,
        ],
        capture=capture,
    )


def upload_file(ssh_ip: str, ssh_port: int, local_path: str, remote_name: str) -> None:
    print(f"  Uploading {remote_name}...")
    run(
        [
            "scp",
            "-i",
            SSH_KEY_PATH,
            "-o",
            "StrictHostKeyChecking=accept-new",
            "-P",
            str(ssh_port),
            local_path,
            f"root@{ssh_ip}:/workspace/migan_data/{remote_name}",
        ]
    )


def upload_training_data(ssh_ip: str, ssh_port: int, dpo_data: str) -> bool:
    print("[Data] Uploading training data and scripts...")
    files = {
        "identity_sft.jsonl": "api/training_data/identity_sft_1k.jsonl",
        "identity_immunity_sft.jsonl": "training_data/identity_immunity_sft.jsonl",
        "identity_immunity_dpo.jsonl": "training_data/identity_immunity_dpo.jsonl",
        "runpod_train_fixed_v4.py": "training_package/runpod_train_fixed_v4.py",
        "runpod_sanity_eval.py": "training_package/runpod_sanity_eval.py",
    }
    if dpo_data:
        files["dpo_export.jsonl"] = dpo_data

    missing = [path for path in files.values() if not os.path.exists(path)]
    if missing:
        print("ERROR: Missing required local files:")
        for path in missing:
            print(f"  - {path}")
        return False

    ssh_cmd(ssh_ip, ssh_port, "mkdir -p /workspace/migan_data")
    for remote_name, local_path in files.items():
        upload_file(ssh_ip, ssh_port, local_path, remote_name)
    return True


def setup_environment(ssh_ip: str, ssh_port: int) -> bool:
    setup_cmd = """
set -e
cd /workspace
echo "[1] Checking data..."
ls -lh /workspace/migan_data/
echo "[2] Installing stable training stack..."
pip install -q torch==2.5.1 transformers==4.48.0 trl==0.11.4 accelerate==0.34.0 bitsandbytes==0.44.0 peft==0.13.0 datasets rich 2>&1 | tail -8
pip uninstall -y torchvision torchaudio >/tmp/uninstall_vision_audio.log 2>&1 || true
python3 - <<'PY'
import torch, transformers, trl
print("torch", torch.__version__, "cuda", torch.cuda.is_available())
print("transformers", transformers.__version__)
print("trl", trl.__version__)
PY
"""
    result = ssh_cmd(ssh_ip, ssh_port, setup_cmd, capture=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        return False
    return True


def start_training(ssh_ip: str, ssh_port: int, mode: str) -> bool:
    if mode == "smoke":
        dpo_path = "/workspace/migan_data/identity_immunity_dpo.jsonl"
        output_dir = "/workspace/training_output_identity_smoke"
        extra_args = "--max-sft-samples 80 --max-dpo-samples 28 --max-steps 8 --batch-size 1 --grad-accum 1 --max-length 1024"
    elif mode == "micro":
        dpo_path = "/workspace/migan_data/identity_immunity_dpo.jsonl"
        output_dir = "/workspace/training_output_identity_micro"
        extra_args = "--sft-max-steps 180 --dpo-max-steps 120 --merge --batch-size 1 --grad-accum 2 --max-length 1536 --lr 8e-6"
    else:
        dpo_path = "/workspace/migan_data/dpo_export.jsonl"
        output_dir = "/workspace/training_output_v5_identity_immunity"
        extra_args = "--batch-size 1 --grad-accum 4 --max-length 2048"

    train_cmd = f"""
set -e
cd /workspace
if [ ! -f "{dpo_path}" ]; then
    echo "Missing DPO data: {dpo_path}" >&2
    exit 2
fi
rm -rf {output_dir}
nohup python3 /workspace/migan_data/runpod_train_fixed_v4.py \\
  --dpo-data {dpo_path} \\
  --identity-data /workspace/migan_data/identity_sft.jsonl \\
  --extra-identity-data /workspace/migan_data/identity_immunity_sft.jsonl \\
  --extra-dpo-data /workspace/migan_data/identity_immunity_dpo.jsonl \\
  --output-dir {output_dir} \\
  --base-model Qwen/Qwen2.5-7B-Instruct \\
  --epochs 1 {extra_args} \\
  > /workspace/train_identity_immunity.log 2>&1 &
echo "Training started with PID: $!"
sleep 2
ps aux | grep runpod_train_fixed_v4 | grep -v grep
"""
    result = ssh_cmd(ssh_ip, ssh_port, train_cmd, capture=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["smoke", "micro", "full"], default="smoke")
    parser.add_argument("--dpo-data", default="", help="Real DPO export required for full mode.")
    args = parser.parse_args()

    if args.mode == "full" and not args.dpo_data:
        print("ERROR: --mode full requires --dpo-data.")
        return 1

    print("=" * 60)
    print("RunPod Training Launcher v3 - identity immunity")
    print("=" * 60)

    api_key = os.environ.get("RUNPOD_API_KEY", "")
    if not api_key:
        print("ERROR: Set RUNPOD_API_KEY env var")
        return 1
    runpod.api_key = api_key

    pub_key = get_or_create_ssh_key()
    pod = find_pod()
    if pod:
        pod_id = pod["id"]
        status = pod.get("desiredStatus", "unknown")
        print(f"[RunPod] Found existing pod: {POD_NAME} ({pod_id}), status={status}")
        if status != "RUNNING":
            try:
                runpod.resume_pod(pod_id, gpu_count=1)
                time.sleep(30)
            except Exception as exc:
                print(f"[RunPod] Resume failed ({exc}); creating a fresh pod instead.")
                pod_id = create_pod(pub_key)
    else:
        pod_id = create_pod(pub_key)

    ssh_ip, ssh_port = wait_for_ssh(pod_id)
    result = ssh_cmd(ssh_ip, ssh_port, "echo SSH_OK", capture=True)
    if result.returncode != 0 or "SSH_OK" not in result.stdout:
        print("ERROR: Cannot connect via SSH.")
        return 1

    if not upload_training_data(ssh_ip, ssh_port, args.dpo_data):
        return 1
    if not setup_environment(ssh_ip, ssh_port):
        return 1
    if not start_training(ssh_ip, ssh_port, args.mode):
        return 1

    print("\n" + "=" * 60)
    print("Training started.")
    print(f"Mode: {args.mode}")
    print(f"Pod: {POD_NAME} ({pod_id})")
    print(f"SSH: ssh -i ~/.ssh/runpod_migan root@{ssh_ip} -p {ssh_port}")
    print(f"Monitor: ssh -i ~/.ssh/runpod_migan root@{ssh_ip} -p {ssh_port} 'tail -f /workspace/train_identity_immunity.log'")
    try:
        print(f"Cost: ~${runpod.get_pod(pod_id).get('costPerHr', 0):.2f}/hr")
    except Exception as exc:
        print(f"Cost lookup skipped: {exc}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
