import logging
import time

from fastapi import APIRouter, Depends, Form, status
from fastapi.responses import JSONResponse
from langchain_core.language_models.chat_models import BaseChatModel
from qdrant_client import QdrantClient

from app.agents.safety_checker import check_output_safety, safety_checks_passed
from app.agents.schemas.claim_submission import ClaimSubmission
from app.agents.schemas.safety_checks_schema import SafetyChecksOut
from app.agents.triage_agent import TriageAgentResult, run_triage_agent
from app.agents.triage_synthesis import synthesize_triage_assessment
from app.constants.agent.safety_check_retry_limits import MAX_SAFETY_CHECK_ATTEMPTS
from app.constants.api.triage_route_error_codes import (
    CLAIM_NOT_FOUND_ERROR_CODE,
    TRACE_NOT_FOUND_ERROR_CODE,
)
from app.constants.claims.claim_id_config import generate_claim_id
from app.constants.claims.claim_taxonomy import PolicyType
from app.dependencies import (
    get_claim_embedder,
    get_cost_table,
    get_coverage_table,
    get_qdrant_client,
    get_triage_chat_model,
)
from app.rag.embedder import ClaimEmbedder
from app.routers.claim_input_parsing import (
    ParsedClaimInput,
    extract_pdf_text,
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
        "Runs the triageAgent ReAct loop over a damage photo and/or text "
        "description (plus an optional supporting PDF) and returns a structured "
        "triage report."
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
    policy_type: PolicyType = Form(default=PolicyType.STANDARD_HOMEOWNER),
    llm: BaseChatModel = Depends(get_triage_chat_model),
    client: QdrantClient = Depends(get_qdrant_client),
    embedder: ClaimEmbedder = Depends(get_claim_embedder),
    cost_table: dict = Depends(get_cost_table),
    coverage_table: dict = Depends(get_coverage_table),
    store: TriageReportStore = Depends(get_triage_report_store),
) -> TriageResponseOut:
    image_data_urls = claim_input.image_data_urls
    document_text = (
        await extract_pdf_text(claim_input.document) if claim_input.document is not None else None
    )

    submission = ClaimSubmission(
        description=claim_input.description,
        policy_type=policy_type,
        image_data_urls=image_data_urls,
        document_text=document_text,
    )

    start_time = time.monotonic()
    result = run_triage_agent(submission, llm, client, embedder, cost_table, coverage_table)
    triage_assessment, safety_checks = _resolve_safe_triage_assessment(llm, result)
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
        claim_id=claim_id, steps=result.trace_steps, total_duration_ms=total_duration_ms
    )
    store.save(claim_id, response.model_dump(), trace.model_dump())
    return response


def _resolve_safe_triage_assessment(
    llm: BaseChatModel, result: TriageAgentResult
) -> tuple[dict, SafetyChecksOut]:
    triage_assessment = result.triage_assessment
    safety_checks = check_output_safety(llm, triage_assessment)

    attempt = 1
    while not safety_checks_passed(safety_checks) and attempt < MAX_SAFETY_CHECK_ATTEMPTS:
        logger.warning(
            "Triage output failed safety check on attempt %d/%d; regenerating.",
            attempt,
            MAX_SAFETY_CHECK_ATTEMPTS,
        )
        triage_assessment = synthesize_triage_assessment(llm, result.messages)
        safety_checks = check_output_safety(llm, triage_assessment)
        attempt += 1

    return triage_assessment, safety_checks


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
    summary="Get the ReAct execution trace for a triage run",
    description="Returns the recorded reason/act/observe trace for a completed triage run.",
    response_model=AgentTraceOut,
    responses={
        status.HTTP_200_OK: {"model": AgentTraceOut, "description": "Agent execution trace."},
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
