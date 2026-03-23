"""
Prontuário — histórico clínico + análises dos debates anteriores.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from datetime import datetime

import streamlit as st

from config.settings import LOGS_DIR, PRONTUARIO_PATH
from services.memory_manager import append_to_prontuario, correct_entry, read_prontuario

st.set_page_config(page_title="Prontuário — HealthCore", page_icon="📋", layout="wide")

st.title("📋 Prontuário")

tab_prontuario, tab_analises = st.tabs(["📄 Histórico Clínico", "🔬 Análises Anteriores"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Prontuário
# ══════════════════════════════════════════════════════════════════════════════

with tab_prontuario:
    st.caption("Somente leitura — entradas são sempre adicionadas, nunca sobrescritas (R6).")

    prontuario = read_prontuario()

    if not prontuario.strip():
        st.warning("Prontuário vazio. Adicione a primeira entrada abaixo.")
    else:
        if PRONTUARIO_PATH.exists():
            stat = PRONTUARIO_PATH.stat()
            col1, col2, col3 = st.columns(3)
            col1.metric("Tamanho", f"{round(stat.st_size/1024, 1)} KB")
            col2.metric("Última atualização", datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"))
            col3.metric("Linhas", len(prontuario.splitlines()))
            st.divider()

        st.markdown(prontuario)

    st.divider()

    with st.expander("➕ Adicionar entrada manual", expanded=False):
        with st.form("add_entry"):
            entry_text = st.text_area("Texto da entrada", height=150,
                                       placeholder="Ex: Consulta com Dr. X — ajuste de medicamento Y...")
            if st.form_submit_button("💾 Salvar", type="primary"):
                if not entry_text.strip():
                    st.warning("Digite o texto.")
                else:
                    try:
                        append_to_prontuario(entry_text.strip())
                        st.success("Salvo!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro: {e}")

    with st.expander("✏️ Corrigir entrada existente", expanded=False):
        st.caption("Não apaga o original — adiciona nota de correção datada.")
        with st.form("correct_entry"):
            original = st.text_area("Trecho original", height=80)
            correction = st.text_area("Correção / nota", height=80)
            if st.form_submit_button("✏️ Registrar correção"):
                if not original.strip() or not correction.strip():
                    st.warning("Preencha os dois campos.")
                else:
                    try:
                        correct_entry(original.strip(), correction.strip())
                        st.success("Correção registrada!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Análises anteriores (debate logs)
# ══════════════════════════════════════════════════════════════════════════════

with tab_analises:
    st.caption("Histórico completo de análises: síntese, hipótese clínica e objeções do agente cético.")

    # Load all debate logs
    entries = []
    if LOGS_DIR.exists():
        for log_file in sorted(LOGS_DIR.glob("*.jsonl"), reverse=True):
            for line in log_file.read_text(encoding="utf-8").splitlines():
                try:
                    e = json.loads(line)
                    if e.get("synthesis") or e.get("clinical"):
                        entries.append(e)
                except Exception:
                    continue

    if not entries:
        st.info("Nenhuma análise registrada ainda. Analise exames pela página Upload ou pelo terminal.")
        st.stop()

    # Filters
    col1, col2 = st.columns([2, 1])
    with col1:
        search = st.text_input("🔍 Buscar nas análises", placeholder="ex: colesterol, fígado, vitamina D...")
    with col2:
        urgency_filter = st.selectbox("Filtrar por urgência",
                                       ["Todas", "EMERGÊNCIA", "URGENTE", "IMPORTANTE", "MONITORAR", "INFORMATIVO"])

    # Filter entries
    filtered = entries
    if urgency_filter != "Todas":
        filtered = [e for e in filtered if e.get("urgency", "") == urgency_filter]
    if search:
        q = search.lower()
        filtered = [e for e in filtered if
                    q in (e.get("synthesis", "") + e.get("clinical", "") + e.get("input", "")).lower()]

    st.caption(f"{len(filtered)} análise(s) encontrada(s)")
    st.divider()

    URGENCY_EMOJI = {
        "EMERGÊNCIA": "🔴🚨",
        "URGENTE": "🔴",
        "IMPORTANTE": "🟠",
        "MONITORAR": "🟡",
        "INFORMATIVO": "🟢",
    }

    for entry in filtered:
        urgency = entry.get("urgency", "INFORMATIVO")
        emoji = URGENCY_EMOJI.get(urgency, "🟢")
        ts = entry.get("timestamp", "")
        date_str = ts[:10] if ts else "—"
        user_input = entry.get("input", entry.get("user_input", ""))[:80]

        with st.expander(f"{emoji} {date_str} — {urgency} — {user_input}", expanded=False):

            # Synthesis — always show first and expanded
            synthesis = entry.get("synthesis", "")
            if synthesis:
                st.markdown("### Síntese HealthCore")
                st.markdown(synthesis)

            # Clinical hypothesis
            clinical = entry.get("clinical", "")
            if clinical and "[Modo rápido" not in clinical and "[Scan rápido" not in clinical:
                st.divider()
                with st.expander("🩺 Hipótese Clínica completa", expanded=False):
                    st.markdown(clinical)

            # Skeptic objections
            skeptic = entry.get("skeptic", "")
            if skeptic:
                st.divider()
                with st.expander("🔬 Objeções do Agente Cético", expanded=False):
                    st.markdown(skeptic)

            # Genomics
            genomics = entry.get("genomics", "")
            if genomics:
                st.divider()
                with st.expander("🧬 Análise Genômica", expanded=False):
                    st.markdown(genomics)

            # Skills used
            skills = entry.get("skills_used", [])
            if skills:
                st.caption(f"Especialidades ativadas: {', '.join(skills)}")

            # Save to prontuário button
            if synthesis and not entry.get("is_emergency"):
                if st.button("💾 Salvar no prontuário", key=f"save_{ts}"):
                    text = (
                        f"### Análise HealthCore — {date_str}\n"
                        f"**Urgência:** {urgency}\n\n"
                        f"**Input:** {user_input}\n\n"
                        f"**Síntese:**\n{synthesis[:1500]}"
                    )
                    try:
                        append_to_prontuario(text)
                        st.success("Salvo no prontuário!")
                    except Exception as ex:
                        st.error(f"Erro: {ex}")
