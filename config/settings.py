"""
Central configuration for HealthCore.
All paths and model settings live here — never hardcode paths elsewhere.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Project root
BASE_DIR = Path(__file__).parent.parent

# Patient data (all gitignored)
PRONTUARIO_PATH = BASE_DIR / "PRONTUARIO.md"
EXAMES_PATH = BASE_DIR / "EXAMES_HISTORICO.md"
LAUDOS_DIR = BASE_DIR / "laudos"
LOGS_DIR = BASE_DIR / "logs" / "debates"

# Public assets
SKILLS_DIR = BASE_DIR / "skills"
AGENT_PROMPTS_DIR = BASE_DIR / "agents" / "prompts"
TEMPLATES_DIR = BASE_DIR / "templates"

# Anthropic
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = os.getenv("HEALTHCORE_MODEL", "claude-sonnet-4-6")
MAX_TOKENS = 8192

# Google Drive (optional)
GDRIVE_ENABLED = os.getenv("GDRIVE_ENABLED", "false").lower() == "true"

# Consent flag
CONSENT_FLAG = Path.home() / ".healthcore_consent"
