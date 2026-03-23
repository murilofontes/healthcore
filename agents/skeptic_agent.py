"""
Skeptic Agent — challenges clinical hypotheses with scientific rigor.
Wrapper around the Anthropic Messages API with the skeptic system prompt.
"""

import anthropic

from config.settings import MAX_TOKENS, MODEL
from services.memory_manager import load_agent_prompt


class SkepticAgent:
    def __init__(self, client: anthropic.Anthropic):
        self.client = client
        self.system_prompt = load_agent_prompt("skeptic")

    def challenge(
        self,
        clinical_hypothesis: str,
        user_input: str,
        prontuario: str,
        exames: str,
    ) -> str:
        """
        Challenges the clinical hypothesis.
        The skeptic agent sees the full clinical output to critique it properly.

        Args:
            clinical_hypothesis: Full output from the clinical agent.
            user_input: Original user question for context.
            prontuario: Full content of PRONTUARIO.md.
            exames: Full content of EXAMES_HISTORICO.md.
        """
        user_message = _build_skeptic_prompt(
            clinical_hypothesis, user_input, prontuario, exames
        )

        response = self.client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=self.system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        return response.content[0].text


def _build_skeptic_prompt(
    clinical_hypothesis: str,
    user_input: str,
    prontuario: str,
    exames: str,
) -> str:
    return "\n".join([
        "## CONTEXTO ORIGINAL",
        user_input,
        "",
        "## PRONTUÁRIO DO PACIENTE",
        prontuario,
        "",
        "## HISTÓRICO DE EXAMES",
        exames,
        "",
        "## HIPÓTESE DO AGENTE CLÍNICO (para você questionar)",
        clinical_hypothesis,
        "",
        "Analise criticamente a hipótese acima. Identifique limitações, dados insuficientes, "
        "extrapolações e qualidade de evidência. Use os flags obrigatórios quando aplicável.",
    ])
