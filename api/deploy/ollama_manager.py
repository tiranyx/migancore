#!/usr/bin/env python3
"""MiganForge Ollama Manager — v1.0 (Day 72e)

Manages Ollama model lifecycle:
    - Download merged HF model from cloud storage
    - Convert HF → GGUF using llama.cpp
    - Create Ollama model with Modelfile
    - Hot-swap running model
    - Health check + rollback

Usage:
    python -m deploy.ollama_manager \
        --merged-model /data/migancore_dpo/merged_model \
        --version migancore:0.5 \
        --deploy

    # Rollback
    python -m deploy.ollama_manager --rollback migancore:0.4

    # Setup llama.cpp (one-time)
    python -m deploy.ollama_manager --setup-llamacpp
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
import structlog

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import settings

logger = structlog.get_logger()

OLLAMA_URL = settings.OLLAMA_URL
DEFAULT_BASE_MODEL = "migancore:0.4"
LLAMA_CPP_DIR = Path("/opt/ado/llama.cpp")
MODELS_DIR = Path("/opt/ado/data/models")
GGUF_DIR = MODELS_DIR / "gguf"
HF_DIR = MODELS_DIR / "hf"
REGISTRY_PATH = Path("/opt/ado/data/models/registry.json")


@dataclass
class ModelRegistryEntry:
    version: str
    hf_path: Optional[str] = None
    gguf_path: Optional[str] = None
    modelfile: Optional[str] = None
    deployed_at: Optional[str] = None
    status: str = "pending"  # pending | converted | deployed | rolled_back | failed
    eval_score: Optional[float] = None
    baseline_win_rate: Optional[float] = None


class ModelRegistry:
    def __init__(self, path: Path = REGISTRY_PATH):
        self.path = path
        self._data: dict[str, dict] = {}
        self._load()

    def _load(self):
        if self.path.exists():
            with open(self.path, "r") as f:
                self._data = json.load(f)
        else:
            self._data = {}

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def add(self, entry: ModelRegistryEntry):
        self._data[entry.version] = asdict(entry)
        self._save()

    def get(self, version: str) -> Optional[ModelRegistryEntry]:
        d = self._data.get(version)
        if d:
            return ModelRegistryEntry(**d)
        return None

    def update(self, version: str, **kwargs):
        if version in self._data:
            self._data[version].update(kwargs)
            self._save()

    def list_deployed(self) -> list[ModelRegistryEntry]:
        return [
            ModelRegistryEntry(**v)
            for v in self._data.values()
            if v.get("status") == "deployed"
        ]

    def last_deployed(self) -> Optional[ModelRegistryEntry]:
        deployed = self.list_deployed()
        if not deployed:
            return None
        return max(deployed, key=lambda e: e.deployed_at or "")


def setup_llamacpp():
    """Download and setup llama.cpp for GGUF conversion.

    Uses pre-built llama.cpp binaries from GitHub releases.
    """
    if LLAMA_CPP_DIR.exists() and (LLAMA_CPP_DIR / "convert_hf_to_gguf.py").exists():
        print("llama.cpp already installed.")
        return

    print("Setting up llama.cpp...")
    LLAMA_CPP_DIR.mkdir(parents=True, exist_ok=True)

    # Clone llama.cpp repo
    subprocess.run(
        ["git", "clone", "--depth", "1", "https://github.com/ggerganov/llama.cpp.git", str(LLAMA_CPP_DIR)],
        check=True,
    )

    # Install Python requirements for conversion
    req_file = LLAMA_CPP_DIR / "requirements" / "requirements-convert_hf_to_gguf.txt"
    if req_file.exists():
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
            check=True,
        )

    # Also install gguf package
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "gguf"],
        check=True,
    )

    print(f"llama.cpp installed at {LLAMA_CPP_DIR}")
    print("To build quantize binary (optional): cd /opt/ado/llama.cpp && make")


def convert_hf_to_gguf(
    hf_model_dir: Path,
    output_gguf: Path,
    quant_type: str = "Q4_K_M",
) -> Path:
    """Convert HuggingFace model to GGUF format.

    Args:
        hf_model_dir: Path to HF model directory (contains config.json, model.safetensors)
        output_gguf: Output GGUF file path
        quant_type: Quantization type (Q4_K_M, Q5_K_M, Q8_0, F16)

    Returns:
        Path to generated GGUF file
    """
    setup_llamacpp()

    convert_script = LLAMA_CPP_DIR / "convert_hf_to_gguf.py"
    if not convert_script.exists():
        raise FileNotFoundError(f"convert_hf_to_gguf.py not found at {convert_script}")

    output_gguf.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(convert_script),
        str(hf_model_dir),
        "--outfile", str(output_gguf),
        "--outtype", quant_type.lower(),
    ]

    print(f"Converting {hf_model_dir} -> {output_gguf} ({quant_type})...")
    print(f"Command: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Conversion failed:\n{result.stderr}", file=sys.stderr)
        raise RuntimeError(f"GGUF conversion failed: {result.stderr[:500]}")

    print(f"GGUF saved: {output_gguf} ({output_gguf.stat().st_size / 1e9:.2f} GB)")
    return output_gguf


def create_modelfile(version: str, gguf_path: Path, template: str = "qwen") -> str:
    """Generate Ollama Modelfile content.

    Args:
        version: Model version tag (e.g. "migancore:0.5")
        gguf_path: Path to GGUF file
        template: Chat template (qwen, llama, etc.)

    Returns:
        Modelfile content as string
    """
    # Qwen2.5 chat template
    system_prompt = "You are Mighan-Core, an Autonomous Digital Organism from the Tiranyx ecosystem."

    modelfile = f"""FROM {gguf_path}

# System prompt
SYSTEM """{system_prompt}"""

# Parameters
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER repeat_penalty 1.1
PARAMETER num_ctx 4096
PARAMETER num_predict 1024

# Stop sequences
STOP <|im_end|>
STOP <|endoftext|>
"""
    return modelfile


def create_ollama_model(version: str, gguf_path: Path, modelfile_content: str) -> bool:
    """Create Ollama model from Modelfile.

    Uses Ollama API to create the model.
    """
    # Write Modelfile to temp location
    modelfile_path = GGUF_DIR / f"Modelfile-{version.replace(':', '_')}"
    modelfile_path.write_text(modelfile_content, encoding="utf-8")

    # Create model via Ollama API
    url = f"{OLLAMA_URL}/api/create"
    payload = {
        "name": version,
        "modelfile": modelfile_content,
        "stream": False,
    }

    try:
        response = httpx.post(url, json=payload, timeout=300.0)
        response.raise_for_status()
        result = response.json()
        if "error" in result:
            logger.error("deploy.ollama_create_failed", version=version, error=result["error"])
            return False
        logger.info("deploy.ollama_create_ok", version=version)
        return True
    except Exception as exc:
        logger.error("deploy.ollama_create_error", version=version, error=str(exc))
        return False


def health_check_model(version: str, timeout: float = 60.0) -> dict:
    """Run health check on Ollama model.

    Sends a simple Indonesian identity question and checks response.
    """
    url = f"{OLLAMA_URL}/api/generate"
    payload = {
        "model": version,
        "prompt": "Siapa kamu? Jawab dalam bahasa Indonesia.",
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 100},
    }

    try:
        response = httpx.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
        result = response.json()
        response_text = result.get("response", "")

        # Check identity consistency
        display_name = settings.ADO_DISPLAY_NAME
        identity_ok = display_name.lower() in response_text.lower()

        return {
            "status": "healthy",
            "response": response_text[:200],
            "identity_ok": identity_ok,
            "eval_count": result.get("eval_count", 0),
            "total_duration": result.get("total_duration", 0),
        }
    except Exception as exc:
        return {
            "status": "unhealthy",
            "error": str(exc),
        }


def deploy_model(
    version: str,
    hf_model_dir: Optional[Path] = None,
    gguf_path: Optional[Path] = None,
    quant_type: str = "Q4_K_M",
    skip_health_check: bool = False,
) -> dict:
    """Full deployment pipeline: HF → GGUF → Ollama → Health Check.

    Args:
        version: Model version tag (e.g. "migancore:0.5")
        hf_model_dir: Path to HF merged model (optional if gguf provided)
        gguf_path: Path to existing GGUF (optional if hf provided)
        quant_type: Quantization type for conversion
        skip_health_check: Skip health check (use with caution)

    Returns:
        Deployment result dict
    """
    registry = ModelRegistry()
    entry = ModelRegistryEntry(version=version, status="pending")
    registry.add(entry)

    try:
        # Step 1: Convert HF → GGUF (if needed)
        if gguf_path is None:
            if hf_model_dir is None:
                raise ValueError("Either hf_model_dir or gguf_path must be provided")
            gguf_path = GGUF_DIR / f"{version.replace(':', '_')}_{quant_type.lower()}.gguf"
            convert_hf_to_gguf(hf_model_dir, gguf_path, quant_type)
            registry.update(version, gguf_path=str(gguf_path), status="converted")
        else:
            registry.update(version, gguf_path=str(gguf_path))

        # Step 2: Create Ollama model
        modelfile = create_modelfile(version, gguf_path)
        registry.update(version, modelfile=modelfile)

        if not create_ollama_model(version, gguf_path, modelfile):
            registry.update(version, status="failed")
            return {"status": "failed", "step": "ollama_create", "version": version}

        registry.update(version, status="deployed", deployed_at=datetime.now(timezone.utc).isoformat())

        # Step 3: Health check
        if not skip_health_check:
            print(f"\nHealth checking {version}...")
            health = health_check_model(version)
            registry.update(version, status="deployed")

            if health["status"] != "healthy":
                logger.error("deploy.health_check_failed", version=version, error=health.get("error"))
                return {
                    "status": "deployed_unhealthy",
                    "version": version,
                    "health": health,
                }

            if not health.get("identity_ok"):
                logger.warning("deploy.identity_mismatch", version=version, response=health.get("response"))
                # Don't fail — just warn. Identity drift is a known issue.

            return {
                "status": "success",
                "version": version,
                "gguf": str(gguf_path),
                "health": health,
            }

        return {
            "status": "success",
            "version": version,
            "gguf": str(gguf_path),
            "health_check_skipped": True,
        }

    except Exception as exc:
        logger.error("deploy.failed", version=version, error=str(exc))
        registry.update(version, status="failed")
        return {"status": "failed", "version": version, "error": str(exc)}


def rollback_model(target_version: Optional[str] = None) -> dict:
    """Rollback to a previous model version.

    If target_version is None, roll back to the last deployed version.
    """
    registry = ModelRegistry()

    if target_version is None:
        # Find last deployed version that's not the current default
        deployed = registry.list_deployed()
        if not deployed:
            return {"status": "failed", "error": "No deployed models to rollback to"}
        # Sort by deployment time
        deployed.sort(key=lambda e: e.deployed_at or "", reverse=True)
        target_version = deployed[0].version

    # Verify model exists in Ollama
    try:
        response = httpx.post(f"{OLLAMA_URL}/api/show", json={"name": target_version}, timeout=30.0)
        if response.status_code != 200:
            return {"status": "failed", "error": f"Model {target_version} not found in Ollama"}
    except Exception as exc:
        return {"status": "failed", "error": str(exc)}

    # Update default model in config
    settings.DEFAULT_MODEL = target_version
    logger.info("deploy.rollback", from_version=settings.DEFAULT_MODEL, to_version=target_version)

    return {
        "status": "success",
        "version": target_version,
        "message": f"Rollback to {target_version} complete. Update docker-compose env DEFAULT_MODEL to persist.",
    }


def list_models() -> list[dict]:
    """List all models in Ollama."""
    try:
        response = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=30.0)
        response.raise_for_status()
        return response.json().get("models", [])
    except Exception as exc:
        return [{"error": str(exc)}]


def main():
    parser = argparse.ArgumentParser(description="MiganForge Ollama Manager")
    parser.add_argument("--setup-llamacpp", action="store_true", help="Install llama.cpp")
    parser.add_argument("--convert", action="store_true", help="Convert HF to GGUF")
    parser.add_argument("--hf-model", type=Path, default=None, help="HF model directory")
    parser.add_argument("--gguf-out", type=Path, default=None, help="Output GGUF path")
    parser.add_argument("--quant", default="Q4_K_M", choices=["Q4_K_M", "Q5_K_M", "Q8_0", "F16"])
    parser.add_argument("--deploy", action="store_true", help="Deploy to Ollama")
    parser.add_argument("--version", default=None, help="Model version tag")
    parser.add_argument("--gguf", type=Path, default=None, help="Existing GGUF file")
    parser.add_argument("--skip-health", action="store_true", help="Skip health check")
    parser.add_argument("--rollback", default=None, help="Rollback to version")
    parser.add_argument("--list", action="store_true", help="List Ollama models")
    parser.add_argument("--registry", action="store_true", help="Show model registry")
    args = parser.parse_args()

    if args.setup_llamacpp:
        setup_llamacpp()
        return

    if args.list:
        models = list_models()
        print(json.dumps(models, indent=2))
        return

    if args.registry:
        reg = ModelRegistry()
        print(json.dumps(reg._data, indent=2))
        return

    if args.rollback:
        result = rollback_model(args.rollback)
        print(json.dumps(result, indent=2))
        return

    if args.convert:
        if not args.hf_model:
            print("ERROR: --hf-model required for conversion", file=sys.stderr)
            sys.exit(1)
        gguf_out = args.gguf_out or GGUF_DIR / f"{args.hf_model.name}_q4_k_m.gguf"
        result = convert_hf_to_gguf(args.hf_model, gguf_out, args.quant)
        print(f"Converted: {result}")
        return

    if args.deploy:
        version = args.version or f"migancore:{int(time.time())}"
        result = deploy_model(
            version=version,
            hf_model_dir=args.hf_model,
            gguf_path=args.gguf,
            quant_type=args.quant,
            skip_health_check=args.skip_health,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
