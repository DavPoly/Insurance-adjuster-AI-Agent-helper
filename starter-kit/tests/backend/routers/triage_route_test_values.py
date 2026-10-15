"""Fixture values for the triage router tests.

The fake decision client classifies every claim as the same water-damage claim,
so the echoing description, the synthesized free text, and the sample inspection
document used to exercise PDF threading all live here rather than inline in the
test bodies.
"""

UNKNOWN_CLAIM_ID = "triage-unknown-claim-id"

FAKE_CLAIM_DESCRIPTION = "Water is pooling under my kitchen sink."

FAKE_SYNTHESIZED_DAMAGE_DESCRIPTION = "Minor water damage under the kitchen sink."
FAKE_SYNTHESIZED_RECOMMENDATION = "Dispatch an adjuster to confirm scope."

INSPECTION_DOCUMENT_FILENAME = "IMG_001-inspection.pdf"
INSPECTION_DOCUMENT_CONTENT_TYPE = "application/pdf"
# A contiguous phrase from the fixture PDF, chosen so the assertion proves the
# extracted text actually reached node 1 rather than trusting a tautological
# re-extraction inside the test.
INSPECTION_DOCUMENT_TEXT_EXCERPT = "moderate water damage in exactly two rooms"
