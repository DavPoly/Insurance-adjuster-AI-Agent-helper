"""Configuration for the Jev decision model served through OpenRouter's
Decisions API. The decision nodes reuse the existing OpenRouter API key, so no
new credential is introduced here.
"""

DECISION_MODEL_DEFAULT = "typesafe/jev-1.14"
DECISION_ENDPOINT_DEFAULT = "https://openrouter.ai/api/alpha/decisions"
# Image-carrying requests run in Jev's long-context mode and can take a while.
DECISION_REQUEST_TIMEOUT_SECONDS = 120.0
# Noul probabilities at or above this threshold read as "yes".
DECISION_PROBABILITY_THRESHOLD = 0.5
