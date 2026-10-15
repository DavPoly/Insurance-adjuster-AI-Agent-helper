"""End-to-end tests for the triage router.

The real routes run against fakes: a fake Jev decision client serves both node 1
(intake + parameters) and node 4 (output safety) with scripted answers, a fake
chat model answers the single synthesis call, and the qdrant/embedder/table
fakes stand in for the deterministic tools. The tests pin the HTTP contract —
200 with a full assessment and deterministic trace, 400 on intake rejection,
the bounded safety retry (200) and its exhaustion (422), and the trace/report
GETs — plus that the optional PDF's text reaches node 1.
"""

from pathlib import Path

from agents.fake_triage_lookup_tables import FAKE_COST_TABLE, FAKE_COVERAGE_TABLE
from agents.fake_triage_qdrant_client import FakeTriageEmbedder, FakeTriageQdrantClient
from fake_triage_route_dependencies import CountingTriageChatModel, FakeDecisionModelClient
from triage_route_test_values import (
    FAKE_CLAIM_DESCRIPTION,
    FAKE_SYNTHESIZED_DAMAGE_DESCRIPTION,
    FAKE_SYNTHESIZED_RECOMMENDATION,
    INSPECTION_DOCUMENT_CONTENT_TYPE,
    INSPECTION_DOCUMENT_FILENAME,
    INSPECTION_DOCUMENT_TEXT_EXCERPT,
    UNKNOWN_CLAIM_ID,
)

from app.agents.prompts.claim_decision_questions import IS_PROPERTY_DAMAGE_QUESTION_ID
from app.agents.schemas.safety_checks_schema import SafetyChecksOut
from app.agents.schemas.triage_assessment_schema import (
    EstimatedRepairCostOut,
    TriageAssessmentOut,
)
from app.constants.agent.agent_trace_step_types import ACT_STEP_TYPE
from app.constants.agent.deterministic_pipeline_step_names import (
    CLAIM_DECISION_STEP_NAME,
    OUTPUT_SAFETY_STEP_NAME,
    TRIAGE_SYNTHESIS_STEP_NAME,
)
from app.constants.agent.safety_check_retry_limits import MAX_SAFETY_CHECK_ATTEMPTS
from app.constants.agent.triage_tool_names import (
    CHECK_COVERAGE_TOOL_NAME,
    ESTIMATE_REPAIR_COST_TOOL_NAME,
    SEARCH_PAST_CLAIMS_TOOL_NAME,
)
from app.constants.api.triage_route_error_codes import (
    CLAIM_NOT_FOUND_ERROR_CODE,
    INTAKE_VALIDATION_FAILED_ERROR_CODE,
    SAFETY_CHECK_FAILED_ERROR_CODE,
    TRACE_NOT_FOUND_ERROR_CODE,
)
from app.constants.claims.claim_taxonomy import DamageType, SeverityLevel, UrgencyLevel
from app.constants.tools.cost_estimate_currency import DEFAULT_CURRENCY
from app.dependencies import (
    get_claim_embedder,
    get_cost_table,
    get_coverage_table,
    get_decision_model_client,
    get_qdrant_client,
    get_triage_chat_model,
)
from app.main import app
from app.storage.triage_report_store import TriageReportStore, get_triage_report_store

TEST_DOCUMENTS_DIR = Path(__file__).resolve().parents[3] / "data" / "test-documents"

EXPECTED_DETERMINISTIC_ACT_STEPS = [
    CLAIM_DECISION_STEP_NAME,
    SEARCH_PAST_CLAIMS_TOOL_NAME,
    ESTIMATE_REPAIR_COST_TOOL_NAME,
    CHECK_COVERAGE_TOOL_NAME,
    TRIAGE_SYNTHESIS_STEP_NAME,
    OUTPUT_SAFETY_STEP_NAME,
]


def _synthesized_assessment() -> TriageAssessmentOut:
    return TriageAssessmentOut(
        damage_type=DamageType.WATER_DAMAGE,
        severity=SeverityLevel.MINOR,
        affected_areas=[],
        damage_description=FAKE_SYNTHESIZED_DAMAGE_DESCRIPTION,
        estimated_repair_cost=EstimatedRepairCostOut(min=0, max=0, currency=DEFAULT_CURRENCY),
        urgency=UrgencyLevel.LOW,
        recommendation=FAKE_SYNTHESIZED_RECOMMENDATION,
        similar_past_claims=[],
    )


def _passing_safety_checks() -> SafetyChecksOut:
    return SafetyChecksOut(
        no_coverage_promises=True,
        no_legal_advice=True,
        no_settlement_amounts=True,
        no_liability_determination=True,
        no_emotional_language=True,
    )


def _failing_safety_checks() -> SafetyChecksOut:
    return SafetyChecksOut(
        no_coverage_promises=False,
        no_legal_advice=True,
        no_settlement_amounts=True,
        no_liability_determination=True,
        no_emotional_language=True,
    )


def _build_synthesis_chat_model() -> CountingTriageChatModel:
    return CountingTriageChatModel(
        structured_output_values_by_schema={TriageAssessmentOut: _synthesized_assessment()}
    )


def _override_dependencies(
    llm: CountingTriageChatModel,
    store: TriageReportStore,
    decision_client: FakeDecisionModelClient | None = None,
) -> None:
    app.dependency_overrides[get_triage_chat_model] = lambda: llm
    app.dependency_overrides[get_qdrant_client] = lambda: FakeTriageQdrantClient([])
    app.dependency_overrides[get_claim_embedder] = lambda: FakeTriageEmbedder()
    app.dependency_overrides[get_cost_table] = lambda: FAKE_COST_TABLE
    app.dependency_overrides[get_coverage_table] = lambda: FAKE_COVERAGE_TABLE
    app.dependency_overrides[get_triage_report_store] = lambda: store
    app.dependency_overrides[get_decision_model_client] = lambda: (
        decision_client or FakeDecisionModelClient()
    )


def _posted_trace_act_step_names(client, response) -> list[str]:
    claim_id = response.json()["claim_id"]
    trace_response = client.get(f"/api/v1/agent/trace/{claim_id}")
    steps = trace_response.json()["steps"]
    return [step["tool_name"] for step in steps if step["type"] == ACT_STEP_TYPE]


def _observation_following_act(steps: list[dict], tool_name: str) -> dict:
    act_index = next(
        index for index, step in enumerate(steps) if step.get("tool_name") == tool_name
    )
    return steps[act_index + 1]


def test_triage_claim_returns_400_when_no_image_or_description(client):
    response = client.post("/api/v1/claims/triage", data={})

    assert response.status_code == 400
    body = response.json()
    assert body["error"] == INTAKE_VALIDATION_FAILED_ERROR_CODE
    assert body["intake_validation"]["is_property_damage"] is False


def test_triage_claim_returns_400_when_the_decision_client_rejects_the_intake(client):
    decision_client = FakeDecisionModelClient(intake_answers={IS_PROPERTY_DAMAGE_QUESTION_ID: 0.0})
    _override_dependencies(_build_synthesis_chat_model(), TriageReportStore(), decision_client)

    response = client.post("/api/v1/claims/triage", data={"description": FAKE_CLAIM_DESCRIPTION})
    app.dependency_overrides.clear()

    assert response.status_code == 400
    body = response.json()
    assert body["error"] == INTAKE_VALIDATION_FAILED_ERROR_CODE
    assert body["intake_validation"]["is_property_damage"] is False
    assert isinstance(body["message"], str) and body["message"]
    assert not body.get("triage_assessment")


def test_triage_claim_returns_200_with_the_assessment_and_a_deterministic_trace(client):
    _override_dependencies(_build_synthesis_chat_model(), TriageReportStore())

    response = client.post("/api/v1/claims/triage", data={"description": FAKE_CLAIM_DESCRIPTION})
    act_step_names = _posted_trace_act_step_names(client, response)
    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["intake_validation"]["is_valid_image"] is None
    assert body["triage_assessment"]["damage_type"] == DamageType.WATER_DAMAGE.value
    assert body["triage_assessment"]["damage_description"] == FAKE_SYNTHESIZED_DAMAGE_DESCRIPTION
    assert body["triage_assessment"]["recommendation"] == FAKE_SYNTHESIZED_RECOMMENDATION
    assert body["safety_checks"] == _passing_safety_checks().model_dump()
    assert body["claim_id"]
    assert act_step_names == EXPECTED_DETERMINISTIC_ACT_STEPS


def test_triage_claim_threads_the_PDF_text_into_the_intake_decision(client):
    decision_client = FakeDecisionModelClient()
    _override_dependencies(_build_synthesis_chat_model(), TriageReportStore(), decision_client)
    document_bytes = (TEST_DOCUMENTS_DIR / INSPECTION_DOCUMENT_FILENAME).read_bytes()

    response = client.post(
        "/api/v1/claims/triage",
        data={"description": FAKE_CLAIM_DESCRIPTION},
        files={
            "document": (
                INSPECTION_DOCUMENT_FILENAME,
                document_bytes,
                INSPECTION_DOCUMENT_CONTENT_TYPE,
            )
        },
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert INSPECTION_DOCUMENT_TEXT_EXCERPT in str(decision_client.observed_claim_states[-1])


def test_triage_claim_returns_200_when_safety_passes_on_the_first_retry(client):
    decision_client = FakeDecisionModelClient(
        safety_check_attempts=(_failing_safety_checks(), _passing_safety_checks())
    )
    llm = _build_synthesis_chat_model()
    _override_dependencies(llm, TriageReportStore(), decision_client)

    response = client.post("/api/v1/claims/triage", data={"description": FAKE_CLAIM_DESCRIPTION})
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["safety_checks"] == _passing_safety_checks().model_dump()
    assert decision_client.safety_call_count == 2
    # the bounded retry regenerated the draft from the carried inputs before re-checking.
    assert llm.structured_output_invoke_count == 2


def test_triage_claim_stores_a_trace_reflecting_the_final_safety_verdict(client):
    decision_client = FakeDecisionModelClient(
        safety_check_attempts=(_failing_safety_checks(), _passing_safety_checks())
    )
    _override_dependencies(_build_synthesis_chat_model(), TriageReportStore(), decision_client)

    response = client.post("/api/v1/claims/triage", data={"description": FAKE_CLAIM_DESCRIPTION})
    claim_id = response.json()["claim_id"]
    steps = client.get(f"/api/v1/agent/trace/{claim_id}").json()["steps"]
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["safety_checks"] == _passing_safety_checks().model_dump()
    # the stored trace shows the retry's passing verdict, not the discarded first pass.
    safety_observation = _observation_following_act(steps, OUTPUT_SAFETY_STEP_NAME)
    assert safety_observation["tool_output"] == _passing_safety_checks().model_dump()


def test_triage_claim_returns_422_when_safety_never_passes(client):
    decision_client = FakeDecisionModelClient(safety_check_attempts=(_failing_safety_checks(),))
    llm = _build_synthesis_chat_model()
    _override_dependencies(llm, TriageReportStore(), decision_client)

    response = client.post("/api/v1/claims/triage", data={"description": FAKE_CLAIM_DESCRIPTION})
    app.dependency_overrides.clear()

    assert response.status_code == 422
    body = response.json()
    assert body["error"] == SAFETY_CHECK_FAILED_ERROR_CODE
    assert body["safety_checks"] == _failing_safety_checks().model_dump()
    assert decision_client.safety_call_count == MAX_SAFETY_CHECK_ATTEMPTS
    assert llm.structured_output_invoke_count == MAX_SAFETY_CHECK_ATTEMPTS


def test_triage_claim_then_get_report_and_trace_roundtrip(client):
    store = TriageReportStore()
    _override_dependencies(_build_synthesis_chat_model(), store)

    post_response = client.post(
        "/api/v1/claims/triage", data={"description": FAKE_CLAIM_DESCRIPTION}
    )
    claim_id = post_response.json()["claim_id"]

    report_response = client.get(f"/api/v1/claims/{claim_id}")
    trace_response = client.get(f"/api/v1/agent/trace/{claim_id}")
    app.dependency_overrides.clear()

    assert report_response.status_code == 200
    assert report_response.json() == post_response.json()
    assert trace_response.status_code == 200
    trace_body = trace_response.json()
    assert trace_body["claim_id"] == claim_id
    assert isinstance(trace_body["total_duration_ms"], int)


def test_get_triage_report_returns_404_for_an_unknown_claim_id(client):
    response = client.get(f"/api/v1/claims/{UNKNOWN_CLAIM_ID}")

    assert response.status_code == 404
    assert response.json()["error"] == CLAIM_NOT_FOUND_ERROR_CODE


def test_get_agent_trace_returns_404_for_an_unknown_claim_id(client):
    response = client.get(f"/api/v1/agent/trace/{UNKNOWN_CLAIM_ID}")

    assert response.status_code == 404
    assert response.json()["error"] == TRACE_NOT_FOUND_ERROR_CODE
