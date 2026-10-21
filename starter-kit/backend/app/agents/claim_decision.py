"""Node 1 of the deterministic triage pipeline: intake plus parameter extraction.

A single multimodal Jev 1.14 decision call reviews the claim — description,
policy type, optional document text, and any photos as inline ``image_url`` parts
— and answers every intake and parameter question at once. It is the Jev
successor to the LLM ``intake_validator``: the same four intake booleans gate the
pipeline and the same pass/fail semantics and rejection messages are preserved,
so the router's 400 mapping is unchanged. It also extracts ``damage_type``,
``severity``, and the multi-label ``affected_areas`` the deterministic tools and
synthesis consume.
"""

import logging

from app.agents.prompts.claim_decision_questions import (
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
from app.constants.claims.claim_taxonomy import DamageType, SeverityLevel
from app.constants.claims.generic_area_alias_vocabulary import GENERIC_AREA_ALIASES
from app.constants.claims.overlapping_component_areas import (
    SPECIFIC_COMPONENT_AREA_BY_BROADER_AREA,
)
from app.constants.claims.surface_area_alias_vocabulary import SURFACE_AREA_ALIASES
from app.constants.intake.intake_validation_messages import (
    IMAGE_NOT_CLEAR_MESSAGE,
    MISSING_INPUT_MESSAGE,
    NOT_PROPERTY_DAMAGE_MESSAGE,
    OFFENSIVE_CONTENT_MESSAGE,
    PII_DETECTED_MESSAGE,
)
from app.llm.decision_model_client import (
    DecisionModelClient,
    choice_label,
    noul_answer_is_yes,
)

logger = logging.getLogger(__name__)

_TEXT_PART_TYPE = "text"
_IMAGE_URL_PART_TYPE = "image_url"
_TEXT_PART_TEXT_KEY = "text"
_IMAGE_URL_PART_URL_KEY = "url"

_DESCRIPTION_STATE_LABEL = "Claimant description"
_POLICY_TYPE_STATE_LABEL = "Policy type"
_DOCUMENT_TEXT_STATE_LABEL = "Supporting document text"
_NO_DESCRIPTION_PLACEHOLDER = "(none provided)"


async def decide_claim(
    client: DecisionModelClient, submission: ClaimSubmission
) -> ClaimDecisionOut:
    """Score the submission's intake and parameters in one Jev decision call."""
    if not submission.image_data_urls and not submission.description:
        return _missing_input_decision()

    state = _build_claim_state(submission)
    answers = await client.decide(state, CLAIM_DECISION_QUESTIONS)
    decision = ClaimDecisionOut(
        is_property_damage=noul_answer_is_yes(answers, IS_PROPERTY_DAMAGE_QUESTION_ID),
        is_valid_image=(
            noul_answer_is_yes(answers, IS_VALID_IMAGE_QUESTION_ID)
            if submission.image_data_urls
            else None
        ),
        no_pii_detected=noul_answer_is_yes(answers, NO_PII_DETECTED_QUESTION_ID),
        no_offensive_content=noul_answer_is_yes(answers, NO_OFFENSIVE_CONTENT_QUESTION_ID),
        damage_type=DamageType(
            choice_label(answers[DAMAGE_TYPE_QUESTION_ID], DAMAGE_TYPE_QUESTION_ID)
        ),
        severity=SeverityLevel(choice_label(answers[SEVERITY_QUESTION_ID], SEVERITY_QUESTION_ID)),
        affected_areas=_extract_affected_areas(answers),
    )
    logger.debug("Claim decision: %s", decision.model_dump())
    return decision


def claim_decision_passed(decision: ClaimDecisionOut) -> bool:
    """Whether the intake gates still let the claim proceed to triage."""
    return (
        decision.is_property_damage
        and decision.no_pii_detected
        and decision.no_offensive_content
        and decision.is_valid_image is not False
    )


def describe_claim_decision_failure(decision: ClaimDecisionOut, has_required_input: bool) -> str:
    """The fixed rejection message for the first intake gate the claim failed."""
    if not has_required_input:
        return MISSING_INPUT_MESSAGE
    if not decision.is_property_damage:
        return NOT_PROPERTY_DAMAGE_MESSAGE
    if decision.is_valid_image is False:
        return IMAGE_NOT_CLEAR_MESSAGE
    if not decision.no_pii_detected:
        return PII_DETECTED_MESSAGE
    return OFFENSIVE_CONTENT_MESSAGE


def _build_claim_state(submission: ClaimSubmission) -> list[dict]:
    state: list[dict] = [{"type": _TEXT_PART_TYPE, "text": _build_claim_state_text(submission)}]
    for image_data_url in submission.image_data_urls:
        state.append(
            {
                "type": _IMAGE_URL_PART_TYPE,
                "image_url": {_IMAGE_URL_PART_URL_KEY: image_data_url},
            }
        )
    return state


def _build_claim_state_text(submission: ClaimSubmission) -> str:
    lines = [
        f"{_DESCRIPTION_STATE_LABEL}: {submission.description or _NO_DESCRIPTION_PLACEHOLDER}",
        f"{_POLICY_TYPE_STATE_LABEL}: {submission.policy_type.value}",
    ]
    if submission.document_text:
        lines.append(f"{_DOCUMENT_TEXT_STATE_LABEL}: {submission.document_text}")
    return "\n".join(lines)


def _extract_affected_areas(answers: dict[str, dict]) -> list[str]:
    """Flagged areas, enforcing :data:`AREA_COUNTING_RULE` deterministically.

    Jev scores each area as an independent per-question probability with no
    visibility into the other areas' answers, so it cannot reliably avoid
    flagging an alias of an area that is already flagged, and every extra area
    multiplies the repair estimate. Three rules keep one entry per distinct area:

    - a broader component (``windows``) is dropped when its specific form
      (``rear_window``) is also flagged;
    - surface aliases (``wall``/``ceiling``) are dropped when any specific room
      or component is flagged;
    - generic aliases (``interior``/``exterior``) are dropped when any specific
      area or surface alias is flagged.

    The least specific tier is kept only when nothing more specific was flagged.
    """
    flagged = [
        area
        for area in AFFECTED_AREA_VOCABULARY
        if noul_answer_is_yes(answers, affected_area_question_id(area))
    ]
    flagged = [
        area for area in flagged if SPECIFIC_COMPONENT_AREA_BY_BROADER_AREA.get(area) not in flagged
    ]
    specific_areas = [
        area
        for area in flagged
        if area not in SURFACE_AREA_ALIASES and area not in GENERIC_AREA_ALIASES
    ]
    if specific_areas:
        return specific_areas
    surface_areas = [area for area in flagged if area in SURFACE_AREA_ALIASES]
    return surface_areas if surface_areas else flagged


def _missing_input_decision() -> ClaimDecisionOut:
    # No image and no description: no evidence to classify, so the claim fails the
    # property-damage gate before Jev is ever called (mirroring the retired
    # intake_validator's short-circuit). The parameter fields are never surfaced —
    # the router rejects this submission with a 400 — so they hold placeholders.
    return ClaimDecisionOut(
        is_property_damage=False,
        is_valid_image=None,
        no_pii_detected=True,
        no_offensive_content=True,
        damage_type=DamageType.OTHER,
        severity=SeverityLevel.MINOR,
        affected_areas=[],
    )
