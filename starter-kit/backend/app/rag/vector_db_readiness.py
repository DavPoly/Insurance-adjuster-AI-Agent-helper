import logging
import time

from qdrant_client import QdrantClient

from app.constants.rag.vector_db_startup_retry_config import (
    MAX_STARTUP_RETRY_ATTEMPTS,
    STARTUP_RETRY_DELAY_SECONDS,
)

logger = logging.getLogger(__name__)


def wait_for_vector_db_ready(
    client: QdrantClient,
    max_attempts: int = MAX_STARTUP_RETRY_ATTEMPTS,
    delay_seconds: float = STARTUP_RETRY_DELAY_SECONDS,
) -> bool:
    for attempt in range(1, max_attempts + 1):
        try:
            client.get_collections()
            return True
        except Exception:
            logger.warning(
                "Vector DB not ready yet (attempt %d/%d).", attempt, max_attempts, exc_info=True
            )
            if attempt < max_attempts:
                time.sleep(delay_seconds)
    return False
