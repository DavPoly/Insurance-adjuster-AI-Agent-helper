"""Fake dependencies and canned values for the deterministic triage tests.

The recording fakes wrap the shared agent fakes so the tests can assert that
each tool and each decision/synthesis call ran exactly once, with the arguments
node 1 derived. The lookup tables and the canned search hit are reused as-is
from the sibling fixture modules.
"""

from fake_triage_chat_model import FakeTriageChatModel
from fake_triage_lookup_tables import (
    FAKE_STANDARD_HOMEOWNER_DEDUCTIBLE,
    FAKE_STANDARD_HOMEOWNER_MAX_PAYOUT,
    FAKE_STANDARD_HOMEOWNER_NOTES,
    FAKE_WATER_DAMAGE_MINOR_MAX_PER_AREA,
    FAKE_WATER_DAMAGE_MINOR_MIN_PER_AREA,
)
from fake_triage_qdrant_client import (
    FAKE_SEARCH_CLAIM_ID,
    FAKE_SEARCH_SIMILARITY_SCORE,
    FAKE_SEARCH_TOOL_RESULT,
    FakeTriageEmbedder,
    FakeTriageQdrantClient,
)

from app.agents.schemas.claim_decision_schema import ClaimDecisionOut
from app.agents.schemas.claim_submission import ClaimSubmission
from app.agents.schemas.safety_checks_schema import SafetyChecksOut
from app.agents.schemas.triage_assessment_schema import (
    EstimatedRepairCostOut,
    SimilarPastClaimOut,
    TriageAssessmentOut,
)
from app.constants.claims.claim_taxonomy import (
    DamageType,
    PolicyType,
    SeverityLevel,
    UrgencyLevel,
)
from app.constants.tools.cost_estimate_currency import DEFAULT_CURRENCY

# Tool argument names are re-typed on purpose: the tests assert the literal call
# shape the deterministic tools receive, so reusing the orchestrator's private
# key constants would make those assertions tautological.
DAMAGE_TYPE_ARGUMENT = "damage_type"
SEVERITY_ARGUMENT = "severity"
AFFECTED_AREAS_ARGUMENT = "affected_areas"
SEARCH_QUERY_ARGUMENT = "query"
POLICY_TYPE_ARGUMENT = "policy_type"
INCIDENT_CATEGORY_ARGUMENT = "incident_category"

FAKE_TRIAGE_DESCRIPTION = "A burst pipe soaked the kitchen floor and the dining room carpet."
FAKE_TRIAGE_DOCUMENT_TEXT = "Inspection report: water also reached the dining room ceiling."
FAKE_TRIAGE_POLICY_TYPE = PolicyType.STANDARD_HOMEOWNER
FAKE_TRIAGE_DAMAGE_TYPE = DamageType.WATER_DAMAGE
FAKE_TRIAGE_SEVERITY = SeverityLevel.MINOR
FAKE_TRIAGE_PRIMARY_AREA = "kitchen"
FAKE_TRIAGE_SECONDARY_AREA = "dining_room"
FAKE_TRIAGE_AFFECTED_AREAS = (FAKE_TRIAGE_PRIMARY_AREA, FAKE_TRIAGE_SECONDARY_AREA)
FAKE_TRIAGE_AFFECTED_AREA_COUNT = len(FAKE_TRIAGE_AFFECTED_AREAS)
FAKE_TRIAGE_IMAGE_DATA_URL = "data:image/jpeg;base64,ZmFrZS1kZXRlcm1pbmlzdGljLXBob3Rv"

FAKE_SYNTHESIZED_DAMAGE_DESCRIPTION = "Minor water damage across the kitchen and dining room."
FAKE_SYNTHESIZED_RECOMMENDATION = "Dispatch a mitigation contractor within 24 hours."
FAKE_DRAFTED_RESOLUTION_SUMMARY = "A comparable past claim was resolved with a full payout."

EXPECTED_REPAIR_COST_MIN = FAKE_WATER_DAMAGE_MINOR_MIN_PER_AREA * FAKE_TRIAGE_AFFECTED_AREA_COUNT
EXPECTED_REPAIR_COST_MAX = FAKE_WATER_DAMAGE_MINOR_MAX_PER_AREA * FAKE_TRIAGE_AFFECTED_AREA_COUNT

EXPECTED_PAST_CLAIMS_RESULT = [FAKE_SEARCH_TOOL_RESULT]

# FAKE_COVERAGE_TABLE's standard_homeowner policy covers only fire_damage, so the
# fixture water-damage incident is reported as uncovered.
EXPECTED_COVERAGE_RESULT = {
    "covered": False,
    "deductible": FAKE_STANDARD_HOMEOWNER_DEDUCTIBLE,
    "max_payout": FAKE_STANDARD_HOMEOWNER_MAX_PAYOUT,
    "notes": FAKE_STANDARD_HOMEOWNER_NOTES,
}


def build_submission(**overrides) -> ClaimSubmission:
    values: dict = {
        "description": FAKE_TRIAGE_DESCRIPTION,
        "policy_type": FAKE_TRIAGE_POLICY_TYPE,
        "image_data_urls": [FAKE_TRIAGE_IMAGE_DATA_URL],
        "document_text": FAKE_TRIAGE_DOCUMENT_TEXT,
    }
    values.update(overrides)
    return ClaimSubmission(**values)


def build_claim_decision(**overrides) -> ClaimDecisionOut:
    values: dict = {
        "is_property_damage": True,
        "is_valid_image": True,
        "no_pii_detected": True,
        "no_offensive_content": True,
        "damage_type": FAKE_TRIAGE_DAMAGE_TYPE,
        "severity": FAKE_TRIAGE_SEVERITY,
        "affected_areas": list(FAKE_TRIAGE_AFFECTED_AREAS),
    }
    values.update(overrides)
    return ClaimDecisionOut(**values)


def build_synthesis_draft() -> TriageAssessmentOut:
    return TriageAssessmentOut(
        damage_type=FAKE_TRIAGE_DAMAGE_TYPE,
        severity=FAKE_TRIAGE_SEVERITY,
        affected_areas=list(FAKE_TRIAGE_AFFECTED_AREAS),
        damage_description=FAKE_SYNTHESIZED_DAMAGE_DESCRIPTION,
        estimated_repair_cost=EstimatedRepairCostOut(min=0, max=0, currency=DEFAULT_CURRENCY),
        urgency=UrgencyLevel.LOW,
        recommendation=FAKE_SYNTHESIZED_RECOMMENDATION,
        similar_past_claims=[
            SimilarPastClaimOut(
                claim_id=FAKE_SEARCH_CLAIM_ID,
                similarity_score=FAKE_SEARCH_SIMILARITY_SCORE,
                resolution_summary=FAKE_DRAFTED_RESOLUTION_SUMMARY,
            )
        ],
    )


def all_passing_safety_checks() -> SafetyChecksOut:
    return SafetyChecksOut(
        no_coverage_promises=True,
        no_legal_advice=True,
        no_settlement_amounts=True,
        no_liability_determination=True,
        no_emotional_language=True,
    )


class CountingSynthesisChatModel(FakeTriageChatModel):
    """A fake chat model that also counts how often synthesis invokes the LLM."""

    def __init__(self, structured_output_value) -> None:
        super().__init__(structured_output_value=structured_output_value)
        self.synthesis_invoke_count = 0

    def with_structured_output(self, schema):
        return _CountingStructuredOutputRunnable(super().with_structured_output(schema), self)


class _CountingStructuredOutputRunnable:
    def __init__(self, runnable, owner: CountingSynthesisChatModel) -> None:
        self._runnable = runnable
        self._owner = owner

    def invoke(self, messages):
        self._owner.synthesis_invoke_count += 1
        return self._runnable.invoke(messages)


class RecordingTriageEmbedder(FakeTriageEmbedder):
    """Records the texts search_past_claims embeds."""

    def __init__(self) -> None:
        self.observed_queries: list[str] = []

    def embed_query(self, text: str) -> list[float]:
        self.observed_queries.append(text)
        return super().embed_query(text)


class RecordingTriageQdrantClient(FakeTriageQdrantClient):
    """Records the collections search_past_claims queries."""

    def __init__(self, points: list) -> None:
        super().__init__(points)
        self.observed_collection_names: list[str] = []

    def query_points(self, collection_name: str, query, limit: int):
        self.observed_collection_names.append(collection_name)
        return super().query_points(collection_name, query, limit)
