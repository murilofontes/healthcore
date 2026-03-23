"""
PDF Parser — extracts text and lab values from medical exam PDFs.

Uses pdfplumber as primary (better table handling) with pypdf as fallback.
Handles common Brazilian lab formats: Fleury, DASA, Hermes Pardini, Lavoisier.
Raw text is passed to agents for semantic interpretation — we don't try to
be a perfect parser.
"""

import re
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

from config.settings import LAUDOS_DIR


def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    Extracts all text from a PDF, preserving table structure where possible.
    Falls back to pypdf if pdfplumber fails.
    """
    try:
        return _extract_pdfplumber(pdf_path)
    except Exception:
        pass

    try:
        return _extract_pypdf(pdf_path)
    except Exception as e:
        return f"[ERRO NA EXTRAÇÃO DO PDF: {e}]\nArquivo: {pdf_path.name}"


def extract_lab_values(pdf_path: Path) -> List[Dict]:
    """
    Attempts to parse structured lab results from common Brazilian lab formats.
    Returns list of {marker, value, reference, unit, date, lab} dicts.
    Falls back gracefully — caller always receives a list (may be empty).
    """
    raw_text = extract_text_from_pdf(pdf_path)
    values = []

    # Try to detect which lab issued the report
    lab_name = _detect_lab(raw_text)

    # Extract date from report
    report_date = _extract_report_date(raw_text)

    # Pattern: "Marcador ..... valor referência"
    # Handles variations like:
    #   Glicose           95 mg/dL    70-99 mg/dL
    #   HOMA-IR           3,2         < 2,5
    patterns = [
        # "Marker   value unit   ref"
        r"([\w\s\-\/\(\)]+?)\s{2,}([\d,\.]+)\s*([\w\/\%µ]+)?\s+([\d,\.<>\-\s]+[\w\/\%µ]*)",
        # "Marker: value unit"
        r"([\w\s\-\/\(\)]+?):\s*([\d,\.]+)\s*([\w\/\%µ]+)",
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, raw_text, re.MULTILINE):
            groups = match.groups()
            marker = groups[0].strip()
            value = groups[1].strip().replace(",", ".")
            unit = groups[2].strip() if len(groups) > 2 and groups[2] else ""
            reference = groups[3].strip() if len(groups) > 3 and groups[3] else ""

            # Filter out noise (very short names, non-numeric values)
            if len(marker) < 3 or not re.search(r"\d", value):
                continue

            # Skip obvious non-markers
            if any(skip in marker.lower() for skip in ["página", "page", "data", "hora"]):
                continue

            values.append({
                "marker": marker,
                "value": value,
                "unit": unit,
                "reference": reference,
                "date": report_date,
                "lab": lab_name,
                "source_file": pdf_path.name,
            })

    return values


def store_laudo(
    pdf_bytes: bytes,
    label: str,
    report_date: Optional[date] = None,
) -> Path:
    """
    Saves a PDF to laudos/ with standardized naming.
    Returns the saved file path.

    Args:
        pdf_bytes: Raw PDF bytes from file upload.
        label: Short description (e.g., "hemograma-fleury").
        report_date: Date of the exam. Uses today if not provided.
    """
    LAUDOS_DIR.mkdir(exist_ok=True)

    if report_date is None:
        report_date = date.today()

    # Sanitize label for filename
    safe_label = re.sub(r"[^\w\-]", "_", label.lower())
    filename = f"{report_date.strftime('%Y-%m-%d')}_{safe_label}.pdf"
    output_path = LAUDOS_DIR / filename

    # Avoid overwriting existing files
    counter = 1
    while output_path.exists():
        output_path = LAUDOS_DIR / f"{report_date.strftime('%Y-%m-%d')}_{safe_label}_{counter}.pdf"
        counter += 1

    output_path.write_bytes(pdf_bytes)
    return output_path


def list_laudos() -> List[Dict]:
    """
    Returns a list of all stored PDFs with metadata.
    """
    if not LAUDOS_DIR.exists():
        return []

    laudos = []
    for pdf_file in sorted(LAUDOS_DIR.glob("*.pdf"), reverse=True):
        stat = pdf_file.stat()
        laudos.append({
            "filename": pdf_file.name,
            "path": pdf_file,
            "size_kb": round(stat.st_size / 1024, 1),
            "modified": date.fromtimestamp(stat.st_mtime),
        })
    return laudos


# ── Internal helpers ──────────────────────────────────────────────────────────


def _extract_pdfplumber(pdf_path: Path) -> str:
    """Extracts text using pdfplumber, preserving table structure."""
    import pdfplumber

    pages_text = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            # Try to extract tables first
            tables = page.extract_tables()
            if tables:
                table_texts = []
                for table in tables:
                    for row in table:
                        if row:
                            cleaned = [cell or "" for cell in row]
                            table_texts.append(" | ".join(cleaned))
                pages_text.append("\n".join(table_texts))
            else:
                # Fall back to plain text extraction
                text = page.extract_text()
                if text:
                    pages_text.append(text)

    return "\n\n--- PÁGINA ---\n\n".join(pages_text)


def _extract_pypdf(pdf_path: Path) -> str:
    """Fallback: extracts text using pypdf."""
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    pages_text = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages_text.append(text)

    return "\n\n--- PÁGINA ---\n\n".join(pages_text)


def _detect_lab(text: str) -> str:
    """Detects the issuing laboratory from report text."""
    text_lower = text.lower()
    lab_signatures = {
        "Fleury": ["fleury", "grupo fleury"],
        "DASA": ["dasa", "db diagnósticos", "cedilab", "pasteur"],
        "Hermes Pardini": ["hermes pardini", "pardini"],
        "Lavoisier": ["lavoisier"],
        "Einstein": ["einstein", "albert einstein"],
        "Sabin": ["sabin"],
    }
    for lab_name, signatures in lab_signatures.items():
        if any(sig in text_lower for sig in signatures):
            return lab_name
    return "Laboratório desconhecido"


def _extract_report_date(text: str) -> Optional[date]:
    """Extracts the exam date from report text."""
    date_patterns = [
        r"Data.*?(\d{2}/\d{2}/\d{4})",
        r"Coleta.*?(\d{2}/\d{2}/\d{4})",
        r"(\d{2}/\d{2}/\d{4})",
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            try:
                from datetime import datetime
                return datetime.strptime(match.group(1), "%d/%m/%Y").date()
            except ValueError:
                continue
    return None
