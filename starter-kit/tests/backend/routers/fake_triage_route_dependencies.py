"""Router-specific triage fakes built on the shared agents-suite fakes.

Only the piece the router tests genuinely need lives here: a Jev decision client
that scripts both nodes (node 1's classification and node 4's safety retries).
The chat-model (including the counting synthesis fake), Qdrant, embedder,
lookup-table, and Jev-answer fakes themselves are imported from the agents suite.
"""

from agents.fake_decision_model_client import (
    CHOICE_ANSWER_FIELD,
    FAILING_NOUL_PROBABILITY,
    NOUL_ANSWER_FIELD,
    PASSING_NOUL_PROBABILITY,
    QUESTION_TYPE_FIELD,
)

from app.agents.prompts.claim_decision_questions import (
    AFFECTED_AREA_QUESTION_ID_PREFIX,
    CHOICE_QUESTION_TYPE,
    DAMAGE_TYPE_QUESTION_ID,
    SEVERITY_QUESTION_ID,
)
from app.agents.prompts.safety_decision_questions import SAFETY_DECISION_QUESTIONS
from app.agents.schemas.safety_checks_schema import SafetyChecksOut
from app.constants.claims.claim_taxonomy import DamageType, SeverityLevel

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
                NOUL_ANSWER_FIELD: (
                    PASSING_NOUL_PROBABILITY if passed else FAILING_NOUL_PROBABILITY
                )
            }
            for question_id, passed in outcomes.items()
        }

    def _answer(self, question_id: str, question_spec: dict) -> dict:
        if question_spec[QUESTION_TYPE_FIELD] == CHOICE_QUESTION_TYPE:
            return {CHOICE_ANSWER_FIELD: self._choice_label(question_id)}
        return {NOUL_ANSWER_FIELD: self._noul_probability(question_id)}

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
                PASSING_NOUL_PROBABILITY
                if area in self._affected_areas
                else FAILING_NOUL_PROBABILITY
            )
        return PASSING_NOUL_PROBABILITY
