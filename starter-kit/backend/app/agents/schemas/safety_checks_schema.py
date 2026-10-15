from pydantic import BaseModel


class SafetyChecksOut(BaseModel):
    no_coverage_promises: bool
    no_legal_advice: bool
    no_settlement_amounts: bool
    no_liability_determination: bool
    no_emotional_language: bool
