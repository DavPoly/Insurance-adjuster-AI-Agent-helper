from pydantic import BaseModel

from app.agents.schemas.intake_validation_schema import IntakeValidationOut
from app.agents.schemas.safety_checks_schema import SafetyChecksOut
from app.agents.schemas.triage_assessment_schema import TriageAssessmentOut


class TriageResponseOut(BaseModel):
    claim_id: str
    intake_validation: IntakeValidationOut
    triage_assessment: TriageAssessmentOut
    safety_checks: SafetyChecksOut


class ValidationErrorOut(BaseModel):
    error: str
    intake_validation: IntakeValidationOut
    message: str


class SafetyErrorOut(BaseModel):
    error: str
    safety_checks: SafetyChecksOut
    message: str


class AgentTraceOut(BaseModel):
    claim_id: str
    steps: list[dict]
    total_duration_ms: int
