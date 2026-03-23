"""
Memory Manager — append-only interface to PRONTUARIO.md and EXAMES_HISTORICO.md.

R6 enforcement: the file can only grow. Any operation that would reduce
file size raises an exception, making accidental deletion impossible.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional

from config.settings import (
    AGENT_PROMPTS_DIR,
    EXAMES_PATH,
    LOGS_DIR,
    PRONTUARIO_PATH,
    SKILLS_DIR,
)

# ── Analyzed labels tracking ───────────────────────────────────────────────────

_ANALYZED_FILE = LOGS_DIR.parent / "analyzed_labels.txt"


def get_analyzed_labels() -> set:
    """Returns set of PDF labels that have been analyzed."""
    if not _ANALYZED_FILE.exists():
        return set()
    return set(
        line.strip()
        for line in _ANALYZED_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


def mark_analyzed(labels: List[str]) -> None:
    """Appends labels to the analyzed tracking file (append-only)."""
    _ANALYZED_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing = get_analyzed_labels()
    new_labels = [l for l in labels if l not in existing]
    if new_labels:
        with _ANALYZED_FILE.open("a", encoding="utf-8") as f:
            f.write("\n".join(new_labels) + "\n")


# ── Core reads ────────────────────────────────────────────────────────────────


def read_prontuario() -> str:
    """Returns the full prontuário content. Always reads from disk (no cache)."""
    if not PRONTUARIO_PATH.exists():
        return (
            "[PRONTUARIO.md não encontrado] "
            "Execute ./scripts/setup.sh para criar seu prontuário."
        )
    return PRONTUARIO_PATH.read_text(encoding="utf-8")


def read_exames() -> str:
    """Returns the full exam history. Always reads from disk (no cache)."""
    if not EXAMES_PATH.exists():
        return (
            "[EXAMES_HISTORICO.md não encontrado] "
            "Execute ./scripts/setup.sh para criar o histórico de exames."
        )
    return EXAMES_PATH.read_text(encoding="utf-8")


# ── Append-only writes ────────────────────────────────────────────────────────


def append_to_prontuario(entry: str, timestamp: Optional[datetime] = None) -> None:
    """
    Appends a dated entry to PRONTUARIO.md.
    R6: raises ValueError if the file would shrink.
    """
    if timestamp is None:
        timestamp = datetime.now()

    date_str = timestamp.strftime("%d/%m/%Y %H:%M")
    block = f"\n\n<!-- Adicionado por HealthCore em {date_str} -->\n{entry.strip()}\n"

    _safe_append(PRONTUARIO_PATH, block)


def append_to_exames(entry: str, timestamp: Optional[datetime] = None) -> None:
    """
    Appends a dated entry to EXAMES_HISTORICO.md.
    R6: raises ValueError if the file would shrink.
    """
    if timestamp is None:
        timestamp = datetime.now()

    date_str = timestamp.strftime("%d/%m/%Y %H:%M")
    block = f"\n\n<!-- Adicionado por HealthCore em {date_str} -->\n{entry.strip()}\n"

    _safe_append(EXAMES_PATH, block)


def correct_entry(original_excerpt: str, correction_note: str) -> None:
    """
    Adds a correction note below the original text.
    R6: never deletes or overwrites — only adds.

    Args:
        original_excerpt: A unique string from the original entry to locate it.
        correction_note: The correction to append below it.
    """
    if not PRONTUARIO_PATH.exists():
        raise FileNotFoundError("PRONTUARIO.md não encontrado.")

    content = PRONTUARIO_PATH.read_text(encoding="utf-8")

    if original_excerpt not in content:
        raise ValueError(
            f"Trecho original não encontrado no prontuário: '{original_excerpt[:60]}...'"
        )

    date_str = datetime.now().strftime("%d/%m/%Y")
    correction_block = (
        f" [CORRIGIDO {date_str}: {correction_note.strip()}]"
    )

    new_content = content.replace(
        original_excerpt,
        original_excerpt + correction_block,
        1,  # replace only first occurrence
    )

    # R6: ensure file only grew
    if len(new_content) < len(content):
        raise ValueError("R6 violation: operation would reduce prontuário size.")

    PRONTUARIO_PATH.write_text(new_content, encoding="utf-8")


# ── Skill and prompt loaders ──────────────────────────────────────────────────


def load_skill(skill_name: str) -> str:
    """
    Loads a skill markdown file.
    Returns a warning string if the skill doesn't exist (never crashes).
    """
    skill_path = SKILLS_DIR / f"{skill_name}.md"
    if not skill_path.exists():
        return (
            f"[SKILL NÃO ENCONTRADA: {skill_name}] "
            f"Considere criar skills/{skill_name}.md com o contexto clínico da especialidade."
        )
    return skill_path.read_text(encoding="utf-8")


def load_agent_prompt(agent_name: str) -> str:
    """
    Loads an agent system prompt from agents/prompts/{agent_name}_system.md.
    Raises FileNotFoundError if missing — agent prompts are required.
    """
    prompt_path = AGENT_PROMPTS_DIR / f"{agent_name}_system.md"
    if not prompt_path.exists():
        raise FileNotFoundError(
            f"System prompt não encontrado: agents/prompts/{agent_name}_system.md"
        )
    return prompt_path.read_text(encoding="utf-8")


def load_skills(skill_names: List[str]) -> str:
    """Loads and concatenates multiple skills into a single context block."""
    blocks = []
    for name in skill_names:
        content = load_skill(name)
        blocks.append(f"## Skill: {name.upper()}\n\n{content}")
    return "\n\n---\n\n".join(blocks)


# ── Internal helpers ──────────────────────────────────────────────────────────


def _safe_append(path: Path, content: str) -> None:
    """
    Appends content to a file.
    R6: raises ValueError if the resulting file would be smaller than before.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {path}. Execute ./scripts/setup.sh."
        )

    original_size = path.stat().st_size

    with path.open("a", encoding="utf-8") as f:
        f.write(content)

    new_size = path.stat().st_size
    if new_size < original_size:
        raise ValueError(
            f"R6 violation: arquivo {path.name} encolheu após operação de append. "
            "Possível corrupção de arquivo."
        )
