import base64
import io
from dataclasses import dataclass

from fastapi import Depends, File, Form, UploadFile
from langchain_core.language_models.chat_models import BaseChatModel
from pypdf import PdfReader

from app.agents.intake_validator import (
    describe_intake_validation_failure,
    intake_validation_passed,
    validate_claim_intake,
)
from app.agents.schemas.intake_validation_schema import IntakeValidationOut
from app.constants.intake.image_upload_config import DEFAULT_IMAGE_CONTENT_TYPE
from app.dependencies import get_triage_chat_model
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
    llm: BaseChatModel = Depends(get_triage_chat_model),
) -> ParsedClaimInput:
    uploaded_images = collect_uploaded_images(image, images)
    stripped_description = (description or "").strip()
    has_required_input = bool(uploaded_images) or bool(stripped_description)

    image_data_urls = [await encode_image_as_data_url(upload) for upload in uploaded_images]

    intake_validation = validate_claim_intake(llm, image_data_urls, stripped_description)
    if not intake_validation_passed(intake_validation):
        raise IntakeValidationFailed(
            intake_validation=intake_validation,
            message=describe_intake_validation_failure(intake_validation, has_required_input),
        )

    return ParsedClaimInput(
        image_data_urls=image_data_urls,
        description=stripped_description,
        document=document,
        intake_validation=intake_validation,
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
