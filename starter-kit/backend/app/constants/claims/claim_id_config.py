import uuid

GENERATED_CLAIM_ID_PREFIX = "triage"


def generate_claim_id() -> str:
    return f"{GENERATED_CLAIM_ID_PREFIX}-{uuid.uuid4()}"
