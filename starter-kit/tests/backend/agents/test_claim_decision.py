"""Tests for node 1, the combined intake-and-parameter Jev decision.

No HTTP: a fake client mimics ``DecisionModelClient.decide`` and returns canned
answers shaped like the real one, so the tests exercise state composition,
thresholding, and the intake pass/fail semantics the router depends on.
"""

import asyncio

import pytest
from claim_decision_test_fixtures import (
    FAKE_AFFECTED_AREAS,
    FAKE_DAMAGE_TYPE,
    FAKE_DESCRIPTION,
    FAKE_DOCUMENT_TEXT,
    FAKE_IMAGE_DATA_URL,
    FAKE_POLICY_TYPE,
    FAKE_SECOND_IMAGE_DATA_URL,
    FAKE_SEVERITY,
    FAKE_SPECIFIC_AREA,
    IMAGE_URL_PART_KEY,
    IMAGE_URL_PART_TYPE,
    IMAGE_URL_PART_URL_KEY,
    TEXT_PART_TEXT_KEY,
    TEXT_PART_TYPE,
)
from fake_decision_model_client import (
    FAILING_NOUL_PROBABILITY,
    JUST_BELOW_THRESHOLD_PROBABILITY,
    PASSING_NOUL_PROBABILITY,
    QUESTION_TYPE_FIELD,
    FakeDecisionModelClient,
)

from app.agents.claim_decision import (
    claim_decision_passed,
    decide_claim,
    describe_claim_decision_failure,
)
from app.agents.prompts.claim_decision_questions import (
    AFFECTED_AREA_QUESTION_ID_PREFIX,
    CLAIM_DECISION_QUESTIONS,
    DAMAGE_TYPE_QUESTION_ID,
    IS_PROPERTY_DAMAGE_QUESTION_ID,
    IS_VALID_IMAGE_QUESTION_ID,
    NO_OFFENSIVE_CONTENT_QUESTION_ID,
    NO_PII_DETECTED_QUESTION_ID,
    SEVERITY_QUESTION_ID,
    affected_area_question_id,
)
from app.agents.schemas.claim_decision_schema import ClaimDecisionOut
from app.agents.schemas.claim_submission import ClaimSubmission
from app.constants.claims.affected_area_vocabulary import AFFECTED_AREA_VOCABULARY
from app.constants.claims.area_counting_rule import AREA_COUNTING_RULE
from app.constants.claims.claim_taxonomy import DamageType, SeverityLevel
from app.constants.claims.generic_area_alias_vocabulary import GENERIC_AREA_ALIASES
from app.constants.claims.overlapping_component_areas import (
    SPECIFIC_COMPONENT_AREA_BY_BROADER_AREA,
)
from app.constants.claims.severity_classification_rubric import SEVERITY_CLASSIFICATION_RUBRIC
from app.constants.claims.severity_level_definitions import SEVERITY_LEVEL_DEFINITIONS
from app.constants.claims.surface_area_alias_vocabulary import SURFACE_AREA_ALIASES
from app.constants.decision.decision_model_config import DECISION_PROBABILITY_THRESHOLD
from app.constants.intake.intake_validation_messages import (
    IMAGE_NOT_CLEAR_MESSAGE,
    MISSING_INPUT_MESSAGE,
    NOT_PROPERTY_DAMAGE_MESSAGE,
    OFFENSIVE_CONTENT_MESSAGE,
    PII_DETECTED_MESSAGE,
)


def _passing_intake_noul_answers() -> dict[str, float]:
    return {
        IS_PROPERTY_DAMAGE_QUESTION_ID: PASSING_NOUL_PROBABILITY,
        IS_VALID_IMAGE_QUESTION_ID: PASSING_NOUL_PROBABILITY,
        NO_PII_DETECTED_QUESTION_ID: PASSING_NOUL_PROBABILITY,
        NO_OFFENSIVE_CONTENT_QUESTION_ID: PASSING_NOUL_PROBABILITY,
    }


def _choice_answers() -> dict[str, str]:
    return {
        DAMAGE_TYPE_QUESTION_ID: FAKE_DAMAGE_TYPE.value,
        SEVERITY_QUESTION_ID: FAKE_SEVERITY.value,
    }


def _build_client(
    noul_answers: dict[str, float] | None = None,
    choice_answers: dict[str, str] | None = None,
    default_noul_probability: float = FAILING_NOUL_PROBABILITY,
) -> FakeDecisionModelClient:
    return FakeDecisionModelClient(
        noul_probability_by_question_id=(
            noul_answers if noul_answers is not None else _passing_intake_noul_answers()
        ),
        choice_label_by_question_id=(
            choice_answers if choice_answers is not None else _choice_answers()
        ),
        default_noul_probability=default_noul_probability,
    )


def _submission(**overrides) -> ClaimSubmission:
    values: dict = {
        "description": FAKE_DESCRIPTION,
        "policy_type": FAKE_POLICY_TYPE,
        "image_data_urls": [FAKE_IMAGE_DATA_URL],
    }
    values.update(overrides)
    return ClaimSubmission(**values)


def _decision(**overrides) -> ClaimDecisionOut:
    values: dict = {
        "is_property_damage": True,
        "is_valid_image": True,
        "no_pii_detected": True,
        "no_offensive_content": True,
        "damage_type": FAKE_DAMAGE_TYPE,
        "severity": FAKE_SEVERITY,
        "affected_areas": list(FAKE_AFFECTED_AREAS),
    }
    values.update(overrides)
    return ClaimDecisionOut(**values)


def _run_decide_claim(
    client: FakeDecisionModelClient, submission: ClaimSubmission
) -> ClaimDecisionOut:
    return asyncio.run(decide_claim(client, submission))


def _image_parts(state: list[dict]) -> list[dict]:
    return [part for part in state if part[QUESTION_TYPE_FIELD] == IMAGE_URL_PART_TYPE]


def _expected_areas_in_vocabulary_order(areas) -> list[str]:
    return [area for area in AFFECTED_AREA_VOCABULARY if area in areas]


def test_decide_claim_returns_the_full_decision_when_every_answer_passes():
    area_answers = {
        affected_area_question_id(area): PASSING_NOUL_PROBABILITY for area in FAKE_AFFECTED_AREAS
    }
    client = _build_client(noul_answers={**_passing_intake_noul_answers(), **area_answers})

    decision = _run_decide_claim(client, _submission())

    assert decision.is_property_damage is True
    assert decision.is_valid_image is True
    assert decision.no_pii_detected is True
    assert decision.no_offensive_content is True
    assert decision.damage_type == FAKE_DAMAGE_TYPE
    assert decision.severity == FAKE_SEVERITY
    assert decision.affected_areas == _expected_areas_in_vocabulary_order(FAKE_AFFECTED_AREAS)


def test_decide_claim_returns_null_image_validity_for_a_text_only_submission():
    client = _build_client()

    decision = _run_decide_claim(client, _submission(image_data_urls=[]))

    assert decision.is_valid_image is None
    assert decision.is_property_damage is True
    assert _image_parts(client.observed_state) == []


def test_decide_claim_builds_image_parts_for_an_image_only_submission():
    client = _build_client(
        noul_answers={
            **_passing_intake_noul_answers(),
            affected_area_question_id("garage"): PASSING_NOUL_PROBABILITY,
        }
    )

    decision = _run_decide_claim(client, _submission(description=""))

    assert decision.is_valid_image is True
    assert decision.affected_areas == ["garage"]
    assert len(_image_parts(client.observed_state)) == 1
    assert client.call_count == 1


@pytest.mark.parametrize("generic_alias", GENERIC_AREA_ALIASES)
def test_decide_claim_drops_a_generic_alias_flagged_alongside_a_specific_area(generic_alias):
    client = _build_client(
        noul_answers={
            **_passing_intake_noul_answers(),
            affected_area_question_id(FAKE_SPECIFIC_AREA): PASSING_NOUL_PROBABILITY,
            affected_area_question_id(generic_alias): PASSING_NOUL_PROBABILITY,
        }
    )

    decision = _run_decide_claim(client, _submission())

    assert decision.affected_areas == [FAKE_SPECIFIC_AREA]


@pytest.mark.parametrize("generic_alias", GENERIC_AREA_ALIASES)
def test_decide_claim_keeps_a_generic_alias_flagged_alone(generic_alias):
    client = _build_client(
        noul_answers={
            **_passing_intake_noul_answers(),
            affected_area_question_id(generic_alias): PASSING_NOUL_PROBABILITY,
        }
    )

    decision = _run_decide_claim(client, _submission())

    assert decision.affected_areas == [generic_alias]


@pytest.mark.parametrize("surface_alias", SURFACE_AREA_ALIASES)
def test_decide_claim_drops_a_surface_alias_flagged_alongside_a_specific_area(surface_alias):
    client = _build_client(
        noul_answers={
            **_passing_intake_noul_answers(),
            affected_area_question_id(FAKE_SPECIFIC_AREA): PASSING_NOUL_PROBABILITY,
            affected_area_question_id(surface_alias): PASSING_NOUL_PROBABILITY,
        }
    )

    decision = _run_decide_claim(client, _submission())

    assert decision.affected_areas == [FAKE_SPECIFIC_AREA]


@pytest.mark.parametrize("surface_alias", SURFACE_AREA_ALIASES)
def test_decide_claim_keeps_a_surface_alias_flagged_alone(surface_alias):
    client = _build_client(
        noul_answers={
            **_passing_intake_noul_answers(),
            affected_area_question_id(surface_alias): PASSING_NOUL_PROBABILITY,
        }
    )

    decision = _run_decide_claim(client, _submission())

    assert decision.affected_areas == [surface_alias]


@pytest.mark.parametrize("surface_alias", SURFACE_AREA_ALIASES)
@pytest.mark.parametrize("generic_alias", GENERIC_AREA_ALIASES)
def test_decide_claim_drops_a_generic_alias_flagged_alongside_a_surface_alias(
    surface_alias, generic_alias
):
    client = _build_client(
        noul_answers={
            **_passing_intake_noul_answers(),
            affected_area_question_id(surface_alias): PASSING_NOUL_PROBABILITY,
            affected_area_question_id(generic_alias): PASSING_NOUL_PROBABILITY,
        }
    )

    decision = _run_decide_claim(client, _submission())

    assert decision.affected_areas == [surface_alias]


@pytest.mark.parametrize(
    ("broader_area", "specific_area"), SPECIFIC_COMPONENT_AREA_BY_BROADER_AREA.items()
)
def test_decide_claim_drops_a_broader_component_flagged_alongside_its_specific_form(
    broader_area, specific_area
):
    client = _build_client(
        noul_answers={
            **_passing_intake_noul_answers(),
            affected_area_question_id(broader_area): PASSING_NOUL_PROBABILITY,
            affected_area_question_id(specific_area): PASSING_NOUL_PROBABILITY,
        }
    )

    decision = _run_decide_claim(client, _submission())

    assert decision.affected_areas == [specific_area]


@pytest.mark.parametrize("broader_area", SPECIFIC_COMPONENT_AREA_BY_BROADER_AREA)
def test_decide_claim_keeps_a_broader_component_flagged_alone(broader_area):
    client = _build_client(
        noul_answers={
            **_passing_intake_noul_answers(),
            affected_area_question_id(broader_area): PASSING_NOUL_PROBABILITY,
        }
    )

    decision = _run_decide_claim(client, _submission())

    assert decision.affected_areas == [broader_area]


def test_decide_claim_applies_every_area_filter_together():
    broader_area, specific_area = next(iter(SPECIFIC_COMPONENT_AREA_BY_BROADER_AREA.items()))
    flagged_areas = (broader_area, specific_area, *SURFACE_AREA_ALIASES, *GENERIC_AREA_ALIASES)
    client = _build_client(
        noul_answers={
            **_passing_intake_noul_answers(),
            **{affected_area_question_id(area): PASSING_NOUL_PROBABILITY for area in flagged_areas},
        }
    )

    decision = _run_decide_claim(client, _submission())

    assert decision.affected_areas == [specific_area]


def test_area_filter_constants_name_only_vocabulary_areas():
    filter_areas = {
        *SURFACE_AREA_ALIASES,
        *GENERIC_AREA_ALIASES,
        *SPECIFIC_COMPONENT_AREA_BY_BROADER_AREA,
        *SPECIFIC_COMPONENT_AREA_BY_BROADER_AREA.values(),
    }

    assert filter_areas <= set(AFFECTED_AREA_VOCABULARY)


@pytest.mark.parametrize(
    ("failing_question_id", "expected_failure"),
    [
        (IS_PROPERTY_DAMAGE_QUESTION_ID, {"is_property_damage": False}),
        (IS_VALID_IMAGE_QUESTION_ID, {"is_valid_image": False}),
        (NO_PII_DETECTED_QUESTION_ID, {"no_pii_detected": False}),
        (NO_OFFENSIVE_CONTENT_QUESTION_ID, {"no_offensive_content": False}),
    ],
)
def test_decide_claim_flags_the_single_failing_intake_check(failing_question_id, expected_failure):
    client = _build_client(
        noul_answers={
            **_passing_intake_noul_answers(),
            failing_question_id: FAILING_NOUL_PROBABILITY,
        }
    )

    decision = _run_decide_claim(client, _submission())

    expected_intake = {
        "is_property_damage": True,
        "is_valid_image": True,
        "no_pii_detected": True,
        "no_offensive_content": True,
    }
    expected_intake.update(expected_failure)
    assert {field: getattr(decision, field) for field in expected_intake} == expected_intake
    assert claim_decision_passed(decision) is False


@pytest.mark.parametrize(
    ("probability", "expected"),
    [
        (DECISION_PROBABILITY_THRESHOLD, True),
        (JUST_BELOW_THRESHOLD_PROBABILITY, False),
    ],
)
def test_decide_claim_thresholds_an_intake_noul_at_the_probability_bound(probability, expected):
    client = _build_client(
        noul_answers={IS_PROPERTY_DAMAGE_QUESTION_ID: probability},
        default_noul_probability=PASSING_NOUL_PROBABILITY,
    )

    decision = _run_decide_claim(client, _submission())

    assert decision.is_property_damage is expected


@pytest.mark.parametrize(
    ("probability", "expected_included"),
    [
        (DECISION_PROBABILITY_THRESHOLD, True),
        (JUST_BELOW_THRESHOLD_PROBABILITY, False),
    ],
)
def test_decide_claim_thresholds_an_area_noul_at_the_probability_bound(
    probability, expected_included
):
    client = _build_client(
        noul_answers={
            **_passing_intake_noul_answers(),
            affected_area_question_id("kitchen"): probability,
        }
    )

    decision = _run_decide_claim(client, _submission())

    assert ("kitchen" in decision.affected_areas) is expected_included


def test_decide_claim_sends_text_and_inline_image_parts_as_state():
    client = _build_client()

    _run_decide_claim(
        client,
        _submission(
            document_text=FAKE_DOCUMENT_TEXT,
            image_data_urls=[FAKE_IMAGE_DATA_URL, FAKE_SECOND_IMAGE_DATA_URL],
        ),
    )

    state = client.observed_state
    assert isinstance(state, list)
    text_part, *image_parts = state
    assert text_part[QUESTION_TYPE_FIELD] == TEXT_PART_TYPE
    assert FAKE_DESCRIPTION in text_part[TEXT_PART_TEXT_KEY]
    assert FAKE_POLICY_TYPE.value in text_part[TEXT_PART_TEXT_KEY]
    assert FAKE_DOCUMENT_TEXT in text_part[TEXT_PART_TEXT_KEY]
    assert [part[IMAGE_URL_PART_KEY][IMAGE_URL_PART_URL_KEY] for part in image_parts] == [
        FAKE_IMAGE_DATA_URL,
        FAKE_SECOND_IMAGE_DATA_URL,
    ]
    assert all(part[QUESTION_TYPE_FIELD] == IMAGE_URL_PART_TYPE for part in image_parts)
    assert client.observed_questions is CLAIM_DECISION_QUESTIONS


def test_decide_claim_short_circuits_without_calling_jev_when_there_is_no_input():
    client = _build_client()

    decision = _run_decide_claim(client, _submission(description="", image_data_urls=[]))

    assert client.call_count == 0
    assert decision.is_property_damage is False
    assert decision.is_valid_image is None
    assert decision.affected_areas == []
    assert claim_decision_passed(decision) is False


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({}, True),
        ({"is_valid_image": None}, True),
        ({"is_property_damage": False}, False),
        ({"is_valid_image": False}, False),
        ({"no_pii_detected": False}, False),
        ({"no_offensive_content": False}, False),
    ],
)
def test_claim_decision_passed_requires_every_intake_gate(overrides, expected):
    assert claim_decision_passed(_decision(**overrides)) is expected


@pytest.mark.parametrize(
    ("overrides", "has_required_input", "expected_message"),
    [
        ({}, False, MISSING_INPUT_MESSAGE),
        ({"is_property_damage": False}, True, NOT_PROPERTY_DAMAGE_MESSAGE),
        ({"is_valid_image": False}, True, IMAGE_NOT_CLEAR_MESSAGE),
        ({"no_pii_detected": False}, True, PII_DETECTED_MESSAGE),
        ({"no_offensive_content": False}, True, OFFENSIVE_CONTENT_MESSAGE),
    ],
)
def test_describe_claim_decision_failure_maps_each_intake_gate(
    overrides, has_required_input, expected_message
):
    decision = _decision(**overrides)

    assert describe_claim_decision_failure(decision, has_required_input) == expected_message


def test_damage_type_choice_criteria_are_derived_from_the_enum():
    assert CLAIM_DECISION_QUESTIONS[DAMAGE_TYPE_QUESTION_ID]["criteria"] == {
        damage_type.value: damage_type.value for damage_type in DamageType
    }


def test_every_vocabulary_area_has_one_noul_question():
    area_question_ids = [
        question_id
        for question_id in CLAIM_DECISION_QUESTIONS
        if question_id.startswith(AFFECTED_AREA_QUESTION_ID_PREFIX)
    ]

    assert area_question_ids == [
        affected_area_question_id(area) for area in AFFECTED_AREA_VOCABULARY
    ]


def test_questions_reuse_the_area_counting_rule_and_severity_rubric():
    assert (
        SEVERITY_CLASSIFICATION_RUBRIC
        in CLAIM_DECISION_QUESTIONS[SEVERITY_QUESTION_ID]["instructions"]
    )
    assert all(
        AREA_COUNTING_RULE
        in CLAIM_DECISION_QUESTIONS[affected_area_question_id(area)]["instructions"]
        for area in AFFECTED_AREA_VOCABULARY
    )


def test_severity_criteria_define_every_level():
    assert CLAIM_DECISION_QUESTIONS[SEVERITY_QUESTION_ID]["criteria"] == {
        severity.value: SEVERITY_LEVEL_DEFINITIONS[severity] for severity in SeverityLevel
    }
