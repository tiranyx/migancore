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
        "live_components": ["docs/01_SOUL.md", "identity eval", "creator recognition", "persona blocks"],
        "responsibility": "Preserve identity, values, creator bond, voice, and long-term direction across model upgrades.",
        "risk_if_weak": "Migan becomes a generic assistant or drifts away from Fahmi's vision.",
        "next_step": "Add organism anatomy doctrine to SOUL and eval prompts.",
        "gate": "identity_check",
    },
    {
        "id": "otak",
        "name": "Otak",
        "technical_layer": "Cognitive core",
        "live_components": ["Qwen/Ollama brain", "chat router", "LangGraph-style reasoning path", "teacher distillation"],
        "responsibility": "Understand, answer, synthesize, plan, and choose when to use tools.",
        "risk_if_weak": "Responses become shallow, slow, or dependent on external wrappers.",
        "next_step": "Add reasoning effort and eval probes for deep cognitive tasks.",
        "gate": "reasoning_eval",
    },
    {
        "id": "pikiran",
        "name": "Pikiran",
        "technical_layer": "Working memory and thought workspace",
        "live_components": ["conversation context", "reflection journal", "proposal queue", "reasoning traces"],
        "responsibility": "Hold the current problem, synthesize founder intent, and turn ideas into structured next actions.",
        "risk_if_weak": "Good ideas vanish after chat and never become backlog, memory, or training data.",
        "next_step": "Route inspiration, reflection, and chat insights into proposals or docs.",
        "gate": "trace_recorded",
    },
    {
        "id": "akal",
        "name": "Akal",
        "technical_layer": "Judgment and executive control",
        "live_components": ["Dev Organ gates", "readiness runner", "proposal lifecycle", "promotion reports"],
        "responsibility": "Evaluate risk, rank options, require tests, and decide whether an idea can advance.",
        "risk_if_weak": "Autonomy becomes impulsive: code or GPU work starts without evidence.",
        "next_step": "Expand gates with cost, license, eval, and rollback checks for creative modules.",
        "gate": "proposal_gates",
    },
    {
        "id": "syaraf",
        "name": "Syaraf",
        "technical_layer": "Integration and routing layer",
        "live_components": ["tool router", "MCP server", "tool executor", "API routers", "Redis cache"],
        "responsibility": "Transmit intent to tools, services, memory, workers, and external interfaces.",
        "risk_if_weak": "The brain knows what to do but cannot act reliably.",
        "next_step": "Add routing eval for reflex/lightweight/full/tool pathways.",
        "gate": "routing_eval",
    },
    {
        "id": "indera",
        "name": "Indera",
        "technical_layer": "Perception and input modalities",
        "live_components": ["vision describe", "audio/STT hooks", "URL/doc ingestion", "inspiration intake"],
        "responsibility": "Observe images, documents, links, audio, and environment signals before reasoning.",
        "risk_if_weak": "Migan can only process typed chat and misses the world around Fahmi.",
        "next_step": "Standardize modality-as-tool schemas for image, video, audio, document, and web inputs.",
        "gate": "perception_contract",
    },
    {
        "id": "organ",
        "name": "Organ",
        "technical_layer": "Specialized capability modules",
        "live_components": ["Dev Organ", "Artifact Builder backlog", "Image/Video/Voice module backlog", "Code Lab design"],
        "responsibility": "Provide specialized functions that the organism can grow, test, and improve.",
        "risk_if_weak": "Everything stays inside chat; no reusable capability emerges.",
        "next_step": "Build Artifact Builder MVP before heavy GPU modules.",
        "gate": "module_contract",
    },
    {
        "id": "metabolisme",
        "name": "Metabolisme",
        "technical_layer": "Learning, training, and energy economy",
        "live_components": ["auto_train_watchdog proposal mode", "distillation", "feedback pairs", "growth journal"],
        "responsibility": "Convert experience into memory, proposals, evals, datasets, and eventually model upgrades.",
        "risk_if_weak": "Migan consumes interactions but does not digest them into growth.",
        "next_step": "Connect accepted proposals and strong outputs into eval/training datasets.",
        "gate": "learning_evidence",
    },
    {
        "id": "imun",
        "name": "Sistem Imun",
        "technical_layer": "Safety, security, rollback, and boundaries",
        "live_components": ["admin auth", "secret scan", "data boundary gate", "rollback plans", "model lock 0.7c"],
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
