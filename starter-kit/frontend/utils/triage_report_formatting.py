CLAIM_SEQUENCE_NUMBER_WIDTH = 3


def _format_display_claim_id(sequence_number: int, claim_year: int) -> str:
    padded_sequence_number = str(sequence_number).zfill(CLAIM_SEQUENCE_NUMBER_WIDTH)
    return f"CLM-{claim_year}-{padded_sequence_number}"


def format_claim_summary_label(response: dict, sequence_number: int, claim_year: int) -> str:
    assessment = response.get("triage_assessment", {})
    damage_type = assessment.get("damage_type", "unknown")
    severity = assessment.get("severity", "unknown")
    display_claim_id = _format_display_claim_id(sequence_number, claim_year)
    return f"{damage_type}/{severity} ({display_claim_id})"


def format_triage_response_markdown(response: dict, sequence_number: int, claim_year: int) -> str:
    assessment = response.get("triage_assessment", {})
    cost = assessment.get("estimated_repair_cost", {})
    rounded_cost_min = _format_rounded_cost_bound(cost.get("min"))
    rounded_cost_max = _format_rounded_cost_bound(cost.get("max"))
    display_claim_id = _format_display_claim_id(sequence_number, claim_year)

    sections = [
        f"### Triage report : `{display_claim_id}`",
        "\n".join(
            [
                "**Assessment**",
                f"- **Damage type:** {assessment.get('damage_type', 'unknown')}",
                f"- **Severity:** {assessment.get('severity', 'unknown')}",
                "- **Affected areas:** "
                + ", ".join(assessment.get("affected_areas", []) or ["none reported"]),
                f"- **Urgency:** {assessment.get('urgency', 'unknown')}",
                f"- **Estimated repair cost:** {rounded_cost_min}-{rounded_cost_max} "
                f"{cost.get('currency', '')}".strip(),
                f"- **Description:** {assessment.get('damage_description', '')}",
                f"- **Recommendation:** {assessment.get('recommendation', '')}",
            ]
        ),
        _format_similar_claims(assessment.get("similar_past_claims", [])),
    ]
    return "\n\n".join(sections)


def _format_rounded_cost_bound(value: float | None) -> str:
    if value is None:
        return "?"
    return str(round(value))


TRACE_STEP_ICONS = {"reason": "🧭", "act": "🔧", "observe": "📋"}
TRACE_STEP_TITLES = {"reason": "Reasoning", "act": "Action", "observe": "Observation"}
TRACE_STEP_SEPARATOR = "\n\n"


def format_agent_trace_markdown(steps: list[dict]) -> str:
    if not steps:
        return "_No agent trace was recorded for this claim._"
    return TRACE_STEP_SEPARATOR.join(_format_trace_step_block(step) for step in steps)


def _format_trace_step_block(step: dict) -> str:
    step_type = step.get("type", "unknown")
    icon = TRACE_STEP_ICONS.get(step_type, "•")
    title = TRACE_STEP_TITLES.get(step_type, step_type.title())
    header = f"**{icon} Step {step.get('step_number', '?')} — {title}**"

    if step_type == "act":
        tool_input_table = _format_dict_as_table(step.get("tool_input"))
        body = f"Calling `{step.get('tool_name', 'unknown')}`\n\n{tool_input_table}"
    elif step_type == "observe":
        body = _format_tool_output_markdown(step.get("tool_output"))
    else:
        body = step.get("content", "")

    return f"{header}\n\n{body}"


def _format_tool_output_markdown(output: object) -> str:
    if isinstance(output, list) and output and isinstance(output[0], dict):
        return _format_records_as_table(output)
    if isinstance(output, dict):
        return _format_dict_as_table(output)
    return str(output)


def _format_dict_as_table(data: dict | None) -> str:
    if not data:
        return "_(no data)_"
    rows = "\n".join(f"| {key} | {_format_cell_value(value)} |" for key, value in data.items())
    return f"| Field | Value |\n|---|---|\n{rows}"


def _format_records_as_table(records: list[dict]) -> str:
    columns = list(records[0].keys())
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    rows = "\n".join(
        "| " + " | ".join(_format_cell_value(record.get(column)) for column in columns) + " |"
        for record in records
    )
    return "\n".join([header, separator, rows])


def _format_cell_value(value: object) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)


def format_validation_error_markdown(payload: dict) -> str:
    return f"**Submission rejected during intake validation.** {payload.get('message', '')}"


def format_safety_error_markdown(payload: dict) -> str:
    return f"**Generated report failed an output safety check.** {payload.get('message', '')}"


def format_unexpected_error_markdown(status_code: int, raw_text: str) -> str:
    return f"**Unexpected error (HTTP {status_code})**\n\n```\n{raw_text}\n```"


def _format_similar_claims(claims: list[dict]) -> str:
    if not claims:
        return "**Similar past claims**\n- none found"
    lines = ["**Similar past claims**"]
    for claim in claims:
        lines.append(
            f"- `{claim.get('claim_id', 'unknown')}` "
            f"{claim.get('resolution_summary', '')}"
        )
    return "\n".join(lines)
