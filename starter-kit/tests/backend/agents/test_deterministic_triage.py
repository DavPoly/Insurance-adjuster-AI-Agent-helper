"""Tests for the deterministic triage orchestrator.

No HTTP and no real model: a fake chat model answers the single synthesis call,
a recording fake answers node 4's safety questions, and recording fakes wrap the
shared qdrant/embedder fixtures. The tests pin the properties the router relies
on — node 1 is threaded in rather than re-called, each tool runs exactly once
with node-1-derived arguments, synthesis runs once, node 4 scores the
synthesized free text, and the trace reconstructs reason/act/observe steps.
"""

import asyncio

from deterministic_triage_test_fixtures import (
    AFFECTED_AREAS_ARGUMENT,
    DAMAGE_TYPE_ARGUMENT,
    EXPECTED_COVERAGE_RESULT,
    EXPECTED_PAST_CLAIMS_RESULT,
    EXPECTED_REPAIR_COST_MAX,
    EXPECTED_REPAIR_COST_MIN,
    FAILING_NOUL_PROBABILITY,
    FAKE_DRAFTED_RESOLUTION_SUMMARY,
    FAKE_SYNTHESIZED_DAMAGE_DESCRIPTION,
    FAKE_SYNTHESIZED_RECOMMENDATION,
    FAKE_TRIAGE_PRIMARY_AREA,
    FAKE_WATER_DAMAGE_MINOR_MAX_PER_AREA,
    FAKE_WATER_DAMAGE_MINOR_MIN_PER_AREA,
    INCIDENT_CATEGORY_ARGUMENT,
    POLICY_TYPE_ARGUMENT,
    SEARCH_QUERY_ARGUMENT,
    SEVERITY_ARGUMENT,
    CountingSynthesisChatModel,
    RecordingSafetyDecisionClient,
    RecordingTriageEmbedder,
    RecordingTriageQdrantClient,
    all_passing_safety_checks,
    build_claim_decision,
    build_submission,
    build_synthesis_draft,
)
from fake_triage_lookup_tables import FAKE_COST_TABLE, FAKE_COVERAGE_TABLE
from fake_triage_qdrant_client import (
    FAKE_SEARCH_CLAIM_ID,
    FAKE_SEARCH_POINT,
    FAKE_SEARCH_SIMILARITY_SCORE,
)

from app.agents.deterministic_triage import (
    DeterministicTriageResult,
    run_deterministic_triage,
    safety_checks_passed,
)
from app.agents.prompts.safety_decision_questions import (
    NO_COVERAGE_PROMISES_QUESTION_ID,
    SAFETY_DECISION_QUESTIONS,
)
from app.agents.triage_synthesis import synthesize_triage_assessment
from app.constants.agent.agent_trace_step_types import (
    ACT_STEP_TYPE,
    OBSERVE_STEP_TYPE,
    REASON_STEP_TYPE,
)
from app.constants.agent.deterministic_pipeline_step_names import (
    CLAIM_DECISION_STEP_NAME,
    OUTPUT_SAFETY_STEP_NAME,
    TRIAGE_SYNTHESIS_STEP_NAME,
)
from app.constants.agent.triage_tool_names import (
    CHECK_COVERAGE_TOOL_NAME,
    ESTIMATE_REPAIR_COST_TOOL_NAME,
    SEARCH_PAST_CLAIMS_TOOL_NAME,
)
from app.constants.tools.cost_estimate_currency import DEFAULT_CURRENCY


def _run_pipeline(
    submission,
    claim_decision,
    llm,
    decision_client,
    qdrant_client,
    embedder,
) -> DeterministicTriageResult:
    return asyncio.run(
        run_deterministic_triage(
            submission=submission,
            claim_decision=claim_decision,
            llm=llm,
            decision_client=decision_client,
            client=qdrant_client,
            embedder=embedder,
            cost_table=FAKE_COST_TABLE,
            coverage_table=FAKE_COVERAGE_TABLE,
        )
    )


def _build_dependencies() -> tuple:
    return (
        CountingSynthesisChatModel(build_synthesis_draft()),
        RecordingSafetyDecisionClient(),
        RecordingTriageQdrantClient([FAKE_SEARCH_POINT]),
        RecordingTriageEmbedder(),
    )


def _act_step(steps: list[dict], tool_name: str) -> dict:
    return next(step for step in steps if step.get("tool_name") == tool_name)


def _observation_following(steps: list[dict], tool_name: str) -> dict:
    act_index = next(
        index for index, step in enumerate(steps) if step.get("tool_name") == tool_name
    )
    return steps[act_index + 1]


def test_run_deterministic_triage_runs_each_step_once_with_node_1_arguments():
    submission = build_submission()
    claim_decision = build_claim_decision()
    llm, decision_client, qdrant_client, embedder = _build_dependencies()

    result = _run_pipeline(
        submission, claim_decision, llm, decision_client, qdrant_client, embedder
    )

    # node 1 was threaded in from the request parser, so only node 4 hit the client.
    assert decision_client.call_count == 1
    assert decision_client.observed_questions is SAFETY_DECISION_QUESTIONS

    # each deterministic tool ran exactly once; search was keyed on the raw description.
    assert embedder.observed_queries == [submission.description]
    assert len(qdrant_client.observed_collection_names) == 1

    # exactly one synthesis call, and node 4 scored the synthesized free text.
    assert llm.synthesis_invoke_count == 1
    assert isinstance(decision_client.observed_state, str)
    assert FAKE_SYNTHESIZED_DAMAGE_DESCRIPTION in decision_client.observed_state
    assert FAKE_SYNTHESIZED_RECOMMENDATION in decision_client.observed_state

    assert isinstance(result, DeterministicTriageResult)
    assert result.triage_assessment["damage_type"] == claim_decision.damage_type.value
    assert result.triage_assessment["severity"] == claim_decision.severity.value
    assert result.triage_assessment["affected_areas"] == claim_decision.affected_areas
    assert result.triage_assessment["estimated_repair_cost"] == {
        "min": EXPECTED_REPAIR_COST_MIN,
        "max": EXPECTED_REPAIR_COST_MAX,
        "currency": DEFAULT_CURRENCY,
    }
    assert result.triage_assessment["similar_past_claims"] == [
        {
            "claim_id": FAKE_SEARCH_CLAIM_ID,
            "similarity_score": FAKE_SEARCH_SIMILARITY_SCORE,
            "resolution_summary": FAKE_DRAFTED_RESOLUTION_SUMMARY,
        }
    ]
    assert result.safety_checks == all_passing_safety_checks()
    # the carried explicit synthesis inputs mirror node 1 and the tool results.
    assert result.classification == claim_decision
    assert result.tool_results.repair_cost_estimate == {
        "min": EXPECTED_REPAIR_COST_MIN,
        "max": EXPECTED_REPAIR_COST_MAX,
        "currency": DEFAULT_CURRENCY,
    }
    assert result.tool_results.similar_past_claims == EXPECTED_PAST_CLAIMS_RESULT
    assert result.tool_results.coverage == EXPECTED_COVERAGE_RESULT


def test_run_deterministic_triage_records_reason_act_observe_per_step():
    submission = build_submission()
    claim_decision = build_claim_decision()
    llm, decision_client, qdrant_client, embedder = _build_dependencies()

    result = _run_pipeline(
        submission, claim_decision, llm, decision_client, qdrant_client, embedder
    )
    steps = result.trace_steps

    assert [step["type"] for step in steps] == [
        REASON_STEP_TYPE,
        ACT_STEP_TYPE,
        OBSERVE_STEP_TYPE,
    ] * 6
    assert [step["step_number"] for step in steps] == list(range(1, len(steps) + 1))

    act_steps = [step for step in steps if step["type"] == ACT_STEP_TYPE]
    assert [step["tool_name"] for step in act_steps] == [
        CLAIM_DECISION_STEP_NAME,
        SEARCH_PAST_CLAIMS_TOOL_NAME,
        ESTIMATE_REPAIR_COST_TOOL_NAME,
        CHECK_COVERAGE_TOOL_NAME,
        TRIAGE_SYNTHESIS_STEP_NAME,
        OUTPUT_SAFETY_STEP_NAME,
    ]

    assert _act_step(steps, SEARCH_PAST_CLAIMS_TOOL_NAME)["tool_input"] == {
        SEARCH_QUERY_ARGUMENT: submission.description
    }
    assert _act_step(steps, ESTIMATE_REPAIR_COST_TOOL_NAME)["tool_input"] == {
        DAMAGE_TYPE_ARGUMENT: claim_decision.damage_type.value,
        SEVERITY_ARGUMENT: claim_decision.severity.value,
        AFFECTED_AREAS_ARGUMENT: claim_decision.affected_areas,
    }
    assert _act_step(steps, CHECK_COVERAGE_TOOL_NAME)["tool_input"] == {
        POLICY_TYPE_ARGUMENT: submission.policy_type.value,
        INCIDENT_CATEGORY_ARGUMENT: claim_decision.damage_type.value,
    }
    assert "tool_input" not in _act_step(steps, TRIAGE_SYNTHESIS_STEP_NAME)

    assert _observation_following(steps, CLAIM_DECISION_STEP_NAME)["tool_output"] == (
        claim_decision.model_dump(mode="json")
    )
    assert (
        _observation_following(steps, SEARCH_PAST_CLAIMS_TOOL_NAME)["tool_output"]
        == EXPECTED_PAST_CLAIMS_RESULT
    )
    assert _observation_following(steps, ESTIMATE_REPAIR_COST_TOOL_NAME)["tool_output"] == {
        "min": EXPECTED_REPAIR_COST_MIN,
        "max": EXPECTED_REPAIR_COST_MAX,
        "currency": DEFAULT_CURRENCY,
    }
    assert (
        _observation_following(steps, CHECK_COVERAGE_TOOL_NAME)["tool_output"]
        == EXPECTED_COVERAGE_RESULT
    )
    assert (
        _observation_following(steps, TRIAGE_SYNTHESIS_STEP_NAME)["tool_output"]
        == result.triage_assessment
    )
    assert _observation_following(steps, OUTPUT_SAFETY_STEP_NAME)["tool_output"] == (
        all_passing_safety_checks().model_dump()
    )


def test_run_deterministic_triage_keys_the_cost_tool_on_the_threaded_decision():
    claim_decision = build_claim_decision(affected_areas=[FAKE_TRIAGE_PRIMARY_AREA])
    llm, decision_client, qdrant_client, embedder = _build_dependencies()

    result = _run_pipeline(
        build_submission(), claim_decision, llm, decision_client, qdrant_client, embedder
    )

    assert result.triage_assessment["affected_areas"] == [FAKE_TRIAGE_PRIMARY_AREA]
    assert result.triage_assessment["estimated_repair_cost"] == {
        "min": FAKE_WATER_DAMAGE_MINOR_MIN_PER_AREA,
        "max": FAKE_WATER_DAMAGE_MINOR_MAX_PER_AREA,
        "currency": DEFAULT_CURRENCY,
    }


def test_run_deterministic_triage_returns_a_failing_safety_result_for_the_router_retry():
    decision_client = RecordingSafetyDecisionClient(
        {NO_COVERAGE_PROMISES_QUESTION_ID: FAILING_NOUL_PROBABILITY}
    )
    llm = CountingSynthesisChatModel(build_synthesis_draft())

    result = _run_pipeline(
        build_submission(),
        build_claim_decision(),
        llm,
        decision_client,
        RecordingTriageQdrantClient([FAKE_SEARCH_POINT]),
        RecordingTriageEmbedder(),
    )

    assert safety_checks_passed(result.safety_checks) is False
    assert result.safety_checks.no_coverage_promises is False
    # The router's bounded retry regenerates from the carried explicit inputs.
    assert (
        synthesize_triage_assessment(llm, result.classification, result.tool_results)
        == result.triage_assessment
    )


def test_safety_checks_passed_requires_every_check():
    assert safety_checks_passed(all_passing_safety_checks()) is True

    failing = all_passing_safety_checks().model_copy(update={"no_legal_advice": False})

    assert safety_checks_passed(failing) is False
