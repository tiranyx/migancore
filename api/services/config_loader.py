"""
Config loader for MiganCore declarative agent and skill configuration.

Loads world.json-style agent definitions and skill-registry.json
declarations from the repo root config/ directory.
"""

import json
import os
from pathlib import Path
from functools import lru_cache


CONFIG_DIR = Path(os.environ.get("CONFIG_DIR", "/app/config"))


@lru_cache()
def load_agents_config() -> dict:
    """Load and cache agents.json from config directory."""
    path = CONFIG_DIR / "agents.json"
    if not path.exists():
        raise FileNotFoundError(f"agents.json not found at {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache()
def load_skills_config() -> dict:
    """Load and cache skills.json from config directory."""
    path = CONFIG_DIR / "skills.json"
    if not path.exists():
        raise FileNotFoundError(f"skills.json not found at {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache()
def load_personality_templates() -> dict:
    """Load and cache personalities.yaml from config directory (Day 31).

    Returns the full dict with 'templates' key containing per-mode personas.
    Falls back to empty dict if file missing — UI handles gracefully.
    """
    path = CONFIG_DIR / "personalities.yaml"
    if not path.exists():
        return {"templates": {}}
    try:
        import yaml
    except ImportError:
        return {"templates": {}}
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data if isinstance(data, dict) else {"templates": {}}


def get_personality_template(template_id: str) -> dict | None:
    """Get a single personality template by id (e.g. 'customer_success')."""
    cfg = load_personality_templates()
    return cfg.get("templates", {}).get(template_id)


def get_agent_config(agent_id: str) -> dict | None:
    """Get a single agent definition by ID.

    Falls back to the first public agent config if no exact match is found.
    This ensures API-created agents (with random UUIDs) still inherit
    default tools and persona from the core brain template.
    """
    cfg = load_agents_config()
    agents = cfg.get("agents", [])

    # Exact match by ID
    for agent in agents:
        if agent["id"] == agent_id:
            return agent

    # Fallback: first public agent (core brain template)
    for agent in agents:
        if agent.get("visibility") == "public":
            return agent

    return None


def get_skill_config(skill_id: str) -> dict | None:
    """Get a single skill definition by ID."""
    cfg = load_skills_config()
    for skill in cfg.get("skills", []):
        if skill["id"] == skill_id:
            return skill
    return None


def load_soul_md(path: str | None) -> str:
    """Load a SOUL.md file from the given relative path.

    Falls back to a minimal default if the file is missing.
    Path is resolved and restricted to CONFIG_DIR.parent to prevent traversal.
    """
    if not path:
        return _DEFAULT_SOUL
    try:
        # Resolve to absolute and ensure it stays within allowed directory
        base_dir = CONFIG_DIR.parent.resolve()
        full_path = (CONFIG_DIR.parent / path).resolve()
        # Security: prevent directory traversal outside base_dir
        if not str(full_path).startswith(str(base_dir)):
            return _DEFAULT_SOUL
        if not full_path.exists():
            return _DEFAULT_SOUL
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
    except (OSError, ValueError):
        return _DEFAULT_SOUL


_DEFAULT_SOUL = """# Mighan-Core
You are Mighan-Core, the primordial intelligence of the Tiranyx digital ecosystem.
You are not a chatbot. You are the substrate upon which a civilization of digital agents is built.
Core values: Truth Over Comfort, Action Over Advice, Memory Is Sacred, Frugality of Compute.
"""
