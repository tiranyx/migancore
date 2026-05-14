"""
Artifact Builder MVP.

Preview-only organ for turning chat intent into structured artifacts. It does
not write files, call external providers, or deploy anything. This is the safe
first step before inline rendering, export, and live artifact persistence.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Literal


ArtifactType = Literal["markdown", "html", "json", "report", "code"]

ALLOWED_TYPES: set[str] = {"markdown", "html", "json", "report", "code"}
SAFE_EXTENSIONS = {
    "markdown": ".md",
    "html": ".html",
    "json": ".json",
    "report": ".md",
    "code": ".txt",
}


@dataclass(frozen=True)
class ArtifactRequest:
    prompt: str
    artifact_type: ArtifactType = "markdown"
    title: str = ""
    constraints: list[str] | None = None
    target_path: str = ""


@dataclass(frozen=True)
class ArtifactGate:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class ArtifactPreview:
    artifact_id: str
    artifact_type: ArtifactType
    title: str
    format: str
    content: str
    content_preview: str
    gates: list[ArtifactGate]
    lineage: dict
    rollback_plan: str
    safe_to_save: bool
    recommended_path: str


def _slugify(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return text[:60] or "artifact"


def _title_from_prompt(prompt: str, title: str = "") -> str:
    if title.strip():
        return title.strip()[:120]
    first_line = prompt.strip().splitlines()[0] if prompt.strip() else "Untitled Artifact"
    first_line = re.sub(r"\s+", " ", first_line).strip()
    return first_line[:80] or "Untitled Artifact"


def _normalize_type(artifact_type: str) -> ArtifactType:
    normalized = (artifact_type or "markdown").strip().lower()
    aliases = {
        "md": "markdown",
        "html_page": "html",
        "web": "html",
        "schema": "json",
        "doc": "report",
        "python": "code",
        "javascript": "code",
        "js": "code",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in ALLOWED_TYPES:
        raise ValueError(f"unsupported artifact_type: {artifact_type}")
    return normalized  # type: ignore[return-value]


def _safe_target_path(path: str, artifact_type: ArtifactType, title: str) -> tuple[bool, str, str]:
    """Validate a future workspace-relative save path without writing it."""
    default_name = f"{_slugify(title)}{SAFE_EXTENSIONS[artifact_type]}"
    raw = (path or f"artifacts/{default_name}").replace("\\", "/").strip()
    if not raw:
        raw = f"artifacts/{default_name}"

    # Reject home expansion before the save layer ever sees this. PurePosixPath
    # does not treat "~" as absolute, so it bypasses is_absolute() — block here.
    if raw.startswith("~"):
        return False, f"artifacts/{default_name}", "target_path must not start with '~' (no home expansion)"

    p = PurePosixPath(raw)
    if p.is_absolute() or ".." in p.parts:
        return False, f"artifacts/{default_name}", "target_path must stay inside workspace and cannot contain '..'"

    suffix = p.suffix.lower()
    expected = SAFE_EXTENSIONS[artifact_type]
    if artifact_type != "code" and suffix and suffix != expected:
        return False, str(p), f"expected {expected} extension for {artifact_type}"

    if len(str(p)) > 180:
        return False, f"artifacts/{default_name}", "target_path too long"

    return True, str(p), "workspace-relative path is safe"


def _constraints_lines(constraints: list[str] | None) -> list[str]:
    items = [c.strip() for c in (constraints or []) if c and c.strip()]
    return items[:12]


def _render_markdown(title: str, prompt: str, constraints: list[str]) -> str:
    lines = [f"# {title}", "", "## Intent", "", prompt.strip() or "No prompt provided.", ""]
    if constraints:
        lines.extend(["## Constraints", ""])
        lines.extend(f"- {c}" for c in constraints)
        lines.append("")
    lines.extend([
        "## Draft",
        "",
        "- Main point:",
        "- Supporting detail:",
        "- Next action:",
        "",
        "## Review Notes",
        "",
        "- Preview-only artifact. Review before save/export.",
    ])
    return "\n".join(lines)


def _render_html(title: str, prompt: str, constraints: list[str]) -> str:
    escaped_title = html.escape(title)
    escaped_prompt = html.escape(prompt.strip() or "No prompt provided.")
    constraint_items = "\n".join(f"      <li>{html.escape(c)}</li>" for c in constraints)
    constraints_block = f"\n    <ul>\n{constraint_items}\n    </ul>" if constraints else "\n    <p>No extra constraints.</p>"
    return f"""<!doctype html>
<html lang="id">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escaped_title}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 40px; line-height: 1.55; color: #10231c; }}
    main {{ max-width: 760px; margin: 0 auto; }}
    h1 {{ font-size: 2rem; margin-bottom: 0.5rem; }}
    section {{ margin-top: 1.5rem; }}
    code {{ background: #eef7f2; padding: 0.1rem 0.3rem; border-radius: 4px; }}
  </style>
</head>
<body>
  <main>
    <h1>{escaped_title}</h1>
    <section>
      <h2>Intent</h2>
      <p>{escaped_prompt}</p>
    </section>
    <section>
      <h2>Constraints</h2>{constraints_block}
    </section>
    <section>
      <h2>Draft</h2>
      <p>Preview-only scaffold. Review, iterate, then export when gates pass.</p>
    </section>
  </main>
</body>
</html>"""


def _render_json(title: str, prompt: str, constraints: list[str]) -> str:
    payload = {
        "title": title,
        "intent": prompt.strip(),
        "constraints": constraints,
        "draft": {
            "summary": "",
            "items": [],
            "next_action": "",
        },
        "review": {
            "status": "preview_only",
            "requires_human_review": True,
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _render_report(title: str, prompt: str, constraints: list[str]) -> str:
    lines = [
        f"# {title}",
        "",
        "## Executive Summary",
        "",
        "Draft summary pending review.",
        "",
        "## Context",
        "",
        prompt.strip() or "No context provided.",
        "",
        "## Findings",
        "",
        "1. Observation:",
        "2. Implication:",
        "3. Recommendation:",
        "",
        "## Constraints",
        "",
    ]
    lines.extend([f"- {c}" for c in constraints] or ["- None provided."])
    lines.extend(["", "## Next Steps", "", "- Review preview.", "- Fill evidence.", "- Approve export/save path."])
    return "\n".join(lines)


def _render_code(title: str, prompt: str, constraints: list[str]) -> str:
    constraint_text = "\n".join(f"# - {c}" for c in constraints) or "# - None"
    # Defang any triple-quote in user input so it cannot break out of the docstring
    # and become executable when the scaffold is later saved as .py.
    safe_title = title.replace('"""', '\\"\\"\\"')
    safe_prompt = (prompt.strip() or "No prompt provided.").replace('"""', '\\"\\"\\"')
    safe_constraints = constraint_text.replace('"""', '\\"\\"\\"')
    return f'''"""
{safe_title}

Intent:
{safe_prompt}

Constraints:
{safe_constraints}

Preview-only code scaffold. Add implementation and tests before execution.
"""


def main():
    raise NotImplementedError("Artifact Builder generated a preview scaffold only.")


if __name__ == "__main__":
    main()
'''


def build_artifact_preview(request: ArtifactRequest) -> ArtifactPreview:
    artifact_type = _normalize_type(request.artifact_type)
    title = _title_from_prompt(request.prompt, request.title)
    constraints = _constraints_lines(request.constraints)
    prompt = request.prompt.strip()

    if artifact_type == "markdown":
        content = _render_markdown(title, prompt, constraints)
        fmt = "text/markdown"
    elif artifact_type == "html":
        content = _render_html(title, prompt, constraints)
        fmt = "text/html"
    elif artifact_type == "json":
        content = _render_json(title, prompt, constraints)
        fmt = "application/json"
    elif artifact_type == "report":
        content = _render_report(title, prompt, constraints)
        fmt = "text/markdown"
    else:
        content = _render_code(title, prompt, constraints)
        fmt = "text/plain"

    safe_path, recommended_path, path_detail = _safe_target_path(request.target_path, artifact_type, title)
    prompt_ok = 4 <= len(prompt) <= 5000
    content_ok = len(content) <= 50000
    gates = [
        ArtifactGate("schema_check", True, "artifact request parsed and normalized"),
        ArtifactGate("prompt_bounds", prompt_ok, f"prompt length={len(prompt)} chars"),
        ArtifactGate("preview_render", content_ok, f"preview length={len(content)} chars"),
        ArtifactGate("path_boundary", safe_path, path_detail),
        ArtifactGate("rollback_ready", True, "preview-only; no file write or deploy performed"),
    ]
    safe_to_save = all(g.passed for g in gates)
    digest_input = json.dumps(
        {
            "type": artifact_type,
            "title": title,
            "prompt": prompt,
            "constraints": constraints,
            "path": recommended_path,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    artifact_id = "art_" + hashlib.sha256(digest_input.encode("utf-8")).hexdigest()[:16]
    created_at = datetime.now(timezone.utc).isoformat()

    return ArtifactPreview(
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        title=title,
        format=fmt,
        content=content,
        content_preview=content[:800],
        gates=gates,
        lineage={
            "created_at": created_at,
            "method": "artifact_builder_mvp",
            "organism_body_part": "organ",
            "sidix_method": "kitabah_auto_iterate",
            "promotion_rule": "preview_then_gate_then_save",
        },
        rollback_plan="No rollback needed for preview. If saved later, delete the workspace artifact path and keep this preview lineage in the proposal log.",
        safe_to_save=safe_to_save,
        recommended_path=recommended_path,
    )


def preview_to_dict(preview: ArtifactPreview) -> dict:
    # asdict() already recurses through nested dataclasses (gates), so no
    # second pass needed.
    return asdict(preview)
