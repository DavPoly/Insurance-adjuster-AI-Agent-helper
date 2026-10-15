import pytest
from fake_coverage_table import (
    FAKE_COVERAGE_TABLE,
    FAKE_COVERAGE_TABLE_MISSING_POLICIES_KEY,
    FAKE_COVERAGE_TABLE_POLICY_MISSING_COVERED_CATEGORIES,
    FAKE_HOME_POLICY_DEDUCTIBLE,
    FAKE_HOME_POLICY_MAX_PAYOUT,
    FAKE_HOME_POLICY_NOTES,
    FAKE_INCIDENT_CATEGORY_COVERED,
    FAKE_INCIDENT_CATEGORY_UNCOVERED,
    FAKE_POLICY_TYPE_HOME,
    FAKE_UNKNOWN_POLICY_TYPE,
)

from app.tools.coverage_checker import check_coverage


def test_check_coverage_covered_category_on_known_policy():
    result = check_coverage(
        FAKE_POLICY_TYPE_HOME, FAKE_INCIDENT_CATEGORY_COVERED, FAKE_COVERAGE_TABLE
    )
    assert result == {
        "covered": True,
        "deductible": FAKE_HOME_POLICY_DEDUCTIBLE,
        "max_payout": FAKE_HOME_POLICY_MAX_PAYOUT,
        "notes": FAKE_HOME_POLICY_NOTES,
    }


def test_check_coverage_unlisted_category_on_known_policy():
    result = check_coverage(
        FAKE_POLICY_TYPE_HOME, FAKE_INCIDENT_CATEGORY_UNCOVERED, FAKE_COVERAGE_TABLE
    )
    assert result == {
        "covered": False,
        "deductible": FAKE_HOME_POLICY_DEDUCTIBLE,
        "max_payout": FAKE_HOME_POLICY_MAX_PAYOUT,
        "notes": FAKE_HOME_POLICY_NOTES,
    }


def test_check_coverage_rejects_unknown_policy_type():
    with pytest.raises(ValueError):
        check_coverage(
            FAKE_UNKNOWN_POLICY_TYPE, FAKE_INCIDENT_CATEGORY_COVERED, FAKE_COVERAGE_TABLE
        )


def test_check_coverage_rejects_coverage_table_missing_policies_key():
    with pytest.raises(ValueError):
        check_coverage(
            FAKE_POLICY_TYPE_HOME,
            FAKE_INCIDENT_CATEGORY_COVERED,
            FAKE_COVERAGE_TABLE_MISSING_POLICIES_KEY,
        )


def test_check_coverage_treats_missing_covered_categories_as_not_covered():
    result = check_coverage(
        FAKE_POLICY_TYPE_HOME,
        FAKE_INCIDENT_CATEGORY_COVERED,
        FAKE_COVERAGE_TABLE_POLICY_MISSING_COVERED_CATEGORIES,
    )
    assert result == {
        "covered": False,
        "deductible": FAKE_HOME_POLICY_DEDUCTIBLE,
        "max_payout": FAKE_HOME_POLICY_MAX_PAYOUT,
        "notes": FAKE_HOME_POLICY_NOTES,
    }
