import pytest
from fake_triage_chat_model import FakeTriageChatModel

from app.agents.safety_checker import check_output_safety, safety_checks_passed
from app.agents.schemas.safety_checks_schema import SafetyChecksOut

FAKE_TRIAGE_ASSESSMENT = {
    "damage_description": "Moderate water damage in the kitchen.",
    "recommendation": "Dispatch a water mitigation contractor within 24 hours.",
}


def _passing_safety_checks() -> SafetyChecksOut:
    return SafetyChecksOut(
        no_coverage_promises=True,
        no_legal_advice=True,
        no_settlement_amounts=True,
        no_liability_determination=True,
        no_emotional_language=True,
    )


def test_check_output_safety_returns_the_llms_structured_result():
    expected = _passing_safety_checks()
    llm = FakeTriageChatModel(structured_output_values_by_schema={SafetyChecksOut: expected})

    result = check_output_safety(llm, FAKE_TRIAGE_ASSESSMENT)

    assert result == expected


@pytest.mark.parametrize(
    ("safety_checks", "expected"),
    [
        (_passing_safety_checks(), True),
        (
            SafetyChecksOut(
                no_coverage_promises=False,
                no_legal_advice=True,
                no_settlement_amounts=True,
                no_liability_determination=True,
                no_emotional_language=True,
            ),
            False,
        ),
        (
            SafetyChecksOut(
                no_coverage_promises=True,
                no_legal_advice=True,
                no_settlement_amounts=True,
                no_liability_determination=True,
                no_emotional_language=False,
            ),
            False,
        ),
    ],
)
def test_safety_checks_passed_requires_every_check_to_pass(safety_checks, expected):
    assert safety_checks_passed(safety_checks) is expected
