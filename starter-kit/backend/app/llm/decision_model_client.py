"""Thin async client for the Jev decision model served through OpenRouter's
Decisions API. Jev answers typed questions against a shared state and returns
calibrated probabilities; it generates no free text.
"""

import httpx

from app.constants.decision.decision_model_config import (
    DECISION_ENDPOINT_DEFAULT,
    DECISION_MODEL_DEFAULT,
    DECISION_REQUEST_TIMEOUT_SECONDS,
)

_MODEL_REQUEST_FIELD = "model"
_STATE_REQUEST_FIELD = "state"
_QUESTIONS_REQUEST_FIELD = "questions"

_ANSWERS_FIELD = "answers"
_NOUL_FIELD = "noul"
_CHOICE_FIELD = "choice"

_AUTHORIZATION_HEADER = "Authorization"
_CONTENT_TYPE_HEADER = "Content-Type"
_JSON_CONTENT_TYPE = "application/json"
_BEARER_TOKEN_PREFIX = "Bearer "


class DecisionModelClient:
    """Issues one typed-questions batch to Jev per claim stage."""

    def __init__(
        self,
        api_key: str,
        model: str = DECISION_MODEL_DEFAULT,
        endpoint: str = DECISION_ENDPOINT_DEFAULT,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._endpoint = endpoint
        self._transport = transport

    async def decide(self, state: object, questions: dict[str, dict]) -> dict[str, dict]:
        """Score every question against ``state``; return answers keyed by question id.

        ``state`` is text, a structured object, or an array of text/image parts
        (an image is passed inline as an OpenAI-style ``image_url`` part).
        """
        request_body = {
            _MODEL_REQUEST_FIELD: self._model,
            _STATE_REQUEST_FIELD: state,
            _QUESTIONS_REQUEST_FIELD: questions,
        }
        headers = {
            _AUTHORIZATION_HEADER: f"{_BEARER_TOKEN_PREFIX}{self._api_key}",
            _CONTENT_TYPE_HEADER: _JSON_CONTENT_TYPE,
        }
        async with httpx.AsyncClient(
            transport=self._transport,
            timeout=DECISION_REQUEST_TIMEOUT_SECONDS,
        ) as http:
            response = await http.post(self._endpoint, json=request_body, headers=headers)
            response.raise_for_status()
            return response.json().get(_ANSWERS_FIELD, {})


def noul_probability(answer: dict) -> float:
    """Probability that the Noul question's answer is "yes"."""
    return float(answer[_NOUL_FIELD])


def choice_label(answer: dict) -> str:
    """The single label a Choice question selected."""
    return str(answer[_CHOICE_FIELD])
