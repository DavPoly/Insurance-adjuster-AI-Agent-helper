from contextlib import ExitStack

import httpx

from api_client.backend_api_routes import (
    AGENT_TRACE_ROUTE_PATH_TEMPLATE,
    TRIAGE_SUBMISSION_ROUTE_PATH,
)

TRIAGE_REQUEST_TIMEOUT_SECONDS = 120.0


async def submit_triage_claim(
    base_url: str,
    *,
    description: str,
    policy_type: str,
    image_paths: list[str],
    document_path: str | None,
) -> httpx.Response:
    data = {"policy_type": policy_type}
    if description:
        data["description"] = description

    with ExitStack() as stack:
        files = []
        for image_path in image_paths:
            handle = stack.enter_context(open(image_path, "rb"))
            files.append(("images", (image_path, handle)))
        if document_path is not None:
            handle = stack.enter_context(open(document_path, "rb"))
            files.append(("document", (document_path, handle)))

        async with httpx.AsyncClient(timeout=TRIAGE_REQUEST_TIMEOUT_SECONDS) as client:
            return await client.post(
                base_url + TRIAGE_SUBMISSION_ROUTE_PATH,
                data=data,
                files=files or None,
            )


async def fetch_agent_trace(base_url: str, claim_id: str) -> httpx.Response:
    path = AGENT_TRACE_ROUTE_PATH_TEMPLATE.format(claim_id=claim_id)
    async with httpx.AsyncClient(timeout=TRIAGE_REQUEST_TIMEOUT_SECONDS) as client:
        return await client.get(base_url + path)
