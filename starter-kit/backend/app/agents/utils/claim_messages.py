from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from app.agents.prompts.triage_agent_system_prompt import TRIAGE_AGENT_SYSTEM_PROMPT
from app.agents.schemas.claim_submission import ClaimSubmission


def build_initial_messages(submission: ClaimSubmission) -> list[BaseMessage]:
    content_blocks: list[dict] = [{"type": "text", "text": _build_claim_text(submission)}]
    for image_data_url in submission.image_data_urls:
        content_blocks.append({"type": "image_url", "image_url": {"url": image_data_url}})

    return [
        SystemMessage(content=TRIAGE_AGENT_SYSTEM_PROMPT),
        HumanMessage(content=content_blocks),
    ]


def _build_claim_text(submission: ClaimSubmission) -> str:
    parts = [
        f"Policy type: {submission.policy_type.value}",
        f"Claimant description: {submission.description or '(none provided)'}",
    ]
    if submission.document_text:
        parts.append(f"Supporting document text:\n{submission.document_text}")
    return "\n\n".join(parts)
