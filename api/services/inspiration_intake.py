"""
Inspiration Intake.

Turns a creator-provided link or idea into a proposal-ready module backlog item.
This is synthesis only: no browsing, no GPU job, no code execution, no deploy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ModuleProfile:
    module_type: str
    label: str
    title_hint: str
    capability: str
    touched_paths: tuple[str, ...]
    suggested_gates: tuple[str, ...]


_PROFILES = {
    "video_generator": ModuleProfile(
        module_type="video_generator",
        label="Video Generator",
        title_hint="Video Generator module",
        capability="Generate or transform video through a queue-only, cost-gated module.",
        touched_paths=("docs/MODULE_GENERATORS_BACKLOG.md", "api/services/video_generation.py"),
        suggested_gates=(
            "cost_estimate",
            "gpu_budget_check",
            "license_check",
            "queue_check",
            "artifact_preview",
            "rollback_ready",
        ),
    ),
    "image_generator": ModuleProfile(
        module_type="image_generator",
        label="Image Generator",
        title_hint="Image Generator module",
        capability="Generate images from chat prompts with style, aspect ratio, seed, and artifact preview.",
        touched_paths=("docs/MODULE_GENERATORS_BACKLOG.md", "api/services/image_generation.py"),
        suggested_gates=("schema_check", "cost_estimate", "content_policy_check", "artifact_preview", "rollback_ready"),
    ),
    "artifact_builder": ModuleProfile(
        module_type="artifact_builder",
        label="Artifact Builder",
        title_hint="Artifact Builder module",
        capability="Build reusable HTML, markdown, JSON, prompt packs, docs, and eval artifacts from chat.",
        touched_paths=("docs/MODULE_GENERATORS_BACKLOG.md", "api/services/artifact_builder.py", "frontend/backlog.html"),
        suggested_gates=("schema_check", "preview_render", "syntax", "rollback_ready", "unit_tests"),
    ),
    "audio_voice_generator": ModuleProfile(
        module_type="audio_voice_generator",
        label="Audio and Voice Generator",
        title_hint="Audio and Voice Generator module",
        capability="Generate narration, voice, and audio drafts as reviewable artifacts.",
        touched_paths=("docs/MODULE_GENERATORS_BACKLOG.md", "api/services/audio_generation.py"),
        suggested_gates=("voice_policy_check", "artifact_preview", "cost_estimate", "rollback_ready"),
    ),
    "eval_pack_builder": ModuleProfile(
        module_type="eval_pack_builder",
        label="Eval Pack Builder",
        title_hint="Eval Pack Builder module",
        capability="Create regression probes and rubrics for every new module.",
        touched_paths=("docs/MODULE_GENERATORS_BACKLOG.md", "api/eval/module_eval_packs.py"),
        suggested_gates=("eval_exists", "baseline_recorded", "regression_check", "rollback_ready"),
    ),
    "tool_builder": ModuleProfile(
        module_type="tool_builder",
        label="Tool Builder",
        title_hint="Tool Builder module",
        capability="Propose small reusable tools with schema, handler, dry-run, tests, and rollback.",
        touched_paths=("docs/MODULE_GENERATORS_BACKLOG.md", "api/services/tool_executor.py", "config/skills.json"),
        suggested_gates=("contract_check", "data_boundary", "secret_scan", "unit_tests", "rollback_ready"),
    ),
}


def _classify_module(text: str) -> ModuleProfile:
    surface = text.lower()
    if any(term in surface for term in ("ltx", "video", "movie", "a2vid", "text-to-video", "image-to-video")):
        return _PROFILES["video_generator"]
    if any(term in surface for term in ("image", "gambar", "diffusion", "text-to-image")):
        return _PROFILES["image_generator"]
    if any(term in surface for term in ("artifact", "html", "markdown", "json", "doc", "slide", "spreadsheet")):
        return _PROFILES["artifact_builder"]
    if any(term in surface for term in ("audio", "voice", "tts", "speech", "narra", "sound")):
        return _PROFILES["audio_voice_generator"]
    if any(term in surface for term in ("eval", "judge", "rubric", "regression", "test pack")):
        return _PROFILES["eval_pack_builder"]
    return _PROFILES["tool_builder"]


def _source_name(url: str, notes: str) -> str:
    surface = f"{url} {notes}".lower()
    if "lightricks/ltx-2" in surface or "ltx-2" in surface:
        return "LTX-2"
    if url:
        host = url.split("//")[-1].split("/")[0]
        return host or "external inspiration"
    return "creator idea"


def synthesize_inspiration(url: str = "", notes: str = "") -> dict[str, Any]:
    """Return a proposal payload for the sandbox queue."""
    clean_url = (url or "").strip()
    clean_notes = (notes or "").strip()
    surface = f"{clean_url}\n{clean_notes}"
    profile = _classify_module(surface)
    source_name = _source_name(clean_url, clean_notes)

    problem = (
        f"Fahmi shared an inspiration source ({source_name}) that may teach MiganCore a new capability. "
        "The system should not copy or execute it blindly; it should convert the idea into a small, gated module proposal."
    )
    hypothesis = (
        f"Build a proposal-gated {profile.label}. Capability: {profile.capability} "
        f"First step: define request schema, artifact output, suggested gates, cost boundary, and rollback plan."
    )
    if clean_notes:
        hypothesis += f" Creator notes: {clean_notes[:500]}"

    return {
        "title": f"Inspiration: {profile.title_hint} from {source_name}",
        "problem": problem,
        "hypothesis": hypothesis,
        "touched_paths": list(profile.touched_paths),
        "tests": ["python -m pytest tests/test_inspiration_intake.py -q"],
        "rollback_plan": "Reject or archive this proposal; no live module is created by inspiration intake.",
        "source": "owner_command",
        "created_by": "inspiration_intake",
        "metadata": {
            "intake_type": "inspiration",
            "module_type": profile.module_type,
            "module_label": profile.label,
            "source_url": clean_url,
            "source_name": source_name,
            "creator_notes": clean_notes,
            "suggested_gates": list(profile.suggested_gates),
        },
    }
