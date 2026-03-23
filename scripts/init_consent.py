"""
First-run consent check.
Displays disclaimer and blocks execution until user confirms.
Writes a flag file so it only runs once.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import CONSENT_FLAG

DISCLAIMER = """
╔══════════════════════════════════════════════════════════════════════╗
║                         HEALTHCORE                                   ║
║               Sistema de Apoio à Decisão em Saúde                   ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  Este sistema é uma ferramenta de apoio à decisão clínica pessoal.  ║
║  NÃO substitui avaliação médica, diagnóstico ou prescrição          ║
║  profissional.                                                       ║
║                                                                      ║
║  • Todo output é uma hipótese clínica — não um diagnóstico          ║
║  • Dados genéticos de SNP array são hipóteses, não laudos           ║
║  • Em emergências: SAMU 192 / CVV 188                               ║
║  • A responsabilidade clínica final é sempre do profissional        ║
║    de saúde                                                          ║
║                                                                      ║
║  Ao continuar, você confirma que compreende estas limitações.        ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
"""


def check_consent() -> bool:
    """Returns True if consent was previously given."""
    return CONSENT_FLAG.exists()


def request_consent() -> bool:
    """Interactively requests consent. Returns True if accepted."""
    print(DISCLAIMER)
    try:
        answer = input('Digite "CONFIRMO" para continuar: ').strip().upper()
    except (KeyboardInterrupt, EOFError):
        print("\nOperação cancelada.")
        return False

    if answer == "CONFIRMO":
        CONSENT_FLAG.touch()
        print("\nConsentimento registrado. Bem-vindo ao HealthCore.\n")
        return True
    else:
        print("\nConsentimento necessário para uso do sistema.")
        return False


def ensure_consent() -> bool:
    """Checks or requests consent. Returns True if we can proceed."""
    if check_consent():
        return True
    return request_consent()


def request_consent_streamlit() -> None:
    """Streamlit-compatible consent request (used in app.py)."""
    # Handled directly in app.py via st.button — this is a no-op placeholder
    pass


if __name__ == "__main__":
    if not ensure_consent():
        sys.exit(1)
