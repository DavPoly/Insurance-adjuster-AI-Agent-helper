"""Fake coverage-table fixture data for `test_coverage_checker.py`.

Policy figures are defined once here and referenced (never re-typed) by the
test assertions.
"""

FAKE_POLICY_TYPE_HOME = "home"
FAKE_UNKNOWN_POLICY_TYPE = "spacecraft"

FAKE_INCIDENT_CATEGORY_COVERED = "fire"
FAKE_INCIDENT_CATEGORY_UNCOVERED = "flood"

FAKE_HOME_POLICY_DEDUCTIBLE = 1000
FAKE_HOME_POLICY_MAX_PAYOUT = 50000
FAKE_HOME_POLICY_NOTES = "Fake home policy notes for testing."

FAKE_COVERAGE_TABLE = {
    "policies": {
        FAKE_POLICY_TYPE_HOME: {
            "covered_categories": [FAKE_INCIDENT_CATEGORY_COVERED],
            "deductible": FAKE_HOME_POLICY_DEDUCTIBLE,
            "max_payout": FAKE_HOME_POLICY_MAX_PAYOUT,
            "notes": FAKE_HOME_POLICY_NOTES,
        }
    }
}

# A table with no "policies" key at all, for exercising the first .get(..., {}) fallback.
FAKE_COVERAGE_TABLE_MISSING_POLICIES_KEY: dict = {}

# A table with "policies" present, and the policy present, but that policy missing its
# "covered_categories" key, for exercising the policy.get("covered_categories", []) fallback.
FAKE_COVERAGE_TABLE_POLICY_MISSING_COVERED_CATEGORIES = {
    "policies": {
        FAKE_POLICY_TYPE_HOME: {
            "deductible": FAKE_HOME_POLICY_DEDUCTIBLE,
            "max_payout": FAKE_HOME_POLICY_MAX_PAYOUT,
            "notes": FAKE_HOME_POLICY_NOTES,
        }
    }
}
