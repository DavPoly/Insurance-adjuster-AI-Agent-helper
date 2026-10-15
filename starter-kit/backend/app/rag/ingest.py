import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.config import get_settings
from app.constants.rag.claim_embedding_config import CLAIMS_COLLECTION_NAME, EMBEDDING_VECTOR_SIZE
from app.constants.rag.knowledge_base_paths import knowledge_base_dir
from app.rag.claim_records import build_embedding_text, load_claim_records
from app.rag.embedder import ClaimEmbedder
from app.rag.vector_db_readiness import wait_for_vector_db_ready


def claim_point_id(claim_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, claim_id))


def build_point(record: dict, vector: list[float]) -> PointStruct:
    """Build the Qdrant point for a claim record, storing the full record as payload."""
    return PointStruct(id=claim_point_id(record["claim_id"]), vector=vector, payload=record)


def ingest_claims(client: QdrantClient, records: list[dict], embedder: ClaimEmbedder) -> None:
    """Recreate the claims collection and upsert one point per claim record."""
    if client.collection_exists(CLAIMS_COLLECTION_NAME):
        client.delete_collection(CLAIMS_COLLECTION_NAME)
    client.create_collection(
        collection_name=CLAIMS_COLLECTION_NAME,
        vectors_config=VectorParams(size=EMBEDDING_VECTOR_SIZE, distance=Distance.COSINE),
    )

    texts = [build_embedding_text(record) for record in records]
    vectors = embedder.embed_passages(texts)
    points = [build_point(record, vector) for record, vector in zip(records, vectors)]

    client.upsert(collection_name=CLAIMS_COLLECTION_NAME, points=points)


def main() -> None:
    client = QdrantClient(url=get_settings().qdrant_url)
    if not wait_for_vector_db_ready(client):
        raise RuntimeError("Vector DB did not become ready; aborting ingestion.")
    records = load_claim_records(knowledge_base_dir())
    ingest_claims(client, records, ClaimEmbedder())


if __name__ == "__main__":
    main()
