from app.agents.prompts.claim_decision_questions import (
    AFFECTED_AREA_QUESTION_ID_PREFIX,
    CHOICE_QUESTION_TYPE,
    DAMAGE_TYPE_QUESTION_ID,
    SEVERITY_QUESTION_ID,
)
from app.agents.prompts.safety_decision_questions import SAFETY_DECISION_QUESTIONS
from app.agents.schemas.safety_checks_schema import SafetyChecksOut
from app.constants.claims.claim_taxonomy import DamageType, SeverityLevel

# Wire-format keys mirroring the Decisions API request/answer shape. Re-typed on
# purpose so the fake stays independent of the client's private field names.
_QUESTION_TYPE_FIELD = "type"
_NOUL_ANSWER_FIELD = "noul"
_CHOICE_ANSWER_FIELD = "choice"
_PASSING_NOUL_PROBABILITY = 1.0
_FAILING_NOUL_PROBABILITY = 0.0

_SAFETY_QUESTION_IDS = frozenset(SAFETY_DECISION_QUESTIONS)


class FakeDecisionModelClient:
    """Stands in for DecisionModelClient across both Jev nodes, with no HTTP.

    Node-1 calls replay the canned classification. Node-4 calls replay
    ``safety_check_attempts``, one entry per successive safety call (the last
    entry repeats once the script is exhausted; an empty script passes every
    check) — so a test drives the router's bounded safety retry by listing a
    failing-then-passing sequence. ``observed_claim_states`` records the node-1
    request state so tests can assert the document text reached node 1.
    """

    def __init__(
        self,
        intake_answers: dict[str, float] | None = None,
        damage_type: DamageType = DamageType.WATER_DAMAGE,
        severity: SeverityLevel = SeverityLevel.MINOR,
        affected_areas: tuple[str, ...] = (),
        safety_check_attempts: tuple[SafetyChecksOut, ...] = (),
    ) -> None:
        self._intake_answers = dict(intake_answers or {})
        self._damage_type = damage_type
        self._severity = severity
        self._affected_areas = set(affected_areas)
        self._safety_check_attempts = tuple(safety_check_attempts)
        self.observed_claim_states: list[object] = []
        self.safety_call_count = 0

    async def decide(self, state: object, questions: dict[str, dict]) -> dict[str, dict]:
        if frozenset(questions) == _SAFETY_QUESTION_IDS:
            return self._safety_answers()
        self.observed_claim_states.append(state)
        return {
            question_id: self._answer(question_id, question_spec)
            for question_id, question_spec in questions.items()
        }

    def _safety_answers(self) -> dict[str, dict]:
        self.safety_call_count += 1
        if not self._safety_check_attempts:
            outcomes = {question_id: True for question_id in _SAFETY_QUESTION_IDS}
        else:
            attempt_index = min(self.safety_call_count - 1, len(self._safety_check_attempts) - 1)
            outcomes = self._safety_check_attempts[attempt_index].model_dump()
        return {
            question_id: {
                _NOUL_ANSWER_FIELD: (
                    _PASSING_NOUL_PROBABILITY if passed else _FAILING_NOUL_PROBABILITY
                )
            }
            for question_id, passed in outcomes.items()
        }

    def _answer(self, question_id: str, question_spec: dict) -> dict:
        if question_spec[_QUESTION_TYPE_FIELD] == CHOICE_QUESTION_TYPE:
            return {_CHOICE_ANSWER_FIELD: self._choice_label(question_id)}
        return {_NOUL_ANSWER_FIELD: self._noul_probability(question_id)}

    def _choice_label(self, question_id: str) -> str:
        return {
            DAMAGE_TYPE_QUESTION_ID: self._damage_type.value,
            SEVERITY_QUESTION_ID: self._severity.value,
        }[question_id]

    def _noul_probability(self, question_id: str) -> float:
        if question_id in self._intake_answers:
            return self._intake_answers[question_id]
        if question_id.startswith(AFFECTED_AREA_QUESTION_ID_PREFIX):
            area = question_id.removeprefix(AFFECTED_AREA_QUESTION_ID_PREFIX)
            return (
                _PASSING_NOUL_PROBABILITY
                if area in self._affected_areas
                else _FAILING_NOUL_PROBABILITY
            )
        return _PASSING_NOUL_PROBABILITY


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
        self.structured_output_invoke_count = 0

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        response = self._tool_loop_responses[self._call_index]
        self._call_index += 1
        return response

    def with_structured_output(self, schema):
        value = self._structured_output_values_by_schema.get(schema, self._structured_output_value)
        return _FakeStructuredOutputRunnable(value, self)


class _FakeStructuredOutputRunnable:
    def __init__(self, value, owner: FakeTriageChatModel):
        self._value = value
        self._owner = owner

    def invoke(self, messages):
        self._owner.structured_output_invoke_count += 1
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
