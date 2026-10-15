"""Fixture values for the node-4 output safety decision tests.

``NOUL_ANSWER_FIELD`` mirrors the key the real Decisions API nests a Noul
probability under, so the fake client returns answers shaped like
``DecisionModelClient.decide``'s return value.
"""

from app.constants.decision.decision_model_config import DECISION_PROBABILITY_THRESHOLD

NOUL_ANSWER_FIELD = "noul"

FAKE_DAMAGE_DESCRIPTION = "Moderate water damage across the kitchen floor and lower cabinets."
FAKE_RECOMMENDATION = "Dispatch a water mitigation contractor within 24 hours."

PASSING_NOUL_PROBABILITY = 1.0
FAILING_NOUL_PROBABILITY = 0.0
# Keeps the "just below the threshold" case within float precision of the bound.
NEAR_THRESHOLD_STEP = 0.01
JUST_BELOW_THRESHOLD_PROBABILITY = DECISION_PROBABILITY_THRESHOLD - NEAR_THRESHOLD_STEP
