"""Trace step labels for the deterministic pipeline's non-tool calls.

The three tool steps reuse :mod:`app.constants.agent.triage_tool_names`; these
label the two Jev decision calls and the single synthesis call so they render in
the agent trace with the same reason/act/observe schema as the tools.
"""

CLAIM_DECISION_STEP_NAME = "claim_decision"
TRIAGE_SYNTHESIS_STEP_NAME = "triage_synthesis"
OUTPUT_SAFETY_STEP_NAME = "output_safety"
