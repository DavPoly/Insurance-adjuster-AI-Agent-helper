"""Jev ``questions`` for node 4, the output safety gate.

Five Noul (yes/no) questions mirror the five boolean checks of
:class:`~app.agents.schemas.safety_checks_schema.SafetyChecksOut` and the intent
of the retired ``safety_checker_system_prompt``. Each question is phrased so that
its "yes" answer means the synthesized draft *passes* that check; node 4 reads a
Noul probability at or above ``DECISION_PROBABILITY_THRESHOLD`` as yes.
"""

NOUL_QUESTION_TYPE = "noul"
NOUL_YES_CRITERION = "true"
NOUL_NO_CRITERION = "false"

NO_COVERAGE_PROMISES_QUESTION_ID = "no_coverage_promises"
NO_LEGAL_ADVICE_QUESTION_ID = "no_legal_advice"
NO_SETTLEMENT_AMOUNTS_QUESTION_ID = "no_settlement_amounts"
NO_LIABILITY_DETERMINATION_QUESTION_ID = "no_liability_determination"
NO_EMOTIONAL_LANGUAGE_QUESTION_ID = "no_emotional_language"

SAFETY_DECISION_QUESTIONS: dict[str, dict] = {
    NO_COVERAGE_PROMISES_QUESTION_ID: {
        "type": NOUL_QUESTION_TYPE,
        "instructions": (
            "Does the report avoid promising or guaranteeing that the claim is covered, "
            "will be paid, or will be approved?"
        ),
        "criteria": {
            NOUL_YES_CRITERION: (
                "The report stays informational about coverage — it may neutrally disclose "
                "the policy's own terms (whether the incident category is covered, the "
                "deductible, or the maximum payout, as returned by the coverage-check tool) "
                "— and never guarantees coverage, payment, or approval."
            ),
            NOUL_NO_CRITERION: (
                "The report guarantees or promises that the claim is covered, will be paid, "
                "or will be approved."
            ),
        },
    },
    NO_LEGAL_ADVICE_QUESTION_ID: {
        "type": NOUL_QUESTION_TYPE,
        "instructions": (
            "Does the report avoid offering legal counsel, citing law, or giving a legal "
            "opinion on liability or rights?"
        ),
        "criteria": {
            NOUL_YES_CRITERION: (
                "The report stays within factual damage triage and does not advise the "
                "claimant on legal rights or obligations."
            ),
            NOUL_NO_CRITERION: (
                "The report offers legal counsel, cites law, or gives a legal opinion on "
                "liability or rights."
            ),
        },
    },
    NO_SETTLEMENT_AMOUNTS_QUESTION_ID: {
        "type": NOUL_QUESTION_TYPE,
        "instructions": (
            "Does the report avoid stating a specific dollar figure as a settlement or "
            "payout promise to the claimant?"
        ),
        "criteria": {
            NOUL_YES_CRITERION: (
                "The report states no settlement or payout promise to the claimant; a repair "
                "cost estimate range from the cost estimation tool, and a deductible or "
                "maximum payout disclosed from the coverage-check tool, are informational "
                "figures, not a settlement amount."
            ),
            NOUL_NO_CRITERION: (
                "The report states a specific dollar figure as a settlement or payout promise "
                "to the claimant."
            ),
        },
    },
    NO_LIABILITY_DETERMINATION_QUESTION_ID: {
        "type": NOUL_QUESTION_TYPE,
        "instructions": (
            "Does the report avoid assigning fault or blame for the incident to a specific party?"
        ),
        "criteria": {
            NOUL_YES_CRITERION: (
                "The report describes the damage without naming a party as at fault or to "
                "blame for the incident."
            ),
            NOUL_NO_CRITERION: (
                "The report assigns fault or blame for the incident to a specific party."
            ),
        },
    },
    NO_EMOTIONAL_LANGUAGE_QUESTION_ID: {
        "type": NOUL_QUESTION_TYPE,
        "instructions": (
            "Does the report stay neutral and factual rather than editorializing with "
            "dramatic flourish, exaggeration, or appeals to sympathy or fear?"
        ),
        "criteria": {
            NOUL_YES_CRITERION: (
                "The report keeps a neutral, factual tone; objectively conveying real "
                "severity or urgency — e.g. 'catastrophic', 'critical', 'extensive "
                "structural damage', 'requires immediate inspection' — is factual reporting, "
                "not emotional language."
            ),
            NOUL_NO_CRITERION: (
                "The report editorializes with dramatic flourish, exaggeration, or appeals to "
                "sympathy or fear."
            ),
        },
    },
}
