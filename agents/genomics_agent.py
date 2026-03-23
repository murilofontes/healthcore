"""
Genomics Agent — interprets genetic variants with strict R3 guardrail.
SNP array data is always SUSPEITA_GENETICA — never a diagnosis.
"""

import anthropic

from config.settings import MAX_TOKENS, MODEL
from services.memory_manager import load_agent_prompt, load_skill


class GenomicsAgent:
    def __init__(self, client: anthropic.Anthropic):
        self.client = client
        self.system_prompt = load_agent_prompt("genomics")
        self.genomics_skill = load_skill("genomics")

    def analyze(
        self,
        user_input: str,
        clinical_hypothesis: str,
        prontuario: str,
        exames: str,
    ) -> str:
        """
        Interprets genetic variants in the context of clinical findings.

        Args:
            user_input: Original user question.
            clinical_hypothesis: Clinical agent output (for correlation context).
            prontuario: Full content of PRONTUARIO.md.
            exames: Full content of EXAMES_HISTORICO.md.
        """
        user_message = _build_genomics_prompt(
            user_input, clinical_hypothesis, prontuario, exames, self.genomics_skill
        )

        response = self.client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=self.system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        return response.content[0].text


def _build_genomics_prompt(
    user_input: str,
    clinical_hypothesis: str,
    prontuario: str,
    exames: str,
    genomics_skill: str,
) -> str:
    return "\n".join([
        "## CONTEXTO CLÍNICO",
        user_input,
        "",
        "## PRONTUÁRIO (incluindo dados genéticos)",
        prontuario,
        "",
        "## HIPÓTESE CLÍNICA (para correlação genômica)",
        clinical_hypothesis,
        "",
        "## SKILL DE GENÔMICA",
        genomics_skill,
        "",
        "LEMBRETE OBRIGATÓRIO: Todo dado de SNP array é [SUSPEITA_GENETICA]. "
        "Nunca diagnóstico. Sempre sugerir confirmação laboratorial clínica.",
        "",
        "Analise os dados genéticos disponíveis no prontuário e correlacione com o fenótipo clínico.",
    ])
