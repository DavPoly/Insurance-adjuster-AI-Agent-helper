"""Fake Qdrant client + embedder for exercising search_past_claims tool wiring.
Ranking/recall behavior itself is covered by tests/backend/tools/test_claim_search.py.
"""

FAKE_SEARCH_CLAIM_ID = "CLM-9999-001"
FAKE_SEARCH_SIMILARITY_SCORE = 0.87

FAKE_SEARCH_RESULT_PAYLOAD = {
    "claim_id": FAKE_SEARCH_CLAIM_ID,
    "damage_type": "water_damage",
    "severity": "moderate",
    "affected_areas": ["kitchen"],
    "resolution": "covered_full",
    "repair_cost_actual": 5200,
}

FAKE_SEARCH_TOOL_RESULT = {
    "claim_id": FAKE_SEARCH_CLAIM_ID,
    "similarity_score": FAKE_SEARCH_SIMILARITY_SCORE,
    **{key: value for key, value in FAKE_SEARCH_RESULT_PAYLOAD.items() if key != "claim_id"},
}


class _FakePoint:
    def __init__(self, payload: dict, score: float):
        self.payload = payload
        self.score = score


class _FakeQueryResponse:
    def __init__(self, points: list):
        self.points = points


class FakeTriageQdrantClient:
    def __init__(self, points: list):
        self._points = points

    def query_points(self, collection_name: str, query, limit: int):
        return _FakeQueryResponse(self._points[:limit])


class FakeTriageEmbedder:
    def embed_query(self, text: str) -> list[float]:
        return [0.0]


FAKE_SEARCH_POINT = _FakePoint(FAKE_SEARCH_RESULT_PAYLOAD, FAKE_SEARCH_SIMILARITY_SCORE)
