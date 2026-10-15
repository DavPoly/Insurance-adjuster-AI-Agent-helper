import json
import logging
import time

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from langchain_core.language_models.chat_models import BaseChatModel
from qdrant_client import QdrantClient

from app.agents.deterministic_triage import (
    DeterministicTriageResult,
    run_deterministic_triage,
    safety_checks_passed,
)
from app.agents.safety_decision import check_output_safety
from app.agents.schemas.safety_checks_schema import SafetyChecksOut
from app.agents.triage_synthesis import synthesize_triage_assessment
from app.constants.agent.deterministic_pipeline_step_names import (
    OUTPUT_SAFETY_STEP_NAME,
    TRIAGE_SYNTHESIS_STEP_NAME,
)
from app.constants.agent.safety_check_retry_limits import MAX_SAFETY_CHECK_ATTEMPTS
from app.constants.agent.triage_assessment_field_names import (
    DAMAGE_DESCRIPTION_FIELD,
    RECOMMENDATION_FIELD,
)
from app.constants.api.triage_route_error_codes import (
    CLAIM_NOT_FOUND_ERROR_CODE,
    TRACE_NOT_FOUND_ERROR_CODE,
)
from app.constants.claims.claim_id_config import generate_claim_id
from app.dependencies import (
    get_claim_embedder,
    get_cost_table,
    get_coverage_table,
    get_decision_model_client,
    get_qdrant_client,
    get_triage_chat_model,
)
from app.llm.decision_model_client import DecisionModelClient
from app.rag.embedder import ClaimEmbedder
from app.routers.claim_input_parsing import (
    ParsedClaimInput,
    parse_and_validate_claim_input,
)
from app.routers.triage_exceptions import SafetyCheckFailed
from app.routers.triage_schemas import (
    AgentTraceOut,
    SafetyErrorOut,
    TriageResponseOut,
    ValidationErrorOut,
)
from app.storage.triage_report_store import TriageReportStore, get_triage_report_store

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/claims/triage",
    summary="Submit a claim for triage",
    description=(
        "Runs the deterministic triage pipeline over a damage photo and/or text "
        "description (plus an optional supporting PDF): a Jev intake-and-parameter "
        "decision, the deterministic cost/coverage/past-claim tools, a single "
        "generative synthesis call, and a Jev output-safety decision. Returns a "
        "structured triage report."
    ),
    response_model=TriageResponseOut,
    responses={
        status.HTTP_200_OK: {
            "model": TriageResponseOut,
            "description": "Triage completed successfully.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ValidationErrorOut,
            "description": "Invalid input (failed intake validation).",
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "model": SafetyErrorOut,
            "description": "Safety check failed on output.",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Unexpected server error."},
    },
)
async def triage_claim(
    claim_input: ParsedClaimInput = Depends(parse_and_validate_claim_input),
    llm: BaseChatModel = Depends(get_triage_chat_model),
    decision_client: DecisionModelClient = Depends(get_decision_model_client),
    qdrant_client: QdrantClient = Depends(get_qdrant_client),
    embedder: ClaimEmbedder = Depends(get_claim_embedder),
    cost_table: dict = Depends(get_cost_table),
    coverage_table: dict = Depends(get_coverage_table),
    store: TriageReportStore = Depends(get_triage_report_store),
) -> TriageResponseOut:
    start_time = time.monotonic()
    result = await run_deterministic_triage(
        submission=claim_input.submission,
        claim_decision=claim_input.claim_decision,
        llm=llm,
        decision_client=decision_client,
        qdrant_client=qdrant_client,
        embedder=embedder,
        cost_table=cost_table,
        coverage_table=coverage_table,
    )
    triage_assessment, safety_checks = await _resolve_safe_triage_assessment(
        llm, decision_client, result
    )
    total_duration_ms = int((time.monotonic() - start_time) * 1000)

    if not safety_checks_passed(safety_checks):
        raise SafetyCheckFailed(
            safety_checks=safety_checks,
            message=(
                "The generated triage report failed an output safety check after "
                f"{MAX_SAFETY_CHECK_ATTEMPTS} attempts."
            ),
        )

    claim_id = generate_claim_id()
    response = TriageResponseOut(
        claim_id=claim_id,
        intake_validation=claim_input.intake_validation,
        triage_assessment=triage_assessment,
        safety_checks=safety_checks,
    )
    trace = AgentTraceOut(
        claim_id=claim_id,
        steps=_trace_steps_reflecting_final_outcome(
            result.trace_steps, triage_assessment, safety_checks
        ),
        total_duration_ms=total_duration_ms,
    )
    store.save(claim_id, response.model_dump(), trace.model_dump())
    return response


async def _resolve_safe_triage_assessment(
    llm: BaseChatModel,
    decision_client: DecisionModelClient,
    result: DeterministicTriageResult,
) -> tuple[dict, SafetyChecksOut]:
    """Keep the first pass's assessment unless node 4 fails, then regenerate in place.

    The pipeline has already run node 4 once, so its verdict seeds the loop; on
    failure the router regenerates from the carried claim context, classification,
    and tool results and re-checks with node 4, bounded by
    ``MAX_SAFETY_CHECK_ATTEMPTS``.
    """
    triage_assessment = result.triage_assessment
    safety_checks = result.safety_checks

    attempt = 1
    while not safety_checks_passed(safety_checks) and attempt < MAX_SAFETY_CHECK_ATTEMPTS:
        logger.warning(
            "Triage output failed safety check on attempt %d/%d; regenerating.",
            attempt,
            MAX_SAFETY_CHECK_ATTEMPTS,
        )
        triage_assessment = synthesize_triage_assessment(
            llm, result.classification, result.tool_results, result.claim_context
        )
        safety_checks = await check_output_safety(
            decision_client,
            triage_assessment[DAMAGE_DESCRIPTION_FIELD],
            triage_assessment[RECOMMENDATION_FIELD],
        )
        attempt += 1

    return triage_assessment, safety_checks


def _trace_steps_reflecting_final_outcome(
    trace_steps: list[dict],
    triage_assessment: dict,
    safety_checks: SafetyChecksOut,
) -> list[dict]:
    """Rewrite the pipeline trace's synthesis and safety observations to the final outcome.

    The pipeline builds its trace from the first pass, but the bounded safety retry
    above can regenerate the draft; storing that trace as-is would show the
    discarded first pass. This updates the two affected observations so the stored
    trace matches the returned assessment and safety verdict.
    """
    steps = [dict(step) for step in trace_steps]
    _set_traced_observation(steps, TRIAGE_SYNTHESIS_STEP_NAME, triage_assessment)
    _set_traced_observation(steps, OUTPUT_SAFETY_STEP_NAME, safety_checks.model_dump())
    return steps


def _set_traced_observation(steps: list[dict], tool_name: str, tool_output: object) -> None:
    # Invariant: the orchestrator deterministically emits an act step (and its
    # following observe step) for every operation, so the lookup below never
    # raises StopIteration for a step name the pipeline built.
    act_index = next(
        index for index, step in enumerate(steps) if step.get("tool_name") == tool_name
    )
    observation = steps[act_index + 1]
    observation["content"] = json.dumps(tool_output, default=str)
    observation["tool_output"] = tool_output


@router.get(
    "/claims/{claim_id}",
    summary="Retrieve a completed triage report",
    description="Returns a previously completed triage report by claim_id.",
    response_model=TriageResponseOut,
    responses={
        status.HTTP_200_OK: {"model": TriageResponseOut, "description": "Triage report."},
        status.HTTP_404_NOT_FOUND: {"description": "Claim not found."},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Unexpected server error."},
    },
)
def get_triage_report(claim_id: str, store: TriageReportStore = Depends(get_triage_report_store)):
    report = store.get_report(claim_id)
    if report is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": CLAIM_NOT_FOUND_ERROR_CODE,
                "message": "No triage report for this claim_id.",
            },
        )
    return report


@router.get(
    "/agent/trace/{claim_id}",
    summary="Get the triage execution trace for a triage run",
    description="Returns the recorded reason/act/observe trace for a completed triage run.",
    response_model=AgentTraceOut,
    responses={
        status.HTTP_200_OK: {"model": AgentTraceOut, "description": "Triage execution trace."},
        status.HTTP_404_NOT_FOUND: {"description": "Trace not found."},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Unexpected server error."},
    },
)
def get_agent_trace(claim_id: str, store: TriageReportStore = Depends(get_triage_report_store)):
    trace = store.get_trace(claim_id)
    if trace is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": TRACE_NOT_FOUND_ERROR_CODE,
                "message": "No agent trace for this claim_id.",
            },
        )
    return trace
