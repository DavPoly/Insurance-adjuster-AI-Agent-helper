import json

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, ToolMessage

from app.agents.prompts.triage_synthesis_prompt import TRIAGE_SYNTHESIS_SYSTEM_PROMPT
from app.agents.schemas.triage_assessment_schema import TriageAssessmentOut
from app.constants.agent.triage_tool_names import (
    ESTIMATE_REPAIR_COST_TOOL_NAME,
    SEARCH_PAST_CLAIMS_TOOL_NAME,
)
from app.constants.tools.cost_estimate_currency import DEFAULT_CURRENCY


def synthesize_triage_assessment(llm: BaseChatModel, messages: list[BaseMessage]) -> dict:
    """One LLM call over the full ReAct trace that writes the final triage report."""
    synthesis_messages = [
        SystemMessage(content=TRIAGE_SYNTHESIS_SYSTEM_PROMPT),
        *messages[1:],
    ]
    structured_llm = llm.with_structured_output(TriageAssessmentOut)
    draft: TriageAssessmentOut = structured_llm.invoke(synthesis_messages)
    assessment = draft.model_dump(mode="json")

    repair_cost_call = _last_tool_call(messages, ESTIMATE_REPAIR_COST_TOOL_NAME)
    if repair_cost_call is not None:
        arguments, observation = repair_cost_call
        assessment["damage_type"] = arguments["damage_type"]
        assessment["severity"] = arguments["severity"]
        assessment["affected_areas"] = arguments["affected_areas"]
        assessment["estimated_repair_cost"] = observation

    past_claims_observation = _last_tool_observation(messages, SEARCH_PAST_CLAIMS_TOOL_NAME)
    if past_claims_observation is not None:
        assessment["similar_past_claims"] = _apply_verbatim_past_claims(
            past_claims_observation, draft.similar_past_claims
        )

    return assessment


def _last_tool_observation(messages: list[BaseMessage], tool_name: str):
    for message in reversed(messages):
        if isinstance(message, ToolMessage) and message.name == tool_name:
            return json.loads(message.content)
    return None


def _last_tool_call(messages: list[BaseMessage], tool_name: str):
    tool_messages_by_call_id = {
        message.tool_call_id: message for message in messages if isinstance(message, ToolMessage)
    }
    for message in reversed(messages):
        if not isinstance(message, AIMessage):
            continue
        for tool_call in reversed(message.tool_calls):
            if tool_call["name"] != tool_name:
                continue
            tool_message = tool_messages_by_call_id.get(tool_call["id"])
            if tool_message is None:
                continue
            return tool_call["args"], json.loads(tool_message.content)
    return None


def _apply_verbatim_past_claims(raw_records: list[dict], drafted_claims: list) -> list[dict]:
    drafted_summary_by_claim_id = {
        claim.claim_id: claim.resolution_summary for claim in drafted_claims
    }
    return [
        {
            "claim_id": record["claim_id"],
            "similarity_score": record["similarity_score"],
            "resolution_summary": drafted_summary_by_claim_id.get(
                record["claim_id"], _fallback_resolution_summary(record)
            ),
        }
        for record in raw_records
    ]


def _fallback_resolution_summary(record: dict) -> str:
    resolution = record["resolution"].replace("_", " ")
    return (
        f"Resolved as {resolution}, with an actual repair cost of "
        f"{record['repair_cost_actual']} {DEFAULT_CURRENCY}."
    )
