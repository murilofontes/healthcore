"""
Clinical Agent — formulates clinical hypotheses based on patient data.
Wrapper around the Anthropic Messages API with the clinical system prompt.
"""

import anthropic

from config.settings import MAX_TOKENS, MODEL
from services.memory_manager import load_agent_prompt


class ClinicalAgent:
    def __init__(self, client: anthropic.Anthropic):
        self.client = client
        self.system_prompt = load_agent_prompt("clinical")

    def analyze(
        self,
        user_input: str,
        prontuario: str,
        exames: str,
        skills_context: str = "",
        pdf_text: str = "",
    ) -> str:
        """
        Formulates a clinical hypothesis based on the patient context.

        Args:
            user_input: The user's question or the new exam data.
            prontuario: Full content of PRONTUARIO.md.
            exames: Full content of EXAMES_HISTORICO.md.
            skills_context: Concatenated relevant skill files.
            pdf_text: Extracted text from a PDF exam (optional).
        """
        user_message = _build_clinical_prompt(
            user_input, prontuario, exames, skills_context, pdf_text
        )

        response = self.client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=self.system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        return response.content[0].text


def _build_clinical_prompt(
    user_input: str,
    prontuario: str,
    exames: str,
    skills_context: str,
    pdf_text: str,
) -> str:
    parts = [
        "## PRONTUÁRIO DO PACIENTE",
        prontuario,
        "",
        "## HISTÓRICO DE EXAMES",
        exames,
    ]

    if skills_context:
        parts += ["", "## CONTEXTO DE ESPECIALIDADES ATIVAS", skills_context]

    if pdf_text:
        parts += ["", "## TEXTO EXTRAÍDO DO LAUDO/EXAME", pdf_text]

    parts += [
        "",
        "## PERGUNTA / DADO NOVO",
        user_input,
        "",
        "Formule sua hipótese clínica seguindo rigorosamente o formato e os guardrails do sistema.",
    ]

    return "\n".join(parts)
