from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel
from qdrant_client import QdrantClient

from app.config import get_settings
from app.constants.tools.tool_lookup_table_paths import cost_table_path, coverage_table_path
from app.llm.triage_chat_model import build_triage_chat_model
from app.rag.embedder import ClaimEmbedder
from app.tools.loader import load_json_table


@lru_cache
def get_qdrant_client() -> QdrantClient:
    """Process-wide singleton: avoids reopening a client connection per request."""
    return QdrantClient(url=get_settings().qdrant_url)


@lru_cache
def get_claim_embedder() -> ClaimEmbedder:
    """Process-wide singleton: loading the local embedding model is expensive."""
    return ClaimEmbedder()


@lru_cache
def get_cost_table() -> dict:
    return load_json_table(cost_table_path())


@lru_cache
def get_coverage_table() -> dict:
    return load_json_table(coverage_table_path())


@lru_cache
def get_triage_chat_model() -> BaseChatModel:
    """Process-wide singleton: avoids rebuilding the chat client per request."""
    return build_triage_chat_model(get_settings())
