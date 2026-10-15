import asyncio

import pytest
from fake_decision_model_client import (
    FAILING_NOUL_PROBABILITY,
    JUST_BELOW_THRESHOLD_PROBABILITY,
    FakeDecisionModelClient,
)
from safety_decision_test_fixtures import (
    FAKE_DAMAGE_DESCRIPTION,
    FAKE_RECOMMENDATION,
)

from app.agents.prompts.safety_decision_questions import SAFETY_DECISION_QUESTIONS
from app.agents.safety_decision import check_output_safety
from app.agents.schemas.safety_checks_schema import SafetyChecksOut
from app.constants.decision.decision_model_config import DECISION_PROBABILITY_THRESHOLD


def _all_passing_safety_checks() -> SafetyChecksOut:
    return SafetyChecksOut(
        no_coverage_promises=True,
        no_legal_advice=True,
        no_settlement_amounts=True,
        no_liability_determination=True,
        no_emotional_language=True,
    )


def _run_check_output_safety(client: FakeDecisionModelClient) -> SafetyChecksOut:
    return asyncio.run(check_output_safety(client, FAKE_DAMAGE_DESCRIPTION, FAKE_RECOMMENDATION))


def test_check_output_safety_returns_valid_checks_when_every_answer_passes():
    result = _run_check_output_safety(FakeDecisionModelClient({}))

    assert result == _all_passing_safety_checks()
    assert all(result.model_dump().values())


@pytest.mark.parametrize("failing_question_id", list(SAFETY_DECISION_QUESTIONS))
def test_check_output_safety_flags_the_single_failing_check(failing_question_id):
    # A question id doubles as its SafetyChecksOut field name by design, so the
    # expected result is every check passing except the one under test.
    assert failing_question_id in SafetyChecksOut.model_fields
    client = FakeDecisionModelClient({failing_question_id: FAILING_NOUL_PROBABILITY})

    result = _run_check_output_safety(client)

    expected_fields = _all_passing_safety_checks().model_dump()
    expected_fields[failing_question_id] = False
    assert result == SafetyChecksOut(**expected_fields)


def test_check_output_safety_reads_a_probability_at_the_threshold_as_passing():
    client = FakeDecisionModelClient({}, default_noul_probability=DECISION_PROBABILITY_THRESHOLD)

    result = _run_check_output_safety(client)

    assert all(result.model_dump().values())


def test_check_output_safety_reads_a_probability_below_the_threshold_as_failing():
    client = FakeDecisionModelClient({}, default_noul_probability=JUST_BELOW_THRESHOLD_PROBABILITY)

    result = _run_check_output_safety(client)

    assert not any(result.model_dump().values())


def test_check_output_safety_sends_the_draft_text_as_state_with_the_node_4_questions():
    client = FakeDecisionModelClient({})

    _run_check_output_safety(client)

    assert isinstance(client.observed_state, str)
    assert FAKE_DAMAGE_DESCRIPTION in client.observed_state
    assert FAKE_RECOMMENDATION in client.observed_state
    assert client.observed_questions is SAFETY_DECISION_QUESTIONS
