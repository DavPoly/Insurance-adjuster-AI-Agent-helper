from dataclasses import dataclass, field

from app.constants.claims.claim_taxonomy import PolicyType


@dataclass
class ClaimSubmission:
    """The claim input handed to the triage agent, already assembled from the
    multipart request (image encoding and PDF text extraction happen upstream).
    """

    description: str
    policy_type: PolicyType
    image_data_urls: list[str] = field(default_factory=list)
    document_text: str | None = None
