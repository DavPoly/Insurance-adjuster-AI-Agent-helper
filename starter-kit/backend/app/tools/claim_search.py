from qdrant_client import QdrantClient

from app.constants.rag.claim_embedding_config import CLAIMS_COLLECTION_NAME
from app.constants.rag.claim_search_config import SIMILAR_CLAIMS_TOP_K
from app.rag.embedder import ClaimEmbedder


def search_past_claims(query: str, client: QdrantClient, embedder: ClaimEmbedder) -> list[dict]:
    """Semantic search over the historical claims collection.

    Args:
        query: Natural language description of the damage.
        client: Qdrant client to search against.
        embedder: Embeds the query text.

    Returns:
        Up to SIMILAR_CLAIMS_TOP_K matches, ordered by descending similarity, each
        shaped as {claim_id, similarity_score, damage_type, severity,
        affected_areas, resolution, repair_cost_actual}.
    """
    query_vector = embedder.embed_query(query)
    response = client.query_points(
        collection_name=CLAIMS_COLLECTION_NAME,
        query=query_vector,
        limit=SIMILAR_CLAIMS_TOP_K,
    )

    return [
        {
            "claim_id": point.payload["claim_id"],
            "similarity_score": point.score,
            "damage_type": point.payload["damage_type"],
            "severity": point.payload["severity"],
            "affected_areas": point.payload["affected_areas"],
            "resolution": point.payload["resolution"],
            "repair_cost_actual": point.payload["repair_cost_actual"],
        }
        for point in response.points
    ]
