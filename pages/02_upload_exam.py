"""
Upload de Exame — PDF upload, extraction, analysis and storage.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date

import streamlit as st

from agents.debate import DebateEngine
from config.guardrails import URGENCY_LEVELS
from services.memory_manager import append_to_exames
from services.pdf_parser import extract_lab_values, extract_text_from_pdf, store_laudo

st.set_page_config(page_title="Upload de Exame — HealthCore", page_icon="📄", layout="wide")

st.title("📄 Upload de Exame")
st.caption(
    "Envie um laudo em PDF. O sistema extrai o texto e aciona os agentes para análise contextualizada."
)

# ── Session state ─────────────────────────────────────────────────────────────

if "engine" not in st.session_state:
    try:
        st.session_state.engine = DebateEngine()
    except ValueError as e:
        st.error(f"⚠️ {e}")
        st.stop()

if "extracted_text" not in st.session_state:
    st.session_state.extracted_text = ""

if "upload_result" not in st.session_state:
    st.session_state.upload_result = None

# ── Upload form ───────────────────────────────────────────────────────────────

with st.form("upload_form"):
    uploaded_file = st.file_uploader(
        "Selecione o PDF do laudo",
        type=["pdf"],
        help="Laudos de laboratórios como Fleury, DASA, Hermes Pardini, Lavoisier, etc.",
    )

    col1, col2 = st.columns(2)
    with col1:
        exam_label = st.text_input(
            "Descrição do exame",
            placeholder="ex: hemograma-fleury, painel-metabolico-dasa",
            help="Será usado como nome do arquivo salvo.",
        )
    with col2:
        exam_date = st.date_input(
            "Data do exame",
            value=date.today(),
            max_value=date.today(),
        )

    context_note = st.text_area(
        "Contexto adicional (opcional)",
        placeholder="ex: em jejum de 12h, primeira semana de uso de tirzepatida...",
        height=80,
    )

    submitted = st.form_submit_button("📤 Extrair e Analisar", type="primary")

if submitted and uploaded_file:
    if not exam_label:
        st.warning("Por favor, adicione uma descrição para o exame.")
        st.stop()

    # Save PDF locally
    with st.spinner("Salvando PDF..."):
        pdf_bytes = uploaded_file.read()
        saved_path = store_laudo(pdf_bytes, exam_label, exam_date)
        st.success(f"PDF salvo em `{saved_path.name}`")

    # Extract text
    with st.spinner("Extraindo texto do PDF..."):
        extracted = extract_text_from_pdf(saved_path)
        lab_values = extract_lab_values(saved_path)
        st.session_state.extracted_text = extracted

    # Show preview
    with st.expander("📋 Texto extraído (preview)", expanded=False):
        st.text(extracted[:3000] + ("..." if len(extracted) > 3000 else ""))

    if lab_values:
        st.markdown(f"**{len(lab_values)} valores detectados automaticamente:**")
        import pandas as pd
        df = pd.DataFrame(lab_values)[["marker", "value", "unit", "reference"]]
        st.dataframe(df, use_container_width=True)

    # Run debate
    user_input = f"Novo laudo: {exam_label} ({exam_date})"
    if context_note:
        user_input += f"\n\nContexto: {context_note}"

    with st.spinner("Debatendo hipóteses com os agentes..."):
        try:
            result = st.session_state.engine.run(user_input, pdf_text=extracted)
            st.session_state.upload_result = result
        except Exception as e:
            st.error(f"Erro na análise: {e}")
            st.stop()

    # Show result
    urgency_info = URGENCY_LEVELS.get(result.urgency, {})
    emoji = urgency_info.get("emoji", "🟢")
    st.subheader(f"Análise do Laudo {emoji} {result.urgency}")

    if result.clinical:
        with st.expander("🩺 Hipótese Clínica", expanded=True):
            st.markdown(result.clinical)
    if result.skeptic:
        with st.expander("🔬 Objeções do Agente Cético", expanded=False):
            st.markdown(result.skeptic)
    if result.genomics:
        with st.expander("🧬 Análise Genômica", expanded=False):
            st.markdown(result.genomics)

    st.subheader("Síntese")
    st.markdown(result.synthesis)

    # Save parsed values to exam history
    if lab_values:
        st.divider()
        if st.button("💾 Salvar valores no histórico de exames"):
            lines = [f"\n\n## Exame: {exam_label} — {exam_date}\n"]
            lines.append("| Marcador | Valor | Unidade | Referência |")
            lines.append("|----------|-------|---------|-----------|")
            for v in lab_values:
                lines.append(
                    f"| {v['marker']} | {v['value']} | {v.get('unit','')} | {v.get('reference','')} |"
                )
            try:
                append_to_exames("\n".join(lines))
                st.success("Valores salvos no EXAMES_HISTORICO.md!")
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")

elif submitted and not uploaded_file:
    st.warning("Por favor, selecione um arquivo PDF.")
