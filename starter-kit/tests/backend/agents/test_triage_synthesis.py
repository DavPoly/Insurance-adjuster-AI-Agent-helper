import json

from fake_triage_chat_model import FakeTriageChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.agents.schemas.triage_assessment_schema import (
    EstimatedRepairCostOut,
    SimilarPastClaimOut,
    TriageAssessmentOut,
)
from app.agents.triage_synthesis import synthesize_triage_assessment
from app.constants.agent.triage_tool_names import (
    ESTIMATE_REPAIR_COST_TOOL_NAME,
    SEARCH_PAST_CLAIMS_TOOL_NAME,
)

FAKE_TOOL_ESTIMATE = {"min": 2000, "max": 8000, "currency": "USD"}
FAKE_PAST_CLAIM_RECORD = {
    "claim_id": "CLM-2099-001",
    "similarity_score": 0.91,
    "damage_type": "water_damage",
    "severity": "moderate",
    "affected_areas": ["kitchen"],
    "resolution": "covered_full",
    "repair_cost_actual": 5200,
}


FAKE_TOOL_ESTIMATE_ARGS = {
    "damage_type": "water_damage",
    "severity": "moderate",
    "affected_areas": ["kitchen"],
}


def _build_trace_messages(estimate_args: dict = FAKE_TOOL_ESTIMATE_ARGS) -> list:
    return [
        HumanMessage(content="claim text"),
        AIMessage(
            content="Looking up cost.",
            tool_calls=[
                {
                    "name": ESTIMATE_REPAIR_COST_TOOL_NAME,
                    "args": estimate_args,
                    "id": "call-1",
                }
            ],
        ),
        ToolMessage(
            content=json.dumps(FAKE_TOOL_ESTIMATE),
            tool_call_id="call-1",
            name=ESTIMATE_REPAIR_COST_TOOL_NAME,
        ),
        ToolMessage(
            content=json.dumps([FAKE_PAST_CLAIM_RECORD]),
            tool_call_id="call-2",
            name=SEARCH_PAST_CLAIMS_TOOL_NAME,
        ),
    ]


def _build_draft(similar_past_claims: list[SimilarPastClaimOut]) -> TriageAssessmentOut:
    return TriageAssessmentOut(
        damage_type="water_damage",
        severity="moderate",
        affected_areas=["kitchen"],
        damage_description="Water damage in the kitchen.",
        estimated_repair_cost=EstimatedRepairCostOut(min=1, max=2, currency="USD"),
        urgency="medium",
        recommendation="Dispatch an adjuster.",
        similar_past_claims=similar_past_claims,
    )


def test_synthesize_triage_assessment_overrides_cost_and_claim_fields_verbatim():
    draft = _build_draft(
        [
            SimilarPastClaimOut(
                claim_id="CLM-2099-001",
                similarity_score=0.5,
                resolution_summary="LLM-written summary.",
            )
        ]
    )
    llm = FakeTriageChatModel(structured_output_value=draft)

    assessment = synthesize_triage_assessment(llm, _build_trace_messages())

    assert assessment["estimated_repair_cost"] == FAKE_TOOL_ESTIMATE
    assert assessment["similar_past_claims"] == [
        {
            "claim_id": "CLM-2099-001",
            "similarity_score": 0.91,
            "resolution_summary": "LLM-written summary.",
        }
    ]


def test_synthesize_triage_assessment_overrides_scope_fields_from_the_cost_tool_call():
    drifted_draft = TriageAssessmentOut(
        damage_type="fire_damage",
        severity="severe",
        affected_areas=["kitchen", "attic"],
        damage_description="Water damage in the kitchen.",
        estimated_repair_cost=EstimatedRepairCostOut(min=1, max=2, currency="USD"),
        urgency="medium",
        recommendation="Dispatch an adjuster.",
        similar_past_claims=[],
    )
    llm = FakeTriageChatModel(structured_output_value=drifted_draft)

    assessment = synthesize_triage_assessment(llm, _build_trace_messages())

    assert assessment["damage_type"] == FAKE_TOOL_ESTIMATE_ARGS["damage_type"]
    assert assessment["severity"] == FAKE_TOOL_ESTIMATE_ARGS["severity"]
    assert assessment["affected_areas"] == FAKE_TOOL_ESTIMATE_ARGS["affected_areas"]


def test_synthesize_triage_assessment_falls_back_to_a_generated_summary_for_unmatched_claims():
    llm = FakeTriageChatModel(structured_output_value=_build_draft([]))

    assessment = synthesize_triage_assessment(llm, _build_trace_messages())

    assert assessment["similar_past_claims"] == [
        {
            "claim_id": "CLM-2099-001",
            "similarity_score": 0.91,
            "resolution_summary": (
                "Resolved as covered full, with an actual repair cost of 5200 USD."
            ),
        }
    ]
