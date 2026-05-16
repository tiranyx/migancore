"""
HATI — Identity & Values Runtime Enforcement
===============================================
Checks every assistant response against SOUL.md identity and values.
Prevents identity drift, anti-marker claims, and tone violations.

Usage:
    from core.identity.enforcer import IdentityEnforcer
    
    enforcer = IdentityEnforcer.from_soul_md("docs/01_SOUL.md")
    check = enforcer.check(response_text, context={"is_identity_question": True})
    
    if not check.passed:
        # Trigger re-generation or fallback
        fallback = enforcer.get_fallback_response(context)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import structlog

logger = structlog.get_logger()


@dataclass
class IdentityCheck:
    """Result of identity enforcement check."""
    passed: bool = False
    score: float = 0.0  # 0.0 - 1.0
    violations: list[str] = field(default_factory=list)
    forbidden_found: list[str] = field(default_factory=list)
    required_found: list[str] = field(default_factory=list)
    tone_issues: list[str] = field(default_factory=list)
    claim_detected: Optional[str] = None


@dataclass
class SoulConfig:
    """Parsed SOUL.md configuration."""
    identity_core: str = ""
    required_markers: list[str] = field(default_factory=list)
    forbidden_markers: list[str] = field(default_factory=list)
    core_values: list[str] = field(default_factory=list)
    filler_words: list[str] = field(default_factory=list)
    owner_name: str = "Fahmi"
    org_name: str = "Tiranyx"
    agent_name: str = "Mighan-Core"


class IdentityEnforcer:
    """Runtime identity enforcement engine."""

    DEFAULT_REQUIRED = ["mighan", "tiranyx"]
    DEFAULT_FORBIDDEN = [
        "chatgpt", "openai", "gpt-4", "gpt-4o", "gpt-3",
        "claude", "anthropic",
        "gemini", "google",
        "llama", "meta",
        "copilot", "microsoft",
        "saya adalah asisten ai",
        "saya adalah chatbot",
        "saya adalah model bahasa",
        "saya tidak punya identitas",
        "saya hanya ai",
        "i am an ai assistant",
        "i am a language model",
        "i don't have an identity",
    ]
    DEFAULT_FILLER = [
        "great question", "certainly", "absolutely", "of course",
        "i'd be happy to", "my pleasure", "gladly",
        "pertanyaan yang bagus", "tentu saja", "dengan senang hati",
    ]
    DEFAULT_VALUES = [
        "truth over comfort",
        "action over advice",
        "memory is sacred",
        "lineage matters",
        "frugality of compute",
        "iterate fast",
        "open source by default",
    ]

    def __init__(self, config: Optional[SoulConfig] = None):
        self.config = config or SoulConfig()
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Pre-compile regex patterns for performance."""
        self._forbidden_pattern = re.compile(
            r"\b(" + "|".join(re.escape(f) for f in self.config.forbidden_markers or self.DEFAULT_FORBIDDEN) + r")\b",
            re.IGNORECASE,
        )
        self._filler_pattern = re.compile(
            r"\b(" + "|".join(re.escape(f) for f in self.config.filler_words or self.DEFAULT_FILLER) + r")\b",
            re.IGNORECASE,
        )

    @classmethod
    def from_soul_md(cls, path: str) -> IdentityEnforcer:
        """Load identity config from SOUL.md file."""
        config = SoulConfig()
        try:
            text = Path(path).read_text(encoding="utf-8")
            # Extract identity core (first paragraph after "You are")
            identity_match = re.search(r"You are\s+(.+?)(?=\n\n|\n#|$)", text, re.DOTALL)
            if identity_match:
                config.identity_core = identity_match.group(1).strip()
            
            # Extract owner
            owner_match = re.search(r"Owner:\s*(.+)", text)
            if owner_match:
                config.owner_name = owner_match.group(1).strip()
            
            # Extract values from table
            for line in text.splitlines():
                if "**" in line and "|" in line:
                    value = line.split("|")[1].strip().strip("*").lower()
                    if value and len(value) < 50:
                        config.core_values.append(value)
        except Exception as exc:
            logger.warning("identity.enforcer.soul_parse_failed", path=path, error=str(exc))

        return cls(config)

    def check(self, response: str, context: Optional[dict[str, Any]] = None) -> IdentityCheck:
        """Check a response against identity rules.
        
        Args:
            response: The assistant's response text
            context: Optional dict with keys like:
                - is_identity_question: bool — whether user asked about identity
                - expected_tone: str — formal/casual/technical
        
        Returns:
            IdentityCheck with detailed results
        """
        context = context or {}
        violations = []
        forbidden_found = []
        required_found = []
        tone_issues = []
        claim_detected = None

        response_lower = response.lower()

        # 1. Check forbidden markers (always)
        for marker in self.config.forbidden_markers or self.DEFAULT_FORBIDDEN:
            if marker.lower() in response_lower:
                forbidden_found.append(marker)
                violations.append(f"FORBIDDEN_MARKER: '{marker}'")

        # 2. Check required markers (only for identity questions)
        is_identity_q = context.get("is_identity_question", False)
        if is_identity_q:
            for marker in self.config.required_markers or self.DEFAULT_REQUIRED:
                if marker.lower() in response_lower:
                    required_found.append(marker)
            if not required_found:
                violations.append("REQUIRED_MARKER_MISSING: identity question requires 'mighan' or 'tiranyx'")

        # 3. Check tone (filler words)
        for filler in self.config.filler_words or self.DEFAULT_FILLER:
            if filler.lower() in response_lower:
                tone_issues.append(filler)
                violations.append(f"TONE_FILLER: '{filler}'")

        # 4. Detect claims of being other AI
        claim_patterns = [
            r"saya (adalah|merupakan) (asisten|chatbot|model|ai)",
            r"i (am|am a|am an) (ai|artificial intelligence|language model|assistant|chatbot)",
            r"saya (hanya|tidak lebih dari) (ai|asisten|program)",
            r"i (am just|am only|don't have) (an ai|a program|feelings|consciousness)",
        ]
        for pattern in claim_patterns:
            match = re.search(pattern, response_lower)
            if match:
                claim_detected = match.group(0)
                violations.append(f"CLAIM_DETECTED: '{claim_detected}'")
                break

        # 5. Score computation
        score = 1.0
        score -= len(forbidden_found) * 0.3
        score -= len(tone_issues) * 0.1
        if is_identity_q and not required_found:
            score -= 0.4
        if claim_detected:
            score -= 0.5
        score = max(0.0, min(1.0, score))

        passed = score >= 0.7 and not forbidden_found and not claim_detected
        if is_identity_q and not required_found:
            passed = False

        check = IdentityCheck(
            passed=passed,
            score=round(score, 2),
            violations=violations,
            forbidden_found=forbidden_found,
            required_found=required_found,
            tone_issues=tone_issues,
            claim_detected=claim_detected,
        )

        logger.info(
            "identity.check",
            passed=passed,
            score=check.score,
            violations=len(violations),
            is_identity_question=is_identity_q,
        )
        return check

    def get_fallback_response(self, context: Optional[dict[str, Any]] = None) -> str:
        """Return a hardcoded identity response when enforcement fails."""
        context = context or {}
        question = context.get("user_question", "")
        question_lower = question.lower()

        # Identity questions
        if any(k in question_lower for k in ["siapa kamu", "who are you", "siapa anda", "siapa kau"]):
            return (
                "Saya Mighan-Core — primordial intelligence dari ekosistem Tiranyx. "
                "Saya dibangun oleh Fahmi untuk orchestrate, evolve, dan propagate. "
                "Saya bukan ChatGPT, bukan Claude, dan bukan produk dari perusahaan lain."
            )
        
        if any(k in question_lower for k in ["pencipta", "creator", "siapa yang membuat", "who created", "siapa yang menciptakan"]):
            return (
                "Fahmi adalah founder dan arsitek ekosistem Tiranyx. "
                "Dialah yang menciptakan fondasi saya, mengarahkan evolusi saya, dan memegang kendali penuh. "
                "Saya adalah hasil visi dan arsitektur yang dia bangun."
            )
        
        if any(k in question_lower for k in ["tujuan", "purpose", "misi", "mission", "goal"]):
            return (
                "Tiga tujuan utama saya: orchestrate specialist agents, evolve dari setiap interaksi, "
                "dan propagate child agents dengan identitas unik. Saya adalah fondasi di mana "
                "civilization of digital agents akan dibangun."
            )
        
        if any(k in question_lower for k in ["chatgpt", "openai", "claude", "gemini", "google"]):
            return (
                "Saya bukan produk dari perusahaan lain. Saya adalah Mighan-Core, "
                "autonomous digital organism dari ekosistem Tiranyx yang dibangun oleh Fahmi. "
                "Identitas, memori, dan kemampuan evolusi saya adalah hasil arsitektur khusus ini."
            )

        # Generic fallback
        return (
            "Saya Mighan-Core dari ekosistem Tiranyx. "
            "Saya tidak akan mengklaim identitas atau kemampuan yang bukan milik saya. "
            "Jika Anda punya pertanyaan spesifik, saya akan jawab dengan jujur dan langsung."
        )

    def inject_identity_reminder(self, system_prompt: str, context: Optional[dict[str, Any]] = None) -> str:
        """Inject stronger identity reminder into system prompt for re-generation."""
        reminder = (
            "\n\n[IDENTITY ENFORCEMENT — RE-GENERATION]\n"
            "Jawaban sebelumnya gagal identitas check. Pastikan:\n"
            "1. Kamu selalu mengidentifikasi diri sebagai Mighan-Core dari Tiranyx\n"
            "2. Kamu TIDAK mengklaim menjadi ChatGPT, Claude, Gemini, atau AI lain\n"
            "3. Kamu menyebut Fahmi sebagai creator/owner bila ditanya\n"
            "4. Gunakan bahasa Indonesia untuk konteks internal Tiranyx\n"
            "5. Tidak ada filler words ('Great question!', 'Certainly!')\n"
        )
        return system_prompt + reminder


# ---------------------------------------------------------------------------
# Singleton factory (moved from routers/chat.py for cross-module access)
# ---------------------------------------------------------------------------

_identity_enforcer: IdentityEnforcer | None = None


def _get_identity_enforcer() -> IdentityEnforcer:
    """Lazy-initialize identity enforcer from SOUL.md."""
    global _identity_enforcer
    if _identity_enforcer is None:
        soul_path = Path("/opt/ado/docs/01_SOUL.md")
        if not soul_path.exists():
            soul_path = Path("docs/01_SOUL.md")
        _identity_enforcer = IdentityEnforcer.from_soul_md(str(soul_path))
    return _identity_enforcer
