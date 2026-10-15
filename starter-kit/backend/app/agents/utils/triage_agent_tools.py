from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient

from app.constants.agent.triage_tool_names import (
    CHECK_COVERAGE_TOOL_NAME,
    ESTIMATE_REPAIR_COST_TOOL_NAME,
    SEARCH_PAST_CLAIMS_TOOL_NAME,
)
from app.constants.claims.area_counting_rule import AREA_COUNTING_RULE
from app.constants.claims.claim_taxonomy import DamageType, PolicyType, SeverityLevel
from app.rag.embedder import ClaimEmbedder
from app.tools.claim_search import search_past_claims
from app.tools.cost_estimator import estimate_repair_cost
from app.tools.coverage_checker import check_coverage


class SearchPastClaimsInput(BaseModel):
    query: str = Field(description="Natural language description of the damage.")


class EstimateRepairCostInput(BaseModel):
    damage_type: DamageType
    severity: SeverityLevel
    affected_areas: list[str] = Field(
        description=f"Distinct rooms or exterior components affected. {AREA_COUNTING_RULE}"
    )


class CheckCoverageInput(BaseModel):
    policy_type: PolicyType
    incident_category: DamageType


def build_triage_agent_tools(
    client: QdrantClient, embedder: ClaimEmbedder, cost_table: dict, coverage_table: dict
) -> list[BaseTool]:

    @tool(SEARCH_PAST_CLAIMS_TOOL_NAME, args_schema=SearchPastClaimsInput)
    def search_past_claims_tool(query: str) -> list[dict]:
        """Search the vector knowledge base of historical claims for similar incidents."""
        return search_past_claims(query, client, embedder)

    @tool(ESTIMATE_REPAIR_COST_TOOL_NAME, args_schema=EstimateRepairCostInput)
    def estimate_repair_cost_tool(
        damage_type: DamageType, severity: SeverityLevel, affected_areas: list[str]
    ) -> dict:
        """Estimate a repair cost range from damage_type, severity, and affected_areas."""
        return estimate_repair_cost(damage_type.value, severity.value, affected_areas, cost_table)

    @tool(CHECK_COVERAGE_TOOL_NAME, args_schema=CheckCoverageInput)
    def check_coverage_tool(policy_type: PolicyType, incident_category: DamageType) -> dict:
        """Check what a policy_type covers for an incident_category."""
        return check_coverage(policy_type.value, incident_category.value, coverage_table)

    return [search_past_claims_tool, estimate_repair_cost_tool, check_coverage_tool]
