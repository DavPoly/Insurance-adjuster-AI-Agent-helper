"""Field names of the synthesized triage assessment's free-text parts.

Both the deterministic orchestrator and the triage router read these two fields
to feed the node-4 output safety check (and the router again on a safety retry),
so their names live in one place instead of a private pair in each module.
"""

DAMAGE_DESCRIPTION_FIELD = "damage_description"
RECOMMENDATION_FIELD = "recommendation"
