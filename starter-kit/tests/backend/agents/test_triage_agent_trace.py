from deterministic_trace_test_fixtures import (
    FAKE_DETERMINISTIC_ACT_CONTENT,
    FAKE_DETERMINISTIC_OBSERVE_CONTENT,
    FAKE_DETERMINISTIC_REASON_CONTENT,
    FAKE_DETERMINISTIC_TOOL_INPUT,
    FAKE_DETERMINISTIC_TOOL_NAME,
    FAKE_DETERMINISTIC_TOOL_OUTPUT,
    FAKE_DETERMINISTIC_TRACED_AT,
)

from app.agents.utils.triage_agent_trace import (
    DeterministicStepRecord,
    build_deterministic_trace_steps,
)
from app.constants.agent.agent_trace_step_types import (
    ACT_STEP_TYPE,
    OBSERVE_STEP_TYPE,
    REASON_STEP_TYPE,
)


def _deterministic_record(step_type: str, content: str, **overrides) -> DeterministicStepRecord:
    values: dict = {
        "step_type": step_type,
        "content": content,
        "recorded_at": FAKE_DETERMINISTIC_TRACED_AT,
    }
    values.update(overrides)
    return DeterministicStepRecord(**values)


def test_build_deterministic_trace_steps_renders_reason_act_observe_with_their_fields():
    records = [
        _deterministic_record(REASON_STEP_TYPE, FAKE_DETERMINISTIC_REASON_CONTENT),
        _deterministic_record(
            ACT_STEP_TYPE,
            FAKE_DETERMINISTIC_ACT_CONTENT,
            tool_name=FAKE_DETERMINISTIC_TOOL_NAME,
            tool_input=FAKE_DETERMINISTIC_TOOL_INPUT,
        ),
        _deterministic_record(
            OBSERVE_STEP_TYPE,
            FAKE_DETERMINISTIC_OBSERVE_CONTENT,
            tool_output=FAKE_DETERMINISTIC_TOOL_OUTPUT,
        ),
    ]

    steps = build_deterministic_trace_steps(records)

    assert [step["type"] for step in steps] == [
        REASON_STEP_TYPE,
        ACT_STEP_TYPE,
        OBSERVE_STEP_TYPE,
    ]
    assert [step["step_number"] for step in steps] == [1, 2, 3]
    assert [step["timestamp"] for step in steps] == [FAKE_DETERMINISTIC_TRACED_AT] * 3

    reason_step, act_step, observe_step = steps
    assert reason_step["content"] == FAKE_DETERMINISTIC_REASON_CONTENT
    assert "tool_name" not in reason_step
    assert "tool_input" not in reason_step
    assert "tool_output" not in reason_step

    assert act_step["content"] == FAKE_DETERMINISTIC_ACT_CONTENT
    assert act_step["tool_name"] == FAKE_DETERMINISTIC_TOOL_NAME
    assert act_step["tool_input"] == FAKE_DETERMINISTIC_TOOL_INPUT
    assert "tool_output" not in act_step

    assert observe_step["content"] == FAKE_DETERMINISTIC_OBSERVE_CONTENT
    assert observe_step["tool_output"] == FAKE_DETERMINISTIC_TOOL_OUTPUT
    assert "tool_name" not in observe_step
    assert "tool_input" not in observe_step


def test_build_deterministic_trace_steps_returns_no_steps_for_an_empty_run():
    assert build_deterministic_trace_steps([]) == []
