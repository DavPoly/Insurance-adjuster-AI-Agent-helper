import os
from pathlib import Path

DEFAULT_KNOWLEDGE_BASE_DIR = "/app/data/knowledge-base"
KNOWLEDGE_BASE_DIR_ENV_VAR = "KNOWLEDGE_BASE_DIR"


def knowledge_base_dir() -> Path:
    """Directory holding historical claim JSON records, overridable via KNOWLEDGE_BASE_DIR."""
    return Path(os.environ.get(KNOWLEDGE_BASE_DIR_ENV_VAR, DEFAULT_KNOWLEDGE_BASE_DIR))
