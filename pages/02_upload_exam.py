"""
Upload de Exame — PDF individual, ZIP com múltiplos laudos, ou histórico em planilha.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import io
import zipfile
from datetime import date

import streamlit as st

from agents.debate import DebateEngine
from config.guardrails import URGENCY_LEVELS
from services.memory_manager import append_to_exames
from services.pdf_parser import extract_lab_values, extract_text_from_pdf, store_laudo

st.set_page_config(page_title="Upload de Exame — HealthCore", page_icon="📄", layout="wide")

st.title("📄 Upload de Exame")
st.caption(
    "PDF individual, ZIP com vários laudos, ou planilha com histórico completo."
)

# ── Session state ─────────────────────────────────────────────────────────────

if "engine" not in st.session_state:
    try:
        st.session_state.engine = DebateEngine()
    except ValueError as e:
        st.error(f"⚠️ {e}")
        st.stop()

if "upload_result" not in st.session_state:
    st.session_state.upload_result = None


# ══════════════════════════════════════════════════════════════════════════════
# Helper functions (defined before use)
# ══════════════════════════════════════════════════════════════════════════════

def _save_lab_values_to_history(lab_values: list, label: str, exam_date: date):
    """Saves extracted lab values to EXAMES_HISTORICO.md."""
    lines = [f"\n\n## Exame: {label} — {exam_date}\n"]
    lines.append("| Marcador | Valor | Unidade | Referência |")
    lines.append("|----------|-------|---------|-----------|")
    for v in lab_values:
        lines.append(
            f"| {v['marker']} | {v['value']} | {v.get('unit', '')} | {v.get('reference', '')} |"
        )
    try:
        append_to_exames("\n".join(lines))
        st.success(f"✓ {len(lab_values)} valores salvos no EXAMES_HISTORICO.md!")
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")


def _show_debate_result(result, key_prefix: str = ""):
    """Renders a DebateResult in the UI."""
    urgency_info = URGENCY_LEVELS.get(result.urgency, {})
    emoji = urgency_info.get("emoji", "🟢")

    if result.urgency in ("EMERGÊNCIA", "URGENTE"):
        st.error(f"{emoji} **{result.urgency}**")
    elif result.urgency == "IMPORTANTE":
        st.warning(f"{emoji} **{result.urgency}**")
    else:
        st.info(f"{emoji} **{result.urgency}**")

    if result.clinical:
        with st.expander("🩺 Hipótese Clínica", expanded=True):
            st.markdown(result.clinical)
    if result.skeptic:
        with st.expander("🔬 Agente Cético", expanded=False):
            st.markdown(result.skeptic)
    if result.genomics:
        with st.expander("🧬 Análise Genômica", expanded=False):
            st.markdown(result.genomics)

    st.subheader("Síntese")
    st.markdown(result.synthesis)


# ══════════════════════════════════════════════════════════════════════════════
# Mode tabs
# ══════════════════════════════════════════════════════════════════════════════

tab_single, tab_zip, tab_history = st.tabs([
    "📄 PDF individual",
    "🗜️ ZIP com múltiplos laudos",
    "📊 Histórico completo (planilha)",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Single PDF
# ══════════════════════════════════════════════════════════════════════════════

with tab_single:
    with st.form("upload_single"):
        uploaded_file = st.file_uploader(
            "Selecione o PDF do laudo",
            type=["pdf"],
            help="Fleury, DASA, Hermes Pardini, Lavoisier, Einstein, Sabin, etc.",
        )
        col1, col2 = st.columns(2)
        with col1:
            exam_label = st.text_input("Descrição", placeholder="ex: hemograma-fleury")
        with col2:
            exam_date = st.date_input("Data do exame", value=date.today(), max_value=date.today())

        context_note = st.text_area(
            "Contexto adicional (opcional)",
            placeholder="ex: em jejum de 12h, primeira semana de tirzepatida...",
            height=80,
        )
        submitted_single = st.form_submit_button("📤 Extrair e Analisar", type="primary")

    if submitted_single:
        if not uploaded_file:
            st.warning("Selecione um arquivo PDF.")
        elif not exam_label:
            st.warning("Adicione uma descrição para o exame.")
        else:
            import pandas as pd

            with st.spinner("Salvando e extraindo..."):
                saved_path = store_laudo(uploaded_file.read(), exam_label, exam_date)
                extracted = extract_text_from_pdf(saved_path)
                lab_values = extract_lab_values(saved_path)

            st.success(f"✓ Salvo: `{saved_path.name}`")

            with st.expander("📋 Texto extraído (preview)", expanded=False):
                st.text(extracted[:3000] + ("..." if len(extracted) > 3000 else ""))

            if lab_values:
                st.markdown(f"**{len(lab_values)} valores detectados:**")
                st.dataframe(
                    pd.DataFrame(lab_values)[["marker", "value", "unit", "reference"]],
                    use_container_width=True,
                )

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

            _show_debate_result(result)

            if lab_values:
                st.divider()
                if st.button("💾 Salvar valores no histórico", key="save_single"):
                    _save_lab_values_to_history(lab_values, exam_label, exam_date)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — ZIP upload
# ══════════════════════════════════════════════════════════════════════════════

with tab_zip:
    st.info(
        "Compacte todos os seus PDFs em um arquivo ZIP e envie de uma vez. "
        "Cada PDF será salvo em `laudos/` e analisado. "
        "Subpastas são suportadas."
    )

    with st.form("upload_zip"):
        uploaded_zip = st.file_uploader("Selecione o arquivo ZIP", type=["zip"])
        zip_date = st.date_input(
            "Data padrão (usada quando não detectada no PDF)",
            value=date.today(),
            max_value=date.today(),
        )
        zip_context = st.text_area(
            "Contexto geral (opcional)",
            placeholder="ex: painel anual 2025, todos do Fleury...",
            height=80,
        )
        analyze_all = st.checkbox("Analisar todos em conjunto com os agentes", value=True)
        submitted_zip = st.form_submit_button("📦 Processar ZIP", type="primary")

    if submitted_zip:
        if not uploaded_zip:
            st.warning("Selecione um arquivo ZIP.")
        else:
            import pandas as pd

            try:
                zf = zipfile.ZipFile(io.BytesIO(uploaded_zip.read()))
            except zipfile.BadZipFile:
                st.error("Arquivo ZIP inválido ou corrompido.")
                st.stop()

            pdf_entries = [
                n for n in zf.namelist()
                if n.lower().endswith(".pdf") and not n.startswith("__MACOSX")
            ]

            if not pdf_entries:
                st.warning("Nenhum PDF encontrado no ZIP.")
                st.stop()

            st.success(f"✓ {len(pdf_entries)} PDF(s) encontrado(s) no ZIP")

            all_lab_values = []
            all_texts = []
            progress = st.progress(0)

            for i, pdf_name in enumerate(pdf_entries):
                progress.progress(
                    (i + 1) / len(pdf_entries),
                    text=f"Processando ({i+1}/{len(pdf_entries)}): {Path(pdf_name).name}",
                )
                pdf_bytes = zf.read(pdf_name)
                label = Path(pdf_name).stem.replace(" ", "_").lower()[:50]
                saved_path = store_laudo(pdf_bytes, label, zip_date)
                extracted = extract_text_from_pdf(saved_path)
                lab_values = extract_lab_values(saved_path)
                all_lab_values.extend(lab_values)
                all_texts.append(f"## {Path(pdf_name).name}\n\n{extracted}")

                with st.expander(
                    f"📄 {Path(pdf_name).name} — {len(lab_values)} valores", expanded=False
                ):
                    if lab_values:
                        st.dataframe(
                            pd.DataFrame(lab_values)[["marker", "value", "unit", "reference"]],
                            use_container_width=True,
                        )
                    else:
                        st.text(extracted[:800] + "...")

            progress.empty()
            zf.close()

            st.success(
                f"✓ {len(pdf_entries)} PDFs salvos | "
                f"{len(all_lab_values)} valores extraídos no total"
            )

            if analyze_all and all_texts:
                user_input = f"Painel completo: {len(pdf_entries)} laudos ({zip_date})"
                if zip_context:
                    user_input += f"\n\nContexto: {zip_context}"

                with st.spinner(f"Analisando {len(pdf_entries)} laudos em conjunto..."):
                    try:
                        result = st.session_state.engine.run(
                            user_input,
                            pdf_text="\n\n---\n\n".join(all_texts)[:8000],
                        )
                        st.session_state.upload_result = result
                    except Exception as e:
                        st.error(f"Erro na análise: {e}")
                        st.stop()

                st.subheader("Análise Consolidada")
                _show_debate_result(result)

            if all_lab_values:
                st.divider()
                if st.button("💾 Salvar todos os valores no histórico", key="save_zip"):
                    _save_lab_values_to_history(
                        all_lab_values, f"painel-zip-{zip_date}", zip_date
                    )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Historical import (CSV / Excel / Google Sheets)
# ══════════════════════════════════════════════════════════════════════════════

with tab_history:
    st.markdown("""
    ### Importe o histórico completo dos seus exames

    Use esta aba para carregar **todos os exames da sua vida** de uma vez,
    organizados em planilha.

    **Formatos suportados:** CSV, Excel (.xlsx, .xls)

    ---

    #### Formato esperado da planilha

    A planilha deve ter as colunas abaixo (nomes flexíveis — o sistema tenta detectar automaticamente):

    | marcador | data | valor | referencia | unidade | contexto |
    |----------|------|-------|------------|---------|---------|
    | HOMA-IR | 2024-11-15 | 3.2 | < 2.5 | — | em jejum |
    | Ferritina | 2024-11-15 | 542 | 12-300 ng/mL | ng/mL | — |
    | TSH | 2023-06-10 | 2.1 | 0.4-4.0 | mUI/L | — |

    💡 **Dica:** Exporte direto do Google Sheets como CSV para importar aqui.
    """)

    # Download template
    template_csv = (
        "marcador,data,valor,referencia,unidade,contexto\n"
        "HOMA-IR,2024-11-15,3.2,< 2.5,,em jejum\n"
        "Ferritina,2024-11-15,542,12-300 ng/mL,ng/mL,\n"
        "TSH,2023-06-10,2.1,0.4-4.0 mUI/L,mUI/L,\n"
        "Vitamina D,2024-03-20,28,30-60 ng/mL,ng/mL,\n"
    )
    st.download_button(
        "⬇️ Baixar planilha modelo (CSV)",
        data=template_csv.encode("utf-8"),
        file_name="historico_exames_modelo.csv",
        mime="text/csv",
    )

    st.divider()

    with st.form("upload_history"):
        hist_file = st.file_uploader(
            "Selecione o CSV ou Excel com seu histórico",
            type=["csv", "xlsx", "xls"],
        )
        hist_context = st.text_area(
            "Contexto geral (opcional)",
            placeholder="ex: histórico completo 2019-2025, Fleury + Einstein...",
            height=80,
        )
        analyze_hist = st.checkbox(
            "Analisar o histórico completo com os agentes após importar",
            value=True,
        )
        submitted_hist = st.form_submit_button("📥 Importar Histórico", type="primary")

    if submitted_hist:
        if not hist_file:
            st.warning("Selecione um arquivo CSV ou Excel.")
        else:
            import pandas as pd

            # Read file
            try:
                if hist_file.name.endswith(".csv"):
                    df = pd.read_csv(hist_file)
                else:
                    df = pd.read_excel(hist_file)
            except Exception as e:
                st.error(f"Erro ao ler arquivo: {e}")
                st.stop()

            # Normalize column names
            df.columns = [c.lower().strip() for c in df.columns]
            col_map = _detect_columns(df.columns.tolist())

            if not col_map.get("marcador") or not col_map.get("valor"):
                st.error(
                    "Não foi possível detectar as colunas 'marcador' e 'valor'. "
                    "Verifique se a planilha segue o formato do modelo."
                )
                st.dataframe(df.head(), use_container_width=True)
                st.stop()

            st.success(f"✓ {len(df)} registros lidos")
            st.dataframe(df.head(10), use_container_width=True)

            # Convert to EXAMES_HISTORICO.md format
            with st.spinner("Convertendo para o formato do prontuário..."):
                md_lines = _dataframe_to_history_md(df, col_map)

            with st.expander("Preview do histórico importado (primeiras 30 linhas)", expanded=False):
                st.text("\n".join(md_lines[:30]))

            if st.form_submit_button:
                pass  # form already submitted

            # Save to EXAMES_HISTORICO.md
            try:
                append_to_exames("\n".join(md_lines))
                st.success(
                    f"✓ {len(df)} registros salvos em EXAMES_HISTORICO.md! "
                    "Acesse a página **Histórico** para visualizar os gráficos."
                )
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")
                st.stop()

            # Analyze with agents
            if analyze_hist:
                summary = _build_history_summary(df, col_map)
                user_input = f"Histórico completo importado: {len(df)} registros"
                if hist_context:
                    user_input += f"\n\nContexto: {hist_context}"

                with st.spinner("Analisando histórico completo com os agentes..."):
                    try:
                        result = st.session_state.engine.run(
                            user_input, pdf_text=summary
                        )
                        st.session_state.upload_result = result
                    except Exception as e:
                        st.error(f"Erro na análise: {e}")
                        st.stop()

                st.subheader("Análise do Histórico Completo")
                _show_debate_result(result)


# ── Column detection helpers ──────────────────────────────────────────────────

def _detect_columns(columns: list) -> dict:
    """Tries to map flexible column names to our standard schema."""
    mapping = {}
    aliases = {
        "marcador": ["marcador", "exame", "marker", "teste", "analito", "nome"],
        "data": ["data", "date", "data_coleta", "data coleta", "data_exame"],
        "valor": ["valor", "value", "resultado", "result"],
        "referencia": ["referencia", "referência", "ref", "reference", "vr", "valor_ref"],
        "unidade": ["unidade", "unit", "unid", "units"],
        "contexto": ["contexto", "context", "obs", "observação", "observacao", "nota"],
    }
    for field, candidates in aliases.items():
        for col in columns:
            if col in candidates or any(c in col for c in candidates):
                mapping[field] = col
                break
    return mapping


def _dataframe_to_history_md(df, col_map: dict) -> list:
    """Converts a DataFrame to EXAMES_HISTORICO.md table format."""
    import pandas as pd

    lines = ["\n\n## Histórico Importado\n"]

    # Group by marker for better organization
    marker_col = col_map["marcador"]
    date_col = col_map.get("data", "")
    value_col = col_map["valor"]
    ref_col = col_map.get("referencia", "")
    unit_col = col_map.get("unidade", "")
    ctx_col = col_map.get("contexto", "")

    markers = df[marker_col].dropna().unique()

    for marker in sorted(markers):
        marker_df = df[df[marker_col] == marker].copy()
        if date_col and date_col in df.columns:
            try:
                marker_df = marker_df.sort_values(date_col)
            except Exception:
                pass

        lines.append(f"\n### {marker}\n")
        lines.append("| Data | Valor | Referência | Contexto |")
        lines.append("|------|-------|-----------|---------|")

        for _, row in marker_df.iterrows():
            data = str(row.get(date_col, "—")) if date_col else "—"
            valor = str(row.get(value_col, ""))
            if unit_col and unit_col in df.columns and str(row.get(unit_col, "")):
                valor += f" {row.get(unit_col, '')}"
            ref = str(row.get(ref_col, "")) if ref_col else ""
            ctx = str(row.get(ctx_col, "")) if ctx_col else ""
            lines.append(f"| {data} | {valor} | {ref} | {ctx} |")

    return lines


def _build_history_summary(df, col_map: dict) -> str:
    """Builds a compact text summary of the history for the agent context."""
    marker_col = col_map["marcador"]
    value_col = col_map["valor"]
    date_col = col_map.get("data", "")

    lines = [f"Histórico com {len(df)} registros, {df[marker_col].nunique()} marcadores únicos.\n"]

    for marker in sorted(df[marker_col].dropna().unique()):
        marker_df = df[df[marker_col] == marker]
        values = marker_df[value_col].dropna().tolist()
        if values:
            if date_col and date_col in df.columns:
                try:
                    marker_df = marker_df.sort_values(date_col)
                    first_date = marker_df[date_col].iloc[0]
                    last_date = marker_df[date_col].iloc[-1]
                    lines.append(
                        f"- {marker}: {len(values)} medições ({first_date} → {last_date}), "
                        f"último valor: {values[-1]}"
                    )
                except Exception:
                    lines.append(f"- {marker}: {len(values)} medições, último: {values[-1]}")
            else:
                lines.append(f"- {marker}: {len(values)} medições")

    return "\n".join(lines[:100])  # limit to avoid context overflow
