"""Tests for the triage synthesis seam over explicit classification + tool results.

A fake chat model answers the single structured-output call and records the
message it received. The tests pin the verbatim stitching of the deterministic
fields (scope, cost, past claims) over the LLM's free text, that the prompt is
grounded in the supplied tool results, and that a claim ID the LLM invents is
dropped in favour of the supplied result.
"""

import json

from fake_triage_chat_model import FakeTriageChatModel

from app.agents.prompts.triage_synthesis_prompt import TRIAGE_SYNTHESIS_SYSTEM_PROMPT
from app.agents.schemas.claim_decision_schema import ClaimDecisionOut
from app.agents.schemas.triage_assessment_schema import (
    EstimatedRepairCostOut,
    SimilarPastClaimOut,
    TriageAssessmentOut,
)
from app.agents.triage_synthesis import SynthesisToolResults, synthesize_triage_assessment
from app.constants.agent.triage_tool_names import (
    CHECK_COVERAGE_TOOL_NAME,
    ESTIMATE_REPAIR_COST_TOOL_NAME,
    SEARCH_PAST_CLAIMS_TOOL_NAME,
)
from app.constants.claims.claim_taxonomy import (
    DamageType,
    SeverityLevel,
    UrgencyLevel,
)
from app.constants.tools.cost_estimate_currency import DEFAULT_CURRENCY

FAKE_DRAFTED_REPAIR_COST_MIN = 1
FAKE_DRAFTED_REPAIR_COST_MAX = 2

FAKE_TOOL_ESTIMATE = {"min": 2000, "max": 8000, "currency": DEFAULT_CURRENCY}
FAKE_COVERAGE_RESULT = {
    "covered": True,
    "deductible": 1500,
    "notes": "Fake standard coverage notes.",
}
FAKE_PAST_CLAIM_RECORD = {
    "claim_id": "CLM-2099-001",
    "similarity_score": 0.91,
    "damage_type": DamageType.WATER_DAMAGE.value,
    "severity": SeverityLevel.MODERATE.value,
    "affected_areas": ["kitchen"],
    "resolution": "covered_full",
    "repair_cost_actual": 5200,
}

FAKE_LLM_WRITTEN_RESOLUTION_SUMMARY = "LLM-written summary."
FAKE_INVENTED_PAST_CLAIM_ID = "CLM-0000-INVENTED"

FAKE_DRIFTED_DAMAGE_TYPE = DamageType.FIRE_DAMAGE
FAKE_DRIFTED_SEVERITY = SeverityLevel.SEVERE
FAKE_DRIFTED_AFFECTED_AREA = "attic"

FAKE_CLASSIFICATION_DAMAGE_TYPE = DamageType.WATER_DAMAGE
FAKE_CLASSIFICATION_SEVERITY = SeverityLevel.MODERATE
FAKE_CLASSIFICATION_AFFECTED_AREAS = ["kitchen"]


def _build_classification(**overrides) -> ClaimDecisionOut:
    values: dict = {
        "is_property_damage": True,
        "is_valid_image": True,
        "no_pii_detected": True,
        "no_offensive_content": True,
        "damage_type": FAKE_CLASSIFICATION_DAMAGE_TYPE,
        "severity": FAKE_CLASSIFICATION_SEVERITY,
        "affected_areas": list(FAKE_CLASSIFICATION_AFFECTED_AREAS),
    }
    values.update(overrides)
    return ClaimDecisionOut(**values)


def _build_tool_results(**overrides) -> SynthesisToolResults:
    values: dict = {
        "repair_cost_estimate": FAKE_TOOL_ESTIMATE,
        "similar_past_claims": [FAKE_PAST_CLAIM_RECORD],
        "coverage": FAKE_COVERAGE_RESULT,
    }
    values.update(overrides)
    return SynthesisToolResults(**values)


def _build_draft(similar_past_claims: list[SimilarPastClaimOut]) -> TriageAssessmentOut:
    return TriageAssessmentOut(
        damage_type=FAKE_CLASSIFICATION_DAMAGE_TYPE,
        severity=FAKE_CLASSIFICATION_SEVERITY,
        affected_areas=list(FAKE_CLASSIFICATION_AFFECTED_AREAS),
        damage_description="Water damage in the kitchen.",
        estimated_repair_cost=EstimatedRepairCostOut(
            min=FAKE_DRAFTED_REPAIR_COST_MIN,
            max=FAKE_DRAFTED_REPAIR_COST_MAX,
            currency=DEFAULT_CURRENCY,
        ),
        urgency=UrgencyLevel.MEDIUM,
        recommendation="Dispatch an adjuster.",
        similar_past_claims=similar_past_claims,
    )


def test_synthesize_triage_assessment_stitches_cost_and_scope_fields_verbatim():
    draft = _build_draft(
        [
            SimilarPastClaimOut(
                claim_id=FAKE_PAST_CLAIM_RECORD["claim_id"],
                similarity_score=0.5,
                resolution_summary=FAKE_LLM_WRITTEN_RESOLUTION_SUMMARY,
            )
        ]
    )
    llm = FakeTriageChatModel(structured_output_value=draft)

    assessment = synthesize_triage_assessment(llm, _build_classification(), _build_tool_results())

    assert assessment["estimated_repair_cost"] == FAKE_TOOL_ESTIMATE
    assert assessment["damage_type"] == FAKE_CLASSIFICATION_DAMAGE_TYPE.value
    assert assessment["severity"] == FAKE_CLASSIFICATION_SEVERITY.value
    assert assessment["affected_areas"] == FAKE_CLASSIFICATION_AFFECTED_AREAS
    assert assessment["similar_past_claims"] == [
        {
            "claim_id": FAKE_PAST_CLAIM_RECORD["claim_id"],
            "similarity_score": FAKE_PAST_CLAIM_RECORD["similarity_score"],
            "resolution_summary": FAKE_LLM_WRITTEN_RESOLUTION_SUMMARY,
        }
    ]


def test_synthesize_triage_assessment_overrides_scope_fields_from_the_classification():
    drifted_draft = TriageAssessmentOut(
        damage_type=FAKE_DRIFTED_DAMAGE_TYPE,
        severity=FAKE_DRIFTED_SEVERITY,
        affected_areas=[FAKE_DRIFTED_AFFECTED_AREA],
        damage_description="Water damage in the kitchen.",
        estimated_repair_cost=EstimatedRepairCostOut(
            min=FAKE_DRAFTED_REPAIR_COST_MIN,
            max=FAKE_DRAFTED_REPAIR_COST_MAX,
            currency=DEFAULT_CURRENCY,
        ),
        urgency=UrgencyLevel.MEDIUM,
        recommendation="Dispatch an adjuster.",
        similar_past_claims=[],
    )
    llm = FakeTriageChatModel(structured_output_value=drifted_draft)

    assessment = synthesize_triage_assessment(llm, _build_classification(), _build_tool_results())

    assert assessment["damage_type"] == FAKE_CLASSIFICATION_DAMAGE_TYPE.value
    assert assessment["severity"] == FAKE_CLASSIFICATION_SEVERITY.value
    assert assessment["affected_areas"] == FAKE_CLASSIFICATION_AFFECTED_AREAS


def test_synthesize_triage_assessment_falls_back_to_a_generated_summary_for_unmatched_claims():
    llm = FakeTriageChatModel(structured_output_value=_build_draft([]))

    assessment = synthesize_triage_assessment(llm, _build_classification(), _build_tool_results())

    assert assessment["similar_past_claims"] == [
        {
            "claim_id": FAKE_PAST_CLAIM_RECORD["claim_id"],
            "similarity_score": FAKE_PAST_CLAIM_RECORD["similarity_score"],
            "resolution_summary": (
                "Resolved as covered full, with an actual repair cost of 5200 USD."
            ),
        }
    ]


def test_synthesize_triage_assessment_drops_a_past_claim_the_llm_invented():
    llm = FakeTriageChatModel(
        structured_output_value=_build_draft(
            [
                SimilarPastClaimOut(
                    claim_id=FAKE_INVENTED_PAST_CLAIM_ID,
                    similarity_score=0.99,
                    resolution_summary="A claim that is not in the tool results.",
                )
            ]
        )
    )

    assessment = synthesize_triage_assessment(llm, _build_classification(), _build_tool_results())

    assert [claim["claim_id"] for claim in assessment["similar_past_claims"]] == [
        FAKE_PAST_CLAIM_RECORD["claim_id"]
    ]


def test_synthesize_triage_assessment_grounds_the_prompt_in_the_supplied_results():
    llm = FakeTriageChatModel(structured_output_value=_build_draft([]))

    synthesize_triage_assessment(llm, _build_classification(), _build_tool_results())

    system_message, context_message = llm.structured_output_messages
    assert system_message.content == TRIAGE_SYNTHESIS_SYSTEM_PROMPT
    context = json.loads(context_message.content)
    assert context[ESTIMATE_REPAIR_COST_TOOL_NAME] == FAKE_TOOL_ESTIMATE
    assert context[SEARCH_PAST_CLAIMS_TOOL_NAME] == [FAKE_PAST_CLAIM_RECORD]
    assert context[CHECK_COVERAGE_TOOL_NAME] == FAKE_COVERAGE_RESULT
