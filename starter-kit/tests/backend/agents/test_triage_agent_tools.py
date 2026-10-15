from fake_triage_lookup_tables import (
    FAKE_COST_TABLE,
    FAKE_COVERAGE_TABLE,
    FAKE_STANDARD_HOMEOWNER_DEDUCTIBLE,
    FAKE_STANDARD_HOMEOWNER_MAX_PAYOUT,
    FAKE_STANDARD_HOMEOWNER_NOTES,
    FAKE_WATER_DAMAGE_MINOR_MAX_PER_AREA,
    FAKE_WATER_DAMAGE_MINOR_MIN_PER_AREA,
)
from fake_triage_qdrant_client import (
    FAKE_SEARCH_POINT,
    FAKE_SEARCH_QUERY,
    FAKE_SEARCH_TOOL_RESULT,
    FakeTriageEmbedder,
    FakeTriageQdrantClient,
)

from app.agents.utils.triage_agent_tools import build_triage_agent_tools
from app.constants.agent.triage_tool_names import (
    CHECK_COVERAGE_TOOL_NAME,
    ESTIMATE_REPAIR_COST_TOOL_NAME,
    SEARCH_PAST_CLAIMS_TOOL_NAME,
)
from app.constants.tools.cost_estimate_currency import DEFAULT_CURRENCY


def _build_tools() -> dict:
    client = FakeTriageQdrantClient([FAKE_SEARCH_POINT])
    embedder = FakeTriageEmbedder()
    tools = build_triage_agent_tools(client, embedder, FAKE_COST_TABLE, FAKE_COVERAGE_TABLE)
    return {tool.name: tool for tool in tools}


def test_build_triage_agent_tools_returns_the_three_required_tools():
    tools = _build_tools()

    assert set(tools) == {
        SEARCH_PAST_CLAIMS_TOOL_NAME,
        ESTIMATE_REPAIR_COST_TOOL_NAME,
        CHECK_COVERAGE_TOOL_NAME,
    }


def test_search_past_claims_tool_delegates_to_the_vector_store_collaborators():
    tools = _build_tools()

    result = tools[SEARCH_PAST_CLAIMS_TOOL_NAME].invoke({"query": FAKE_SEARCH_QUERY})

    assert result == [FAKE_SEARCH_TOOL_RESULT]


def test_estimate_repair_cost_tool_converts_enum_args_to_plain_strings():
    tools = _build_tools()

    result = tools[ESTIMATE_REPAIR_COST_TOOL_NAME].invoke(
        {"damage_type": "water_damage", "severity": "minor", "affected_areas": ["kitchen"]}
    )

    assert result == {
        "min": FAKE_WATER_DAMAGE_MINOR_MIN_PER_AREA,
        "max": FAKE_WATER_DAMAGE_MINOR_MAX_PER_AREA,
        "currency": DEFAULT_CURRENCY,
    }


def test_check_coverage_tool_converts_enum_args_to_plain_strings():
    tools = _build_tools()

    result = tools[CHECK_COVERAGE_TOOL_NAME].invoke(
        {"policy_type": "standard_homeowner", "incident_category": "fire_damage"}
    )

    assert result == {
        "covered": True,
        "deductible": FAKE_STANDARD_HOMEOWNER_DEDUCTIBLE,
        "max_payout": FAKE_STANDARD_HOMEOWNER_MAX_PAYOUT,
        "notes": FAKE_STANDARD_HOMEOWNER_NOTES,
    }
