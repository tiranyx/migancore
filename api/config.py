"""
MiganCore API Configuration
Pydantic-settings based configuration with environment variable support.
"""

import os
from pathlib import Path
from typing import Optional

from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = False

    # Security
    JWT_PRIVATE_KEY_PATH: str = "/etc/ado/keys/private.pem"
    JWT_PUBLIC_KEY_PATH: str = "/etc/ado/keys/public.pem"
    JWT_ALGORITHM: str = "RS256"
    # Day 43: bumped 15 -> 60 min (was forcing user 401 errors mid-debug session).
    # Frontend now does silent refresh on 401 anyway, but longer TTL = fewer
    # refresh round-trips + better UX during streaming chats (CPU 7B 30-90s).
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ISSUER: str = "https://api.migancore.com"
    JWT_AUDIENCE: str = "migancore-api"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://ado_app:changeme@postgres:5432/ado"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Redis
    REDIS_URL: str = "redis://:changeme@redis:6379/0"

    # Qdrant
    QDRANT_URL: str = "http://qdrant:6333"
    QDRANT_API_KEY: Optional[str] = None

    # Ollama
    OLLAMA_URL: str = "http://ollama:11434"
    DEFAULT_MODEL: str = "migancore:0.4"

    # Letta
    LETTA_URL: str = "http://letta:8283"
    LETTA_PASSWORD: Optional[str] = None

    # Admin
    ADMIN_SECRET_KEY: str = ""  # X-Admin-Key header value; empty = admin disabled

    # External APIs — Tool Expansion (Day 24)
    FAL_KEY: Optional[str] = None          # fal.ai API key for image/video generation
    WORKSPACE_DIR: str = "/app/workspace"  # Sandboxed file system for read_file/write_file

    # Day 27: ElevenLabs TTS
    ELEVENLABS_KEY: Optional[str] = None
    ELEVENLABS_VOICE_ID: str = "pIdeS8l1cmJzzqqt7NRc"  # User's "Menit" voice (Day 28 update)
    ELEVENLABS_MODEL: str = "eleven_flash_v2_5"        # ~75ms TTFB, free-tier compatible

    # Day 28: Teacher API keys for distillation pipeline
    ANTHROPIC_API_KEY: Optional[str] = None    # Claude (judge + alt teacher)
    OPENAI_API_KEY: Optional[str] = None       # GPT (alt teacher)
    KIMI_API_KEY: Optional[str] = None         # Moonshot Kimi K2 (primary teacher — bilingual ID)
    GEMINI_API_KEY: Optional[str] = None       # Google Gemini (cheap teacher)
    # Day 67: Search API keys for cognitive tools
    TAVILY_API_KEY: Optional[str] = None       # Tavily real-time search (tavily_search tool)
    SERPER_API_KEY: Optional[str] = None       # Serper Google search (serper_search tool)


    # Distillation budget caps
    DISTILL_BUDGET_USD_HARD_CAP: float = 5.0   # Pipeline aborts if estimated spend > this
    DISTILL_MARGIN_THRESHOLD: float = 2.0      # Only keep pairs with judge_diff >= this

    # Day 37: CAI judge backend selection (research: 2-of-N quorum > single judge, -30% bad pairs)
    # Options: "ollama" (default, free, slow ~10-20s), "quorum" (Kimi+Gemini, fast 1-2s, ~$0.001/critique)
    # Fallback chain on quorum mode: Kimi -> Gemini -> Ollama (graceful degrade)
    JUDGE_BACKEND: str = "ollama"
    # Quorum requires both judges to agree on revision_needed (score <= threshold both)
    # If only one says yes, defer to Ollama tiebreak (when fallback enabled)
    JUDGE_QUORUM_REQUIRE_CONSENSUS: bool = True
    DISTILL_MAX_OUTPUT_TOKENS: int = 600       # Per teacher response cap

    # Day 27: API Keys (server-side pepper for HMAC)
    # If empty, falls back to hash of JWT private key (dev convenience).
    # Production: set explicit 32+ char secret.
    API_KEY_PEPPER: Optional[str] = None

    # Day 27: Memory pruning daemon
    MEMORY_PRUNE_DAYS: int = 30           # Delete points older than this many days
    MEMORY_PRUNE_IMPORTANCE_MAX: float = 0.7  # Only prune points BELOW this importance

    # Day 61: ADO License System (inspired by Ixonomic coin minting)
    # LICENSE_PATH: path to license.json on the deployed ADO instance
    # LICENSE_SECRET_KEY: HMAC-SHA256 key for offline validation (set per-instance)
    # LICENSE_DEMO_MODE: if True, ADO runs without license (beta/evaluation instances)
    LICENSE_PATH: str = "/opt/ado/license.json"
    LICENSE_SECRET_KEY: Optional[str] = None    # Set in .env — NEVER commit
    LICENSE_DEMO_MODE: bool = True              # True = run without license (beta)
    # ADO_DISPLAY_NAME: white-label override (fallback if no license — for migancore.com)
    ADO_DISPLAY_NAME: str = "Migan"
    # Day 62 (Codex review): ISSUER MODE gate
    # LICENSE_ISSUER_MODE=true → /v1/license/mint and /v1/license/batch are active
    # Set ONLY on api.migancore.com (the parent platform that mints licenses).
    # All child ADO deployments: leave unset/false → those routes return 404.
    # Prevents child ADO from forging licenses if LICENSE_INTERNAL_KEY is exposed.
    # Future: migrate to Ed25519 asymmetric signature for BERLIAN air-gapped tier.
    LICENSE_ISSUER_MODE: bool = False

    # Observability
    ENVIRONMENT: str = Field(default="production", pattern="^(development|staging|production|testing)$")
    LOG_LEVEL: str = "INFO"

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()


# ---------------------------------------------------------------------------
# Day 48 [H7] — Fail-safe credential check at import time.
# Prevents accidental production deploy with hardcoded "changeme" defaults.
# ---------------------------------------------------------------------------
def _assert_no_default_creds() -> None:
    """Crash startup if production env still uses placeholder credentials.

    Production = ENVIRONMENT='production'. Any "changeme" or empty critical
    secret triggers ImportError at module load (fast-fail beats silent
    accept-and-leak).
    """
    if settings.ENVIRONMENT != "production":
        return
    bad = []
    # DATABASE_URL must not contain :changeme@
    if ":changeme@" in (settings.DATABASE_URL or ""):
        bad.append("DATABASE_URL still has ':changeme@' (default password)")
    # REDIS_URL same check (only flag if password segment present)
    if ":changeme@" in (settings.REDIS_URL or ""):
        bad.append("REDIS_URL still has ':changeme@' (default password)")
    # ADMIN_SECRET_KEY must be either set OR explicitly empty (admin-disabled)
    if settings.ADMIN_SECRET_KEY and len(settings.ADMIN_SECRET_KEY) < 16:
        bad.append("ADMIN_SECRET_KEY is shorter than 16 chars — increase entropy")
    if bad:
        raise RuntimeError(
            "Refusing to start — default/weak credentials detected in production:\n  - "
            + "\n  - ".join(bad)
            + "\nSet real values via .env or container env vars before deploy."
        )


_assert_no_default_creds()


def load_jwt_keys() -> tuple[str, str]:
    """Load RSA private and public keys from filesystem."""
    private_path = Path(settings.JWT_PRIVATE_KEY_PATH)
    public_path = Path(settings.JWT_PUBLIC_KEY_PATH)

    if not private_path.exists():
        raise FileNotFoundError(f"JWT private key not found: {private_path}")
    if not public_path.exists():
        raise FileNotFoundError(f"JWT public key not found: {public_path}")

    private_key = private_path.read_text(encoding="utf-8")
    public_key = public_path.read_text(encoding="utf-8")
    return private_key, public_key
