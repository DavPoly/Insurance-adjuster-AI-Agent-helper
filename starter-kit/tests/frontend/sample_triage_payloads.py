"""Fixture payloads shaped like the real triage API responses, for exercising
triage_report_formatting's pure markdown builders without a live backend.
"""

SAMPLE_CLAIM_ID = "triage-sample-0001"
SAMPLE_CLAIM_SEQUENCE_NUMBER = 7
SAMPLE_CLAIM_YEAR = 2026
SAMPLE_UNROUNDED_COST_MIN = 3499.6
SAMPLE_UNROUNDED_COST_MAX = 7000.2
SAMPLE_ROUNDED_COST_MIN = 3500
SAMPLE_ROUNDED_COST_MAX = 7000

SAMPLE_TRIAGE_RESPONSE = {
    "claim_id": SAMPLE_CLAIM_ID,
    "intake_validation": {
        "is_property_damage": True,
        "is_valid_image": True,
        "no_pii_detected": True,
        "no_offensive_content": True,
    },
    "triage_assessment": {
        "damage_type": "water_damage",
        "severity": "moderate",
        "affected_areas": ["kitchen", "dining_room"],
        "damage_description": "Burst supply pipe flooded the kitchen and dining room.",
        "estimated_repair_cost": {"min": 4000, "max": 16000, "currency": "USD"},
        "urgency": "high",
        "recommendation": "Dispatch a water mitigation contractor within 24 hours.",
        "similar_past_claims": [
            {
                "claim_id": "CLM-0042",
                "similarity_score": 0.91,
                "resolution_summary": "Similar burst-pipe claim resolved with full kitchen repair.",
            }
        ],
    },
    "safety_checks": {
        "no_coverage_promises": True,
        "no_legal_advice": True,
        "no_settlement_amounts": True,
        "no_liability_determination": True,
        "no_emotional_language": True,
    },
}

SAMPLE_VALIDATION_ERROR_PAYLOAD = {
    "error": "intake_validation_failed",
    "message": "At least an image or a non-blank description is required.",
    "intake_validation": {
        "is_property_damage": False,
        "is_valid_image": None,
        "no_pii_detected": True,
        "no_offensive_content": True,
    },
}

SAMPLE_SAFETY_ERROR_PAYLOAD = {
    "error": "safety_check_failed",
    "message": "The generated triage report failed an output safety check.",
    "safety_checks": {
        "no_coverage_promises": False,
        "no_legal_advice": True,
        "no_settlement_amounts": True,
        "no_liability_determination": True,
        "no_emotional_language": True,
    },
}

SAMPLE_TRACE_STEPS = [
    {"type": "reason", "step_number": 1, "content": "I should estimate repair cost first."},
    {
        "type": "act",
        "step_number": 2,
        "content": "Calling estimate_repair_cost",
        "tool_name": "estimate_repair_cost",
        "tool_input": {
            "damage_type": "water_damage",
            "severity": "moderate",
            "affected_areas": ["kitchen"],
        },
    },
    {
        "type": "observe",
        "step_number": 3,
        "content": '{"min": 2000, "max": 8000}',
        "tool_output": {"min": 2000, "max": 8000},
    },
]

SAMPLE_LIST_OBSERVE_STEP = {
    "type": "observe",
    "step_number": 4,
    "content": "list of matching claims",
    "tool_output": [
        {"claim_id": "CLM-0042", "similarity_score": 0.91},
        {"claim_id": "CLM-0099", "similarity_score": 0.77},
    ],
}
