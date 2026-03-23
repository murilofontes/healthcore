"""
Chat page — main interface for multi-agent clinical debate.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from agents.debate import DebateEngine, DebateResult
from config.guardrails import URGENCY_LEVELS
from services.memory_manager import append_to_prontuario, read_prontuario

st.set_page_config(page_title="Chat — HealthCore", page_icon="💬", layout="wide")

st.title("💬 Chat Clínico")
st.caption(
    "Converse com os agentes clínico e cético. "
    "Cada resposta passa por um debate interno antes de chegar até você."
)

# ── Session state ─────────────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_result" not in st.session_state:
    st.session_state.last_result = None

if "engine" not in st.session_state:
    try:
        st.session_state.engine = DebateEngine()
    except ValueError as e:
        st.error(f"⚠️ {e}")
        st.stop()

# ── Sidebar controls ──────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### Configurações")
    show_debate = st.toggle("Mostrar debate completo (Clínico + Cético)", value=False)
    show_genomics = st.toggle("Mostrar análise genômica (quando disponível)", value=True)

    st.divider()
    if st.button("🗑️ Limpar conversa"):
        st.session_state.messages = []
        st.session_state.last_result = None
        st.rerun()

    st.divider()
    st.markdown("**Emergência:** SAMU 192")
    st.markdown("**CVV:** 188")

# ── Display message history ───────────────────────────────────────────────────

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Chat input ────────────────────────────────────────────────────────────────

user_input = st.chat_input(
    "Pergunte sobre seus exames, sintomas ou saúde...",
    key="chat_input",
)

if user_input:
    # Display user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Run debate
    with st.chat_message("assistant"):
        with st.spinner("Debatendo hipóteses clínicas..."):
            try:
                result: DebateResult = st.session_state.engine.run(user_input)
                st.session_state.last_result = result
            except Exception as e:
                st.error(f"Erro ao processar: {e}")
                st.stop()

        # Display urgency badge
        urgency_info = URGENCY_LEVELS.get(result.urgency, {})
        emoji = urgency_info.get("emoji", "🟢")
        description = urgency_info.get("description", "")

        if result.urgency == "EMERGÊNCIA":
            st.error(f"{emoji} **{result.urgency}** — {description}")
        elif result.urgency == "URGENTE":
            st.error(f"{emoji} **{result.urgency}** — {description}")
        elif result.urgency == "IMPORTANTE":
            st.warning(f"{emoji} **{result.urgency}** — {description}")
        elif result.urgency == "MONITORAR":
            st.info(f"{emoji} **{result.urgency}** — {description}")
        else:
            st.success(f"{emoji} **{result.urgency}** — {description}")

        # Skills used
        if result.skills_used:
            st.caption(f"Especialidades ativadas: {', '.join(result.skills_used)}")

        # Show full debate if toggled
        if show_debate and result.clinical and not result.is_emergency:
            with st.expander("🩺 Hipótese do Agente Clínico", expanded=False):
                st.markdown(result.clinical)
            with st.expander("🔬 Objeções do Agente Cético", expanded=False):
                st.markdown(result.skeptic)

        if show_genomics and result.genomics:
            with st.expander("🧬 Análise Genômica", expanded=False):
                st.markdown(result.genomics)

        # Main synthesis
        st.markdown(result.synthesis)
        st.session_state.messages.append({"role": "assistant", "content": result.synthesis})

# ── Save to prontuário ────────────────────────────────────────────────────────

if st.session_state.last_result and not st.session_state.last_result.is_emergency:
    result = st.session_state.last_result
    if result.synthesis and result.urgency != "INFORMATIVO":
        st.divider()
        col1, col2 = st.columns([3, 1])
        with col1:
            st.caption(
                "Deseja salvar a síntese desta conversa no prontuário? "
                "Isso registrará permanentemente esta análise no seu histórico."
            )
        with col2:
            if st.button("💾 Salvar no prontuário", type="secondary"):
                try:
                    entry = (
                        f"### Sessão HealthCore — {result.urgency}\n\n"
                        f"**Pergunta:** {result.user_input}\n\n"
                        f"**Síntese:**\n{result.synthesis[:1000]}...\n\n"
                        f"*Skills utilizadas: {', '.join(result.skills_used) or 'nenhuma'}*"
                    )
                    append_to_prontuario(entry)
                    st.success("Salvo no prontuário!")
                    st.session_state.last_result.prontuario_updated = True
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
