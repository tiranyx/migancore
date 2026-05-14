"""
Canonical organism architecture map for MiganCore.

This turns Fahmi's biological language into a stable technical contract.
It is intentionally read-only: architecture visibility, not autonomy by itself.
"""

from __future__ import annotations

from typing import Any


ORGANISM_LAYERS: list[dict[str, Any]] = [
    {
        "id": "jiwa",
        "name": "Jiwa",
        "technical_layer": "Identity and constitutional layer",
        "implementation_status": "partial",
        "live_components": ["docs/01_SOUL.md", "identity eval", "creator recognition", "persona blocks"],
        "backlog_refs": ["creator-bond eval", "organism identity eval", "white-label persona"],
        "responsibility": "Preserve identity, values, creator bond, voice, and long-term direction across model upgrades.",
        "risk_if_weak": "Migan becomes a generic assistant or drifts away from Fahmi's vision.",
        "next_step": "Add organism anatomy doctrine to SOUL and eval prompts.",
        "gate": "identity_check",
    },
    {
        "id": "otak",
        "name": "Otak",
        "technical_layer": "Cognitive core",
        "implementation_status": "partial",
        "live_components": ["Qwen/Ollama brain", "chat router", "LangGraph-style reasoning path", "teacher distillation"],
        "backlog_refs": ["Qwen3 baseline", "reasoning traces", "causal reasoning template", "routing eval"],
        "responsibility": "Understand, answer, synthesize, plan, and choose when to use tools.",
        "risk_if_weak": "Responses become shallow, slow, or dependent on external wrappers.",
        "next_step": "Add reasoning effort and eval probes for deep cognitive tasks.",
        "gate": "reasoning_eval",
    },
    {
        "id": "pikiran",
        "name": "Pikiran",
        "technical_layer": "Working memory and thought workspace",
        "implementation_status": "partial",
        "live_components": ["conversation context", "reflection journal", "proposal queue", "reasoning traces"],
        "backlog_refs": ["sleep-time consolidator", "chat insight to proposal", "thought artifact previews"],
        "responsibility": "Hold the current problem, synthesize founder intent, and turn ideas into structured next actions.",
        "risk_if_weak": "Good ideas vanish after chat and never become backlog, memory, or training data.",
        "next_step": "Route inspiration, reflection, and chat insights into proposals or docs.",
        "gate": "trace_recorded",
    },
    {
        "id": "akal",
        "name": "Akal",
        "technical_layer": "Judgment and executive control",
        "implementation_status": "partial",
        "live_components": ["Dev Organ gates", "readiness runner", "proposal lifecycle", "promotion reports"],
        "backlog_refs": ["Gate Runner v3", "cost/license/content gates", "approved proposal promotion"],
        "responsibility": "Evaluate risk, rank options, require tests, and decide whether an idea can advance.",
        "risk_if_weak": "Autonomy becomes impulsive: code or GPU work starts without evidence.",
        "next_step": "Expand gates with cost, license, eval, and rollback checks for creative modules.",
        "gate": "proposal_gates",
    },
    {
        "id": "syaraf",
        "name": "Syaraf",
        "technical_layer": "Integration and routing layer",
        "implementation_status": "partial",
        "live_components": ["tool router", "MCP server", "tool executor", "API routers", "Redis cache"],
        "backlog_refs": ["routing decision eval", "A2A endpoint", "enterprise connectors", "tool policy enforcement"],
        "responsibility": "Transmit intent to tools, services, memory, workers, and external interfaces.",
        "risk_if_weak": "The brain knows what to do but cannot act reliably.",
        "next_step": "Add routing eval for reflex/lightweight/full/tool pathways.",
        "gate": "routing_eval",
    },
    {
        "id": "indera",
        "name": "Indera",
        "technical_layer": "Perception and input modalities",
        "implementation_status": "partial",
        "live_components": ["vision describe", "audio/STT hooks", "URL/doc ingestion", "inspiration intake"],
        "backlog_refs": ["video perception", "document upload workflow", "STT streaming", "modality schemas"],
        "responsibility": "Observe images, documents, links, audio, and environment signals before reasoning.",
        "risk_if_weak": "Migan can only process typed chat and misses the world around Fahmi.",
        "next_step": "Standardize modality-as-tool schemas for image, video, audio, document, and web inputs.",
        "gate": "perception_contract",
    },
    {
        "id": "organ",
        "name": "Organ",
        "technical_layer": "Specialized capability modules",
        "implementation_status": "planned",
        "live_components": ["Dev Organ", "Artifact Builder backlog", "Image/Video/Voice module backlog", "Code Lab design"],
        "backlog_refs": ["Artifact Builder MVP", "Image Generator", "Video Generator", "Voice Generator", "Tool Builder", "Eval Pack Builder"],
        "responsibility": "Provide specialized functions that the organism can grow, test, and improve.",
        "risk_if_weak": "Everything stays inside chat; no reusable capability emerges.",
        "next_step": "Build Artifact Builder MVP before heavy GPU modules.",
        "gate": "module_contract",
    },
    {
        "id": "metabolisme",
        "name": "Metabolisme",
        "technical_layer": "Learning, training, and energy economy",
        "implementation_status": "partial",
        "live_components": ["auto_train_watchdog proposal mode", "distillation", "feedback pairs", "growth journal"],
        "backlog_refs": ["feedback to DPO", "accepted proposal to eval", "Hafidz export", "skill_distiller"],
        "responsibility": "Convert experience into memory, proposals, evals, datasets, and eventually model upgrades.",
        "risk_if_weak": "Migan consumes interactions but does not digest them into growth.",
        "next_step": "Connect accepted proposals and strong outputs into eval/training datasets.",
        "gate": "learning_evidence",
    },
    {
        "id": "imun",
        "name": "Sistem Imun",
        "technical_layer": "Safety, security, rollback, and boundaries",
        "implementation_status": "partial",
        "live_components": ["admin auth", "secret scan", "data boundary gate", "rollback plans", "model lock 0.7c"],
        "backlog_refs": ["tenant/RLS tests", "license Ed25519", "PII scrubber", "cost/license/content gate library"],
        "responsibility": "Prevent secret leaks, tenant boundary errors, unsafe deploys, and identity regression.",
        "risk_if_weak": "Self-improvement damages production or leaks sensitive data.",
        "next_step": "Make cost/license/content/security gates reusable for all new modules.",
        "gate": "safety_gates",
    },
]


def organism_status() -> dict[str, Any]:
    return {
        "doctrine": "digital_organism_architecture",
        "version": "2026-05-15.1",
        "promotion_rule": "proposal_gated",
        "status_legend": {
            "live": "Runtime-ready and production validated.",
            "partial": "Implemented enough to use, but missing one or more contract/gate/eval links.",
            "planned": "Backlog and contracts exist, but runtime module is not built yet.",
            "blocked": "Known blocker prevents safe implementation.",
        },
        "core_loop": [
            "observe",
            "synthesize",
            "propose",
            "gate",
            "sandbox",
            "validate",
            "promote",
            "monitor",
            "learn",
        ],
        "layers": ORGANISM_LAYERS,
    }
