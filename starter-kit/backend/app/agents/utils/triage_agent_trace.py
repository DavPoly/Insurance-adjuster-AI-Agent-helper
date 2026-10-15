import json
from dataclasses import dataclass

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

from app.constants.agent.agent_trace_step_types import (
    ACT_STEP_TYPE,
    OBSERVE_STEP_TYPE,
    REASON_STEP_TYPE,
)
from app.constants.agent.trace_metadata_keys import TRACED_AT_METADATA_KEY


@dataclass(frozen=True)
class DeterministicStepRecord:
    """One ordered step of a deterministic triage run, before numbering.

    The deterministic orchestrator fills these in as it walks the fixed
    pipeline, so the trace can be reconstructed without any ReAct message
    history. ``tool_name``/``tool_input``/``tool_output`` mirror the fields the
    message-based builder attaches to its act/observe steps.
    """

    step_type: str
    content: str
    recorded_at: str
    tool_name: str | None = None
    tool_input: dict | None = None
    tool_output: object = None


def build_deterministic_trace_steps(records: list[DeterministicStepRecord]) -> list[dict]:
    """Builds AgentTrace-shaped steps from a deterministic run's step records."""
    steps: list[dict] = []
    for index, record in enumerate(records, start=1):
        step: dict = {
            "type": record.step_type,
            "content": record.content,
            "timestamp": record.recorded_at,
        }
        if record.tool_name is not None:
            step["tool_name"] = record.tool_name
        if record.tool_input is not None:
            step["tool_input"] = record.tool_input
        if record.tool_output is not None:
            step["tool_output"] = record.tool_output
        step["step_number"] = index
        steps.append(step)
    return steps


def build_trace_steps(messages: list[BaseMessage]) -> list[dict]:
    """Builds AgentTrace-shaped steps from the triage agent's message history."""
    tool_messages_by_call_id = {
        message.tool_call_id: message for message in messages if isinstance(message, ToolMessage)
    }

    steps: list[dict] = []
    for message in messages:
        if not isinstance(message, AIMessage):
            continue

        if message.content:
            steps.append(_build_step(REASON_STEP_TYPE, message.content, message))

        for tool_call in message.tool_calls:
            tool_message = tool_messages_by_call_id.get(tool_call["id"])
            if tool_message is None:
                continue

            steps.append(
                _build_step(
                    ACT_STEP_TYPE,
                    f"Calling {tool_call['name']}",
                    message,
                    tool_name=tool_call["name"],
                    tool_input=tool_call["args"],
                )
            )
            steps.append(
                _build_step(
                    OBSERVE_STEP_TYPE,
                    tool_message.content,
                    tool_message,
                    tool_output=json.loads(tool_message.content),
                )
            )

    for index, step in enumerate(steps, start=1):
        step["step_number"] = index
    return steps


def _build_step(
    step_type: str,
    content: str,
    source_message: BaseMessage,
    tool_name: str | None = None,
    tool_input: dict | None = None,
    tool_output: object = None,
) -> dict:
    step = {
        "type": step_type,
        "content": content,
        "timestamp": source_message.additional_kwargs[TRACED_AT_METADATA_KEY],
    }
    if tool_name is not None:
        step["tool_name"] = tool_name
    if tool_input is not None:
        step["tool_input"] = tool_input
    if tool_output is not None:
        step["tool_output"] = tool_output
    return step
