from pydantic import BaseModel


class IntakeValidationOut(BaseModel):
    is_property_damage: bool
    is_valid_image: bool | None
    no_pii_detected: bool
    no_offensive_content: bool
