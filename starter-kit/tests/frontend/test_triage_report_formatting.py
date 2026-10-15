from sample_triage_payloads import (
    SAMPLE_CLAIM_SEQUENCE_NUMBER,
    SAMPLE_CLAIM_YEAR,
    SAMPLE_LIST_OBSERVE_STEP,
    SAMPLE_ROUNDED_COST_MAX,
    SAMPLE_ROUNDED_COST_MIN,
    SAMPLE_SAFETY_ERROR_PAYLOAD,
    SAMPLE_TRACE_STEPS,
    SAMPLE_TRIAGE_RESPONSE,
    SAMPLE_UNROUNDED_COST_MAX,
    SAMPLE_UNROUNDED_COST_MIN,
    SAMPLE_VALIDATION_ERROR_PAYLOAD,
)

from utils.triage_report_formatting import (
    CLAIM_SEQUENCE_NUMBER_WIDTH,
    format_agent_trace_markdown,
    format_claim_summary_label,
    format_safety_error_markdown,
    format_triage_response_markdown,
    format_unexpected_error_markdown,
    format_validation_error_markdown,
)

UNEXPECTED_ERROR_STATUS_CODE = 503
UNEXPECTED_ERROR_RAW_TEXT = "upstream dependency unavailable"


def test_format_triage_response_markdown_includes_claim_id_and_core_fields():
    markdown = format_triage_response_markdown(
        SAMPLE_TRIAGE_RESPONSE, SAMPLE_CLAIM_SEQUENCE_NUMBER, SAMPLE_CLAIM_YEAR
    )

    padded_sequence_number = str(SAMPLE_CLAIM_SEQUENCE_NUMBER).zfill(CLAIM_SEQUENCE_NUMBER_WIDTH)
    assert f"CLM-{SAMPLE_CLAIM_YEAR}-{padded_sequence_number}" in markdown
    assessment = SAMPLE_TRIAGE_RESPONSE["triage_assessment"]
    assert assessment["damage_type"] in markdown
    assert assessment["recommendation"] in markdown
    cost = assessment["estimated_repair_cost"]
    assert str(cost["min"]) in markdown and str(cost["max"]) in markdown
    similar_claim_id = assessment["similar_past_claims"][0]["claim_id"]
    assert similar_claim_id in markdown


def test_format_triage_response_markdown_omits_intake_and_safety_sections():
    markdown = format_triage_response_markdown(
        SAMPLE_TRIAGE_RESPONSE, SAMPLE_CLAIM_SEQUENCE_NUMBER, SAMPLE_CLAIM_YEAR
    )

    assert "Intake validation" not in markdown
    assert "Output safety checks" not in markdown


def test_format_triage_response_markdown_bolds_assessment_labels():
    markdown = format_triage_response_markdown(
        SAMPLE_TRIAGE_RESPONSE, SAMPLE_CLAIM_SEQUENCE_NUMBER, SAMPLE_CLAIM_YEAR
    )

    assert "**Damage type:**" in markdown
    assert "**Severity:**" in markdown
    assert "**Affected areas:**" in markdown
    assert "**Urgency:**" in markdown
    assert "**Estimated repair cost:**" in markdown
    assert "**Description:**" in markdown
    assert "**Recommendation:**" in markdown


def test_format_triage_response_markdown_rounds_repair_cost_to_whole_numbers():
    assessment_with_decimal_cost = {
        **SAMPLE_TRIAGE_RESPONSE["triage_assessment"],
        "estimated_repair_cost": {
            "min": SAMPLE_UNROUNDED_COST_MIN,
            "max": SAMPLE_UNROUNDED_COST_MAX,
            "currency": "USD",
        },
    }
    response = {**SAMPLE_TRIAGE_RESPONSE, "triage_assessment": assessment_with_decimal_cost}

    markdown = format_triage_response_markdown(
        response, SAMPLE_CLAIM_SEQUENCE_NUMBER, SAMPLE_CLAIM_YEAR
    )

    assert f"{SAMPLE_ROUNDED_COST_MIN}-{SAMPLE_ROUNDED_COST_MAX}" in markdown
    assert str(SAMPLE_UNROUNDED_COST_MIN) not in markdown
    assert str(SAMPLE_UNROUNDED_COST_MAX) not in markdown


def test_format_triage_response_markdown_handles_missing_repair_cost():
    assessment_without_cost = {
        key: value
        for key, value in SAMPLE_TRIAGE_RESPONSE["triage_assessment"].items()
        if key != "estimated_repair_cost"
    }
    response = {**SAMPLE_TRIAGE_RESPONSE, "triage_assessment": assessment_without_cost}

    markdown = format_triage_response_markdown(
        response, SAMPLE_CLAIM_SEQUENCE_NUMBER, SAMPLE_CLAIM_YEAR
    )

    assert "**Estimated repair cost:** ?-?" in markdown


def test_format_triage_response_markdown_handles_no_similar_claims():
    assessment_without_claims = {
        **SAMPLE_TRIAGE_RESPONSE["triage_assessment"],
        "similar_past_claims": [],
    }
    response = {**SAMPLE_TRIAGE_RESPONSE, "triage_assessment": assessment_without_claims}

    markdown = format_triage_response_markdown(
        response, SAMPLE_CLAIM_SEQUENCE_NUMBER, SAMPLE_CLAIM_YEAR
    )

    assert "none found" in markdown


def test_format_agent_trace_markdown_lists_every_step_in_order():
    markdown = format_agent_trace_markdown(SAMPLE_TRACE_STEPS)

    for step in SAMPLE_TRACE_STEPS:
        assert str(step["step_number"]) in markdown
    assert "estimate_repair_cost" in markdown


def test_format_agent_trace_markdown_renders_tables_not_raw_dict_reprs():
    markdown = format_agent_trace_markdown(SAMPLE_TRACE_STEPS)

    assert "{'" not in markdown
    assert "| Field | Value |" in markdown
    act_step, observe_step = SAMPLE_TRACE_STEPS[1], SAMPLE_TRACE_STEPS[2]
    for key, value in act_step["tool_input"].items():
        assert key in markdown
        if isinstance(value, list):
            assert ", ".join(value) in markdown
        else:
            assert str(value) in markdown
    for key, value in observe_step["tool_output"].items():
        assert key in markdown
        assert str(value) in markdown


def test_format_agent_trace_markdown_separates_steps_with_blank_line():
    markdown = format_agent_trace_markdown(SAMPLE_TRACE_STEPS)

    assert markdown.count("Step 1") == 1
    assert markdown.count("Step 2") == 1
    assert "\n\n**" in markdown


def test_format_agent_trace_markdown_renders_list_output_as_table_rows():
    markdown = format_agent_trace_markdown([SAMPLE_LIST_OBSERVE_STEP])

    assert "{'" not in markdown
    for record in SAMPLE_LIST_OBSERVE_STEP["tool_output"]:
        assert record["claim_id"] in markdown
        assert str(record["similarity_score"]) in markdown


def test_format_agent_trace_markdown_handles_empty_trace():
    markdown = format_agent_trace_markdown([])

    assert "No agent trace" in markdown


def test_format_validation_error_markdown_includes_message_but_not_flags():
    markdown = format_validation_error_markdown(SAMPLE_VALIDATION_ERROR_PAYLOAD)

    assert SAMPLE_VALIDATION_ERROR_PAYLOAD["message"] in markdown
    assert "is_property_damage" not in markdown
    assert "Intake validation" not in markdown


def test_format_safety_error_markdown_includes_message_but_not_flags():
    markdown = format_safety_error_markdown(SAMPLE_SAFETY_ERROR_PAYLOAD)

    assert SAMPLE_SAFETY_ERROR_PAYLOAD["message"] in markdown
    assert "no_coverage_promises" not in markdown
    assert "Output safety checks" not in markdown


def test_format_unexpected_error_markdown_includes_status_and_body():
    markdown = format_unexpected_error_markdown(
        UNEXPECTED_ERROR_STATUS_CODE, UNEXPECTED_ERROR_RAW_TEXT
    )

    assert str(UNEXPECTED_ERROR_STATUS_CODE) in markdown
    assert UNEXPECTED_ERROR_RAW_TEXT in markdown


def test_format_claim_summary_label_includes_damage_severity_and_sequential_claim_number():
    label = format_claim_summary_label(
        SAMPLE_TRIAGE_RESPONSE, SAMPLE_CLAIM_SEQUENCE_NUMBER, SAMPLE_CLAIM_YEAR
    )

    assessment = SAMPLE_TRIAGE_RESPONSE["triage_assessment"]
    padded_sequence_number = str(SAMPLE_CLAIM_SEQUENCE_NUMBER).zfill(CLAIM_SEQUENCE_NUMBER_WIDTH)
    assert assessment["damage_type"] in label
    assert assessment["severity"] in label
    assert f"CLM-{SAMPLE_CLAIM_YEAR}-{padded_sequence_number}" in label
