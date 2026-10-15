"""Fake cost-matrix fixture data for `test_cost_estimator.py`.

Per-area cost figures are defined once here and referenced (never re-typed) by
the test assertions, including the multi-area expected totals.
"""

FAKE_WATER_DAMAGE_MINOR_MIN_PER_AREA = 500
FAKE_WATER_DAMAGE_MINOR_MAX_PER_AREA = 2000
FAKE_WATER_DAMAGE_MODERATE_MIN_PER_AREA = 2000
FAKE_WATER_DAMAGE_MODERATE_MAX_PER_AREA = 8000

FAKE_COST_TABLE = {
    "cost_matrix": {
        "water_damage": {
            "minor": {
                "min_per_area": FAKE_WATER_DAMAGE_MINOR_MIN_PER_AREA,
                "max_per_area": FAKE_WATER_DAMAGE_MINOR_MAX_PER_AREA,
            },
            "moderate": {
                "min_per_area": FAKE_WATER_DAMAGE_MODERATE_MIN_PER_AREA,
                "max_per_area": FAKE_WATER_DAMAGE_MODERATE_MAX_PER_AREA,
            },
        }
    }
}

# A table with no "cost_matrix" key at all, for exercising the first .get(..., {}) fallback.
FAKE_COST_TABLE_MISSING_COST_MATRIX_KEY: dict = {}

# A table with "cost_matrix" present but the requested damage_type absent, for
# exercising the second .get(..., {}) fallback.
FAKE_COST_TABLE_MISSING_DAMAGE_TYPE = {"cost_matrix": {}}

FAKE_DISTINCT_AREA_COUNT_TWO = 2
