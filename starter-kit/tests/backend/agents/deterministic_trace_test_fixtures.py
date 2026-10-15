"""Fixture values for the deterministic trace-builder tests.

Kept separate from the message-based cases in test_triage_agent_trace.py so the
two builders' fixtures do not collide while both live in the trace module.
"""

FAKE_DETERMINISTIC_TRACED_AT = "2026-02-02T00:00:00+00:00"
FAKE_DETERMINISTIC_REASON_CONTENT = "Deciding which deterministic step to run next."
FAKE_DETERMINISTIC_ACT_CONTENT = "Calling fake_tool"
FAKE_DETERMINISTIC_OBSERVE_CONTENT = '{"echoed": "hi"}'
FAKE_DETERMINISTIC_TOOL_NAME = "fake_tool"
FAKE_DETERMINISTIC_TOOL_INPUT = {"value": "hi"}
FAKE_DETERMINISTIC_TOOL_OUTPUT = {"echoed": "hi"}
