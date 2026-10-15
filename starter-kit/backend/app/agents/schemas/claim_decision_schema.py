"""Node-1 output: the combined intake verdict and extracted claim parameters.

Mirrors the four booleans of the response contract's ``IntakeValidation`` (so the
router's rejection mapping is unchanged) and adds the parameters the deterministic
tools and synthesis need. ``is_valid_image`` is ``None`` for a text-only
submission, matching the contract's nullable field.
"""

from pydantic import BaseModel

from app.constants.claims.claim_taxonomy import DamageType, SeverityLevel


class ClaimDecisionOut(BaseModel):
    is_property_damage: bool
    is_valid_image: bool | None
    no_pii_detected: bool
    no_offensive_content: bool
    damage_type: DamageType
    severity: SeverityLevel
    affected_areas: list[str]
