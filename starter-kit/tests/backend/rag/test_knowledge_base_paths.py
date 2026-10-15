from pathlib import Path

from app.constants.rag.knowledge_base_paths import (
    DEFAULT_KNOWLEDGE_BASE_DIR,
    KNOWLEDGE_BASE_DIR_ENV_VAR,
    knowledge_base_dir,
)


def test_knowledge_base_dir_resolves_to_container_default_when_env_var_unset(monkeypatch):
    monkeypatch.delenv(KNOWLEDGE_BASE_DIR_ENV_VAR, raising=False)

    assert knowledge_base_dir() == Path(DEFAULT_KNOWLEDGE_BASE_DIR)


def test_knowledge_base_dir_resolves_to_env_var_override(monkeypatch, tmp_path):
    monkeypatch.setenv(KNOWLEDGE_BASE_DIR_ENV_VAR, str(tmp_path))

    assert knowledge_base_dir() == tmp_path
