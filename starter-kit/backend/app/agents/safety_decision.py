"""Node 4 of the deterministic triage pipeline: the output safety gate.

Reviews the free-text parts of the synthesized draft (``damage_description`` and
``recommendation``) with a single text-only Jev 1.14 decision call — five Noul
questions mirroring the boolean checks of :class:`SafetyChecksOut`. This is the
Jev successor to the LLM ``safety_checker``; it keeps that checker's field
semantics, where a ``True`` field means the draft passed that check.
"""

import logging

from app.agents.prompts.safety_decision_questions import (
    NO_COVERAGE_PROMISES_QUESTION_ID,
    NO_EMOTIONAL_LANGUAGE_QUESTION_ID,
    NO_LEGAL_ADVICE_QUESTION_ID,
    NO_LIABILITY_DETERMINATION_QUESTION_ID,
    NO_SETTLEMENT_AMOUNTS_QUESTION_ID,
    SAFETY_DECISION_QUESTIONS,
)
from app.agents.schemas.safety_checks_schema import SafetyChecksOut
from app.constants.decision.decision_model_config import DECISION_PROBABILITY_THRESHOLD
from app.llm.decision_model_client import DecisionModelClient, noul_probability

logger = logging.getLogger(__name__)

_DAMAGE_DESCRIPTION_STATE_LABEL = "damage_description"
_RECOMMENDATION_STATE_LABEL = "recommendation"


async def check_output_safety(
    client: DecisionModelClient,
    damage_description: str,
    recommendation: str,
) -> SafetyChecksOut:
    """Score the draft's free-text fields against the five output safety checks."""
    state = _build_safety_review_state(damage_description, recommendation)
    answers = await client.decide(state, SAFETY_DECISION_QUESTIONS)
    safety_checks = SafetyChecksOut(
        no_coverage_promises=_noul_holds(answers, NO_COVERAGE_PROMISES_QUESTION_ID),
        no_legal_advice=_noul_holds(answers, NO_LEGAL_ADVICE_QUESTION_ID),
        no_settlement_amounts=_noul_holds(answers, NO_SETTLEMENT_AMOUNTS_QUESTION_ID),
        no_liability_determination=_noul_holds(answers, NO_LIABILITY_DETERMINATION_QUESTION_ID),
        no_emotional_language=_noul_holds(answers, NO_EMOTIONAL_LANGUAGE_QUESTION_ID),
    )
    logger.debug("Output safety checks: %s", safety_checks.model_dump())
    return safety_checks


def _build_safety_review_state(damage_description: str, recommendation: str) -> str:
    return (
        f"{_DAMAGE_DESCRIPTION_STATE_LABEL}: {damage_description}\n\n"
        f"{_RECOMMENDATION_STATE_LABEL}: {recommendation}"
    )


def _noul_holds(answers: dict[str, dict], question_id: str) -> bool:
    return noul_probability(answers[question_id]) >= DECISION_PROBABILITY_THRESHOLD
