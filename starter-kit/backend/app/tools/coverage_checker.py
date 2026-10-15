def check_coverage(policy_type: str, incident_category: str, coverage_table: dict) -> dict:
    """Determine whether a policy covers a given incident category.

    Args:
        policy_type: Key into ``coverage_table["policies"]``, e.g. ``"home"``.
        incident_category: Category name checked against the policy's
            ``covered_categories`` list, e.g. ``"fire"``.
        coverage_table: A lookup table shaped like::

            {
                "policies": {
                    policy_type: {
                        "covered_categories": list[str],
                        "deductible": int,
                        "max_payout": int,
                        "notes": str,
                    }
                }
            }

    Returns:
        A dict shaped like ``{"covered": bool, "deductible": int, "max_payout": int,
        "notes": str}``, where ``covered`` is ``True`` if ``incident_category`` is
        present in the policy's ``covered_categories`` list. A policy missing
        ``covered_categories`` is treated as covering nothing.

    Raises:
        ValueError: If ``policy_type`` is not present in
            ``coverage_table["policies"]``.
    """
    policy = coverage_table.get("policies", {}).get(policy_type)
    if policy is None:
        raise ValueError(f"Unknown policy_type={policy_type!r}")

    covered = incident_category in policy.get("covered_categories", [])

    return {
        "covered": covered,
        "deductible": policy["deductible"],
        "max_payout": policy["max_payout"],
        "notes": policy["notes"],
    }
