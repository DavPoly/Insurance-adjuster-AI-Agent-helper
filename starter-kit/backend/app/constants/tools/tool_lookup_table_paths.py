import os
from pathlib import Path

DEFAULT_TOOLS_DIR = "/app/tools"
COST_TABLE_FILENAME = "cost-estimator.json"
COVERAGE_TABLE_FILENAME = "coverage-table.json"
TOOLS_DIR_ENV_VAR = "TOOLS_DIR"


def tools_dir() -> Path:
    """Directory holding the tool lookup tables, overridable via TOOLS_DIR."""
    return Path(os.environ.get(TOOLS_DIR_ENV_VAR, DEFAULT_TOOLS_DIR))


def cost_table_path() -> Path:
    """Path to the repair-cost lookup table JSON file."""
    return tools_dir() / COST_TABLE_FILENAME


def coverage_table_path() -> Path:
    """Path to the policy-coverage lookup table JSON file."""
    return tools_dir() / COVERAGE_TABLE_FILENAME
