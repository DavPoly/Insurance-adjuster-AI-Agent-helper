import asyncio

import httpx
import pytest

from app.constants.decision.decision_model_config import (
    DECISION_ENDPOINT_DEFAULT,
    DECISION_MODEL_DEFAULT,
)
from app.llm.decision_model_client import DecisionModelClient, choice_label, noul_probability
from llm.fake_decision_model_client_fixtures import (
    AUTHORIZATION_HEADER,
    CONTENT_TYPE_HEADER,
    EXPECTED_BEARER_AUTHORIZATION,
    EXPECTED_HTTP_METHOD,
    FAKE_ANSWERS,
    FAKE_CHOICE_LABEL,
    FAKE_CLAIM_STATE,
    FAKE_DAMAGE_TYPE_QUESTION_ID,
    FAKE_DECISION_ENDPOINT,
    FAKE_DECISION_MODEL,
    FAKE_ERROR_RESPONSE_BODY,
    FAKE_NON_SUCCESS_STATUS_CODE,
    FAKE_NOUL_PROBABILITY,
    FAKE_OPENROUTER_API_KEY,
    FAKE_PROPERTY_DAMAGE_QUESTION_ID,
    FAKE_QUESTIONS,
    FAKE_SUCCESS_RESPONSE_BODY,
    JSON_CONTENT_TYPE,
    MODEL_REQUEST_FIELD,
    QUESTIONS_REQUEST_FIELD,
    STATE_REQUEST_FIELD,
    RecordingDecisionTransport,
)


def build_client(transport: RecordingDecisionTransport) -> DecisionModelClient:
    return DecisionModelClient(
        api_key=FAKE_OPENROUTER_API_KEY,
        model=FAKE_DECISION_MODEL,
        endpoint=FAKE_DECISION_ENDPOINT,
        transport=transport,
    )


def test_decide_posts_the_model_state_and_questions_payload():
    transport = RecordingDecisionTransport(FAKE_SUCCESS_RESPONSE_BODY)

    asyncio.run(build_client(transport).decide(FAKE_CLAIM_STATE, FAKE_QUESTIONS))

    assert transport.last_request.method == EXPECTED_HTTP_METHOD
    assert transport.last_request_json == {
        MODEL_REQUEST_FIELD: FAKE_DECISION_MODEL,
        STATE_REQUEST_FIELD: FAKE_CLAIM_STATE,
        QUESTIONS_REQUEST_FIELD: FAKE_QUESTIONS,
    }


def test_decide_posts_to_the_configured_endpoint():
    transport = RecordingDecisionTransport(FAKE_SUCCESS_RESPONSE_BODY)

    asyncio.run(build_client(transport).decide(FAKE_CLAIM_STATE, FAKE_QUESTIONS))

    assert str(transport.last_request.url) == FAKE_DECISION_ENDPOINT


def test_decide_authenticates_with_the_bearer_api_key():
    transport = RecordingDecisionTransport(FAKE_SUCCESS_RESPONSE_BODY)

    asyncio.run(build_client(transport).decide(FAKE_CLAIM_STATE, FAKE_QUESTIONS))

    assert transport.last_request.headers[AUTHORIZATION_HEADER] == EXPECTED_BEARER_AUTHORIZATION
    assert transport.last_request.headers[CONTENT_TYPE_HEADER] == JSON_CONTENT_TYPE


def test_decide_returns_answers_keyed_by_question_id():
    transport = RecordingDecisionTransport(FAKE_SUCCESS_RESPONSE_BODY)

    answers = asyncio.run(build_client(transport).decide(FAKE_CLAIM_STATE, FAKE_QUESTIONS))

    assert answers == FAKE_ANSWERS


def test_decide_raises_on_non_success_response():
    transport = RecordingDecisionTransport(
        FAKE_ERROR_RESPONSE_BODY,
        status_code=FAKE_NON_SUCCESS_STATUS_CODE,
    )

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(build_client(transport).decide(FAKE_CLAIM_STATE, FAKE_QUESTIONS))


def test_decide_defaults_to_the_configured_model_and_endpoint():
    transport = RecordingDecisionTransport(FAKE_SUCCESS_RESPONSE_BODY)
    client = DecisionModelClient(api_key=FAKE_OPENROUTER_API_KEY, transport=transport)

    asyncio.run(client.decide(FAKE_CLAIM_STATE, FAKE_QUESTIONS))

    assert transport.last_request_json[MODEL_REQUEST_FIELD] == DECISION_MODEL_DEFAULT
    assert str(transport.last_request.url) == DECISION_ENDPOINT_DEFAULT


def test_noul_probability_reads_the_noul_field():
    answer = FAKE_ANSWERS[FAKE_PROPERTY_DAMAGE_QUESTION_ID]

    assert noul_probability(answer) == FAKE_NOUL_PROBABILITY


def test_choice_label_reads_the_choice_field():
    answer = FAKE_ANSWERS[FAKE_DAMAGE_TYPE_QUESTION_ID]

    assert choice_label(answer) == FAKE_CHOICE_LABEL
