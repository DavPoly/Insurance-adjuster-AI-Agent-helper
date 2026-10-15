"""Deterministic triage orchestrator — the Jev successor to the ReAct agent.

Runs the fixed five-stage pipeline with no model in the control loop:

1. node 1 (intake + parameter extraction) is already resolved upstream and
   threaded in as a :class:`ClaimDecisionOut`, so it is never re-called here;
2. the three deterministic tools (past-claim search, cost estimate, coverage
   check) are invoked directly, never through a tool-binding model;
3. a single generative LLM call writes the draft report;
4. node 4 scores that draft for output safety.

Every step is recorded as a :class:`DeterministicStepRecord` so the trace
endpoint can rebuild the reason/act/observe history from the pipeline itself
rather than from any ReAct message list. The bounded safety retry lives in the
router: it reuses the first pass's ``safety_checks`` and, on failure, re-runs
synthesis over the carried ``synthesis_messages`` before re-checking safety.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from qdrant_client import QdrantClient

from app.agents.prompts.triage_synthesis_prompt import TRIAGE_SYNTHESIS_SYSTEM_PROMPT
from app.agents.safety_decision import check_output_safety
from app.agents.schemas.claim_decision_schema import ClaimDecisionOut
from app.agents.schemas.claim_submission import ClaimSubmission
from app.agents.schemas.safety_checks_schema import SafetyChecksOut
from app.agents.triage_synthesis import synthesize_triage_assessment
from app.agents.utils.triage_agent_trace import (
    DeterministicStepRecord,
    build_deterministic_trace_steps,
)
from app.constants.agent.agent_trace_step_types import (
    ACT_STEP_TYPE,
    OBSERVE_STEP_TYPE,
    REASON_STEP_TYPE,
)
from app.constants.agent.deterministic_pipeline_step_names import (
    CLAIM_DECISION_STEP_NAME,
    OUTPUT_SAFETY_STEP_NAME,
    TRIAGE_SYNTHESIS_STEP_NAME,
)
from app.constants.agent.triage_tool_names import (
    CHECK_COVERAGE_TOOL_NAME,
    ESTIMATE_REPAIR_COST_TOOL_NAME,
    SEARCH_PAST_CLAIMS_TOOL_NAME,
)
from app.llm.decision_model_client import DecisionModelClient
from app.rag.embedder import ClaimEmbedder
from app.tools.claim_search import search_past_claims
from app.tools.cost_estimator import estimate_repair_cost
from app.tools.coverage_checker import check_coverage

logger = logging.getLogger(__name__)

_ACT_CONTENT_TEMPLATE = "Calling {name}"

_CLAIM_DECISION_REASON = (
    "Reviewing the claim for intake validity and extracting the damage parameters."
)
_SEARCH_PAST_CLAIMS_REASON = "Searching the historical claims for similar incidents."
_ESTIMATE_REPAIR_COST_REASON = "Estimating the repair cost from the extracted damage parameters."
_CHECK_COVERAGE_REASON = "Checking the policy's coverage for the incident category."
_TRIAGE_SYNTHESIS_REASON = "Drafting the structured triage report from the tool results."
_OUTPUT_SAFETY_REASON = "Reviewing the draft against the output safety checks."

_DAMAGE_TYPE_INPUT_KEY = "damage_type"
_SEVERITY_INPUT_KEY = "severity"
_AFFECTED_AREAS_INPUT_KEY = "affected_areas"
_SEARCH_QUERY_INPUT_KEY = "query"
_POLICY_TYPE_INPUT_KEY = "policy_type"
_INCIDENT_CATEGORY_INPUT_KEY = "incident_category"

_DAMAGE_DESCRIPTION_KEY = "damage_description"
_RECOMMENDATION_KEY = "recommendation"

_ESTIMATE_REPAIR_COST_TOOL_CALL_ID = "estimate_repair_cost_call"
_SEARCH_PAST_CLAIMS_TOOL_CALL_ID = "search_past_claims_call"
_CHECK_COVERAGE_TOOL_CALL_ID = "check_coverage_call"

_POLICY_TYPE_CONTEXT_LABEL = "Policy type"
_DESCRIPTION_CONTEXT_LABEL = "Claimant description"
_DOCUMENT_TEXT_CONTEXT_LABEL = "Supporting document text"
_DAMAGE_TYPE_CONTEXT_LABEL = "Extracted damage type"
_SEVERITY_CONTEXT_LABEL = "Extracted severity"
_AFFECTED_AREAS_CONTEXT_LABEL = "Extracted affected areas"
_NO_DESCRIPTION_PLACEHOLDER = "(none provided)"
_NO_AFFECTED_AREAS_PLACEHOLDER = "(none detected)"


@dataclass
class DeterministicTriageResult:
    """Everything the triage route consumes from one deterministic run.

    ``synthesis_messages`` carries the inline-built synthesis input so the
    router's bounded safety retry can regenerate the draft without rerunning the
    deterministic tools — the analogue of the retired agent's ``messages``.
    """

    triage_assessment: dict
    safety_checks: SafetyChecksOut
    trace_steps: list[dict]
    synthesis_messages: list[BaseMessage]


async def run_deterministic_triage(
    submission: ClaimSubmission,
    claim_decision: ClaimDecisionOut,
    llm: BaseChatModel,
    decision_client: DecisionModelClient,
    client: QdrantClient,
    embedder: ClaimEmbedder,
    cost_table: dict,
    coverage_table: dict,
) -> DeterministicTriageResult:
    """Run the fixed tools → synthesis → safety pipeline for one claim."""
    past_claims = search_past_claims(submission.description, client, embedder)
    repair_cost_estimate = estimate_repair_cost(
        claim_decision.damage_type.value,
        claim_decision.severity.value,
        claim_decision.affected_areas,
        cost_table,
    )
    coverage = check_coverage(
        submission.policy_type.value,
        claim_decision.damage_type.value,
        coverage_table,
    )
    logger.info(
        "Deterministic triage: damage_type=%s severity=%s area_count=%d "
        "similar_claims=%d covered=%s",
        claim_decision.damage_type.value,
        claim_decision.severity.value,
        len(claim_decision.affected_areas),
        len(past_claims),
        coverage["covered"],
    )

    synthesis_messages = _build_synthesis_messages(
        submission, claim_decision, repair_cost_estimate, past_claims, coverage
    )
    triage_assessment = synthesize_triage_assessment(llm, synthesis_messages)

    safety_checks = await check_output_safety(
        decision_client,
        triage_assessment[_DAMAGE_DESCRIPTION_KEY],
        triage_assessment[_RECOMMENDATION_KEY],
    )
    logger.info(
        "Deterministic triage: safety_checks_passed=%s", safety_checks_passed(safety_checks)
    )

    trace_steps = build_deterministic_trace_steps(
        _build_trace_records(
            submission,
            claim_decision,
            repair_cost_estimate,
            past_claims,
            coverage,
            triage_assessment,
            safety_checks,
        )
    )
    return DeterministicTriageResult(
        triage_assessment=triage_assessment,
        safety_checks=safety_checks,
        trace_steps=trace_steps,
        synthesis_messages=synthesis_messages,
    )


def safety_checks_passed(safety_checks: SafetyChecksOut) -> bool:
    """Whether every output safety check holds (mirrors ``SafetyChecksOut``)."""
    return all(safety_checks.model_dump().values())


def _build_trace_records(
    submission: ClaimSubmission,
    claim_decision: ClaimDecisionOut,
    repair_cost_estimate: dict,
    past_claims: list[dict],
    coverage: dict,
    triage_assessment: dict,
    safety_checks: SafetyChecksOut,
) -> list[DeterministicStepRecord]:
    return [
        _reason_record(_CLAIM_DECISION_REASON),
        _act_record(CLAIM_DECISION_STEP_NAME),
        _observe_record(claim_decision.model_dump(mode="json")),
        _reason_record(_SEARCH_PAST_CLAIMS_REASON),
        _act_record(
            SEARCH_PAST_CLAIMS_TOOL_NAME, {_SEARCH_QUERY_INPUT_KEY: submission.description}
        ),
        _observe_record(past_claims),
        _reason_record(_ESTIMATE_REPAIR_COST_REASON),
        _act_record(
            ESTIMATE_REPAIR_COST_TOOL_NAME, _estimate_repair_cost_arguments(claim_decision)
        ),
        _observe_record(repair_cost_estimate),
        _reason_record(_CHECK_COVERAGE_REASON),
        _act_record(
            CHECK_COVERAGE_TOOL_NAME, _check_coverage_arguments(submission, claim_decision)
        ),
        _observe_record(coverage),
        _reason_record(_TRIAGE_SYNTHESIS_REASON),
        _act_record(TRIAGE_SYNTHESIS_STEP_NAME),
        _observe_record(triage_assessment),
        _reason_record(_OUTPUT_SAFETY_REASON),
        _act_record(OUTPUT_SAFETY_STEP_NAME),
        _observe_record(safety_checks.model_dump()),
    ]


def _build_synthesis_messages(
    submission: ClaimSubmission,
    claim_decision: ClaimDecisionOut,
    repair_cost_estimate: dict,
    past_claims: list[dict],
    coverage: dict,
) -> list[BaseMessage]:
    """Assemble the synthesis input inline, in the shape ``triage_synthesis`` reads.

    The first entry is discarded by ``synthesize_triage_assessment`` (it prepends
    its own system prompt); the trailing tool call/result messages carry the
    deterministic outputs the synthesis step stitches back verbatim.
    """
    return [
        SystemMessage(content=TRIAGE_SYNTHESIS_SYSTEM_PROMPT),
        HumanMessage(content=_build_synthesis_claim_context(submission, claim_decision)),
        AIMessage(
            content=_TRIAGE_SYNTHESIS_REASON,
            tool_calls=[
                {
                    "name": ESTIMATE_REPAIR_COST_TOOL_NAME,
                    "args": _estimate_repair_cost_arguments(claim_decision),
                    "id": _ESTIMATE_REPAIR_COST_TOOL_CALL_ID,
                },
                {
                    "name": SEARCH_PAST_CLAIMS_TOOL_NAME,
                    "args": {_SEARCH_QUERY_INPUT_KEY: submission.description},
                    "id": _SEARCH_PAST_CLAIMS_TOOL_CALL_ID,
                },
                {
                    "name": CHECK_COVERAGE_TOOL_NAME,
                    "args": _check_coverage_arguments(submission, claim_decision),
                    "id": _CHECK_COVERAGE_TOOL_CALL_ID,
                },
            ],
        ),
        ToolMessage(
            content=json.dumps(repair_cost_estimate),
            tool_call_id=_ESTIMATE_REPAIR_COST_TOOL_CALL_ID,
            name=ESTIMATE_REPAIR_COST_TOOL_NAME,
        ),
        ToolMessage(
            content=json.dumps(past_claims),
            tool_call_id=_SEARCH_PAST_CLAIMS_TOOL_CALL_ID,
            name=SEARCH_PAST_CLAIMS_TOOL_NAME,
        ),
        ToolMessage(
            content=json.dumps(coverage),
            tool_call_id=_CHECK_COVERAGE_TOOL_CALL_ID,
            name=CHECK_COVERAGE_TOOL_NAME,
        ),
    ]


def _build_synthesis_claim_context(
    submission: ClaimSubmission, claim_decision: ClaimDecisionOut
) -> str:
    parts = [
        f"{_POLICY_TYPE_CONTEXT_LABEL}: {submission.policy_type.value}",
        f"{_DESCRIPTION_CONTEXT_LABEL}: {submission.description or _NO_DESCRIPTION_PLACEHOLDER}",
    ]
    if submission.document_text:
        parts.append(f"{_DOCUMENT_TEXT_CONTEXT_LABEL}:\n{submission.document_text}")
    parts.append(f"{_DAMAGE_TYPE_CONTEXT_LABEL}: {claim_decision.damage_type.value}")
    parts.append(f"{_SEVERITY_CONTEXT_LABEL}: {claim_decision.severity.value}")
    affected_areas = ", ".join(claim_decision.affected_areas) or _NO_AFFECTED_AREAS_PLACEHOLDER
    parts.append(f"{_AFFECTED_AREAS_CONTEXT_LABEL}: {affected_areas}")
    return "\n\n".join(parts)


def _estimate_repair_cost_arguments(claim_decision: ClaimDecisionOut) -> dict:
    return {
        _DAMAGE_TYPE_INPUT_KEY: claim_decision.damage_type.value,
        _SEVERITY_INPUT_KEY: claim_decision.severity.value,
        _AFFECTED_AREAS_INPUT_KEY: claim_decision.affected_areas,
    }


def _check_coverage_arguments(
    submission: ClaimSubmission, claim_decision: ClaimDecisionOut
) -> dict:
    return {
        _POLICY_TYPE_INPUT_KEY: submission.policy_type.value,
        _INCIDENT_CATEGORY_INPUT_KEY: claim_decision.damage_type.value,
    }


def _reason_record(content: str) -> DeterministicStepRecord:
    return DeterministicStepRecord(
        step_type=REASON_STEP_TYPE, content=content, recorded_at=_now_iso()
    )


def _act_record(tool_name: str, tool_input: dict | None = None) -> DeterministicStepRecord:
    return DeterministicStepRecord(
        step_type=ACT_STEP_TYPE,
        content=_ACT_CONTENT_TEMPLATE.format(name=tool_name),
        recorded_at=_now_iso(),
        tool_name=tool_name,
        tool_input=tool_input,
    )


def _observe_record(tool_output: object) -> DeterministicStepRecord:
    return DeterministicStepRecord(
        step_type=OBSERVE_STEP_TYPE,
        content=json.dumps(tool_output, default=str),
        recorded_at=_now_iso(),
        tool_output=tool_output,
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
