"""Registry organ — build Ollama tools spec from skills config."""

import json
from typing import Any

import structlog

from services.config_loader import load_skills_config

logger = structlog.get_logger()


def build_ollama_tools_spec(skill_ids: list[str]) -> list[dict]:
    """Build Ollama-compatible tools specification from skill IDs.

    Loads skills.json and filters to only the requested skill_ids.
    Returns a list of dicts that Ollama's /api/chat endpoint accepts
    as the `tools` parameter.
    """
    all_skills = load_skills_config()
    spec: list[dict] = []

    for sid in skill_ids:
        skill = all_skills.get(sid)
        if not skill:
            logger.warning("tools.spec.skill_not_found", skill_id=sid)
            continue
        spec.append({
            "type": "function",
            "function": {
                "name": sid,
                "description": skill.get("description", ""),
                "parameters": skill.get("parameters", {"type": "object", "properties": {}}),
            },
        })

    logger.info("tools.spec.built", requested=len(skill_ids), resolved=len(spec))
    return spec
