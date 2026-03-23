"""
HealthCore — Entry point.
Consent check → Streamlit multipage app.
"""

import sys
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

from scripts.init_consent import check_consent, request_consent_streamlit

st.set_page_config(
    page_title="HealthCore",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Consent gate
if not check_consent():
    st.title("HealthCore — Apoio à Decisão em Saúde")
    st.warning(
        "**Antes de continuar, leia e confirme o disclaimer abaixo.**",
        icon="⚠️",
    )
    st.markdown("""
    > Este sistema é uma ferramenta de **apoio à decisão clínica pessoal**.
    > **Não substitui** avaliação médica, diagnóstico ou prescrição profissional.
    >
    > - Todo output é uma **hipótese clínica** — não um diagnóstico
    > - Dados genéticos de SNP array são hipóteses, não laudos
    > - Em emergências: **SAMU 192** / CVV 188
    > - A responsabilidade clínica final é sempre do profissional de saúde
    """)

    if st.button("✅ Confirmo que entendi as limitações — Continuar", type="primary"):
        from config.settings import CONSENT_FLAG
        CONSENT_FLAG.touch()
        st.rerun()
    st.stop()

# ── Main landing page ─────────────────────────────────────────────────────────

st.title("🏥 HealthCore")
st.caption("Sistema de apoio à decisão em saúde pessoal")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.info("### 💬 Chat\nConverse com os agentes clínico e cético sobre seus exames e saúde.")

with col2:
    st.info("### 📄 Upload de Exame\nEnvie laudos em PDF para análise contextualizada.")

with col3:
    st.info("### 📊 Histórico\nVisualize tendências dos seus marcadores ao longo do tempo.")

with col4:
    st.info("### 📋 Relatório\nGere um PDF estruturado para levar ao médico.")

st.divider()
st.markdown(
    "**Use o menu lateral** para navegar entre as seções. "
    "Comece pelo **Chat** para fazer perguntas sobre seus exames."
)

# Sidebar info
with st.sidebar:
    st.markdown("### HealthCore")
    st.markdown("v1.0 | Mar/2026")
    st.divider()
    st.markdown("**Emergência:** SAMU 192")
    st.markdown("**Apoio emocional:** CVV 188")
    st.divider()
    st.caption(
        "HealthCore não emite diagnósticos. "
        "Leve sempre as hipóteses ao seu médico."
    )
