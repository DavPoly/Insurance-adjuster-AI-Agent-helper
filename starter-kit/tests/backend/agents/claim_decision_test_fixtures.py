"""Fixture values for the node-1 (claim decision) tests.

The answer wire constants live in ``fake_decision_model_client``; this module
holds the canned submission/decision values and the OpenAI-style state-part
keys. The ``*_PART_*`` keys mirror the state parts the Decisions API accepts and
are wire format on purpose, so the tests assert the literal request shape rather
than reusing the node's private field-name constants.
"""

from app.constants.claims.claim_taxonomy import DamageType, PolicyType, SeverityLevel

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
