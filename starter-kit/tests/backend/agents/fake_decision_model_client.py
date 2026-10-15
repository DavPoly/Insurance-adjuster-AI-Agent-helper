"""Shared fake Jev decision client and the answer wire constants for the
node-1, node-4, and deterministic-triage test suites.

The fake itself is used by those three suites; the router suite reuses the
``*_FIELD`` constants below but drives its own scripted decision client. The
``*_FIELD`` keys and the probability bounds mirror the OpenRouter Decisions
API's answer wire shape, and are re-typed here on purpose: the consuming tests
assert the literal payload shape, so importing the production
``DecisionModelClient``'s private field-name constants instead would make those
assertions tautological (they would keep passing even if a production key were
renamed). The llm transport fixtures deliberately re-declare the same wire field
names so their request-shape assertions stay independent of this module.
"""

from app.agents.prompts.claim_decision_questions import CHOICE_QUESTION_TYPE
from app.constants.decision.decision_model_config import DECISION_PROBABILITY_THRESHOLD

NOUL_ANSWER_FIELD = "noul"
CHOICE_ANSWER_FIELD = "choice"
QUESTION_TYPE_FIELD = "type"

PASSING_NOUL_PROBABILITY = 1.0
FAILING_NOUL_PROBABILITY = 0.0
# Keeps the "just below the threshold" case within float precision of the bound.
NEAR_THRESHOLD_STEP = 0.01
JUST_BELOW_THRESHOLD_PROBABILITY = DECISION_PROBABILITY_THRESHOLD - NEAR_THRESHOLD_STEP


class FakeDecisionModelClient:
    """Stands in for ``DecisionModelClient`` with no HTTP; records the request.

    ``decide`` records the ``state`` and ``questions`` it was handed — so tests
    can assert what each node grounded its call in — and answers every question
    from the supplied maps, falling back to ``default_noul_probability`` for a
    Noul question that is not listed. ``call_count`` counts the calls received.

    ``default_noul_probability`` is a constructor argument rather than a fixed
    module constant because the suites disagree: the node-1 suite defaults to
    *failing* answers (so a test must opt a question into passing), while the
    node-4 and pipeline suites default to *passing*.
    """

    def __init__(
        self,
        noul_probability_by_question_id: dict[str, float] | None = None,
        choice_label_by_question_id: dict[str, str] | None = None,
        default_noul_probability: float = PASSING_NOUL_PROBABILITY,
    ) -> None:
        self._noul_probability_by_question_id = dict(noul_probability_by_question_id or {})
        self._choice_label_by_question_id = dict(choice_label_by_question_id or {})
        self._default_noul_probability = default_noul_probability
        self.observed_state: object | None = None
        self.observed_questions: dict[str, dict] | None = None
        self.call_count = 0

    async def decide(self, state: object, questions: dict[str, dict]) -> dict[str, dict]:
        self.call_count += 1
        self.observed_state = state
        self.observed_questions = questions
        return {
            question_id: self._answer(question_id, question_spec)
            for question_id, question_spec in questions.items()
        }

    def _answer(self, question_id: str, question_spec: dict) -> dict:
        if question_spec[QUESTION_TYPE_FIELD] == CHOICE_QUESTION_TYPE:
            return {CHOICE_ANSWER_FIELD: self._choice_label_by_question_id[question_id]}
        return {
            NOUL_ANSWER_FIELD: self._noul_probability_by_question_id.get(
                question_id, self._default_noul_probability
            )
        }
