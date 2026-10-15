import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from app.agents.utils.triage_agent_trace import build_trace_steps
from app.constants.agent.agent_trace_step_types import (
    ACT_STEP_TYPE,
    OBSERVE_STEP_TYPE,
    REASON_STEP_TYPE,
)
from app.constants.agent.trace_metadata_keys import TRACED_AT_METADATA_KEY

FAKE_TOOL_NAME = "fake_tool"
FAKE_TOOL_CALL_ID = "call-1"
FAKE_TOOL_RESULT = {"echoed": "hi"}
FAKE_TRACED_AT = "2026-01-01T00:00:00+00:00"


def _ai_message_with_tool_call() -> AIMessage:
    return AIMessage(
        content="Looking something up.",
        tool_calls=[{"name": FAKE_TOOL_NAME, "args": {"value": "hi"}, "id": FAKE_TOOL_CALL_ID}],
        additional_kwargs={TRACED_AT_METADATA_KEY: FAKE_TRACED_AT},
    )


def _tool_message() -> ToolMessage:
    return ToolMessage(
        content=json.dumps(FAKE_TOOL_RESULT),
        tool_call_id=FAKE_TOOL_CALL_ID,
        name=FAKE_TOOL_NAME,
        additional_kwargs={TRACED_AT_METADATA_KEY: FAKE_TRACED_AT},
    )


def _final_ai_message() -> AIMessage:
    return AIMessage(
        content="Ready to finalize.",
        additional_kwargs={TRACED_AT_METADATA_KEY: FAKE_TRACED_AT},
    )


def test_build_trace_steps_emits_a_paired_reason_act_observe_sequence():
    messages = [
        SystemMessage(content="system prompt"),
        HumanMessage(content="claim text"),
        _ai_message_with_tool_call(),
        _tool_message(),
        _final_ai_message(),
    ]

    steps = build_trace_steps(messages)

    assert [step["type"] for step in steps] == [
        REASON_STEP_TYPE,
        ACT_STEP_TYPE,
        OBSERVE_STEP_TYPE,
        REASON_STEP_TYPE,
    ]
    assert [step["step_number"] for step in steps] == [1, 2, 3, 4]

    reason_step, act_step, observe_step, final_reason_step = steps
    assert reason_step["content"] == "Looking something up."
    assert "tool_name" not in reason_step
    assert "tool_output" not in reason_step

    assert act_step["tool_name"] == FAKE_TOOL_NAME
    assert act_step["tool_input"] == {"value": "hi"}
    assert "tool_output" not in act_step

    assert observe_step["tool_output"] == FAKE_TOOL_RESULT
    assert "tool_name" not in observe_step
    assert "tool_input" not in observe_step

    assert final_reason_step["content"] == "Ready to finalize."


def test_build_trace_steps_skips_an_unexecuted_tool_call_left_by_the_iteration_cap():
    messages = [
        HumanMessage(content="claim text"),
        _ai_message_with_tool_call(),
        # No matching ToolMessage: the loop hit max_iterations before executing it.
    ]

    steps = build_trace_steps(messages)

    assert [step["type"] for step in steps] == [REASON_STEP_TYPE]
