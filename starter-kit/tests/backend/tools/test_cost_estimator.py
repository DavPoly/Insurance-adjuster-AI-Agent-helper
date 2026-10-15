import pytest
from fake_cost_estimator_table import (
    FAKE_COST_TABLE,
    FAKE_COST_TABLE_MISSING_COST_MATRIX_KEY,
    FAKE_COST_TABLE_MISSING_DAMAGE_TYPE,
    FAKE_DISTINCT_AREA_COUNT_TWO,
    FAKE_WATER_DAMAGE_MINOR_MAX_PER_AREA,
    FAKE_WATER_DAMAGE_MINOR_MIN_PER_AREA,
    FAKE_WATER_DAMAGE_MODERATE_MAX_PER_AREA,
    FAKE_WATER_DAMAGE_MODERATE_MIN_PER_AREA,
)

from app.constants.tools.cost_estimate_currency import DEFAULT_CURRENCY
from app.tools.cost_estimator import estimate_repair_cost


def test_estimate_repair_cost_single_area():
    result = estimate_repair_cost("water_damage", "minor", ["kitchen"], FAKE_COST_TABLE)
    assert result == {
        "min": FAKE_WATER_DAMAGE_MINOR_MIN_PER_AREA,
        "max": FAKE_WATER_DAMAGE_MINOR_MAX_PER_AREA,
        "currency": DEFAULT_CURRENCY,
    }


def test_estimate_repair_cost_multiplies_by_distinct_area_count():
    result = estimate_repair_cost(
        "water_damage", "moderate", ["kitchen", "dining_room"], FAKE_COST_TABLE
    )
    assert result == {
        "min": FAKE_WATER_DAMAGE_MODERATE_MIN_PER_AREA * FAKE_DISTINCT_AREA_COUNT_TWO,
        "max": FAKE_WATER_DAMAGE_MODERATE_MAX_PER_AREA * FAKE_DISTINCT_AREA_COUNT_TWO,
        "currency": DEFAULT_CURRENCY,
    }


def test_estimate_repair_cost_deduplicates_areas_case_and_whitespace_insensitively():
    result = estimate_repair_cost("water_damage", "minor", ["Kitchen", "kitchen "], FAKE_COST_TABLE)
    assert result == {
        "min": FAKE_WATER_DAMAGE_MINOR_MIN_PER_AREA,
        "max": FAKE_WATER_DAMAGE_MINOR_MAX_PER_AREA,
        "currency": DEFAULT_CURRENCY,
    }


def test_estimate_repair_cost_rejects_unknown_damage_type():
    with pytest.raises(ValueError):
        estimate_repair_cost("meteor_strike", "minor", ["kitchen"], FAKE_COST_TABLE)


def test_estimate_repair_cost_rejects_unknown_severity():
    with pytest.raises(ValueError):
        estimate_repair_cost("water_damage", "catastrophic", ["kitchen"], FAKE_COST_TABLE)


def test_estimate_repair_cost_treats_empty_affected_areas_as_single_area():
    result = estimate_repair_cost("water_damage", "minor", [], FAKE_COST_TABLE)
    assert result == {
        "min": FAKE_WATER_DAMAGE_MINOR_MIN_PER_AREA,
        "max": FAKE_WATER_DAMAGE_MINOR_MAX_PER_AREA,
        "currency": DEFAULT_CURRENCY,
    }


def test_estimate_repair_cost_treats_whitespace_only_affected_areas_as_single_area():
    result = estimate_repair_cost("water_damage", "minor", ["   ", "\t"], FAKE_COST_TABLE)
    assert result == {
        "min": FAKE_WATER_DAMAGE_MINOR_MIN_PER_AREA,
        "max": FAKE_WATER_DAMAGE_MINOR_MAX_PER_AREA,
        "currency": DEFAULT_CURRENCY,
    }


def test_estimate_repair_cost_rejects_cost_table_missing_cost_matrix_key():
    with pytest.raises(ValueError):
        estimate_repair_cost(
            "water_damage", "minor", ["kitchen"], FAKE_COST_TABLE_MISSING_COST_MATRIX_KEY
        )


def test_estimate_repair_cost_rejects_cost_table_missing_damage_type():
    with pytest.raises(ValueError):
        estimate_repair_cost(
            "water_damage", "minor", ["kitchen"], FAKE_COST_TABLE_MISSING_DAMAGE_TYPE
        )
