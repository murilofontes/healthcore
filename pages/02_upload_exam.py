"""
Upload de Exame — painel de laudos salvos + upload de novos.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import io
import json
import zipfile
from datetime import date, datetime
from typing import Dict, List, Optional

import streamlit as st

from agents.debate import DebateEngine
from config.guardrails import URGENCY_LEVELS
from config.settings import LAUDOS_DIR, LOGS_DIR
from services.memory_manager import append_to_exames
from services.pdf_parser import extract_lab_values, extract_text_from_pdf, store_laudo

st.set_page_config(page_title="Exames — HealthCore", page_icon="📄", layout="wide")

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
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _analyzed_labels() -> set:
    """Returns set of PDF labels that already have a debate log entry."""
    labels = set()
    if not LOGS_DIR.exists():
        return labels
    for log_file in sorted(LOGS_DIR.glob("*.jsonl")):
        try:
            for line in log_file.read_text(encoding="utf-8").splitlines():
                entry = json.loads(line)
                inp = entry.get("input", "").lower()
                # Match "novo laudo: label" or "painel completo"
                if "novo laudo:" in inp or "painel" in inp:
                    # extract label after "novo laudo: "
                    if "novo laudo:" in inp:
                        label = inp.split("novo laudo:")[-1].split("(")[0].strip()
                        labels.add(label)
                    if "painel" in inp:
                        labels.add("__zip__")
        except Exception:
            continue
    return labels


def _list_laudos() -> List[Dict]:
    """Returns sorted list of PDFs in laudos/ with metadata."""
    if not LAUDOS_DIR.exists():
        return []
    laudos = []
    for f in sorted(LAUDOS_DIR.glob("*.pdf"), reverse=True):
        stat = f.stat()
        laudos.append({
            "path": f,
            "name": f.name,
            "label": f.stem,
            "size_kb": round(stat.st_size / 1024, 1),
            "date": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d"),
        })
    return laudos


def _show_debate_result(result):
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


def _save_lab_values_to_history(lab_values: list, label: str, exam_date: date):
    lines = [f"\n\n## Exame: {label} — {exam_date}\n"]
    lines += ["| Marcador | Valor | Unidade | Referência |", "|----------|-------|---------|-----------|"]
    for v in lab_values:
        lines.append(f"| {v['marker']} | {v['value']} | {v.get('unit','')} | {v.get('reference','')} |")
    try:
        append_to_exames("\n".join(lines))
        st.success(f"✓ {len(lab_values)} valores salvos no EXAMES_HISTORICO.md!")
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")


def _run_analysis(pdf_path: Path, label: str, context: str = "") -> None:
    """Extracts and analyzes a single PDF from laudos/."""
    import pandas as pd

    with st.spinner(f"Extraindo texto de `{pdf_path.name}`..."):
        extracted = extract_text_from_pdf(pdf_path)
        lab_values = extract_lab_values(pdf_path)

    if lab_values:
        with st.expander(f"📋 {len(lab_values)} valores detectados", expanded=False):
            st.dataframe(
                pd.DataFrame(lab_values)[["marker", "value", "unit", "reference"]],
                use_container_width=True,
            )

    user_input = f"Novo laudo: {label} ({pdf_path.stat().st_mtime})"
    if context:
        user_input += f"\n\nContexto: {context}"

    with st.spinner("Debatendo hipóteses com os agentes..."):
        try:
            result = st.session_state.engine.run(user_input, pdf_text=extracted)
            st.session_state.upload_result = result
        except Exception as e:
            st.error(f"Erro na análise: {e}")
            return

    _show_debate_result(result)

    if lab_values:
        if st.button("💾 Salvar valores no histórico", key=f"save_{label}"):
            _save_lab_values_to_history(lab_values, label, date.today())


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Painel de laudos salvos
# ══════════════════════════════════════════════════════════════════════════════

laudos = _list_laudos()
analyzed = _analyzed_labels()

st.title("📄 Exames")

if laudos:
    analyzed_count = sum(1 for l in laudos if l["label"] in analyzed)
    pending_count = len(laudos) - analyzed_count

    col1, col2, col3 = st.columns(3)
    col1.metric("Laudos salvos", len(laudos))
    col2.metric("Analisados", analyzed_count)
    col3.metric("Pendentes", pending_count, delta=f"-{pending_count}" if pending_count else None,
                delta_color="inverse")

    st.divider()

    # Pending analysis
    pending = [l for l in laudos if l["label"] not in analyzed]
    if pending:
        st.subheader(f"⏳ Pendentes de análise ({len(pending)})")
        st.caption("Laudos salvos que ainda não foram analisados pelos agentes.")

        # Select all / analyze batch
        col_a, col_b = st.columns([3, 1])
        with col_a:
            selected = st.multiselect(
                "Selecione para analisar",
                options=[l["name"] for l in pending],
                default=[l["name"] for l in pending],
                label_visibility="collapsed",
            )
        with col_b:
            batch_size = st.selectbox("Lote", [3, 5, 10], index=1, label_visibility="collapsed")

        if st.button(f"▶️ Analisar selecionados ({len(selected)})", type="primary", disabled=not selected):
            selected_paths = [l["path"] for l in pending if l["name"] in selected]
            batches = [selected_paths[i:i+batch_size] for i in range(0, len(selected_paths), batch_size)]
            st.info(f"Processando {len(selected_paths)} laudos em {len(batches)} lote(s).")

            for b_idx, batch in enumerate(batches):
                texts = []
                for pdf_path in batch:
                    with st.spinner(f"Extraindo: {pdf_path.name}"):
                        texts.append(f"## {pdf_path.name}\n\n{extract_text_from_pdf(pdf_path)}")

                user_input = f"Painel lote {b_idx+1}/{len(batches)}: {len(batch)} laudos"
                with st.spinner(f"Analisando lote {b_idx+1}/{len(batches)}..."):
                    try:
                        result = st.session_state.engine.run(
                            user_input,
                            pdf_text="\n\n---\n\n".join(texts)[:8000],
                        )
                        st.session_state.upload_result = result
                    except Exception as e:
                        st.error(f"Erro no lote {b_idx+1}: {e}")
                        break

                with st.expander(f"📊 Resultado — Lote {b_idx+1}/{len(batches)}", expanded=True):
                    _show_debate_result(result)

            st.rerun()

        # Individual pending items
        with st.expander("Ver lista completa de pendentes", expanded=False):
            for l in pending:
                c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                c1.write(f"📄 `{l['name']}`")
                c2.write(l["date"])
                c3.write(f"{l['size_kb']} KB")
                if c4.button("Analisar", key=f"btn_{l['label']}"):
                    st.subheader(f"Análise: {l['name']}")
                    _run_analysis(l["path"], l["label"])

        st.divider()

    # Already analyzed
    done = [l for l in laudos if l["label"] in analyzed]
    if done:
        with st.expander(f"✅ Já analisados ({len(done)})", expanded=False):
            for l in done:
                c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                c1.write(f"✅ `{l['name']}`")
                c2.write(l["date"])
                c3.write(f"{l['size_kb']} KB")
                if c4.button("Re-analisar", key=f"re_{l['label']}"):
                    st.subheader(f"Re-análise: {l['name']}")
                    _run_analysis(l["path"], l["label"])

else:
    st.info("Nenhum laudo salvo ainda. Faça o upload abaixo.")

st.divider()


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Upload de novos laudos
# ══════════════════════════════════════════════════════════════════════════════

st.subheader("➕ Adicionar laudos")

tab_single, tab_zip, tab_history = st.tabs([
    "📄 PDF individual",
    "🗜️ ZIP com múltiplos laudos",
    "📊 Histórico em planilha (CSV/Excel)",
])

# ── TAB 1: Single PDF ─────────────────────────────────────────────────────────

with tab_single:
    with st.form("upload_single"):
        uploaded_file = st.file_uploader("PDF do laudo", type=["pdf"])
        col1, col2 = st.columns(2)
        with col1:
            exam_label = st.text_input("Descrição", placeholder="ex: hemograma-fleury")
        with col2:
            exam_date = st.date_input("Data do exame", value=date.today(), max_value=date.today())
        context_note = st.text_area("Contexto (opcional)", height=68,
                                    placeholder="ex: em jejum de 12h...")
        submitted_single = st.form_submit_button("📤 Salvar e Analisar", type="primary")

    if submitted_single:
        if not uploaded_file:
            st.warning("Selecione um PDF.")
        elif not exam_label:
            st.warning("Adicione uma descrição.")
        else:
            saved_path = store_laudo(uploaded_file.read(), exam_label, exam_date)
            st.success(f"✓ Salvo: `{saved_path.name}`")
            _run_analysis(saved_path, exam_label, context_note)
            st.rerun()

# ── TAB 2: ZIP ────────────────────────────────────────────────────────────────

with tab_zip:
    st.caption("Compacte todos os PDFs em um ZIP. Cada um será salvo em `laudos/`. Analise depois pelo painel acima.")

    with st.form("upload_zip"):
        uploaded_zip = st.file_uploader("Arquivo ZIP", type=["zip"])
        zip_date = st.date_input("Data padrão", value=date.today(), max_value=date.today())
        zip_only = st.checkbox("Apenas salvar (analisar depois pelo painel)", value=True)
        submitted_zip = st.form_submit_button("📦 Processar ZIP", type="primary")

    if submitted_zip:
        if not uploaded_zip:
            st.warning("Selecione um ZIP.")
        else:
            try:
                zf = zipfile.ZipFile(io.BytesIO(uploaded_zip.read()))
            except zipfile.BadZipFile:
                st.error("ZIP inválido.")
                st.stop()

            pdf_entries = [n for n in zf.namelist()
                           if n.lower().endswith(".pdf") and not n.startswith("__MACOSX")]
            if not pdf_entries:
                st.warning("Nenhum PDF no ZIP.")
                st.stop()

            progress = st.progress(0, text="Salvando PDFs...")
            for i, pdf_name in enumerate(pdf_entries):
                progress.progress((i+1)/len(pdf_entries),
                                   text=f"Salvando {i+1}/{len(pdf_entries)}: {Path(pdf_name).name}")
                label = Path(pdf_name).stem.replace(" ", "_").lower()[:50]
                store_laudo(zf.read(pdf_name), label, zip_date)

            progress.empty()
            zf.close()
            st.success(f"✓ {len(pdf_entries)} PDFs salvos em `laudos/`. Use o painel acima para analisar.")
            st.rerun()

# ── TAB 3: CSV/Excel history ──────────────────────────────────────────────────

with tab_history:
    st.markdown("Importe uma planilha com histórico completo de exames.")

    template_csv = (
        "marcador,data,valor,referencia,unidade,contexto\n"
        "Glicose,2024-11-15,95,70-99 mg/dL,mg/dL,em jejum\n"
        "TSH,2024-11-15,2.1,0.4-4.0 mUI/L,mUI/L,\n"
        "Vitamina D,2024-03-20,28,30-60 ng/mL,ng/mL,\n"
    )
    st.download_button("⬇️ Baixar modelo CSV", data=template_csv.encode("utf-8"),
                       file_name="modelo_historico.csv", mime="text/csv")

    with st.form("upload_history"):
        hist_file = st.file_uploader("CSV ou Excel", type=["csv", "xlsx", "xls"])
        hist_context = st.text_area("Contexto (opcional)", height=68,
                                    placeholder="ex: histórico completo 2019-2025...")
        analyze_hist = st.checkbox("Analisar com os agentes após importar", value=False)
        submitted_hist = st.form_submit_button("📥 Importar", type="primary")

    if submitted_hist:
        if not hist_file:
            st.warning("Selecione um arquivo.")
        else:
            import pandas as pd

            try:
                df = pd.read_csv(hist_file) if hist_file.name.endswith(".csv") else pd.read_excel(hist_file)
            except Exception as e:
                st.error(f"Erro ao ler: {e}")
                st.stop()

            df.columns = [c.lower().strip() for c in df.columns]
            col_map = _detect_columns(df.columns.tolist())

            if not col_map.get("marcador") or not col_map.get("valor"):
                st.error("Não foi possível detectar colunas 'marcador' e 'valor'. Verifique o modelo.")
                st.dataframe(df.head(), use_container_width=True)
                st.stop()

            st.success(f"✓ {len(df)} registros, {df[col_map['marcador']].nunique()} marcadores")
            st.dataframe(df.head(8), use_container_width=True)

            md_lines = _dataframe_to_history_md(df, col_map)
            try:
                append_to_exames("\n".join(md_lines))
                st.success("✓ Salvo em EXAMES_HISTORICO.md! Veja os gráficos na página Histórico.")
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")
                st.stop()

            if analyze_hist:
                summary = _build_history_summary(df, col_map)
                user_input = f"Histórico importado: {len(df)} registros"
                if hist_context:
                    user_input += f"\n\nContexto: {hist_context}"
                with st.spinner("Analisando com os agentes..."):
                    try:
                        result = st.session_state.engine.run(user_input, pdf_text=summary)
                        st.session_state.upload_result = result
                    except Exception as e:
                        st.error(f"Erro na análise: {e}")
                        st.stop()
                _show_debate_result(result)


# ── Column helpers ────────────────────────────────────────────────────────────

def _detect_columns(columns: list) -> dict:
    mapping = {}
    aliases = {
        "marcador": ["marcador", "exame", "marker", "teste", "analito", "nome"],
        "data":     ["data", "date", "data_coleta", "data coleta", "data_exame"],
        "valor":    ["valor", "value", "resultado", "result"],
        "referencia": ["referencia", "referência", "ref", "reference", "vr", "valor_ref"],
        "unidade":  ["unidade", "unit", "unid", "units"],
        "contexto": ["contexto", "context", "obs", "observação", "observacao", "nota"],
    }
    for field, candidates in aliases.items():
        for col in columns:
            if col in candidates or any(c in col for c in candidates):
                mapping[field] = col
                break
    return mapping


def _dataframe_to_history_md(df, col_map: dict) -> list:
    import pandas as pd
    marker_col = col_map["marcador"]
    date_col   = col_map.get("data", "")
    value_col  = col_map["valor"]
    ref_col    = col_map.get("referencia", "")
    unit_col   = col_map.get("unidade", "")
    ctx_col    = col_map.get("contexto", "")

    lines = ["\n\n## Histórico Importado\n"]
    for marker in sorted(df[marker_col].dropna().unique()):
        mdf = df[df[marker_col] == marker].copy()
        if date_col and date_col in df.columns:
            try: mdf = mdf.sort_values(date_col)
            except Exception: pass
        lines += [f"\n### {marker}\n", "| Data | Valor | Referência | Contexto |",
                  "|------|-------|-----------|---------|"]
        for _, row in mdf.iterrows():
            d   = str(row.get(date_col, "—")) if date_col else "—"
            v   = str(row.get(value_col, ""))
            if unit_col and unit_col in df.columns and str(row.get(unit_col, "")):
                v += f" {row.get(unit_col, '')}"
            r   = str(row.get(ref_col, "")) if ref_col else ""
            ctx = str(row.get(ctx_col, "")) if ctx_col else ""
            lines.append(f"| {d} | {v} | {r} | {ctx} |")
    return lines


def _build_history_summary(df, col_map: dict) -> str:
    import pandas as pd
    marker_col = col_map["marcador"]
    value_col  = col_map["valor"]
    date_col   = col_map.get("data", "")
    lines = [f"Histórico: {len(df)} registros, {df[marker_col].nunique()} marcadores.\n"]
    for marker in sorted(df[marker_col].dropna().unique()):
        mdf = df[df[marker_col] == marker]
        vals = mdf[value_col].dropna().tolist()
        if vals:
            if date_col and date_col in df.columns:
                try:
                    mdf = mdf.sort_values(date_col)
                    lines.append(f"- {marker}: {len(vals)} medições "
                                 f"({mdf[date_col].iloc[0]} → {mdf[date_col].iloc[-1]}), "
                                 f"último: {vals[-1]}")
                except Exception:
                    lines.append(f"- {marker}: {len(vals)} medições, último: {vals[-1]}")
            else:
                lines.append(f"- {marker}: {len(vals)} medições")
    return "\n".join(lines[:100])
