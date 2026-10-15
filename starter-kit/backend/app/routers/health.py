import logging

from fastapi import APIRouter, Depends, status
from qdrant_client import QdrantClient

from app.config import Settings, get_settings
from app.constants.api.health_check_status_labels import (
    HEALTHY_STATUS,
    LLM_CONFIGURED,
    LLM_NOT_CONFIGURED,
    VECTOR_DB_CONNECTED,
    VECTOR_DB_DISCONNECTED,
)
from app.dependencies import get_qdrant_client

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/health",
    summary="Health check",
    description=(
        "Reports service readiness: whether the Qdrant vector database is reachable "
        "and whether LLM credentials (OPENROUTER_API_KEY, LLM_MODEL) are configured."
    ),
    responses={
        status.HTTP_200_OK: {"description": "Service is healthy."},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Health check failed unexpectedly."},
    },
)
def health_check(
    settings: Settings = Depends(get_settings),
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
) -> dict:
    try:
        qdrant_client.get_collections()
        vector_db_status = VECTOR_DB_CONNECTED
    except Exception:
        logger.warning("Qdrant health check failed", exc_info=True)
        vector_db_status = VECTOR_DB_DISCONNECTED

    llm_status = (
        LLM_CONFIGURED if settings.openrouter_api_key and settings.llm_model else LLM_NOT_CONFIGURED
    )

    return {
        "status": HEALTHY_STATUS,
        "services": {"vector_db": vector_db_status, "llm": llm_status},
    }
