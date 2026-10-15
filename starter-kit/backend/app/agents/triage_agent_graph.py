import json
import logging
from datetime import datetime, timezone

from langchain_core.messages import ToolMessage
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langgraph.graph import END, StateGraph

from app.agents.schemas.triage_agent_state import TriageAgentState
from app.constants.agent.trace_metadata_keys import TRACED_AT_METADATA_KEY
from app.constants.agent.triage_agent_config import MAX_REACT_ITERATIONS

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_triage_agent_graph(
    llm_with_tools: Runnable,
    tools: list[BaseTool],
    max_iterations: int = MAX_REACT_ITERATIONS,
) -> Runnable:
    """Compiles the triage agent's 2-node ReAct loop."""
    tools_by_name = {tool.name: tool for tool in tools}

    def reason_act(state: TriageAgentState) -> dict:
        response = llm_with_tools.invoke(state["messages"])
        response.additional_kwargs[TRACED_AT_METADATA_KEY] = _now_iso()
        return {"messages": [response], "iteration_count": state["iteration_count"] + 1}

    def execute_tool(state: TriageAgentState) -> dict:
        last_message = state["messages"][-1]
        tool_messages = []
        for tool_call in last_message.tool_calls:
            tool = tools_by_name.get(tool_call["name"])
            if tool is None:
                result = {"error": f"Unknown tool {tool_call['name']!r}"}
            else:
                try:
                    result = tool.invoke(tool_call["args"])
                except Exception as exc:
                    logger.warning("Tool %s failed: %s", tool_call["name"], exc)
                    result = {"error": str(exc)}
            tool_messages.append(
                ToolMessage(
                    content=json.dumps(result),
                    tool_call_id=tool_call["id"],
                    name=tool_call["name"],
                    additional_kwargs={TRACED_AT_METADATA_KEY: _now_iso()},
                )
            )
        return {"messages": tool_messages}

    def route_after_reason_act(state: TriageAgentState) -> str:
        last_message = state["messages"][-1]
        if not getattr(last_message, "tool_calls", None):
            return END
        if state["iteration_count"] >= max_iterations:
            logger.warning("Triage agent hit max_iterations=%d; stopping.", max_iterations)
            return END
        return "execute_tool"

    graph = StateGraph(TriageAgentState)
    graph.add_node("reason_act", reason_act)
    graph.add_node("execute_tool", execute_tool)
    graph.set_entry_point("reason_act")
    graph.add_conditional_edges(
        "reason_act", route_after_reason_act, {"execute_tool": "execute_tool", END: END}
    )
    graph.add_edge("execute_tool", "reason_act")
    return graph.compile()
