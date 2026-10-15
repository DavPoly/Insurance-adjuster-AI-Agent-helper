import base64
import io
from dataclasses import dataclass

from fastapi import Depends, File, Form, UploadFile
from pypdf import PdfReader

from app.agents.claim_decision import (
    claim_decision_passed,
    decide_claim,
    describe_claim_decision_failure,
)
from app.agents.schemas.claim_decision_schema import ClaimDecisionOut
from app.agents.schemas.claim_submission import ClaimSubmission
from app.agents.schemas.intake_validation_schema import IntakeValidationOut
from app.constants.claims.claim_taxonomy import PolicyType
from app.constants.intake.image_upload_config import DEFAULT_IMAGE_CONTENT_TYPE
from app.dependencies import get_decision_model_client
from app.llm.decision_model_client import DecisionModelClient
from app.routers.triage_exceptions import IntakeValidationFailed


@dataclass
class ParsedClaimInput:
    image_data_urls: list[str]
    description: str
    document: UploadFile | None
    intake_validation: IntakeValidationOut


async def parse_and_validate_claim_input(
    image: UploadFile | None = File(default=None),
    images: list[UploadFile] | None = File(default=None),
    description: str | None = Form(default=None),
    document: UploadFile | None = File(default=None),
    policy_type: PolicyType = Form(default=PolicyType.STANDARD_HOMEOWNER),
    decision_client: DecisionModelClient = Depends(get_decision_model_client),
) -> ParsedClaimInput:
    uploaded_images = collect_uploaded_images(image, images)
    stripped_description = (description or "").strip()
    has_required_input = bool(uploaded_images) or bool(stripped_description)

    image_data_urls = [await encode_image_as_data_url(upload) for upload in uploaded_images]

    submission = ClaimSubmission(
        description=stripped_description,
        policy_type=policy_type,
        image_data_urls=image_data_urls,
    )
    claim_decision = await decide_claim(decision_client, submission)
    intake_validation = to_intake_validation(claim_decision)
    if not claim_decision_passed(claim_decision):
        raise IntakeValidationFailed(
            intake_validation=intake_validation,
            message=describe_claim_decision_failure(claim_decision, has_required_input),
        )

    return ParsedClaimInput(
        image_data_urls=image_data_urls,
        description=stripped_description,
        document=document,
        intake_validation=intake_validation,
    )


def to_intake_validation(claim_decision: ClaimDecisionOut) -> IntakeValidationOut:
    """Project the node-1 decision onto the response contract's intake booleans."""
    return IntakeValidationOut(
        is_property_damage=claim_decision.is_property_damage,
        is_valid_image=claim_decision.is_valid_image,
        no_pii_detected=claim_decision.no_pii_detected,
        no_offensive_content=claim_decision.no_offensive_content,
    )


def collect_uploaded_images(
    image: UploadFile | None, images: list[UploadFile] | None
) -> list[UploadFile]:
    collected = list(images or [])
    if image is not None:
        collected.insert(0, image)
    return collected


async def encode_image_as_data_url(upload: UploadFile) -> str:
    contents = await upload.read()
    encoded = base64.b64encode(contents).decode("ascii")
    content_type = upload.content_type or DEFAULT_IMAGE_CONTENT_TYPE
    return f"data:{content_type};base64,{encoded}"


async def extract_pdf_text(document: UploadFile) -> str:
    contents = await document.read()
    reader = PdfReader(io.BytesIO(contents))
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
