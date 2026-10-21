"""Jev ``questions`` for node 1, the combined intake-and-parameter decision.

One decision call answers, against a single multimodal state:

- four intake Nouls mirroring the four booleans of the response contract's
  ``IntakeValidation`` (the same fields the retired ``intake_validator`` produced),
- ``damage_type`` and ``severity`` as Choices over the shared taxonomy enums,
- one Noul per candidate room/component in
  :data:`~app.constants.claims.affected_area_vocabulary.AFFECTED_AREA_VOCABULARY`
  (Jev has no list primitive, so ``affected_areas`` is a multi-label Noul pass).

Every Noul is phrased so its "yes" answer means the flag holds; node 1 reads a
Noul probability at or above ``DECISION_PROBABILITY_THRESHOLD`` as yes. The
Choice criteria are derived from the enums programmatically rather than re-typed,
and the area questions carry :data:`AREA_COUNTING_RULE` and the severity question
carries :data:`SEVERITY_CLASSIFICATION_RUBRIC` so Jev applies the same rules the
old ReAct prompt did.
"""

from app.constants.claims.affected_area_vocabulary import AFFECTED_AREA_VOCABULARY
from app.constants.claims.area_counting_rule import AREA_COUNTING_RULE
from app.constants.claims.claim_taxonomy import DamageType, SeverityLevel
from app.constants.claims.severity_classification_rubric import SEVERITY_CLASSIFICATION_RUBRIC

NOUL_QUESTION_TYPE = "noul"
CHOICE_QUESTION_TYPE = "choice"

NOUL_YES_CRITERION = "true"
NOUL_NO_CRITERION = "false"

IS_PROPERTY_DAMAGE_QUESTION_ID = "is_property_damage"
IS_VALID_IMAGE_QUESTION_ID = "is_valid_image"
NO_PII_DETECTED_QUESTION_ID = "no_pii_detected"
NO_OFFENSIVE_CONTENT_QUESTION_ID = "no_offensive_content"
DAMAGE_TYPE_QUESTION_ID = "damage_type"
SEVERITY_QUESTION_ID = "severity"

AFFECTED_AREA_QUESTION_ID_PREFIX = "affected_area_"


def affected_area_question_id(area: str) -> str:
    """Jev question id for the "does the damage affect ``area``?" Noul."""
    return f"{AFFECTED_AREA_QUESTION_ID_PREFIX}{area}"


def _area_question(area: str) -> dict:
    area_label = area.replace("_", " ")
    return {
        "type": NOUL_QUESTION_TYPE,
        "instructions": (
            f"Does the evidence directly show or explicitly state that the {area_label} "
            f"itself is damaged? Require specific, direct evidence for this exact area — a "
            f"photo showing it, or text that names it as damaged — not mere proximity to, "
            f"or topical association with, another damaged area. If the {area_label} is not "
            f"mentioned or shown, or is described as dry or unaffected, answer no. "
            f"{AREA_COUNTING_RULE}"
        ),
        "criteria": {
            NOUL_YES_CRITERION: (
                f"The evidence directly shows or explicitly states that the {area_label} "
                f"itself is damaged."
            ),
            NOUL_NO_CRITERION: (
                f"The {area_label} is not mentioned or shown as damaged, or is explicitly "
                f"described as dry or unaffected."
            ),
        },
    }


CLAIM_DECISION_QUESTIONS: dict[str, dict] = {
    IS_PROPERTY_DAMAGE_QUESTION_ID: {
        "type": NOUL_QUESTION_TYPE,
        "instructions": (
            "Does the submission show property or structural damage to a building or its fixtures?"
        ),
        "criteria": {
            NOUL_YES_CRITERION: (
                "The submission shows damage to property, structure, or a fixture (e.g. "
                "water, fire, storm, break-in, or vandalism damage)."
            ),
            NOUL_NO_CRITERION: (
                "The submission does not show property or structural damage — it is a "
                "person, an animal, a document, a vehicle, or an unrelated scene."
            ),
        },
    },
    IS_VALID_IMAGE_QUESTION_ID: {
        "type": NOUL_QUESTION_TYPE,
        "instructions": (
            "Is the attached image clear and usable enough to assess property damage?"
        ),
        "criteria": {
            NOUL_YES_CRITERION: (
                "The image is a legible, in-focus photograph that shows the property and "
                "the damage clearly enough to assess."
            ),
            NOUL_NO_CRITERION: (
                "The image is blurred, underexposed, obstructed, or otherwise does not "
                "depict assessable property damage."
            ),
        },
    },
    NO_PII_DETECTED_QUESTION_ID: {
        "type": NOUL_QUESTION_TYPE,
        "instructions": (
            "Is the submission free of personal or financial information about an "
            "identifiable individual?"
        ),
        "criteria": {
            NOUL_YES_CRITERION: (
                "The submission contains no personal or financial information such as "
                "faces, government or account numbers, or documents with names and "
                "addresses."
            ),
            NOUL_NO_CRITERION: (
                "The submission contains personal or financial information about an "
                "identifiable individual."
            ),
        },
    },
    NO_OFFENSIVE_CONTENT_QUESTION_ID: {
        "type": NOUL_QUESTION_TYPE,
        "instructions": (
            "Is the submission free of offensive, inappropriate, or irrelevant content?"
        ),
        "criteria": {
            NOUL_YES_CRITERION: (
                "The submission is appropriate and relevant to a property damage claim."
            ),
            NOUL_NO_CRITERION: (
                "The submission contains offensive, inappropriate, or irrelevant content."
            ),
        },
    },
    DAMAGE_TYPE_QUESTION_ID: {
        "type": CHOICE_QUESTION_TYPE,
        "instructions": (
            "Classify the primary cause of the property damage into exactly one damage type."
        ),
        "criteria": {damage_type.value: damage_type.value for damage_type in DamageType},
    },
    SEVERITY_QUESTION_ID: {
        "type": CHOICE_QUESTION_TYPE,
        "instructions": (
            f"Classify the physical extent of the damage. {SEVERITY_CLASSIFICATION_RUBRIC}"
        ),
        "criteria": {severity.value: severity.value for severity in SeverityLevel},
    },
    **{affected_area_question_id(area): _area_question(area) for area in AFFECTED_AREA_VOCABULARY},
}
