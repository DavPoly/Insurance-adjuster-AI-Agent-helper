"""Fake claim records and a fake embedder for testing search_past_claims without
the real embedding model or real Qdrant data.

Fake vectors use disjoint "spike" directions per record so cosine similarity
against a fixed fake query vector produces a deterministic, non-trivial ranking.
"""

from app.constants.rag.claim_embedding_config import EMBEDDING_VECTOR_SIZE
from app.rag.claim_records import build_embedding_text


def _spike_vector(spike_start: int, spike_value: float = 1.0) -> list[float]:
    vector = [0.0] * EMBEDDING_VECTOR_SIZE
    for offset in range(4):
        vector[spike_start + offset] = spike_value
    return vector


FAKE_CLAIM_ID_BEST_MATCH = "CLM-2099-001"
FAKE_CLAIM_ID_PARTIAL_MATCH = "CLM-2099-002"
FAKE_CLAIM_ID_WEAK_MATCH = "CLM-2099-003"
FAKE_FILLER_CLAIM_IDS = ["CLM-2099-004", "CLM-2099-005", "CLM-2099-006", "CLM-2099-007"]

FAKE_QUERY_TEXT = "Pipe burst under the kitchen sink."
FAKE_QUERY_VECTOR = [
    best + partial for best, partial in zip(_spike_vector(0), _spike_vector(100, spike_value=0.4))
]

FAKE_RECORD_BEST_MATCH = {
    "claim_id": FAKE_CLAIM_ID_BEST_MATCH,
    "damage_type": "water_damage",
    "severity": "moderate",
    "affected_areas": ["kitchen"],
    "description": "Pipe burst beneath the kitchen sink overnight.",
    "adjuster_notes": "Confirmed by plumber invoice.",
    "resolution": "covered_full",
    "repair_cost_actual": 5200,
}

FAKE_RECORD_PARTIAL_MATCH = {
    "claim_id": FAKE_CLAIM_ID_PARTIAL_MATCH,
    "damage_type": "storm_damage",
    "severity": "minor",
    "affected_areas": ["roof"],
    "description": "Hail damaged several roof shingles.",
    "adjuster_notes": "Minor cosmetic damage only.",
    "resolution": "covered_partial",
    "repair_cost_actual": 1200,
}

FAKE_RECORD_WEAK_MATCH = {
    "claim_id": FAKE_CLAIM_ID_WEAK_MATCH,
    "damage_type": "vandalism",
    "severity": "minor",
    "affected_areas": ["fence"],
    "description": "Graffiti found on the backyard fence.",
    "adjuster_notes": "No fraud indicators noted.",
    "resolution": "denied",
    "repair_cost_actual": 0,
}

FAKE_FILLER_RECORDS = [
    {
        "claim_id": claim_id,
        "damage_type": "other",
        "severity": "minor",
        "affected_areas": ["garage"],
        "description": f"Filler claim {claim_id} used only to pad result count.",
        "adjuster_notes": "Not relevant to the fake query.",
        "resolution": "denied",
        "repair_cost_actual": 0,
    }
    for claim_id in FAKE_FILLER_CLAIM_IDS
]

_FAKE_VECTOR_BY_CLAIM_ID = {
    FAKE_CLAIM_ID_BEST_MATCH: _spike_vector(0),
    FAKE_CLAIM_ID_PARTIAL_MATCH: _spike_vector(100),
    FAKE_CLAIM_ID_WEAK_MATCH: _spike_vector(200),
    **{
        claim_id: _spike_vector(204 + 4 * index)
        for index, claim_id in enumerate(FAKE_FILLER_CLAIM_IDS)
    },
}


class FakeClaimSearchEmbedder:
    def __init__(self, vector_for_text: dict, vector_for_query: dict):
        self._vector_for_text = vector_for_text
        self._vector_for_query = vector_for_query

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return [self._vector_for_text[text] for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector_for_query[text]


def build_fake_claim_search_embedder(records: list[dict]) -> FakeClaimSearchEmbedder:
    vector_for_text = {
        build_embedding_text(record): _FAKE_VECTOR_BY_CLAIM_ID[record["claim_id"]]
        for record in records
    }
    return FakeClaimSearchEmbedder(vector_for_text, {FAKE_QUERY_TEXT: FAKE_QUERY_VECTOR})
