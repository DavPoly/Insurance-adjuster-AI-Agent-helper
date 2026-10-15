from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.prompts.intake_validator_system_prompt import INTAKE_VALIDATOR_SYSTEM_PROMPT
from app.agents.schemas.intake_validation_schema import IntakeValidationOut
from app.constants.intake.intake_validation_messages import (
    IMAGE_NOT_CLEAR_MESSAGE,
    MISSING_INPUT_MESSAGE,
    NOT_PROPERTY_DAMAGE_MESSAGE,
    OFFENSIVE_CONTENT_MESSAGE,
    PII_DETECTED_MESSAGE,
)


def validate_claim_intake(
    llm: BaseChatModel, image_data_urls: list[str], description: str
) -> IntakeValidationOut:
    if not image_data_urls and not description:
        return IntakeValidationOut(
            is_property_damage=False,
            is_valid_image=None,
            no_pii_detected=True,
            no_offensive_content=True,
        )

    content_blocks: list[dict] = [
        {"type": "text", "text": _build_intake_review_text(description, bool(image_data_urls))}
    ]
    for image_data_url in image_data_urls:
        content_blocks.append({"type": "image_url", "image_url": {"url": image_data_url}})

    structured_llm = llm.with_structured_output(IntakeValidationOut)
    result: IntakeValidationOut = structured_llm.invoke(
        [
            SystemMessage(content=INTAKE_VALIDATOR_SYSTEM_PROMPT),
            HumanMessage(content=content_blocks),
        ]
    )

    if not image_data_urls:
        result.is_valid_image = None
    return result


def _build_intake_review_text(description: str, has_images: bool) -> str:
    if has_images:
        return f"Claimant description: {description or '(none provided)'}"
    return f"Claimant description (text-only submission, no image attached): {description}"


def intake_validation_passed(intake_validation: IntakeValidationOut) -> bool:
    return (
        intake_validation.is_property_damage
        and intake_validation.no_pii_detected
        and intake_validation.no_offensive_content
        and intake_validation.is_valid_image is not False
    )


def describe_intake_validation_failure(
    intake_validation: IntakeValidationOut, has_required_input: bool
) -> str:
    if not has_required_input:
        return MISSING_INPUT_MESSAGE
    if not intake_validation.is_property_damage:
        return NOT_PROPERTY_DAMAGE_MESSAGE
    if intake_validation.is_valid_image is False:
        return IMAGE_NOT_CLEAR_MESSAGE
    if not intake_validation.no_pii_detected:
        return PII_DETECTED_MESSAGE
    return OFFENSIVE_CONTENT_MESSAGE
