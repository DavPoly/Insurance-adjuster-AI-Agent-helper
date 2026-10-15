from fake_claim_search_data import (
    FAKE_CLAIM_ID_BEST_MATCH,
    FAKE_CLAIM_ID_PARTIAL_MATCH,
    FAKE_CLAIM_ID_WEAK_MATCH,
    FAKE_FILLER_RECORDS,
    FAKE_QUERY_TEXT,
    FAKE_RECORD_BEST_MATCH,
    FAKE_RECORD_PARTIAL_MATCH,
    FAKE_RECORD_WEAK_MATCH,
    build_fake_claim_search_embedder,
)
from qdrant_client import QdrantClient

from app.constants.rag.claim_search_config import SIMILAR_CLAIMS_TOP_K
from app.rag.ingest import ingest_claims
from app.tools.claim_search import search_past_claims


def test_search_past_claims_ranks_results_by_descending_similarity():
    client = QdrantClient(location=":memory:")
    records = [FAKE_RECORD_BEST_MATCH, FAKE_RECORD_PARTIAL_MATCH, FAKE_RECORD_WEAK_MATCH]
    ingest_claims(client, records, build_fake_claim_search_embedder(records))

    results = search_past_claims(FAKE_QUERY_TEXT, client, build_fake_claim_search_embedder(records))

    assert [result["claim_id"] for result in results] == [
        FAKE_CLAIM_ID_BEST_MATCH,
        FAKE_CLAIM_ID_PARTIAL_MATCH,
        FAKE_CLAIM_ID_WEAK_MATCH,
    ]


def test_search_past_claims_returns_raw_record_fields():
    client = QdrantClient(location=":memory:")
    records = [FAKE_RECORD_BEST_MATCH]
    ingest_claims(client, records, build_fake_claim_search_embedder(records))

    results = search_past_claims(FAKE_QUERY_TEXT, client, build_fake_claim_search_embedder(records))

    result = dict(results[0])
    similarity_score = result.pop("similarity_score")
    assert result == {
        "claim_id": FAKE_RECORD_BEST_MATCH["claim_id"],
        "damage_type": FAKE_RECORD_BEST_MATCH["damage_type"],
        "severity": FAKE_RECORD_BEST_MATCH["severity"],
        "affected_areas": FAKE_RECORD_BEST_MATCH["affected_areas"],
        "resolution": FAKE_RECORD_BEST_MATCH["resolution"],
        "repair_cost_actual": FAKE_RECORD_BEST_MATCH["repair_cost_actual"],
    }
    assert 0 <= similarity_score <= 1.0


def test_search_past_claims_caps_results_at_similar_claims_top_k():
    client = QdrantClient(location=":memory:")
    records = [
        FAKE_RECORD_BEST_MATCH,
        FAKE_RECORD_PARTIAL_MATCH,
        FAKE_RECORD_WEAK_MATCH,
        *FAKE_FILLER_RECORDS,
    ]
    assert len(records) > SIMILAR_CLAIMS_TOP_K
    ingest_claims(client, records, build_fake_claim_search_embedder(records))

    results = search_past_claims(FAKE_QUERY_TEXT, client, build_fake_claim_search_embedder(records))

    assert len(results) == SIMILAR_CLAIMS_TOP_K
