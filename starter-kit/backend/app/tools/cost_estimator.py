from app.constants.tools.cost_estimate_currency import DEFAULT_CURRENCY


def estimate_repair_cost(
    damage_type: str, severity: str, affected_areas: list[str], cost_table: dict
) -> dict:
    """Estimate a repair cost range for a property damage claim.

    Args:
        damage_type: Key into ``cost_table["cost_matrix"]``, e.g. ``"water_damage"``.
        severity: Key into ``cost_table["cost_matrix"][damage_type]``, e.g. ``"minor"``.
        affected_areas: Area names (e.g. room names) the damage affects. Entries are
            deduplicated case- and whitespace-insensitively; an empty list, or a list
            containing only whitespace-only entries, is treated as a single area.
        cost_table: A lookup table shaped like::

            {
                "cost_matrix": {
                    damage_type: {
                        severity: {"min_per_area": int, "max_per_area": int}
                    }
                }
            }

    Returns:
        A dict shaped like ``{"min": int, "max": int, "currency": str}``, where
        ``min`` and ``max`` are the per-area costs multiplied by the distinct,
        non-blank area count.

    Raises:
        ValueError: If ``damage_type`` is not present in ``cost_table["cost_matrix"]``,
            or ``severity`` is not present for that ``damage_type``.
    """
    cost_per_area_range = cost_table.get("cost_matrix", {}).get(damage_type, {}).get(severity)
    if cost_per_area_range is None:
        raise ValueError(f"No cost data for damage_type={damage_type!r}, severity={severity!r}")

    distinct_areas = {area.strip().lower() for area in affected_areas if area.strip()}
    area_count = max(1, len(distinct_areas))

    return {
        "min": cost_per_area_range["min_per_area"] * area_count,
        "max": cost_per_area_range["max_per_area"] * area_count,
        "currency": DEFAULT_CURRENCY,
    }
