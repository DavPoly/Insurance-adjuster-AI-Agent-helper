"""Fixture values for the node-1 (claim decision) tests.

``NOUL_ANSWER_FIELD`` / ``CHOICE_ANSWER_FIELD`` mirror the keys the real
Decisions API nests an answer under, and the ``*_PART_*`` keys mirror the
OpenAI-style state parts the API accepts. These are the wire format on purpose:
the tests assert the literal request shape, so reusing the node's private
field-name constants would make those assertions tautological.
"""

from app.constants.claims.claim_taxonomy import DamageType, PolicyType, SeverityLevel
from app.constants.decision.decision_model_config import DECISION_PROBABILITY_THRESHOLD

NOUL_ANSWER_FIELD = "noul"
CHOICE_ANSWER_FIELD = "choice"
QUESTION_TYPE_FIELD = "type"

TEXT_PART_TYPE = "text"
IMAGE_URL_PART_TYPE = "image_url"
TEXT_PART_TEXT_KEY = "text"
IMAGE_URL_PART_KEY = "image_url"
IMAGE_URL_PART_URL_KEY = "url"

FAKE_DESCRIPTION = "A burst pipe under the kitchen sink soaked the floor and lower cabinets."
FAKE_POLICY_TYPE = PolicyType.STANDARD_HOMEOWNER
FAKE_DOCUMENT_TEXT = "Inspection report: the water damage also reached the dining room ceiling."
FAKE_IMAGE_DATA_URL = "data:image/jpeg;base64,ZmFrZS1raXRjaGVuLXBob3Rv"
FAKE_SECOND_IMAGE_DATA_URL = "data:image/png;base64,ZmFrZS1zZWNvbmQtcGhvdG8="

FAKE_DAMAGE_TYPE = DamageType.WATER_DAMAGE
FAKE_SEVERITY = SeverityLevel.MODERATE
FAKE_AFFECTED_AREAS = ("kitchen", "dining_room")

PASSING_NOUL_PROBABILITY = 1.0
FAILING_NOUL_PROBABILITY = 0.0
# Keeps the "just below the threshold" case within float precision of the bound.
NEAR_THRESHOLD_STEP = 0.01
JUST_BELOW_THRESHOLD_PROBABILITY = DECISION_PROBABILITY_THRESHOLD - NEAR_THRESHOLD_STEP
