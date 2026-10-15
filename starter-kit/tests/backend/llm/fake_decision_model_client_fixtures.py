"""Fake request inputs and canned Jev responses for exercising
``DecisionModelClient`` with no network access and no real API key.

The field names mirror the OpenRouter Decisions API wire format on purpose: the
client tests assert the literal request shape, so reusing the client's own
(private) field-name constants would make those assertions tautological.
"""

import json

import httpx

FAKE_OPENROUTER_API_KEY = "fake-decision-api-key"
FAKE_DECISION_MODEL = "fake/jev-test-model"
FAKE_DECISION_ENDPOINT = "https://decisions.example.test/api/alpha/decisions"

EXPECTED_HTTP_METHOD = "POST"

MODEL_REQUEST_FIELD = "model"
STATE_REQUEST_FIELD = "state"
QUESTIONS_REQUEST_FIELD = "questions"
ANSWERS_RESPONSE_FIELD = "answers"

AUTHORIZATION_HEADER = "Authorization"
CONTENT_TYPE_HEADER = "Content-Type"
JSON_CONTENT_TYPE = "application/json"
BEARER_TOKEN_PREFIX = "Bearer "
EXPECTED_BEARER_AUTHORIZATION = f"{BEARER_TOKEN_PREFIX}{FAKE_OPENROUTER_API_KEY}"

FAKE_CLAIM_STATE = "Water leaked under the kitchen sink and warped the cabinet."
FAKE_PROPERTY_DAMAGE_QUESTION_ID = "is_property_damage"
FAKE_DAMAGE_TYPE_QUESTION_ID = "damage_type"
FAKE_QUESTIONS = {
    FAKE_PROPERTY_DAMAGE_QUESTION_ID: {"type": "noul"},
    FAKE_DAMAGE_TYPE_QUESTION_ID: {
        "type": "choice",
        "criteria": ["water_damage", "fire_damage"],
    },
}

FAKE_NOUL_PROBABILITY = 0.92
FAKE_CHOICE_LABEL = "water_damage"
FAKE_ANSWERS = {
    FAKE_PROPERTY_DAMAGE_QUESTION_ID: {"noul": FAKE_NOUL_PROBABILITY, "confidence": 0.9},
    FAKE_DAMAGE_TYPE_QUESTION_ID: {"choice": FAKE_CHOICE_LABEL, "confidence": 0.8},
}
FAKE_SUCCESS_RESPONSE_BODY = {ANSWERS_RESPONSE_FIELD: FAKE_ANSWERS}

FAKE_NON_SUCCESS_STATUS_CODE = httpx.codes.BAD_REQUEST
FAKE_ERROR_RESPONSE_BODY = {"error": "malformed state"}


class RecordingDecisionTransport(httpx.AsyncBaseTransport):
    """Captures the outgoing request and replays one canned JSON response."""

    def __init__(
        self,
        response_body: dict,
        status_code: int = httpx.codes.OK,
    ) -> None:
        self._response_body = response_body
        self._status_code = status_code
        self.requests: list[httpx.Request] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(self._status_code, json=self._response_body, request=request)

    @property
    def last_request(self) -> httpx.Request:
        return self.requests[-1]

    @property
    def last_request_json(self) -> dict:
        return json.loads(self.last_request.content)
