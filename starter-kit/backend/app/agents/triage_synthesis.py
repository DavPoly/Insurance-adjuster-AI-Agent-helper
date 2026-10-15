"""Synthesis seam: one LLM call over the explicit classification and tool results.

The deterministic orchestrator passes node 1's classification and the three
deterministic tool results explicitly instead of a ReAct message history. This
module renders that input for the single structured-output call and then stitches
the deterministic fields (``damage_type`` / ``severity`` / ``affected_areas``,
cost, and past claims) verbatim over the LLM's free text.
"""

import json
from dataclasses import dataclass

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.prompts.triage_synthesis_prompt import TRIAGE_SYNTHESIS_SYSTEM_PROMPT
from app.agents.schemas.claim_decision_schema import ClaimDecisionOut
from app.agents.schemas.triage_assessment_schema import TriageAssessmentOut
from app.constants.agent.triage_tool_names import (
    CHECK_COVERAGE_TOOL_NAME,
    ESTIMATE_REPAIR_COST_TOOL_NAME,
    SEARCH_PAST_CLAIMS_TOOL_NAME,
)
from app.constants.tools.cost_estimate_currency import DEFAULT_CURRENCY

_CLASSIFICATION_CONTEXT_KEY = "claim_classification"


@dataclass(frozen=True)
class SynthesisToolResults:
    """The deterministic tool outputs the synthesis call grounds and stitches.

    ``repair_cost_estimate`` is ``estimate_repair_cost``'s result,
    ``similar_past_claims`` is ``search_past_claims``'s ordered result list, and
    ``coverage`` is ``check_coverage``'s result.
    """

    repair_cost_estimate: dict
    similar_past_claims: list[dict]
    coverage: dict


def synthesize_triage_assessment(
    llm: BaseChatModel,
    classification: ClaimDecisionOut,
    tool_results: SynthesisToolResults,
) -> dict:
    """One LLM call over the explicit classification and tool results."""
    structured_llm = llm.with_structured_output(TriageAssessmentOut)
    draft: TriageAssessmentOut = structured_llm.invoke(
        [
            SystemMessage(content=TRIAGE_SYNTHESIS_SYSTEM_PROMPT),
            HumanMessage(content=_render_synthesis_input(classification, tool_results)),
        ]
    )
    assessment = draft.model_dump(mode="json")

    assessment["damage_type"] = classification.damage_type.value
    assessment["severity"] = classification.severity.value
    assessment["affected_areas"] = list(classification.affected_areas)
    assessment["estimated_repair_cost"] = tool_results.repair_cost_estimate
    assessment["similar_past_claims"] = _apply_verbatim_past_claims(
        tool_results.similar_past_claims, draft.similar_past_claims
    )

    return assessment


def _render_synthesis_input(
    classification: ClaimDecisionOut, tool_results: SynthesisToolResults
) -> str:
    """Render the explicit inputs as the single synthesis message the LLM reads."""
    return json.dumps(
        {
            _CLASSIFICATION_CONTEXT_KEY: classification.model_dump(mode="json"),
            ESTIMATE_REPAIR_COST_TOOL_NAME: tool_results.repair_cost_estimate,
            SEARCH_PAST_CLAIMS_TOOL_NAME: tool_results.similar_past_claims,
            CHECK_COVERAGE_TOOL_NAME: tool_results.coverage,
        },
        indent=2,
    )


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
