"""
Histórico de Exames — timeline visualization of lab markers.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

st.set_page_config(page_title="Histórico — HealthCore", page_icon="📊", layout="wide")

st.title("📊 Histórico de Exames")
st.caption("Visualize a evolução dos seus marcadores laboratoriais ao longo do tempo.")

try:
    import pandas as pd
    import plotly.express as px
    from services.exam_indexer import (
        get_categories,
        get_latest_values,
        get_trend,
        list_markers,
        parse_exam_history,
    )
except ImportError as e:
    st.error(f"Dependência não instalada: {e}. Execute: pip install -r requirements.txt")
    st.stop()

# ── Load data ─────────────────────────────────────────────────────────────────

history = parse_exam_history()

if not history:
    st.info(
        "Nenhum exame encontrado em EXAMES_HISTORICO.md. "
        "Preencha o arquivo ou use a página de Upload para importar laudos."
    )
    st.stop()

# ── Latest values overview ────────────────────────────────────────────────────

st.subheader("Últimos Valores")

latest = get_latest_values()
if latest:
    rows = []
    for marker, entry in sorted(latest.items()):
        rows.append({
            "Marcador": marker,
            "Último Valor": f"{entry.value} {entry.reference}",
            "Data": str(entry.date) if entry.date else "—",
            "Status": entry.status,
            "Categoria": entry.category,
        })

    df_latest = pd.DataFrame(rows)

    # Color status column
    def color_status(val):
        if "↑" in str(val):
            return "color: #FF4444"
        elif "↓" in str(val):
            return "color: #4444FF"
        elif "✅" in str(val):
            return "color: #44BB44"
        return ""

    st.dataframe(
        df_latest.style.applymap(color_status, subset=["Status"]),
        use_container_width=True,
        hide_index=True,
    )

st.divider()

# ── Trend chart ───────────────────────────────────────────────────────────────

st.subheader("Evolução de Marcador")

markers = list_markers()
categories = get_categories()

# Group selector
col1, col2 = st.columns([1, 2])
with col1:
    category_filter = st.selectbox(
        "Filtrar por categoria",
        options=["Todas"] + sorted(categories.keys()),
    )

with col2:
    if category_filter == "Todas":
        available_markers = markers
    else:
        available_markers = sorted(categories.get(category_filter, []))

    selected_marker = st.selectbox(
        "Selecione o marcador",
        options=available_markers,
        help="Escolha um marcador para ver sua evolução",
    )

if selected_marker:
    trend = get_trend(selected_marker)

    if len(trend) < 2:
        st.info(
            f"Apenas {len(trend)} registro(s) para '{selected_marker}'. "
            "Adicione mais exames para ver a evolução."
        )
        if trend:
            entry = trend[0]
            st.metric(
                label=selected_marker,
                value=f"{entry.value}",
                help=f"Referência: {entry.reference} | Data: {entry.date}",
            )
    else:
        # Build chart data
        chart_data = []
        for entry in trend:
            if entry.date and entry.value:
                try:
                    numeric_value = float(
                        entry.value.replace(",", ".").split()[0]
                    )
                    chart_data.append({"Data": entry.date, "Valor": numeric_value})
                except (ValueError, IndexError):
                    pass  # Non-numeric values skipped

        if chart_data:
            df_chart = pd.DataFrame(chart_data)
            first_entry = trend[0]
            unit = first_entry.reference.split()[-1] if first_entry.reference else ""

            fig = px.line(
                df_chart,
                x="Data",
                y="Valor",
                title=f"{selected_marker}",
                markers=True,
                labels={"Valor": f"Valor ({unit})" if unit else "Valor"},
            )
            fig.update_traces(line_color="#0066CC", marker_size=8)
            fig.update_layout(hovermode="x unified")

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Valores não numéricos — exibindo tabela.")

    # Always show the full table for selected marker
    with st.expander("Ver tabela completa", expanded=len(trend) < 5):
        rows = []
        for entry in trend:
            rows.append({
                "Data": str(entry.date) if entry.date else "—",
                "Valor": entry.value,
                "Referência": entry.reference,
                "Status": entry.status,
                "Contexto": entry.context,
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ── Multi-marker comparison ───────────────────────────────────────────────────

st.divider()
st.subheader("Comparação de Múltiplos Marcadores")

multi_markers = st.multiselect(
    "Selecione até 5 marcadores para comparar",
    options=markers,
    max_selections=5,
)

if len(multi_markers) >= 2:
    rows = []
    for marker in multi_markers:
        for entry in get_trend(marker):
            if entry.date and entry.value:
                try:
                    val = float(entry.value.replace(",", ".").split()[0])
                    rows.append({"Data": entry.date, "Valor": val, "Marcador": marker})
                except (ValueError, IndexError):
                    pass

    if rows:
        df_multi = pd.DataFrame(rows)
        fig2 = px.line(
            df_multi,
            x="Data",
            y="Valor",
            color="Marcador",
            title="Comparação de Marcadores",
            markers=True,
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Sem dados numéricos suficientes para o gráfico de comparação.")
