from dataclasses import dataclass, field


@dataclass
class ClassifiedAttachments:
    image_paths: list[str] = field(default_factory=list)
    document_path: str | None = None


def classify_attachments(
    attachments: list[tuple[str, str]],
    *,
    image_mime_prefix: str,
    pdf_mime_type: str,
) -> ClassifiedAttachments:
    classified = ClassifiedAttachments()
    for mime_type, file_path in attachments:
        if mime_type.startswith(image_mime_prefix):
            classified.image_paths.append(file_path)
        elif mime_type == pdf_mime_type and classified.document_path is None:
            classified.document_path = file_path
    return classified
