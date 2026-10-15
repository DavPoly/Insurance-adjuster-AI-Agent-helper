from fake_triage_chat_model import FakeTriageChatModel
from fake_triage_lookup_tables import (
    FAKE_COST_TABLE,
    FAKE_COVERAGE_TABLE,
    FAKE_WATER_DAMAGE_MINOR_MAX_PER_AREA,
    FAKE_WATER_DAMAGE_MINOR_MIN_PER_AREA,
)
from fake_triage_qdrant_client import (
    FAKE_SEARCH_POINT,
    FAKE_SEARCH_TOOL_RESULT,
    FakeTriageEmbedder,
    FakeTriageQdrantClient,
)
from langchain_core.messages import AIMessage

from app.agents.schemas.claim_submission import ClaimSubmission
from app.agents.schemas.triage_assessment_schema import (
    EstimatedRepairCostOut,
    SimilarPastClaimOut,
    TriageAssessmentOut,
)
from app.agents.triage_agent import run_triage_agent
from app.constants.agent.agent_trace_step_types import ACT_STEP_TYPE
from app.constants.agent.triage_tool_names import (
    ESTIMATE_REPAIR_COST_TOOL_NAME,
    SEARCH_PAST_CLAIMS_TOOL_NAME,
)
from app.constants.claims.claim_taxonomy import PolicyType


def _final_draft() -> TriageAssessmentOut:
    return TriageAssessmentOut(
        damage_type="water_damage",
        severity="minor",
        affected_areas=["kitchen"],
        damage_description="Minor water damage under the kitchen sink.",
        estimated_repair_cost=EstimatedRepairCostOut(min=0, max=0, currency="USD"),
        urgency="low",
        recommendation="Dispatch an adjuster to confirm scope.",
        similar_past_claims=[
            SimilarPastClaimOut(
                claim_id=FAKE_SEARCH_TOOL_RESULT["claim_id"],
                similarity_score=FAKE_SEARCH_TOOL_RESULT["similarity_score"],
                resolution_summary="A similar past claim was fully covered.",
            )
        ],
    )


def test_run_triage_agent_produces_a_grounded_assessment_and_a_matching_trace():
    llm = FakeTriageChatModel(
        tool_loop_responses=[
            AIMessage(
                content="Searching for similar past claims.",
                tool_calls=[
                    {
                        "name": SEARCH_PAST_CLAIMS_TOOL_NAME,
                        "args": {"query": "pipe burst under the kitchen sink"},
                        "id": "call-1",
                    }
                ],
            ),
            AIMessage(
                content="Estimating the repair cost.",
                tool_calls=[
                    {
                        "name": ESTIMATE_REPAIR_COST_TOOL_NAME,
                        "args": {
                            "damage_type": "water_damage",
                            "severity": "minor",
                            "affected_areas": ["kitchen"],
                        },
                        "id": "call-2",
                    }
                ],
            ),
            AIMessage(content="Ready to finalize."),
        ],
        structured_output_value=_final_draft(),
    )

    result = run_triage_agent(
        submission=ClaimSubmission(
            description="Water is pooling under my kitchen sink.",
            policy_type=PolicyType.STANDARD_HOMEOWNER,
        ),
        llm=llm,
        client=FakeTriageQdrantClient([FAKE_SEARCH_POINT]),
        embedder=FakeTriageEmbedder(),
        cost_table=FAKE_COST_TABLE,
        coverage_table=FAKE_COVERAGE_TABLE,
    )

    assert result.triage_assessment["estimated_repair_cost"] == {
        "min": FAKE_WATER_DAMAGE_MINOR_MIN_PER_AREA,
        "max": FAKE_WATER_DAMAGE_MINOR_MAX_PER_AREA,
        "currency": "USD",
    }
    assert result.triage_assessment["similar_past_claims"] == [
        {
            "claim_id": FAKE_SEARCH_TOOL_RESULT["claim_id"],
            "similarity_score": FAKE_SEARCH_TOOL_RESULT["similarity_score"],
            "resolution_summary": "A similar past claim was fully covered.",
        }
    ]

    act_steps = [step for step in result.trace_steps if step["type"] == ACT_STEP_TYPE]
    assert [step["tool_name"] for step in act_steps] == [
        SEARCH_PAST_CLAIMS_TOOL_NAME,
        ESTIMATE_REPAIR_COST_TOOL_NAME,
    ]
