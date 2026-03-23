"""
Prontuário — visualização e edição manual do prontuário do paciente.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime

import streamlit as st

from config.settings import PRONTUARIO_PATH
from services.memory_manager import append_to_prontuario, correct_entry, read_prontuario

st.set_page_config(page_title="Prontuário — HealthCore", page_icon="📋", layout="wide")

st.title("📋 Prontuário")
st.caption("Histórico clínico completo. Somente leitura — novas entradas são sempre adicionadas, nunca sobrescritas (R6).")

# ── Load ───────────────────────────────────────────────────────────────────────

prontuario = read_prontuario()

if not prontuario.strip():
    st.warning("Prontuário vazio. Adicione a primeira entrada abaixo.")
else:
    # File info
    if PRONTUARIO_PATH.exists():
        stat = PRONTUARIO_PATH.stat()
        size_kb = round(stat.st_size / 1024, 1)
        modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
        col1, col2, col3 = st.columns(3)
        col1.metric("Tamanho", f"{size_kb} KB")
        col2.metric("Última atualização", modified)
        col3.metric("Linhas", len(prontuario.splitlines()))

    st.divider()
    st.markdown(prontuario)

st.divider()

# ── Add entry ──────────────────────────────────────────────────────────────────

with st.expander("➕ Adicionar entrada manual", expanded=False):
    with st.form("add_entry"):
        entry_text = st.text_area(
            "Texto da entrada",
            height=150,
            placeholder="Ex: Consulta com Dr. X em 23/03/2026 — ajuste de dose do medicamento Y...",
        )
        submitted = st.form_submit_button("💾 Salvar no prontuário", type="primary")

    if submitted:
        if not entry_text.strip():
            st.warning("Digite o texto da entrada.")
        else:
            try:
                append_to_prontuario(entry_text.strip())
                st.success("Entrada salva!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro: {e}")

# ── Correct entry ──────────────────────────────────────────────────────────────

with st.expander("✏️ Corrigir entrada existente", expanded=False):
    st.caption("Não apaga o original — adiciona uma nota de correção datada.")
    with st.form("correct_entry"):
        original = st.text_area("Trecho original (copie do prontuário acima)", height=80)
        correction = st.text_area("Correção / nota", height=80,
                                   placeholder="Ex: Valor correto é X, não Y.")
        submitted_corr = st.form_submit_button("✏️ Registrar correção")

    if submitted_corr:
        if not original.strip() or not correction.strip():
            st.warning("Preencha os dois campos.")
        else:
            try:
                correct_entry(original.strip(), correction.strip())
                st.success("Correção registrada!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro: {e}")
