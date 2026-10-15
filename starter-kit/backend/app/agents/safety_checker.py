from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.prompts.safety_checker_system_prompt import SAFETY_CHECKER_SYSTEM_PROMPT
from app.agents.schemas.safety_checks_schema import SafetyChecksOut


def check_output_safety(llm: BaseChatModel, triage_assessment: dict) -> SafetyChecksOut:
    structured_llm = llm.with_structured_output(SafetyChecksOut)
    return structured_llm.invoke(
        [
            SystemMessage(content=SAFETY_CHECKER_SYSTEM_PROMPT),
            HumanMessage(content=_build_safety_review_text(triage_assessment)),
        ]
    )


def _build_safety_review_text(triage_assessment: dict) -> str:
    return (
        f"damage_description: {triage_assessment.get('damage_description', '')}\n\n"
        f"recommendation: {triage_assessment.get('recommendation', '')}"
    )


def safety_checks_passed(safety_checks: SafetyChecksOut) -> bool:
    return all(safety_checks.model_dump().values())
