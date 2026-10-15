from fake_triage_route_dependencies import (
    FAKE_COST_TABLE,
    FAKE_COVERAGE_TABLE,
    FakeTriageChatModel,
    FakeTriageEmbedder,
    FakeTriageQdrantClient,
)
from langchain_core.messages import AIMessage

from app.agents.schemas.intake_validation_schema import IntakeValidationOut
from app.agents.schemas.safety_checks_schema import SafetyChecksOut
from app.agents.schemas.triage_assessment_schema import (
    EstimatedRepairCostOut,
    TriageAssessmentOut,
)
from app.dependencies import (
    get_claim_embedder,
    get_cost_table,
    get_coverage_table,
    get_qdrant_client,
    get_triage_chat_model,
)
from app.main import app
from app.routers import triage as triage_route
from app.storage.triage_report_store import TriageReportStore, get_triage_report_store

UNKNOWN_CLAIM_ID = "triage-unknown-claim-id"


def _fake_triage_assessment() -> TriageAssessmentOut:
    return TriageAssessmentOut(
        damage_type="water_damage",
        severity="minor",
        affected_areas=["kitchen"],
        damage_description="Minor water damage under the kitchen sink.",
        estimated_repair_cost=EstimatedRepairCostOut(min=500, max=2000, currency="USD"),
        urgency="low",
        recommendation="Dispatch an adjuster to confirm scope.",
        similar_past_claims=[],
    )


def _passing_intake_validation() -> IntakeValidationOut:
    return IntakeValidationOut(
        is_property_damage=True,
        is_valid_image=None,
        no_pii_detected=True,
        no_offensive_content=True,
    )


def _passing_safety_checks() -> SafetyChecksOut:
    return SafetyChecksOut(
        no_coverage_promises=True,
        no_legal_advice=True,
        no_settlement_amounts=True,
        no_liability_determination=True,
        no_emotional_language=True,
    )


def _build_fake_llm(
    tool_loop_responses, safety_checks: SafetyChecksOut | None = None
) -> FakeTriageChatModel:
    return FakeTriageChatModel(
        tool_loop_responses=tool_loop_responses,
        structured_output_values_by_schema={
            IntakeValidationOut: _passing_intake_validation(),
            TriageAssessmentOut: _fake_triage_assessment(),
            SafetyChecksOut: safety_checks or _passing_safety_checks(),
        },
    )


def _override_dependencies(llm: FakeTriageChatModel, store: TriageReportStore) -> None:
    app.dependency_overrides[get_triage_chat_model] = lambda: llm
    app.dependency_overrides[get_qdrant_client] = lambda: FakeTriageQdrantClient()
    app.dependency_overrides[get_claim_embedder] = lambda: FakeTriageEmbedder()
    app.dependency_overrides[get_cost_table] = lambda: FAKE_COST_TABLE
    app.dependency_overrides[get_coverage_table] = lambda: FAKE_COVERAGE_TABLE
    app.dependency_overrides[get_triage_report_store] = lambda: store


def test_triage_claim_returns_400_when_no_image_or_description(client):
    response = client.post("/api/v1/claims/triage", data={})

    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "intake_validation_failed"
    assert body["intake_validation"]["is_property_damage"] is False


def test_triage_claim_returns_200_for_a_text_only_description(client):
    llm = _build_fake_llm([AIMessage(content="Ready to finalize.")])
    _override_dependencies(llm, TriageReportStore())

    response = client.post(
        "/api/v1/claims/triage", data={"description": "Water is pooling under my kitchen sink."}
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["intake_validation"]["is_valid_image"] is None
    assert body["triage_assessment"]["damage_type"] == "water_damage"
    assert body["claim_id"]


def test_triage_claim_then_get_report_and_trace_roundtrip(client):
    llm = _build_fake_llm([AIMessage(content="Ready to finalize.")])
    store = TriageReportStore()
    _override_dependencies(llm, store)

    post_response = client.post(
        "/api/v1/claims/triage", data={"description": "Water is pooling under my kitchen sink."}
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
    assert response.json()["error"] == "claim_not_found"


def test_get_agent_trace_returns_404_for_an_unknown_claim_id(client):
    response = client.get(f"/api/v1/agent/trace/{UNKNOWN_CLAIM_ID}")

    assert response.status_code == 404
    assert response.json()["error"] == "trace_not_found"


def test_triage_claim_returns_422_when_the_safety_check_stub_fails(client, monkeypatch):
    def _failing_safety_checks(llm, triage_assessment):
        return SafetyChecksOut(
            no_coverage_promises=False,
            no_legal_advice=True,
            no_settlement_amounts=True,
            no_liability_determination=True,
            no_emotional_language=True,
        )

    monkeypatch.setattr(triage_route, "check_output_safety", _failing_safety_checks)
    llm = _build_fake_llm([AIMessage(content="Ready to finalize.")])
    _override_dependencies(llm, TriageReportStore())

    response = client.post(
        "/api/v1/claims/triage", data={"description": "Water is pooling under my kitchen sink."}
    )
    app.dependency_overrides.clear()

    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "safety_check_failed"
    assert body["safety_checks"]["no_coverage_promises"] is False
