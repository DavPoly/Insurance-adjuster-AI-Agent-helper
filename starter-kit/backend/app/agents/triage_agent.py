from dataclasses import dataclass

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from qdrant_client import QdrantClient

from app.agents.schemas.claim_submission import ClaimSubmission
from app.agents.triage_agent_graph import build_triage_agent_graph
from app.agents.triage_synthesis import synthesize_triage_assessment
from app.agents.utils.claim_messages import build_initial_messages
from app.agents.utils.triage_agent_tools import build_triage_agent_tools
from app.agents.utils.triage_agent_trace import build_trace_steps
from app.rag.embedder import ClaimEmbedder


@dataclass
class TriageAgentResult:
    triage_assessment: dict
    trace_steps: list[dict]
    messages: list[BaseMessage]


def run_triage_agent(
    submission: ClaimSubmission,
    llm: BaseChatModel,
    client: QdrantClient,
    embedder: ClaimEmbedder,
    cost_table: dict,
    coverage_table: dict,
) -> TriageAgentResult:

    tools = build_triage_agent_tools(client, embedder, cost_table, coverage_table)
    graph = build_triage_agent_graph(llm.bind_tools(tools), tools)

    final_state = graph.invoke(
        {"messages": build_initial_messages(submission), "iteration_count": 0}
    )

    trace_steps = build_trace_steps(final_state["messages"])
    triage_assessment = synthesize_triage_assessment(llm, final_state["messages"])
    return TriageAgentResult(
        triage_assessment=triage_assessment,
        trace_steps=trace_steps,
        messages=final_state["messages"],
    )
