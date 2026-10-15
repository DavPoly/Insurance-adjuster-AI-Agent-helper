class FakeTriageChatModel:
    def __init__(
        self,
        tool_loop_responses=None,
        structured_output_value=None,
        structured_output_values_by_schema=None,
    ):
        self._tool_loop_responses = list(tool_loop_responses or [])
        self._call_index = 0
        self._structured_output_value = structured_output_value
        self._structured_output_values_by_schema = structured_output_values_by_schema or {}

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        response = self._tool_loop_responses[self._call_index]
        self._call_index += 1
        return response

    def with_structured_output(self, schema):
        value = self._structured_output_values_by_schema.get(schema, self._structured_output_value)
        return _FakeStructuredOutputRunnable(value)


class _FakeStructuredOutputRunnable:
    def __init__(self, value):
        self._value = value

    def invoke(self, messages):
        return self._value


class _FakeQueryResponse:
    def __init__(self, points: list):
        self.points = points


class FakeTriageQdrantClient:
    def query_points(self, collection_name: str, query, limit: int):
        return _FakeQueryResponse([])


class FakeTriageEmbedder:
    def embed_query(self, text: str) -> list[float]:
        return [0.0]


FAKE_COST_TABLE = {
    "cost_matrix": {
        "water_damage": {"minor": {"min_per_area": 500, "max_per_area": 2000}},
    }
}

FAKE_COVERAGE_TABLE = {
    "policies": {
        "standard_homeowner": {
            "covered_categories": ["water_damage"],
            "deductible": 1500,
            "max_payout": 250000,
            "notes": "Fake standard coverage notes.",
        }
    }
}
