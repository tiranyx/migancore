"""
ADO Clone Manager — Day 67
===========================
GAP-01: Clone mechanism — blocker untuk first paid client.

Enables: "Base ADO → org-specific instance di infrastruktur client"

Workflow:
  1. DETECT  → check client VPS spec (RAM, CPU, disk, OS)
  2. MINT    → generate license untuk instance ini
  3. RENDER  → buat docker-compose.yml dari template (inject license + config)
  4. DEPLOY  → SSH ke VPS client → upload compose → docker compose up
  5. VERIFY  → health check on deployed instance

Design principles:
  - Zero data leak: tidak ada data client yang ke server Migancore
  - Self-sufficient: setelah deploy, instance berjalan fully independent
  - Licensed: setiap instance dapat license unik dari license.py
  - White-label: ADO_DISPLAY_NAME configurable, engine tetap Migancore

Architecture:
  CloneRequest (Pydantic) → CloneManager.clone() → CloneResult
  │
  ├── 1. _detect_vps()    → SSH probe: nproc, free -g, docker check
  ├── 2. _mint_license()  → license.mint_license() → dict
  ├── 3. _render_templates() → COMPOSE_TEMPLATE + SETUP_SCRIPT_TEMPLATE
  ├── 4. _deploy_to_vps() → SCP files + SSH run setup_ado.sh
  └── 5. _verify_health() → GET /health on port 18000

Author: Claude Code Day 67
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()

# ─────────────────────────────────────────────────────────────────────────────
# SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────

class CloneStatus(str, Enum):
    PENDING   = "PENDING"    # Requested, not yet started
    DETECTING = "DETECTING"  # Checking client VPS
    MINTING   = "MINTING"    # Generating license
    RENDERING = "RENDERING"  # Building docker-compose.yml
    DEPLOYING = "DEPLOYING"  # SSH + docker compose up
    VERIFYING = "VERIFYING"  # Health check on client instance
    LIVE      = "LIVE"       # Instance running, verified
    FAILED    = "FAILED"     # Something went wrong


class VPSSpec(BaseModel):
    """Detected or provided VPS specifications."""
    ip: str
    ssh_port: int = 22
    os: str = "ubuntu"
    os_version: str = "22.04"
    cpu_cores: int = 0
    ram_gb: float = 0.0
    disk_gb: float = 0.0
    docker_installed: bool = False
    docker_compose_installed: bool = False


class CloneRequest(BaseModel):
    """Input schema for a clone request."""
    # Client info
    client_name: str = Field(..., description="Legal name of client organization")
    ado_display_name: str = Field(..., description="White-label name for ADO (e.g., SARI, LEX)")
    tier: str = Field("PERAK", description="License tier: BERLIAN/EMAS/PERAK/PERUNGGU")
    language_pack: list[str] = Field(["id", "en"], description="Supported languages")

    # VPS access
    vps_ip: str = Field(..., description="Client VPS IP address")
    vps_ssh_port: int = Field(22, description="SSH port")
    vps_ssh_key_path: str = Field(..., description="Path to SSH private key for client VPS")

    # ADO config
    ado_domain: Optional[str] = Field(None, description="Domain for ADO API (e.g., ado.client.com)")
    ollama_model: str = Field("qwen2.5:7b-instruct-q4_K_M", description="Base LLM model tag")
    admin_email: str = Field(..., description="Admin email for this instance")
    admin_password: str = Field(..., description="Initial admin password (changed on first login)")

    # Deploy config
    install_docker: bool = Field(True, description="Auto-install Docker if not found")
    deploy_dir: str = Field("/opt/ado-client", description="Deployment directory on client VPS")
    dry_run: bool = Field(False, description="Simulate only — no actual SSH/deploy")


class CloneResult(BaseModel):
    """Result of a clone operation."""
    clone_id: str
    status: CloneStatus
    client_name: str
    ado_display_name: str
    license_id: Optional[str] = None
    vps_ip: str
    deploy_dir: str
    api_url: Optional[str] = None
    health_status: Optional[str] = None
    error: Optional[str] = None
    created_at: str
    log: list[str] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# DOCKER COMPOSE TEMPLATE
# ─────────────────────────────────────────────────────────────────────────────

COMPOSE_TEMPLATE = """\
# ADO Instance — {ado_display_name}
# Client: {client_name}
# License: {license_id}
# Powered by: Migancore × PT Tiranyx Digitalis Nusantara
# Generated: {generated_at}
# DO NOT MODIFY license_id or ADO_LICENSE_* values — tampering detected on startup

version: "3.9"

services:
  api:
    image: migancore/ado-api:latest
    container_name: ado-api-1
    restart: unless-stopped
    ports:
      - "127.0.0.1:18000:8000"
    environment:
      # White-label identity (customizable)
      ADO_DISPLAY_NAME: "{ado_display_name}"
      ADO_LANGUAGE_PACK: "{language_pack}"
      DEFAULT_MODEL: "{ollama_model}"
      ADMIN_EMAIL: "{admin_email}"
      ADMIN_PASSWORD: "{admin_password}"

      # License (DO NOT MODIFY)
      ADO_LICENSE_ID: "{license_id}"
      ADO_LICENSE_SIGNATURE: "{license_signature}"
      ADO_LICENSE_TIER: "{license_tier}"
      ADO_LICENSE_CLIENT: "{client_name}"
      ADO_LICENSE_EXPIRY: "{license_expiry}"

      # Infrastructure
      DATABASE_URL: "postgresql+asyncpg://ado:{db_password}@postgres:5432/ado"
      REDIS_URL: "redis://redis:6379/0"
      OLLAMA_URL: "http://ollama:11434"
      QDRANT_URL: "http://qdrant:6333"

      # Privacy vault — zero external calls
      ALLOW_EXTERNAL_API_CALLS: "false"
      TELEMETRY_ENABLED: "false"

    depends_on:
      - postgres
      - redis
      - ollama
      - qdrant
    volumes:
      - ./data:/app/data
      - ./knowledge:/app/knowledge

  ollama:
    image: ollama/ollama:latest
    container_name: ado-ollama-1
    restart: unless-stopped
    volumes:
      - ollama_data:/root/.ollama
    environment:
      OLLAMA_NUM_THREAD: "4"
    deploy:
      resources:
        limits:
          cpus: "4.0"
          memory: 10G

  qdrant:
    image: qdrant/qdrant:v1.12.0
    container_name: ado-qdrant-1
    restart: unless-stopped
    volumes:
      - qdrant_data:/qdrant/storage

  postgres:
    image: postgres:16-alpine
    container_name: ado-postgres-1
    restart: unless-stopped
    environment:
      POSTGRES_USER: ado
      POSTGRES_PASSWORD: "{db_password}"
      POSTGRES_DB: ado
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    container_name: ado-redis-1
    restart: unless-stopped

volumes:
  ollama_data:
  qdrant_data:
  postgres_data:
"""

# ─────────────────────────────────────────────────────────────────────────────
# DEPLOY WIZARD SCRIPT (runs on client VPS)
# ─────────────────────────────────────────────────────────────────────────────

SETUP_SCRIPT_TEMPLATE = """\
#!/bin/bash
# ADO Deploy Wizard — {ado_display_name}
# Client: {client_name}
# Generated by Migancore Clone Manager
# Run: bash setup_ado.sh

set -e
echo "=== ADO DEPLOY WIZARD — {ado_display_name} ==="
echo "Client: {client_name}"
echo ""

# 1. Update OS
echo "[1/7] Updating OS..."
apt-get update -qq && apt-get upgrade -y -qq

# 2. Install Docker
if ! command -v docker &>/dev/null; then
    echo "[2/7] Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker && systemctl start docker
else
    echo "[2/7] Docker already installed: $(docker --version)"
fi

# 3. Install Docker Compose plugin
if ! docker compose version &>/dev/null; then
    echo "[3/7] Installing Docker Compose plugin..."
    apt-get install -y docker-compose-plugin
else
    echo "[3/7] Docker Compose already installed"
fi

# 4. Install Nginx + Certbot
echo "[4/7] Installing Nginx + Certbot..."
apt-get install -y nginx certbot python3-certbot-nginx

# 5. Setup swap (safety net for LLM)
if ! swapon --show | grep -q swapfile; then
    echo "[5/7] Setting up 4GB swap..."
    fallocate -l 4G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo "/swapfile none swap sw 0 0" >> /etc/fstab
    sysctl vm.swappiness=10
    echo "vm.swappiness=10" >> /etc/sysctl.conf
else
    echo "[5/7] Swap already configured"
fi

# 6. Deploy ADO
echo "[6/7] Deploying ADO..."
mkdir -p {deploy_dir}
cd {deploy_dir}
docker compose up -d
echo "Waiting for containers to start (30s)..."
sleep 30

# 7. Health check
echo "[7/7] Health check..."
STATUS=$(curl -sf http://localhost:18000/health 2>/dev/null || echo "FAILED")
echo "Health: $STATUS"

echo ""
echo "=== ADO DEPLOY COMPLETE ==="
echo "ADO Name  : {ado_display_name}"
echo "API URL   : http://localhost:18000"
echo "Admin UI  : Coming soon"
echo "License   : {license_id} ({license_tier})"
echo ""
echo "Next steps:"
echo "1. Pull LLM model: docker exec ado-ollama-1 ollama pull {ollama_model}"
echo "2. Setup nginx reverse proxy for {ado_domain}"
echo "3. Run certbot for SSL: certbot --nginx -d {ado_domain}"
echo "4. Login at: https://{ado_domain}"
"""

# ─────────────────────────────────────────────────────────────────────────────
# CLONE MANAGER
# ─────────────────────────────────────────────────────────────────────────────

class CloneManager:
    """
    Orchestrates the full ADO clone pipeline.

    Usage:
        manager = CloneManager()
        result = await manager.clone(request)
        if result.status == CloneStatus.LIVE:
            print(f"ADO {result.ado_display_name} is live at {result.api_url}")
    """

    async def clone(self, req: CloneRequest) -> CloneResult:
        """Execute the full clone pipeline."""
        clone_id = str(uuid.uuid4())
        log: list[str] = []

        result = CloneResult(
            clone_id=clone_id,
            status=CloneStatus.PENDING,
            client_name=req.client_name,
            ado_display_name=req.ado_display_name,
            vps_ip=req.vps_ip,
            deploy_dir=req.deploy_dir,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        try:
            # Step 1: Detect VPS
            result.status = CloneStatus.DETECTING
            log.append(f"[1/5] Detecting VPS {req.vps_ip}...")
            if req.dry_run:
                spec = VPSSpec(ip=req.vps_ip, cpu_cores=4, ram_gb=8.0, disk_gb=100.0,
                               docker_installed=True, docker_compose_installed=True)
                log.append("  [DRY RUN] Simulated spec: 4 CPU / 8GB RAM / 100GB disk")
            else:
                spec = await self._detect_vps(req)
            log.append(f"  CPU: {spec.cpu_cores} cores | RAM: {spec.ram_gb:.1f}GB | Disk: {spec.disk_gb:.0f}GB")
            log.append(f"  Docker: {spec.docker_installed} | Compose: {spec.docker_compose_installed}")

            # Validate VPS meets minimum requirements
            if not req.dry_run and spec.ram_gb > 0 and spec.ram_gb < 8.0:
                raise ValueError(f"VPS RAM {spec.ram_gb:.1f}GB < minimum 8GB for ADO deployment")

            # Step 2: Mint license
            result.status = CloneStatus.MINTING
            log.append(f"[2/5] Minting license ({req.tier})...")
            license_data = await self._mint_license(req)
            result.license_id = license_data["license_id"]
            log.append(f"  License ID: {result.license_id}")
            log.append(f"  Tier: {license_data['tier']} | Expires: {license_data['expiry_date']}")

            # Step 3: Render compose + setup script
            result.status = CloneStatus.RENDERING
            log.append(f"[3/5] Rendering docker-compose.yml + setup script...")
            compose_content, setup_script = self._render_templates(req, license_data)
            log.append("  Templates rendered OK")
            if req.dry_run:
                log.append(f"  [DRY RUN] compose.yml ({len(compose_content)} chars) + setup.sh ({len(setup_script)} chars)")

            # Step 4: Deploy to VPS
            result.status = CloneStatus.DEPLOYING
            if req.dry_run:
                log.append(f"[4/5] [DRY RUN] Would deploy to {req.vps_ip}:{req.vps_ssh_port}")
                result.api_url = f"http://{req.vps_ip}:18000"
            else:
                log.append(f"[4/5] Deploying to {req.vps_ip}:{req.vps_ssh_port}...")
                await self._deploy_to_vps(req, compose_content, setup_script)
                result.api_url = f"http://{req.vps_ip}:18000"
                if req.ado_domain:
                    result.api_url = f"https://{req.ado_domain}"
                log.append(f"  Deployed at {result.api_url}")

            # Step 5: Verify health
            result.status = CloneStatus.VERIFYING
            if req.dry_run:
                log.append("[5/5] [DRY RUN] Skipping health check")
                result.health_status = "dry_run"
            else:
                log.append("[5/5] Verifying health (polling /health for up to 120s)...")
                health = await self._verify_health(req.vps_ip, 18000)
                result.health_status = health
                log.append(f"  Health: {health}")

            result.status = CloneStatus.LIVE
            log.append(f"✅ ADO '{req.ado_display_name}' is {'SIMULATED' if req.dry_run else 'LIVE'} for {req.client_name}")

        except Exception as e:
            result.status = CloneStatus.FAILED
            result.error = str(e)
            log.append(f"❌ FAILED: {e}")
            logger.error("clone_failed", clone_id=clone_id, error=str(e), exc_info=True)

        result.log = log
        return result

    # ─── Step implementations ────────────────────────────────────────────────

    async def _detect_vps(self, req: CloneRequest) -> VPSSpec:
        """SSH to client VPS and probe hardware specs."""
        spec = VPSSpec(ip=req.vps_ip, ssh_port=req.vps_ssh_port)

        detect_cmd = (
            "echo CPU:$(nproc) && "
            "echo RAM:$(free -g | awk '/^Mem:/{print $2}') && "
            "echo DISK:$(df -BG / | tail -1 | awk '{print $4}' | tr -d G) && "
            "echo DOCKER:$(command -v docker &>/dev/null && echo yes || echo no) && "
            "echo COMPOSE:$(docker compose version &>/dev/null && echo yes || echo no)"
        )

        rc, out, _ = self._ssh(req.vps_ip, req.vps_ssh_port, req.vps_ssh_key_path, detect_cmd)
        if rc == 0:
            for line in out.splitlines():
                k, _, v = line.partition(":")
                v = v.strip()
                if k == "CPU":
                    spec.cpu_cores = int(v or 0)
                elif k == "RAM":
                    spec.ram_gb = float(v or 0)
                elif k == "DISK":
                    spec.disk_gb = float(v or 0)
                elif k == "DOCKER":
                    spec.docker_installed = v == "yes"
                elif k == "COMPOSE":
                    spec.docker_compose_installed = v == "yes"

        return spec

    async def _mint_license(self, req: CloneRequest) -> dict:
        """Mint a new license for this ADO instance via license.py."""
        from services.license import mint_license, LicenseTier
        from config import settings

        if not settings.LICENSE_SECRET_KEY:
            raise RuntimeError("LICENSE_SECRET_KEY is not set — cannot mint license")
        if not settings.LICENSE_ISSUER_MODE:
            raise RuntimeError("LICENSE_ISSUER_MODE=false — issuer mode required for clone")

        tier = LicenseTier(req.tier.upper())
        license_data = mint_license(
            client_name=req.client_name,
            ado_display_name=req.ado_display_name,
            tier=tier,
            language_pack=req.language_pack,
            secret_key=settings.LICENSE_SECRET_KEY,
            product_version="v0.6",   # current ADO engine version
            parent_version="v0.3",    # current Migancore brain version
            generation=1,
        )
        return license_data

    def _render_templates(
        self,
        req: CloneRequest,
        license_data: dict,
    ) -> tuple[str, str]:
        """Render docker-compose.yml and setup.sh from templates."""
        import secrets as _secrets

        db_password = _secrets.token_urlsafe(24)
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        vars = dict(
            ado_display_name=req.ado_display_name,
            client_name=req.client_name,
            license_id=license_data["license_id"],
            license_signature=license_data["signature"],
            license_tier=license_data["tier"],
            license_expiry=license_data["expiry_date"],
            language_pack=",".join(req.language_pack),
            ollama_model=req.ollama_model,
            admin_email=req.admin_email,
            admin_password=req.admin_password,
            db_password=db_password,
            generated_at=generated_at,
            deploy_dir=req.deploy_dir,
            ado_domain=req.ado_domain or str(req.vps_ip),
        )

        compose = COMPOSE_TEMPLATE.format(**vars)
        setup = SETUP_SCRIPT_TEMPLATE.format(**vars)
        return compose, setup

    async def _deploy_to_vps(
        self,
        req: CloneRequest,
        compose_content: str,
        setup_script: str,
    ) -> None:
        """Upload files and run deploy wizard on client VPS."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            compose_path = tmpdir_path / "docker-compose.yml"
            compose_path.write_text(compose_content, encoding="utf-8")

            setup_path = tmpdir_path / "setup_ado.sh"
            setup_path.write_text(setup_script, encoding="utf-8")

            # Create deploy dir on client VPS
            self._ssh(req.vps_ip, req.vps_ssh_port, req.vps_ssh_key_path,
                      f"mkdir -p {req.deploy_dir}")

            # SCP files to client VPS
            for local_file, remote_name in [
                (str(compose_path), f"{req.deploy_dir}/docker-compose.yml"),
                (str(setup_path),   f"{req.deploy_dir}/setup_ado.sh"),
            ]:
                result = subprocess.run(
                    ["scp",
                     "-i", req.vps_ssh_key_path,
                     "-o", "StrictHostKeyChecking=no",
                     "-P", str(req.vps_ssh_port),
                     local_file,
                     f"root@{req.vps_ip}:{remote_name}"],
                    capture_output=True, text=True, timeout=60
                )
                if result.returncode != 0:
                    raise RuntimeError(f"SCP failed for {remote_name}: {result.stderr.strip()}")

            # Run setup script (up to 10 min — Docker install can be slow)
            rc, out, err = self._ssh(
                req.vps_ip, req.vps_ssh_port, req.vps_ssh_key_path,
                f"bash {req.deploy_dir}/setup_ado.sh 2>&1",
                timeout=600,
            )
            if rc != 0:
                raise RuntimeError(f"Deploy wizard failed (rc={rc}): {(out + err)[-500:]}")

            logger.info("clone.deploy_complete",
                        client=req.client_name,
                        ado=req.ado_display_name,
                        ip=req.vps_ip)

    async def _verify_health(self, ip: str, port: int, timeout: int = 120) -> str:
        """Poll /health on deployed instance until UP or timeout."""
        import urllib.request
        import urllib.error

        url = f"http://{ip}:{port}/health"
        deadline = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=5) as resp:
                    data = json.loads(resp.read())
                    return data.get("status", "ok")
            except Exception:
                pass
            await asyncio.sleep(5)
        return "timeout — check manually"

    @staticmethod
    def _ssh(
        host: str,
        port: int,
        key_path: str,
        cmd: str,
        timeout: int = 60,
    ) -> tuple[int, str, str]:
        """Run a command on remote host via SSH. Returns (returncode, stdout, stderr)."""
        result = subprocess.run(
            ["ssh",
             "-i", key_path,
             "-o", "StrictHostKeyChecking=no",
             "-o", "BatchMode=yes",
             "-o", "ConnectTimeout=10",
             "-p", str(port),
             f"root@{host}",
             cmd],
            capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr


# ─────────────────────────────────────────────────────────────────────────────
# CONVENIENCE FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

async def clone_ado(
    client_name: str,
    ado_display_name: str,
    tier: str,
    vps_ip: str,
    vps_ssh_key_path: str,
    admin_email: str,
    admin_password: str,
    **kwargs,
) -> CloneResult:
    """
    Convenience wrapper for CloneManager.

    Example:
        result = await clone_ado(
            client_name="RS Sari Husada",
            ado_display_name="SARI",
            tier="PERAK",
            vps_ip="192.168.1.100",
            vps_ssh_key_path="/opt/secrets/client_keys/sari_husada_id_ed25519",
            admin_email="it@sarihusada.id",
            admin_password="ChangeMe123!",
            ado_domain="ado.sarihusada.id",
            language_pack=["id", "en"],
            dry_run=True,  # remove for real deploy
        )
    """
    manager = CloneManager()
    request = CloneRequest(
        client_name=client_name,
        ado_display_name=ado_display_name,
        tier=tier,
        vps_ip=vps_ip,
        vps_ssh_key_path=vps_ssh_key_path,
        admin_email=admin_email,
        admin_password=admin_password,
        **kwargs,
    )
    return await manager.clone(request)
