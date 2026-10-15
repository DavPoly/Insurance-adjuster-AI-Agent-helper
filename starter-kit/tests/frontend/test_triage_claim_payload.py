from known_attachment_fixture_values import (
    FIRST_DOCUMENT_PATH,
    FIRST_IMAGE_PATH,
    IMAGE_MIME_PREFIX,
    JPEG_MIME_TYPE,
    PDF_MIME_TYPE,
    PNG_MIME_TYPE,
    SECOND_DOCUMENT_PATH,
    SECOND_IMAGE_PATH,
    TEXT_MIME_TYPE,
    UNSUPPORTED_ATTACHMENT_PATH,
)

from utils.triage_claim_payload import classify_attachments


def test_classify_attachments_separates_images_and_document():
    attachments = [
        (JPEG_MIME_TYPE, FIRST_IMAGE_PATH),
        (PDF_MIME_TYPE, FIRST_DOCUMENT_PATH),
        (PNG_MIME_TYPE, SECOND_IMAGE_PATH),
    ]

    result = classify_attachments(
        attachments, image_mime_prefix=IMAGE_MIME_PREFIX, pdf_mime_type=PDF_MIME_TYPE
    )

    assert result.image_paths == [FIRST_IMAGE_PATH, SECOND_IMAGE_PATH]
    assert result.document_path == FIRST_DOCUMENT_PATH


def test_classify_attachments_ignores_unsupported_mime_types():
    attachments = [(TEXT_MIME_TYPE, UNSUPPORTED_ATTACHMENT_PATH)]

    result = classify_attachments(
        attachments, image_mime_prefix=IMAGE_MIME_PREFIX, pdf_mime_type=PDF_MIME_TYPE
    )

    assert result.image_paths == []
    assert result.document_path is None


def test_classify_attachments_keeps_first_document_when_multiple_pdfs_attached():
    attachments = [(PDF_MIME_TYPE, FIRST_DOCUMENT_PATH), (PDF_MIME_TYPE, SECOND_DOCUMENT_PATH)]

    result = classify_attachments(
        attachments, image_mime_prefix=IMAGE_MIME_PREFIX, pdf_mime_type=PDF_MIME_TYPE
    )

    assert result.document_path == FIRST_DOCUMENT_PATH


def test_classify_attachments_handles_no_attachments():
    result = classify_attachments(
        [], image_mime_prefix=IMAGE_MIME_PREFIX, pdf_mime_type=PDF_MIME_TYPE
    )

    assert result.image_paths == []
    assert result.document_path is None
