"""
Gerador de Relatório — creates a structured PDF for doctor visits.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from datetime import date, datetime

import streamlit as st

from config.settings import LOGS_DIR
from services.memory_manager import read_prontuario

st.set_page_config(page_title="Relatório — HealthCore", page_icon="📋", layout="wide")

st.title("📋 Gerador de Relatório para Consulta")
st.caption(
    "Gere um relatório estruturado para levar ao médico. "
    "O documento inclui hipóteses, ressalvas e próximos passos — com disclaimer obrigatório."
)


def load_recent_debates(n: int = 20) -> list[dict]:
    """Loads the most recent debate log entries."""
    entries = []
    if not LOGS_DIR.exists():
        return entries

    log_files = sorted(LOGS_DIR.glob("*.jsonl"), reverse=True)
    for log_file in log_files[:5]:  # Check last 5 days
        try:
            with log_file.open(encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if entry.get("input") and not entry.get("is_emergency"):
                            entries.append(entry)
                    except json.JSONDecodeError:
                        continue
        except Exception:
            continue

        if len(entries) >= n:
            break

    return entries[:n]


# ── Session selection ─────────────────────────────────────────────────────────

debates = load_recent_debates()

if not debates:
    st.info(
        "Nenhuma sessão encontrada nos logs. "
        "Use a página de Chat ou Upload de Exame primeiro para gerar sessões."
    )
    st.stop()

# Build options
options = {}
for d in debates:
    ts = d.get("timestamp", "")
    label = d.get("input", "")[:60]
    urgency = d.get("urgency", "")
    key = f"{ts[:16]} — {urgency} — {label}..."
    options[key] = d

selected_key = st.selectbox(
    "Selecione a sessão para incluir no relatório",
    options=list(options.keys()),
)

selected_debate = options[selected_key]

# ── Report customization ──────────────────────────────────────────────────────

st.divider()
st.subheader("Configurações do Relatório")

col1, col2 = st.columns(2)
with col1:
    report_date = st.date_input("Data do relatório", value=date.today())
    doctor_name = st.text_input("Nome do médico (opcional)", placeholder="Dr. João Silva")
with col2:
    specialty = st.text_input("Especialidade (opcional)", placeholder="Endocrinologia")
    patient_note = st.text_area(
        "Observações adicionais (opcional)",
        placeholder="Contexto que você quer incluir no relatório...",
        height=80,
    )

# ── Preview ───────────────────────────────────────────────────────────────────

st.divider()
st.subheader("Preview do Relatório")

prontuario = read_prontuario()
patient_name = "Paciente"
for line in prontuario.splitlines():
    if "Nome:" in line:
        patient_name = line.split("Nome:")[-1].strip()
        break

# Build report content
urgency = selected_debate.get("urgency", "INFORMATIVO")
skills = selected_debate.get("skills_used", [])
timestamp = selected_debate.get("timestamp", "")[:16]

report_md = f"""
# Relatório de Apoio Clínico — HealthCore

**Data:** {report_date.strftime('%d/%m/%Y')}
**Paciente:** {patient_name}
**Médico:** {doctor_name or 'A preencher'}
**Especialidade:** {specialty or 'A preencher'}
**Gerado em:** {timestamp}

---

> ⚠️ Este documento foi gerado por um sistema de apoio à decisão (HealthCore).
> **Não é um laudo médico, não substitui avaliação clínica e não emite diagnósticos.**
> As informações abaixo são hipóteses clínicas para discussão com o profissional de saúde.

---

## Contexto da Sessão

**Pergunta / dado analisado:**
{selected_debate.get('input', '')}

**Nível de urgência:** {urgency}
**Especialidades ativadas:** {', '.join(skills) if skills else 'geral'}

---

## Próximos Passos Recomendados

*[Esta seção é preenchida a partir da síntese dos agentes — veja a sessão de Chat para o conteúdo completo.]*

{patient_note or ''}

---

## Sessões e Histórico

Para ver a síntese completa desta sessão, consulte o Chat no HealthCore.

---

*Gerado por HealthCore v1.0 — sistema de apoio à decisão em saúde pessoal.*
*[Claude Code](https://claude.ai/code) | Anthropic*
*Este documento não tem valor médico-legal.*
"""

st.markdown(report_md)

# ── Generate PDF ──────────────────────────────────────────────────────────────

st.divider()

col1, col2 = st.columns(2)

with col1:
    if st.button("📄 Gerar PDF", type="primary"):
        try:
            from services.report_generator import generate_report_pdf

            pdf_bytes = generate_report_pdf(
                content_md=report_md,
                patient_name=patient_name,
                report_date=report_date,
            )

            filename = f"healthcore_relatorio_{report_date.strftime('%Y-%m-%d')}.pdf"
            st.download_button(
                label="⬇️ Baixar PDF",
                data=pdf_bytes,
                file_name=filename,
                mime="application/pdf",
            )
            st.success("PDF gerado! Clique em 'Baixar PDF' acima.")
        except Exception as e:
            st.error(f"Erro ao gerar PDF: {e}")
            st.info(
                "Verifique se o WeasyPrint está instalado: `pip install weasyprint`\n\n"
                "Alternativa: copie o texto do preview acima e cole num editor de texto."
            )

with col2:
    # Markdown download as fallback
    st.download_button(
        label="⬇️ Baixar como Markdown",
        data=report_md.encode("utf-8"),
        file_name=f"healthcore_relatorio_{report_date.strftime('%Y-%m-%d')}.md",
        mime="text/markdown",
    )
    st.caption("Alternativa ao PDF — pode ser aberto em qualquer editor de texto.")
