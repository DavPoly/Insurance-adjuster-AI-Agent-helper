from app.agents.schemas.intake_validation_schema import IntakeValidationOut
from app.agents.schemas.safety_checks_schema import SafetyChecksOut


class IntakeValidationFailed(Exception):
    def __init__(self, intake_validation: IntakeValidationOut, message: str):
        self.intake_validation = intake_validation
        self.message = message


class SafetyCheckFailed(Exception):
    def __init__(self, safety_checks: SafetyChecksOut, message: str):
        self.safety_checks = safety_checks
        self.message = message
