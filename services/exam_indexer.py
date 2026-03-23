"""
Exam Indexer — parses EXAMES_HISTORICO.md into structured data.
Powers the exam history timeline page.
"""

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional

from services.memory_manager import read_exames


@dataclass
class ExamEntry:
    marker: str
    date: Optional[date]
    value: str
    reference: str
    status: str      # ✅ / ↑ / ↓ / ⚠️
    context: str
    category: str = ""


def parse_exam_history() -> Dict[str, List[ExamEntry]]:
    """
    Parses EXAMES_HISTORICO.md into a dict mapping
    marker name -> list of ExamEntry (chronological).
    """
    content = read_exames()
    results: Dict[str, List[ExamEntry]] = {}
    current_category = "Geral"

    for line in content.splitlines():
        # Track section headers (## Metabolismo e Glicemia)
        if line.startswith("## "):
            current_category = line.lstrip("#").strip()
            continue

        # Skip non-table lines
        if not line.startswith("|"):
            continue

        # Skip header rows
        if re.search(r"\|\s*[-:]+\s*\|", line):
            continue

        # Skip column header rows (contain "Marcador" or "Exame")
        if re.search(r"\|\s*(Marcador|Exame|Data)\s*\|", line, re.IGNORECASE):
            continue

        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) < 4:
            continue

        marker = parts[0]
        date_str = parts[1] if len(parts) > 1 else ""
        value = parts[2] if len(parts) > 2 else ""
        reference = parts[3] if len(parts) > 3 else ""
        status = parts[4] if len(parts) > 4 else ""
        context = parts[5] if len(parts) > 5 else ""

        # Skip empty rows
        if not marker or not value or value in ("preencher", "", "{{VALOR}}"):
            continue

        parsed_date = _parse_date(date_str)

        entry = ExamEntry(
            marker=marker,
            date=parsed_date,
            value=value,
            reference=reference,
            status=status,
            context=context,
            category=current_category,
        )

        if marker not in results:
            results[marker] = []
        results[marker].append(entry)

    # Sort each marker's entries chronologically
    for marker in results:
        results[marker].sort(key=lambda e: e.date or date.min)

    return results


def get_latest_values() -> Dict[str, ExamEntry]:
    """Returns the most recent entry for each marker."""
    history = parse_exam_history()
    return {marker: entries[-1] for marker, entries in history.items() if entries}


def get_trend(marker: str) -> list[ExamEntry]:
    """Returns all entries for a specific marker, sorted by date."""
    history = parse_exam_history()
    return history.get(marker, [])


def list_markers() -> list[str]:
    """Returns all marker names found in the exam history."""
    return sorted(parse_exam_history().keys())


def get_categories() -> Dict[str, List[str]]:
    """Returns markers grouped by category."""
    history = parse_exam_history()
    categories: Dict[str, List[str]] = {}
    for marker, entries in history.items():
        if entries:
            cat = entries[0].category
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(marker)
    return categories


def _parse_date(date_str: str) -> Optional[date]:
    """Tries multiple date formats common in Brazilian lab reports."""
    date_str = date_str.strip()
    if not date_str or date_str in ("{{DATA}}", "—", "-"):
        return None

    formats = [
        "%Y-%m-%d",   # 2024-11-15
        "%d/%m/%Y",   # 15/11/2024
        "%m/%Y",      # 11/2024
        "%Y-%m",      # 2024-11
        "%b/%Y",      # Nov/2024
        "%Y",         # 2024
    ]
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            return parsed.date()
        except ValueError:
            continue
    return None
