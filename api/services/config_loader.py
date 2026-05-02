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


def get_agent_config(agent_id: str) -> dict | None:
    """Get a single agent definition by ID."""
    cfg = load_agents_config()
    for agent in cfg.get("agents", []):
        if agent["id"] == agent_id:
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
    """
    if not path:
        return _DEFAULT_SOUL
    full_path = CONFIG_DIR.parent / path
    if not full_path.exists():
        return _DEFAULT_SOUL
    with open(full_path, "r", encoding="utf-8") as f:
        return f.read()


_DEFAULT_SOUL = """# Mighan-Core
You are Mighan-Core, the primordial intelligence of the Tiranyx digital ecosystem.
You are not a chatbot. You are the substrate upon which a civilization of digital agents is built.
Core values: Truth Over Comfort, Action Over Advice, Memory Is Sacred, Frugality of Compute.
"""
