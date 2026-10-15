import json

from fake_triage_chat_model import FakeTriageChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import StructuredTool
from pydantic import BaseModel

from app.agents.triage_agent_graph import build_triage_agent_graph

FAKE_TOOL_NAME = "fake_tool"
MAX_ITERATIONS_FOR_CAP_TEST = 3


class _FakeToolInput(BaseModel):
    value: str


def _build_fake_tool(fail: bool = False) -> StructuredTool:
    def _run(value: str) -> dict:
        if fail:
            raise ValueError(f"boom: {value}")
        return {"echoed": value}

    return StructuredTool.from_function(
        func=_run, name=FAKE_TOOL_NAME, description="test tool", args_schema=_FakeToolInput
    )


def _tool_call_message(content: str, call_id: str) -> AIMessage:
    return AIMessage(
        content=content,
        tool_calls=[{"name": FAKE_TOOL_NAME, "args": {"value": call_id}, "id": call_id}],
    )


def test_triage_agent_graph_runs_one_tool_call_then_stops():
    tool = _build_fake_tool()
    llm = FakeTriageChatModel(
        tool_loop_responses=[
            _tool_call_message("Looking something up.", "call-1"),
            AIMessage(content="Ready to finalize."),
        ]
    )
    graph = build_triage_agent_graph(llm, [tool])

    final_state = graph.invoke({"messages": [], "iteration_count": 0})

    assert final_state["iteration_count"] == 2
    assert len(final_state["messages"]) == 3
    tool_message = final_state["messages"][1]
    assert tool_message.name == FAKE_TOOL_NAME
    assert json.loads(tool_message.content) == {"echoed": "call-1"}


def test_triage_agent_graph_tool_error_becomes_observation_not_a_crash():
    tool = _build_fake_tool(fail=True)
    llm = FakeTriageChatModel(
        tool_loop_responses=[
            _tool_call_message("Trying something.", "call-1"),
            AIMessage(content="Giving up, ready to finalize."),
        ]
    )
    graph = build_triage_agent_graph(llm, [tool])

    final_state = graph.invoke({"messages": [], "iteration_count": 0})

    tool_message = final_state["messages"][1]
    assert json.loads(tool_message.content) == {"error": "boom: call-1"}


def test_triage_agent_graph_stops_at_max_iterations():
    tool = _build_fake_tool()
    responses = [
        _tool_call_message("Still looking.", f"call-{index}")
        for index in range(MAX_ITERATIONS_FOR_CAP_TEST + 2)
    ]
    llm = FakeTriageChatModel(tool_loop_responses=responses)
    graph = build_triage_agent_graph(llm, [tool], max_iterations=MAX_ITERATIONS_FOR_CAP_TEST)

    final_state = graph.invoke({"messages": [], "iteration_count": 0})

    assert final_state["iteration_count"] == MAX_ITERATIONS_FOR_CAP_TEST
