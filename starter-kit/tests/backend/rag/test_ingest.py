from fake_claim_embedder import FakeClaimEmbedder
from fake_claim_records import (
    FAKE_CLAIM_ADJUSTER_NOTES_FIRE_DAMAGE,
    FAKE_CLAIM_ADJUSTER_NOTES_WATER_DAMAGE,
    FAKE_CLAIM_DESCRIPTION_FIRE_DAMAGE,
    FAKE_CLAIM_DESCRIPTION_WATER_DAMAGE,
    FAKE_CLAIM_ID_FIRE_DAMAGE,
    FAKE_CLAIM_ID_WATER_DAMAGE,
    FAKE_CLAIM_RECORD_FIRE_DAMAGE,
    FAKE_CLAIM_RECORD_WATER_DAMAGE,
)
from qdrant_client import QdrantClient

from app.constants.rag.claim_embedding_config import CLAIMS_COLLECTION_NAME, EMBEDDING_VECTOR_SIZE
from app.rag.ingest import build_point, claim_point_id, ingest_claims

FAKE_VECTOR_WATER_DAMAGE = [0.1] * EMBEDDING_VECTOR_SIZE
FAKE_VECTOR_FIRE_DAMAGE = [0.2] * EMBEDDING_VECTOR_SIZE

FAKE_EMBEDDING_TEXT_WATER_DAMAGE = (
    f"{FAKE_CLAIM_DESCRIPTION_WATER_DAMAGE}\n\n{FAKE_CLAIM_ADJUSTER_NOTES_WATER_DAMAGE}"
)
FAKE_EMBEDDING_TEXT_FIRE_DAMAGE = (
    f"{FAKE_CLAIM_DESCRIPTION_FIRE_DAMAGE}\n\n{FAKE_CLAIM_ADJUSTER_NOTES_FIRE_DAMAGE}"
)


def fake_embedder():
    return FakeClaimEmbedder(
        vector_for_text={
            FAKE_EMBEDDING_TEXT_WATER_DAMAGE: FAKE_VECTOR_WATER_DAMAGE,
            FAKE_EMBEDDING_TEXT_FIRE_DAMAGE: FAKE_VECTOR_FIRE_DAMAGE,
        }
    )


def test_claim_point_id_is_deterministic_for_the_same_claim_id():
    assert claim_point_id(FAKE_CLAIM_ID_WATER_DAMAGE) == claim_point_id(FAKE_CLAIM_ID_WATER_DAMAGE)


def test_claim_point_id_differs_for_different_claim_ids():
    assert claim_point_id(FAKE_CLAIM_ID_WATER_DAMAGE) != claim_point_id(FAKE_CLAIM_ID_FIRE_DAMAGE)


def test_build_point_carries_the_whole_record_as_payload():
    point = build_point(FAKE_CLAIM_RECORD_WATER_DAMAGE, FAKE_VECTOR_WATER_DAMAGE)

    assert point.id == claim_point_id(FAKE_CLAIM_ID_WATER_DAMAGE)
    assert point.vector == FAKE_VECTOR_WATER_DAMAGE
    assert point.payload == FAKE_CLAIM_RECORD_WATER_DAMAGE


def test_ingest_claims_populates_the_collection_with_one_point_per_record():
    client = QdrantClient(location=":memory:")

    ingest_claims(
        client, [FAKE_CLAIM_RECORD_WATER_DAMAGE, FAKE_CLAIM_RECORD_FIRE_DAMAGE], fake_embedder()
    )

    count = client.count(CLAIMS_COLLECTION_NAME).count
    assert count == 2


def test_ingest_claims_round_trips_the_full_payload():
    client = QdrantClient(location=":memory:")

    ingest_claims(client, [FAKE_CLAIM_RECORD_WATER_DAMAGE], fake_embedder())

    point = client.retrieve(
        CLAIMS_COLLECTION_NAME, ids=[claim_point_id(FAKE_CLAIM_ID_WATER_DAMAGE)]
    )[0]
    assert point.payload == FAKE_CLAIM_RECORD_WATER_DAMAGE


def test_ingest_claims_is_idempotent_across_repeated_runs():
    client = QdrantClient(location=":memory:")

    ingest_claims(client, [FAKE_CLAIM_RECORD_WATER_DAMAGE], fake_embedder())
    ingest_claims(client, [FAKE_CLAIM_RECORD_WATER_DAMAGE], fake_embedder())

    count = client.count(CLAIMS_COLLECTION_NAME).count
    assert count == 1
