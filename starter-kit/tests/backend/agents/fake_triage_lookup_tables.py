"""Minimal fake cost/coverage lookup tables for exercising the deterministic
triage pipeline's tool wiring. The pure lookup logic itself is covered by
tests/backend/tools/test_cost_estimator.py and test_coverage_checker.py.
"""

FAKE_WATER_DAMAGE_MINOR_MIN_PER_AREA = 500
FAKE_WATER_DAMAGE_MINOR_MAX_PER_AREA = 2000

FAKE_COST_TABLE = {
    "cost_matrix": {
        "water_damage": {
            "minor": {
                "min_per_area": FAKE_WATER_DAMAGE_MINOR_MIN_PER_AREA,
                "max_per_area": FAKE_WATER_DAMAGE_MINOR_MAX_PER_AREA,
            }
        }
    }
}

FAKE_STANDARD_HOMEOWNER_DEDUCTIBLE = 1500
FAKE_STANDARD_HOMEOWNER_MAX_PAYOUT = 250000
FAKE_STANDARD_HOMEOWNER_NOTES = "Fake standard coverage notes."

FAKE_COVERAGE_TABLE = {
    "policies": {
        "standard_homeowner": {
            "covered_categories": ["fire_damage"],
            "deductible": FAKE_STANDARD_HOMEOWNER_DEDUCTIBLE,
            "max_payout": FAKE_STANDARD_HOMEOWNER_MAX_PAYOUT,
            "notes": FAKE_STANDARD_HOMEOWNER_NOTES,
        }
    }
}
