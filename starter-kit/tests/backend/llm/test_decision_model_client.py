import asyncio

import httpx
import pytest

from app.constants.decision.decision_model_config import (
    DECISION_ENDPOINT_DEFAULT,
    DECISION_MODEL_DEFAULT,
)
from app.llm.decision_model_client import (
    DecisionModelClient,
    choice_label,
    noul_answer_is_yes,
    noul_probability,
)
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
    FAKE_MISSING_CHOICE_ANSWERS,
    FAKE_MISSING_PROBABILITY_ANSWERS,
    FAKE_NON_NUMERIC_PROBABILITY_ANSWERS,
    FAKE_NON_SUCCESS_STATUS_CODE,
    FAKE_NOUL_PROBABILITY,
    FAKE_NULL_CHOICE_ANSWERS,
    FAKE_NULL_PROBABILITY_ANSWERS,
    FAKE_OPENROUTER_API_KEY,
    FAKE_PROPERTY_DAMAGE_QUESTION_ID,
    FAKE_QUESTIONS,
    FAKE_SUCCESS_RESPONSE_BODY,
    FAKE_UNANSWERED_QUESTION_ID,
    JSON_CONTENT_TYPE,
    JUST_BELOW_THRESHOLD_PROBABILITY,
    MODEL_REQUEST_FIELD,
    NOUL_ANSWER_FIELD,
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


def test_decide_raises_after_the_client_is_closed():
    client = build_client(RecordingDecisionTransport(FAKE_SUCCESS_RESPONSE_BODY))

    async def close_then_decide():
        await client.aclose()
        await client.decide(FAKE_CLAIM_STATE, FAKE_QUESTIONS)

    with pytest.raises(RuntimeError):
        asyncio.run(close_then_decide())


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


def test_noul_answer_is_yes_thresholds_the_named_question():
    assert noul_answer_is_yes(FAKE_ANSWERS, FAKE_PROPERTY_DAMAGE_QUESTION_ID) is True

    below_threshold = {FAKE_PROPERTY_DAMAGE_QUESTION_ID: {"noul": JUST_BELOW_THRESHOLD_PROBABILITY}}
    assert noul_answer_is_yes(below_threshold, FAKE_PROPERTY_DAMAGE_QUESTION_ID) is False


def test_noul_answer_is_yes_names_a_question_the_model_left_unanswered():
    with pytest.raises(ValueError, match=FAKE_UNANSWERED_QUESTION_ID):
        noul_answer_is_yes(FAKE_ANSWERS, FAKE_UNANSWERED_QUESTION_ID)


def test_noul_answer_is_yes_rejects_a_null_probability():
    with pytest.raises(ValueError, match=FAKE_PROPERTY_DAMAGE_QUESTION_ID):
        noul_answer_is_yes(FAKE_NULL_PROBABILITY_ANSWERS, FAKE_PROPERTY_DAMAGE_QUESTION_ID)


def test_noul_answer_is_yes_rejects_a_non_numeric_probability():
    with pytest.raises(ValueError, match=FAKE_PROPERTY_DAMAGE_QUESTION_ID):
        noul_answer_is_yes(FAKE_NON_NUMERIC_PROBABILITY_ANSWERS, FAKE_PROPERTY_DAMAGE_QUESTION_ID)


def test_noul_probability_rejects_a_missing_noul_field():
    answer = FAKE_MISSING_PROBABILITY_ANSWERS[FAKE_PROPERTY_DAMAGE_QUESTION_ID]

    with pytest.raises(ValueError, match=NOUL_ANSWER_FIELD):
        noul_probability(answer, FAKE_PROPERTY_DAMAGE_QUESTION_ID)


def test_choice_label_rejects_a_null_label():
    answer = FAKE_NULL_CHOICE_ANSWERS[FAKE_DAMAGE_TYPE_QUESTION_ID]

    with pytest.raises(ValueError, match=FAKE_DAMAGE_TYPE_QUESTION_ID):
        choice_label(answer, FAKE_DAMAGE_TYPE_QUESTION_ID)


def test_choice_label_rejects_a_missing_choice_field():
    answer = FAKE_MISSING_CHOICE_ANSWERS[FAKE_DAMAGE_TYPE_QUESTION_ID]

    with pytest.raises(ValueError, match=FAKE_DAMAGE_TYPE_QUESTION_ID):
        choice_label(answer, FAKE_DAMAGE_TYPE_QUESTION_ID)
