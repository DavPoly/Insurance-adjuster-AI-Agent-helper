"""Thin async client for the Jev decision model served through OpenRouter's
Decisions API. Jev answers typed questions against a shared state and returns
calibrated probabilities; it generates no free text.
"""

import httpx

from app.constants.decision.decision_model_config import (
    DECISION_ENDPOINT_DEFAULT,
    DECISION_MODEL_DEFAULT,
    DECISION_PROBABILITY_THRESHOLD,
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
        # Reused across calls so repeated requests pool/keep-alive connections
        # instead of paying a fresh TCP+TLS handshake every time.
        self._client = httpx.AsyncClient(
            transport=transport,
            timeout=DECISION_REQUEST_TIMEOUT_SECONDS,
        )

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
        response = await self._client.post(self._endpoint, json=request_body, headers=headers)
        response.raise_for_status()
        return response.json().get(_ANSWERS_FIELD, {})

    async def aclose(self) -> None:
        """Release the pooled connections; the client cannot send requests afterwards."""
        await self._client.aclose()


def noul_answer_is_yes(answers: dict, question_id: str) -> bool:
    """Whether the Noul question's answer reads as "yes" at the configured threshold.

    Raises a descriptive :class:`ValueError` naming the question id when the
    provider returned no answer for it, instead of a bare ``KeyError``; a present
    but malformed answer (a ``null`` or non-numeric probability) raises the same
    from :func:`noul_probability`.
    """
    if question_id not in answers:
        raise ValueError(f"Decision model returned no answer for question '{question_id}'.")
    return noul_probability(answers[question_id], question_id) >= DECISION_PROBABILITY_THRESHOLD


def noul_probability(answer: dict, question_id: str | None = None) -> float:
    """Probability that the Noul question's answer is "yes".

    ``question_id`` is optional context that names the question in error
    messages. A malformed answer payload — no ``noul`` field, a ``null``
    probability, or a non-numeric value — raises a descriptive
    :class:`ValueError` rather than failing obscurely downstream.
    """
    if _NOUL_FIELD not in answer:
        raise ValueError(
            f"{_answer_description(question_id)} is missing the '{_NOUL_FIELD}' probability field."
        )
    probability = answer[_NOUL_FIELD]
    if probability is None:
        raise ValueError(
            f"{_answer_description(question_id)} has a null '{_NOUL_FIELD}' probability."
        )
    try:
        return float(probability)
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"{_answer_description(question_id)} has a non-numeric '{_NOUL_FIELD}' "
            f"probability {probability!r}."
        ) from error


def choice_label(answer: dict, question_id: str | None = None) -> str:
    """The single label a Choice question selected.

    ``question_id`` is optional context that names the question in error
    messages. A malformed answer payload — no ``choice`` field or a ``null``
    label — raises a descriptive :class:`ValueError`.
    """
    if _CHOICE_FIELD not in answer:
        raise ValueError(
            f"{_answer_description(question_id)} is missing the '{_CHOICE_FIELD}' label field."
        )
    label = answer[_CHOICE_FIELD]
    if label is None:
        raise ValueError(f"{_answer_description(question_id)} has a null '{_CHOICE_FIELD}' label.")
    return str(label)


def _answer_description(question_id: str | None) -> str:
    if question_id is None:
        return "Decision answer"
    return f"Decision answer for question '{question_id}'"
