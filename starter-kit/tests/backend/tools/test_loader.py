import json
from pathlib import Path

from known_tool_fixture_values import (
    DAMAGE_SEVERITY_MODERATE,
    POLICY_TYPE_STANDARD_HOMEOWNER,
    STANDARD_HOMEOWNER_DEDUCTIBLE,
    STANDARD_HOMEOWNER_MAX_PAYOUT,
    WATER_DAMAGE_MODERATE_MAX_PER_AREA,
    WATER_DAMAGE_MODERATE_MIN_PER_AREA,
    WATER_DAMAGE_TYPE,
)

from app.constants.tools.tool_lookup_table_paths import (
    COST_TABLE_FILENAME,
    COVERAGE_TABLE_FILENAME,
    DEFAULT_TOOLS_DIR,
    TOOLS_DIR_ENV_VAR,
    cost_table_path,
    coverage_table_path,
)
from app.tools.loader import load_json_table

STARTER_KIT_DIR = Path(__file__).resolve().parents[3]
REAL_TOOLS_DIR = STARTER_KIT_DIR / "tools"

BOM_TEST_TABLE_KEY = "bom_test_key"
BOM_TEST_TABLE_VALUE = "bom_test_value"


def test_load_json_table_reads_real_cost_table(monkeypatch):
    monkeypatch.setenv(TOOLS_DIR_ENV_VAR, str(REAL_TOOLS_DIR))

    table = load_json_table(cost_table_path())

    assert "cost_matrix" in table
    assert WATER_DAMAGE_TYPE in table["cost_matrix"]
    moderate_water_damage = table["cost_matrix"][WATER_DAMAGE_TYPE][DAMAGE_SEVERITY_MODERATE]
    assert moderate_water_damage["min_per_area"] == WATER_DAMAGE_MODERATE_MIN_PER_AREA
    assert moderate_water_damage["max_per_area"] == WATER_DAMAGE_MODERATE_MAX_PER_AREA


def test_load_json_table_reads_real_coverage_table(monkeypatch):
    monkeypatch.setenv(TOOLS_DIR_ENV_VAR, str(REAL_TOOLS_DIR))

    table = load_json_table(coverage_table_path())

    assert "policies" in table
    assert POLICY_TYPE_STANDARD_HOMEOWNER in table["policies"]
    standard_homeowner_policy = table["policies"][POLICY_TYPE_STANDARD_HOMEOWNER]
    assert standard_homeowner_policy["deductible"] == STANDARD_HOMEOWNER_DEDUCTIBLE
    assert standard_homeowner_policy["max_payout"] == STANDARD_HOMEOWNER_MAX_PAYOUT


def test_cost_table_path_resolves_to_container_default_when_tools_dir_unset(monkeypatch):
    monkeypatch.delenv(TOOLS_DIR_ENV_VAR, raising=False)

    assert cost_table_path() == Path(DEFAULT_TOOLS_DIR) / COST_TABLE_FILENAME


def test_coverage_table_path_resolves_to_container_default_when_tools_dir_unset(monkeypatch):
    monkeypatch.delenv(TOOLS_DIR_ENV_VAR, raising=False)

    assert coverage_table_path() == Path(DEFAULT_TOOLS_DIR) / COVERAGE_TABLE_FILENAME


def test_load_json_table_tolerates_a_leading_utf8_bom(tmp_path):
    table_with_bom = tmp_path / "bom_table.json"
    json_body = json.dumps({BOM_TEST_TABLE_KEY: BOM_TEST_TABLE_VALUE})
    table_with_bom.write_text("﻿" + json_body, encoding="utf-8")

    table = load_json_table(table_with_bom)

    assert table == {BOM_TEST_TABLE_KEY: BOM_TEST_TABLE_VALUE}
