"""
Debate Engine — orchestrates the multi-agent clinical debate.

Flow:
  1. Emergency check (pre-API, Python layer — not bypassable)
  2. Out-of-scope check
  3. Detect relevant specialties (skill routing)
  4. Clinical Agent → hypothesis
  5. Skeptic Agent → challenges (sees Clinical output)
  6. Genomics Agent → if DNA data referenced
  7. Orchestrator synthesis
  8. Audit log (JSONL)

All API calls are sequential — Skeptic must see Clinical output.
"""

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List

import anthropic

from agents.clinical_agent import ClinicalAgent
from agents.genomics_agent import GenomicsAgent
from agents.skeptic_agent import SkepticAgent
from config.guardrails import (
    EMERGENCY_RESPONSE,
    EMERGENCY_TRIGGERS,
    OUT_OF_SCOPE_RESPONSE,
    OUT_OF_SCOPE_TRIGGERS,
    SKILL_KEYWORDS,
    SNP_ARRAY_PLATFORMS,
    URGENCY_LEVELS,
)
from config.settings import ANTHROPIC_API_KEY, LOGS_DIR, MAX_TOKENS, MODEL
from services.memory_manager import (
    load_agent_prompt,
    load_skills,
    read_exames,
    read_prontuario,
)


@dataclass
class DebateResult:
    user_input: str
    clinical: str = ""
    skeptic: str = ""
    genomics: str = ""
    synthesis: str = ""
    urgency: str = "INFORMATIVO"
    skills_used: List[str] = field(default_factory=list)
    is_emergency: bool = False
    is_out_of_scope: bool = False
    timestamp: str = ""
    prontuario_updated: bool = False

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    @classmethod
    def emergency(cls, user_input: str) -> "DebateResult":
        return cls(
            user_input=user_input,
            synthesis=EMERGENCY_RESPONSE,
            urgency="EMERGÊNCIA",
            is_emergency=True,
        )

    @classmethod
    def out_of_scope(cls, user_input: str) -> "DebateResult":
        return cls(
            user_input=user_input,
            synthesis=OUT_OF_SCOPE_RESPONSE,
            urgency="INFORMATIVO",
            is_out_of_scope=True,
        )


class DebateEngine:
    def __init__(self):
        if not ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY não configurada. "
                "Execute ./scripts/setup.sh ou adicione ao .env"
            )
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.clinical = ClinicalAgent(self.client)
        self.skeptic = SkepticAgent(self.client)
        self.genomics = GenomicsAgent(self.client)
        self._orchestrator_prompt = load_agent_prompt("orchestrator")

    def run(self, user_input: str, pdf_text: str = "") -> DebateResult:
        """
        Runs the full debate pipeline.

        Args:
            user_input: The user's question or new exam data.
            pdf_text: Optional extracted text from a PDF exam.

        Returns:
            DebateResult with all agent outputs and synthesis.
        """
        # ── 1. Emergency check — MUST happen before any API call ──────────────
        if _is_emergency(user_input):
            result = DebateResult.emergency(user_input)
            _log_debate(result)
            return result

        # ── 2. Out-of-scope check ──────────────────────────────────────────────
        if _is_out_of_scope(user_input):
            result = DebateResult.out_of_scope(user_input)
            _log_debate(result)
            return result

        # ── 3. Load patient context ────────────────────────────────────────────
        prontuario = read_prontuario()
        exames = read_exames()

        # ── 4. Detect relevant specialties ────────────────────────────────────
        skills_needed = _detect_skills(user_input + " " + pdf_text, prontuario)
        skills_context = load_skills(skills_needed) if skills_needed else ""

        # ── 5. Clinical Agent ──────────────────────────────────────────────────
        clinical_response = self.clinical.analyze(
            user_input=user_input,
            prontuario=prontuario,
            exames=exames,
            skills_context=skills_context,
            pdf_text=pdf_text,
        )

        # ── 6. Skeptic Agent (sees Clinical output) ────────────────────────────
        skeptic_response = self.skeptic.challenge(
            clinical_hypothesis=clinical_response,
            user_input=user_input,
            prontuario=prontuario,
            exames=exames,
        )

        # ── 7. Genomics Agent (only if DNA data is referenced) ─────────────────
        genomics_response = ""
        if _needs_genomics(user_input, clinical_response, prontuario):
            genomics_response = self.genomics.analyze(
                user_input=user_input,
                clinical_hypothesis=clinical_response,
                prontuario=prontuario,
                exames=exames,
            )

        # ── 8. Orchestrator synthesis ──────────────────────────────────────────
        synthesis = self._synthesize(
            user_input=user_input,
            clinical=clinical_response,
            skeptic=skeptic_response,
            genomics=genomics_response,
            prontuario=prontuario,
        )

        # ── 9. Extract urgency level ───────────────────────────────────────────
        urgency = _extract_urgency(synthesis + clinical_response)

        result = DebateResult(
            user_input=user_input,
            clinical=clinical_response,
            skeptic=skeptic_response,
            genomics=genomics_response,
            synthesis=synthesis,
            urgency=urgency,
            skills_used=skills_needed,
        )

        # ── 10. Audit log ──────────────────────────────────────────────────────
        _log_debate(result)

        return result

    def _synthesize(
        self,
        user_input: str,
        clinical: str,
        skeptic: str,
        genomics: str,
        prontuario: str,
    ) -> str:
        """Orchestrator synthesis — combines all agent outputs."""
        parts = [
            "## INPUT DO USUÁRIO",
            user_input,
            "",
            "## HIPÓTESE DO AGENTE CLÍNICO",
            clinical,
            "",
            "## OBJEÇÕES DO AGENTE CÉTICO",
            skeptic,
        ]

        if genomics:
            parts += ["", "## ANÁLISE DO AGENTE GENÔMICO", genomics]

        parts += [
            "",
            "## PRONTUÁRIO (para contexto da síntese)",
            prontuario[:3000],  # limit to avoid context overflow
            "",
            "Sintetize o debate acima seguindo rigorosamente seu formato de síntese. "
            "Não suprima as ressalvas do agente cético. "
            "Calibre o nível de urgência ao quadro real.",
        ]

        response = self.client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=self._orchestrator_prompt,
            messages=[{"role": "user", "content": "\n".join(parts)}],
        )

        return response.content[0].text


# ── Guardrail functions (Python layer — not bypassable) ───────────────────────


def _is_emergency(text: str) -> bool:
    """R5: Pre-API emergency detection via string matching."""
    text_lower = text.lower()
    return any(trigger in text_lower for trigger in EMERGENCY_TRIGGERS)


def _is_out_of_scope(text: str) -> bool:
    """Detects requests that violate R1/R2 (diagnosis, prescription)."""
    text_lower = text.lower()
    return any(trigger in text_lower for trigger in OUT_OF_SCOPE_TRIGGERS)


def _needs_genomics(user_input: str, clinical_response: str, prontuario: str) -> bool:
    """Determines if the Genomics Agent should be called."""
    combined = (user_input + " " + clinical_response + " " + prontuario[:500]).lower()
    genomics_triggers = SKILL_KEYWORDS["genomics"] + SNP_ARRAY_PLATFORMS
    return any(trigger in combined for trigger in genomics_triggers)


def _detect_skills(text: str, prontuario: str = "") -> List[str]:
    """
    Routes to relevant specialty skills based on keyword matching.
    Always includes lab_medicine for any clinical question.
    """
    text_lower = (text + " " + prontuario[:300]).lower()
    detected = []

    for skill_name, keywords in SKILL_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            detected.append(skill_name)

    # lab_medicine is always useful for clinical questions
    if "lab_medicine" not in detected and len(text_lower) > 20:
        detected.append("lab_medicine")

    return detected


def _extract_urgency(text: str) -> str:
    """Extracts urgency level from agent output text."""
    text_upper = text.upper()
    for level in URGENCY_LEVELS:
        if level in text_upper:
            return level
    return "INFORMATIVO"


def _log_debate(result: DebateResult) -> None:
    """
    Writes audit log entry per GUARDRAILS.md Section 9.
    File: logs/debates/YYYY-MM-DD.jsonl (append-only, never deleted).
    """
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = LOGS_DIR / f"{today}.jsonl"

        entry = {
            "timestamp": result.timestamp,
            "input": result.user_input,
            "is_emergency": result.is_emergency,
            "is_out_of_scope": result.is_out_of_scope,
            "skills_used": result.skills_used,
            "urgency": result.urgency,
            "agente_clinico": {"output_length": len(result.clinical)},
            "agente_cetico": {"output_length": len(result.skeptic)},
            "agente_genomico": {"output_length": len(result.genomics)},
            "sintese_length": len(result.synthesis),
            "prontuario_atualizado": result.prontuario_updated,
        }

        with log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    except Exception:
        # Log failures must never crash the main application
        pass
