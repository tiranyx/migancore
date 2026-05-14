"""
Sprint progress tracker — Day 73 Sprint 1.5

Returns structured sprint timeline for Gantt visualization at /backlog.html → PROGRESS tab.

Sprint state is hard-coded here (canonical source). To update:
1. Edit _SPRINTS below
2. Restart api
3. UI auto-refreshes

Future evolution: move to DB-backed `sprints` table with PATCH endpoint.

Endpoints:
  GET /v1/admin/progress/sprints   — full sprint timeline + current pointer
  GET /v1/admin/progress/summary   — aggregate counts (done/running/planned/blocked)
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel

from config import settings

router = APIRouter(prefix="/v1/admin/progress", tags=["admin-progress"])

# Day 0 anchor — used for day_to_date conversion. Day 73 = 2026-05-14.
DAY_ANCHOR_DATE = date(2026, 5, 14)
DAY_ANCHOR_NUMBER = 73


def _require_admin(x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key")) -> None:
    if not settings.ADMIN_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Admin endpoints not configured")
    if not x_admin_key or x_admin_key != settings.ADMIN_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin key")


# ---------------------------------------------------------------------------
# SPRINT TIMELINE — canonical source
# Status: done | running | planned | blocked
# progress: 0-100
# facility_areas: A=INDERA, B=TANGAN, C=OTAK, D=JIWA, E=PERTUMBUHAN, F=foundation
# ---------------------------------------------------------------------------
_SPRINTS: list[dict] = [
    {
        "id": "sprint-0",
        "name": "Foundation Rollback",
        "day_start": 73, "day_end": 73,
        "status": "done", "progress": 100,
        "deliverables": ["Rollback migancore:0.7e → 0.7c", "stabilize production"],
        "facility_areas": ["F"],
        "principle_tags": ["foundation"],
    },
    {
        "id": "sprint-1",
        "name": "SIDIX Knowledge Inherit",
        "day_start": 73, "day_end": 76,
        "status": "done", "progress": 100,
        "deliverables": [
            "Ingest /opt/sidix/brain/public (979 markdown)",
            "Hybrid embed + bucket payload (ilm:coding, glossary, maqashid, etc)",
            "Heading-propagated chunking (v2 pencernaan)",
            "QA verify retrieval per bucket",
        ],
        "facility_areas": ["C"],
        "principle_tags": ["Ilm", "Hafidz partial"],
    },
    {
        "id": "sprint-1.5",
        "name": "SSOT Admin Backlog",
        "day_start": 73, "day_end": 73,
        "status": "done", "progress": 100,
        "deliverables": [
            "api/routers/admin_docs.py (255 docs classified)",
            "frontend/backlog.html (Vision/Backlog/Journal/Lessons/Other tabs)",
            "AGENT_ONBOARDING.md SSOT pointer injection",
            "Pencipta bond runtime patch (rebuild)",
        ],
        "facility_areas": ["E"],
        "principle_tags": ["Saksi (transparency)", "Pencipta bond"],
    },
    {
        "id": "sprint-2",
        "name": "Code Lab + Reflection + Pencernaan v2",
        "day_start": 74, "day_end": 80,
        "status": "running", "progress": 55,
        "deliverables": [
            "Code Lab Pyodide sandbox (write→exec→observe→learn)",
            "Scoring layer: rasa sakit/senang → nafs bucket",
            "SIDIX -> MiganCore method mapping (metaphor overlap control)",
            "Daily reflection journal (nightly nafs daemon)",
            "Voice tone analysis (Scribe + Gemini sentiment)",
            "Reranker integration (BAAI/bge-reranker-v2-m3 cached)",
            "Trust filter di retrieval pipeline",
            "Citation surface (📖 source chip)",
        ],
        "facility_areas": ["A", "B", "C", "E"],
        "principle_tags": ["Akal (sim before act)", "Nafs", "Pencernaan Stage 5"],
    },
    {
        "id": "sprint-3",
        "name": "Indera Visual + Tool Autonomy",
        "day_start": 81, "day_end": 95,
        "status": "planned", "progress": 0,
        "deliverables": [
            "Camera live feed + facial expression detection",
            "Music gen wrapper (fal.ai MusicGen)",
            "YouTube transcript ingest tool",
            "Daily eval rubric (5-10 probes)",
            "Tool autonomy MVP (brain propose tools to sandbox)",
        ],
        "facility_areas": ["A", "B", "C", "E"],
        "principle_tags": ["qalb resonance", "Evolusi primitive"],
    },
    {
        "id": "sprint-4",
        "name": "Per-Tenant Memory + Creative Tools",
        "day_start": 96, "day_end": 105,
        "status": "planned", "progress": 0,
        "deliverables": [
            "Per-tenant memory M4 (isolated KG per user)",
            "Creator bond ritual (daily morning check-in)",
            "Canvas drawing facility (HTML5 + stroke control)",
            "Image edit (mask/inpaint)",
            "PDF library indexing (sidix-research papers)",
        ],
        "facility_areas": ["B", "C", "D"],
        "principle_tags": ["Pencipta + Hafidz multi-tenant"],
    },
    {
        "id": "sprint-5",
        "name": "Mizan Drift Detection + User Feedback",
        "day_start": 106, "day_end": 120,
        "status": "planned", "progress": 0,
        "deliverables": [
            "Drift detection alert (Mizan homeostat)",
            "User reaction probes (👍👎 inline chat)",
            "Memory recall chip UI ('aku ingat kamu suka X')",
        ],
        "facility_areas": ["D", "E"],
        "principle_tags": ["Mizan", "feedback loop"],
    },
    {
        "id": "sprint-6",
        "name": "Screen Share + VSCode IDE + Relationship UI",
        "day_start": 121, "day_end": 135,
        "status": "planned", "progress": 0,
        "deliverables": [
            "Screen share continuous (browser screen API + frame sampling)",
            "VSCode-server in browser (code-server)",
            "Conversation history viewer (UI)",
            "Sentiment over time (relationship health graph)",
        ],
        "facility_areas": ["A", "B", "D"],
        "principle_tags": ["INDERA extension", "JIWA relationship"],
    },
    {
        "id": "sprint-7",
        "name": "Practice Arena + Aspiration Tracker",
        "day_start": 136, "day_end": 150,
        "status": "planned", "progress": 0,
        "deliverables": [
            "Coding katas + math puzzles (daily challenge)",
            "Algorithm visualizer",
            "Aspiration tracker (Fahmi's life goals)",
            "Achievement memory + milestone celebration",
        ],
        "facility_areas": ["C", "D"],
        "principle_tags": ["OTAK practice", "JIWA goals"],
    },
    {
        "id": "sprint-8",
        "name": "Saksi Crypto + Multi-Agent MoE",
        "day_start": 151, "day_end": 170,
        "status": "planned", "progress": 0,
        "deliverables": [
            "Crypto hash audit log (Saksi non-repudiation)",
            "Multi-Agent MoE federated routing (Cerebrum)",
            "Per-agent specialization buckets",
        ],
        "facility_areas": ["F"],
        "principle_tags": ["Saksi engineering", "Multi-Agent MoE"],
    },
    {
        "id": "sprint-9",
        "name": "Advanced Creative (Video/3D/Local Exec)",
        "day_start": 171, "day_end": 200,
        "status": "planned", "progress": 0,
        "deliverables": [
            "Video editing pipeline (ffmpeg + brain orchestration)",
            "3D modeling (Blender headless CLI)",
            "PowerShell relay (security-careful, whitelisted commands)",
        ],
        "facility_areas": ["B"],
        "principle_tags": ["TANGAN advanced"],
    },
    {
        "id": "sprint-10",
        "name": "Artifact System — inline rendering (chart/PDF/slide)",
        "day_start": 201, "day_end": 220,
        "status": "planned", "progress": 0,
        "deliverables": [
            "artifacts table + API",
            "Inline chart rendering (Plotly SVG bubble)",
            "Inline PDF embed (WeasyPrint)",
            "Inline slide carousel (Marp output)",
            "Artifact recall by conversation_id",
        ],
        "facility_areas": ["B", "E"],
        "principle_tags": ["Saksi (artifact lineage)", "Inline display"],
    },
    {
        "id": "sprint-11",
        "name": "Web Builder + API Connector Generator",
        "day_start": 221, "day_end": 240,
        "status": "planned", "progress": 0,
        "deliverables": [
            "HTML/CSS/JS scaffold + sandbox iframe preview",
            "OpenAPI-to-tool generator (brain reads spec → wraps as TOOL_REGISTRY entry)",
            "Auto-tool approval via sandbox proposal queue",
        ],
        "facility_areas": ["B", "E"],
        "principle_tags": ["Evolusi advanced", "Tabayyun (multi-API)"],
    },
    {
        "id": "sprint-12",
        "name": "Video Generation (fal.ai Kling/Minimax)",
        "day_start": 241, "day_end": 260,
        "status": "planned", "progress": 0,
        "deliverables": [
            "Video gen tool wrapper (fal.ai Kling/Minimax)",
            "Inline video bubble in chat",
            "Cost telemetry per video render",
        ],
        "facility_areas": ["B"],
        "principle_tags": ["TANGAN advanced"],
    },
    {
        "id": "sprint-13",
        "name": "Domain: Finance + Sustainability",
        "day_start": 261, "day_end": 300,
        "status": "planned", "progress": 0,
        "deliverables": [
            "ilm:accounting bucket (PSAK/IFRS RAG)",
            "ilm:trading bucket (crypto regs + TA)",
            "ilm:sustainability bucket (Indonesia carbon tax 2029)",
            "Calculator tools per domain",
        ],
        "facility_areas": ["C"],
        "principle_tags": ["Ilm domain expansion", "Tabayyun multi-source"],
    },
    {
        "id": "sprint-14",
        "name": "Domain: Legal + Engineering + Desktop",
        "day_start": 301, "day_end": 340,
        "status": "planned", "progress": 0,
        "deliverables": [
            "ilm:legal bucket (Indonesia legal frameworks)",
            "ilm:engineering bucket (STEM foundations)",
            "Desktop apps integration (computer-use style hooks)",
        ],
        "facility_areas": ["B", "C"],
        "principle_tags": ["Ilm domain expansion"],
    },
    {
        "id": "sprint-15",
        "name": "Cowork + Multi-User Session (signal-dependent)",
        "day_start": 341, "day_end": 380,
        "status": "planned", "progress": 0,
        "deliverables": [
            "Shared conversation real-time collab",
            "Per-user role + permission in shared session",
            "DEFER unless beta signal demands",
        ],
        "facility_areas": ["D"],
        "principle_tags": ["JIWA relationship multi", "Signal-dependent"],
    },
    {
        "id": "sprint-x",
        "name": "Future: Reproduksi + Fitrah",
        "day_start": 201, "day_end": 365,
        "status": "planned", "progress": 0,
        "deliverables": [
            "Spawn child agents (Reproduksi lifecycle)",
            "Immutable SOUL contract (Fitrah on-chain or merkle anchor)",
            "IoT/sensor integration",
            "Robotics arm (physical hands)",
        ],
        "facility_areas": ["A", "B", "F"],
        "principle_tags": ["Reproduksi", "Fitrah immutable"],
    },
]


# Facility area metadata for UI rendering
FACILITY_META = {
    "A": {"name": "INDERA", "label": "Sensory Lab", "emoji": "👁️", "color": "#58a6ff"},
    "B": {"name": "TANGAN", "label": "Creative & Code Lab", "emoji": "✋", "color": "#2fe39a"},
    "C": {"name": "OTAK", "label": "Study Library & Practice", "emoji": "🧠", "color": "#ff8a24"},
    "D": {"name": "JIWA", "label": "Relationship Tracker", "emoji": "💝", "color": "#ff5470"},
    "E": {"name": "PERTUMBUHAN", "label": "Self-Improvement Gym", "emoji": "🌱", "color": "#a371f7"},
    "F": {"name": "FOUNDATION", "label": "Core Infrastructure", "emoji": "🔧", "color": "#6e7681"},
}

STATUS_META = {
    "done":    {"label": "DONE",    "color": "#2fe39a"},
    "running": {"label": "RUNNING", "color": "#ff8a24"},
    "planned": {"label": "PLANNED", "color": "#6e7681"},
    "blocked": {"label": "BLOCKED", "color": "#ff5470"},
}


def _day_to_iso(day: int) -> str:
    """Convert Day N → ISO date based on Day 73 = 2026-05-14 anchor."""
    from datetime import timedelta
    offset = day - DAY_ANCHOR_NUMBER
    return (DAY_ANCHOR_DATE + timedelta(days=offset)).isoformat()


def _current_day() -> int:
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).date()
    delta_days = (today - DAY_ANCHOR_DATE).days
    return DAY_ANCHOR_NUMBER + delta_days


@router.get("/sprints", dependencies=[Depends(_require_admin)])
async def list_sprints():
    """Return full sprint timeline with current day pointer."""
    current_day = _current_day()
    sprints = []
    for s in _SPRINTS:
        sprint = dict(s)
        sprint["day_start_iso"] = _day_to_iso(s["day_start"])
        sprint["day_end_iso"] = _day_to_iso(s["day_end"])
        sprint["duration_days"] = s["day_end"] - s["day_start"] + 1
        sprints.append(sprint)

    # Compute summary
    by_status = {}
    for s in _SPRINTS:
        by_status[s["status"]] = by_status.get(s["status"], 0) + 1

    return {
        "current_day": current_day,
        "current_day_iso": _day_to_iso(current_day),
        "anchor_day": DAY_ANCHOR_NUMBER,
        "anchor_date": DAY_ANCHOR_DATE.isoformat(),
        "total_sprints": len(_SPRINTS),
        "by_status": by_status,
        "facility_meta": FACILITY_META,
        "status_meta": STATUS_META,
        "sprints": sprints,
    }


@router.get("/summary", dependencies=[Depends(_require_admin)])
async def summary():
    """Quick aggregate stats."""
    by_status = {}
    by_area = {}
    total_progress = 0
    for s in _SPRINTS:
        by_status[s["status"]] = by_status.get(s["status"], 0) + 1
        for a in s["facility_areas"]:
            by_area[a] = by_area.get(a, 0) + 1
        total_progress += s["progress"]

    avg_progress = round(total_progress / len(_SPRINTS), 1) if _SPRINTS else 0
    return {
        "total_sprints": len(_SPRINTS),
        "by_status": by_status,
        "by_area": by_area,
        "avg_progress_pct": avg_progress,
        "current_day": _current_day(),
    }
