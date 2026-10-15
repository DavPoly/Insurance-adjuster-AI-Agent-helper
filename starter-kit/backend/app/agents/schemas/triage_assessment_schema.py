from pydantic import BaseModel, Field

from app.constants.claims.claim_taxonomy import DamageType, SeverityLevel, UrgencyLevel


class EstimatedRepairCostOut(BaseModel):
    min: float
    max: float
    currency: str


class SimilarPastClaimOut(BaseModel):
    claim_id: str
    similarity_score: float = Field(ge=0, le=1)
    resolution_summary: str


class TriageAssessmentOut(BaseModel):
    damage_type: DamageType
    severity: SeverityLevel
    affected_areas: list[str]
    damage_description: str
    estimated_repair_cost: EstimatedRepairCostOut
    urgency: UrgencyLevel
    recommendation: str
    similar_past_claims: list[SimilarPastClaimOut]
