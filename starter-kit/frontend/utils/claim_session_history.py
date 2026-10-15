from dataclasses import dataclass
from datetime import UTC, datetime

import chainlit as cl

CLAIMS_SESSION_KEY = "claims"
ACTIVE_TRACE_ELEMENT_SESSION_KEY = "active_trace_element"


@dataclass
class StoredClaim:
    response: dict
    trace_steps: list[dict] | None
    sequence_number: int
    claim_year: int


def get_stored_claims() -> dict[str, StoredClaim]:
    return cl.user_session.get(CLAIMS_SESSION_KEY) or {}


def store_claim(claim_id: str, response: dict, trace_steps: list[dict] | None) -> StoredClaim:
    claims = get_stored_claims()
    stored_claim = StoredClaim(
        response=response,
        trace_steps=trace_steps,
        sequence_number=len(claims) + 1,
        claim_year=datetime.now(UTC).year,
    )
    claims[claim_id] = stored_claim
    cl.user_session.set(CLAIMS_SESSION_KEY, claims)
    return stored_claim


def get_active_trace_element() -> cl.Text | None:
    return cl.user_session.get(ACTIVE_TRACE_ELEMENT_SESSION_KEY)


def set_active_trace_element(trace_element: cl.Text) -> None:
    cl.user_session.set(ACTIVE_TRACE_ELEMENT_SESSION_KEY, trace_element)
