"""Hand-written adjuster-style queries for evaluating search_past_claims recall
against the real starter-kit/data/knowledge-base/*.json records.

Each query describes a damage scenario in general terms (cause, location,
severity) rather than reusing the specific nouns a knowledge-base record uses
for itself (e.g. "an old appliance", not "a 12-year-old hot water heater"), so
the eval measures semantic generalization rather than near-paraphrase matching.
Because the queries are broader, more than one historical claim can be a
legitimately correct match; expected_claim_ids lists every claim that is a
defensible top result for that query, not just the single closest record.
"""

from typing import NamedTuple


class ClaimSearchEvalCase(NamedTuple):
    query: str
    expected_claim_ids: tuple[str, ...]


CLAIM_SEARCH_EVAL_CASES: list[ClaimSearchEvalCase] = [
    ClaimSearchEvalCase(
        query=(
            "Homeowner found standing water in the basement after an old "
            "appliance stopped working properly."
        ),
        expected_claim_ids=("CLM-2024-017", "CLM-2024-022"),
    ),
    ClaimSearchEvalCase(
        query="An unnoticed plumbing leak caused water damage to the kitchen floor and cabinetry.",
        expected_claim_ids=("CLM-2023-001", "CLM-2024-025"),
    ),
    ClaimSearchEvalCase(
        query=(
            "Heavy rainfall overwhelmed a home's drainage system, flooding the "
            "lower level and ruining furniture and belongings."
        ),
        expected_claim_ids=("CLM-2024-022",),
    ),
    ClaimSearchEvalCase(
        query=(
            "Water intrusion from the roof during a storm left visible "
            "staining inside an upstairs room."
        ),
        expected_claim_ids=("CLM-2023-002", "CLM-2024-023"),
    ),
    ClaimSearchEvalCase(
        query=(
            "A cooking-related fire in the kitchen spread and caused "
            "significant damage to nearby rooms."
        ),
        expected_claim_ids=("CLM-2023-003",),
    ),
    ClaimSearchEvalCase(
        query=(
            "A severe weather event triggered an electrical fire that damaged "
            "the upper floors of the home."
        ),
        expected_claim_ids=("CLM-2024-020",),
    ),
    ClaimSearchEvalCase(
        query=(
            "An appliance malfunction in the laundry area started a small "
            "fire that caused smoke damage nearby."
        ),
        expected_claim_ids=("CLM-2024-027",),
    ),
    ClaimSearchEvalCase(
        query="Severe weather caused impact damage to the roof and an attached structure.",
        expected_claim_ids=("CLM-2023-004", "CLM-2023-008"),
    ),
    ClaimSearchEvalCase(
        query=(
            "An extreme windstorm caused catastrophic structural damage to the "
            "home's exterior and upper levels."
        ),
        expected_claim_ids=("CLM-2024-016",),
    ),
    ClaimSearchEvalCase(
        query=(
            "Storm winds knocked over a large tree that crushed part of an "
            "outbuilding on the property."
        ),
        expected_claim_ids=("CLM-2023-008",),
    ),
    ClaimSearchEvalCase(
        query=(
            "Someone forced their way into the home while the residents were "
            "away and damaged the entry and interior rooms."
        ),
        expected_claim_ids=("CLM-2023-005", "CLM-2024-024"),
    ),
    ClaimSearchEvalCase(
        query=(
            "A break-in occurred through a rear window while no one was home, "
            "and a small amount of money was missing afterward."
        ),
        expected_claim_ids=("CLM-2023-011",),
    ),
    ClaimSearchEvalCase(
        query="The exterior of the property was defaced with unauthorized markings.",
        expected_claim_ids=("CLM-2023-009",),
    ),
    ClaimSearchEvalCase(
        query=(
            "Gradual structural shifting led to visible cracking and "
            "settling issues in part of the house."
        ),
        expected_claim_ids=("CLM-2023-014",),
    ),
]
