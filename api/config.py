"""
MiganCore API Configuration
Pydantic-settings based configuration with environment variable support.
"""

import os
from pathlib import Path
from typing import Optional

from pydantic import Field
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
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
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
    DEFAULT_MODEL: str = "qwen2.5:7b-instruct-q4_K_M"

    # Letta
    LETTA_URL: str = "http://letta:8283"
    LETTA_PASSWORD: Optional[str] = None

    # Admin
    ADMIN_SECRET_KEY: str = ""  # X-Admin-Key header value; empty = admin disabled

    # External APIs — Tool Expansion (Day 24)
    FAL_KEY: Optional[str] = None          # fal.ai API key for image/video generation
    WORKSPACE_DIR: str = "/app/workspace"  # Sandboxed file system for read_file/write_file

    # Observability
    ENVIRONMENT: str = Field(default="production", pattern="^(development|staging|production)$")
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()


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
