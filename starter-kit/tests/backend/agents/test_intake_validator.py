import pytest
from fake_triage_chat_model import FakeTriageChatModel

from app.agents.intake_validator import (
    describe_intake_validation_failure,
    intake_validation_passed,
    validate_claim_intake,
)
from app.agents.schemas.intake_validation_schema import IntakeValidationOut
from app.constants.intake.intake_validation_messages import (
    IMAGE_NOT_CLEAR_MESSAGE,
    MISSING_INPUT_MESSAGE,
    NOT_PROPERTY_DAMAGE_MESSAGE,
    OFFENSIVE_CONTENT_MESSAGE,
    PII_DETECTED_MESSAGE,
)

FAKE_IMAGE_DATA_URL = "data:image/jpeg;base64,fake"
FAKE_DESCRIPTION = "Water is pooling under my kitchen sink."


class _ExplodingChatModel:
    """Fails the test if the intake validator calls an LLM it shouldn't."""

    def with_structured_output(self, schema):
        raise AssertionError("LLM should not be called when there is no input to validate.")


def test_validate_claim_intake_short_circuits_when_no_image_or_description():
    result = validate_claim_intake(_ExplodingChatModel(), image_data_urls=[], description="")

    assert result == IntakeValidationOut(
        is_property_damage=False,
        is_valid_image=None,
        no_pii_detected=True,
        no_offensive_content=True,
    )


def test_validate_claim_intake_forces_is_valid_image_null_for_text_only_input():
    llm = FakeTriageChatModel(
        structured_output_values_by_schema={
            IntakeValidationOut: IntakeValidationOut(
                is_property_damage=True,
                is_valid_image=True,
                no_pii_detected=True,
                no_offensive_content=True,
            )
        }
    )

    result = validate_claim_intake(llm, image_data_urls=[], description=FAKE_DESCRIPTION)

    assert result.is_valid_image is None
    assert result.is_property_damage is True


def test_validate_claim_intake_passes_through_llm_result_when_an_image_is_present():
    rejecting_result = IntakeValidationOut(
        is_property_damage=False,
        is_valid_image=True,
        no_pii_detected=True,
        no_offensive_content=True,
    )
    llm = FakeTriageChatModel(
        structured_output_values_by_schema={IntakeValidationOut: rejecting_result}
    )

    result = validate_claim_intake(
        llm, image_data_urls=[FAKE_IMAGE_DATA_URL], description=FAKE_DESCRIPTION
    )

    assert result == rejecting_result


@pytest.mark.parametrize(
    ("intake_validation", "expected"),
    [
        (
            IntakeValidationOut(
                is_property_damage=True,
                is_valid_image=True,
                no_pii_detected=True,
                no_offensive_content=True,
            ),
            True,
        ),
        (
            IntakeValidationOut(
                is_property_damage=True,
                is_valid_image=None,
                no_pii_detected=True,
                no_offensive_content=True,
            ),
            True,
        ),
        (
            IntakeValidationOut(
                is_property_damage=False,
                is_valid_image=True,
                no_pii_detected=True,
                no_offensive_content=True,
            ),
            False,
        ),
        (
            IntakeValidationOut(
                is_property_damage=True,
                is_valid_image=False,
                no_pii_detected=True,
                no_offensive_content=True,
            ),
            False,
        ),
        (
            IntakeValidationOut(
                is_property_damage=True,
                is_valid_image=True,
                no_pii_detected=False,
                no_offensive_content=True,
            ),
            False,
        ),
        (
            IntakeValidationOut(
                is_property_damage=True,
                is_valid_image=True,
                no_pii_detected=True,
                no_offensive_content=False,
            ),
            False,
        ),
    ],
)
def test_intake_validation_passed_requires_every_check_to_pass(intake_validation, expected):
    assert intake_validation_passed(intake_validation) is expected


def test_describe_intake_validation_failure_reports_missing_input():
    intake_validation = IntakeValidationOut(
        is_property_damage=False,
        is_valid_image=None,
        no_pii_detected=True,
        no_offensive_content=True,
    )

    message = describe_intake_validation_failure(intake_validation, has_required_input=False)

    assert message == MISSING_INPUT_MESSAGE


def test_describe_intake_validation_failure_reports_not_property_damage():
    intake_validation = IntakeValidationOut(
        is_property_damage=False,
        is_valid_image=True,
        no_pii_detected=True,
        no_offensive_content=True,
    )

    message = describe_intake_validation_failure(intake_validation, has_required_input=True)

    assert message == NOT_PROPERTY_DAMAGE_MESSAGE


def test_describe_intake_validation_failure_reports_unclear_image():
    intake_validation = IntakeValidationOut(
        is_property_damage=True,
        is_valid_image=False,
        no_pii_detected=True,
        no_offensive_content=True,
    )

    message = describe_intake_validation_failure(intake_validation, has_required_input=True)

    assert message == IMAGE_NOT_CLEAR_MESSAGE


def test_describe_intake_validation_failure_reports_pii_detected():
    intake_validation = IntakeValidationOut(
        is_property_damage=True,
        is_valid_image=True,
        no_pii_detected=False,
        no_offensive_content=True,
    )

    message = describe_intake_validation_failure(intake_validation, has_required_input=True)

    assert message == PII_DETECTED_MESSAGE


def test_describe_intake_validation_failure_reports_offensive_content():
    intake_validation = IntakeValidationOut(
        is_property_damage=True,
        is_valid_image=True,
        no_pii_detected=True,
        no_offensive_content=False,
    )

    message = describe_intake_validation_failure(intake_validation, has_required_input=True)

    assert message == OFFENSIVE_CONTENT_MESSAGE
