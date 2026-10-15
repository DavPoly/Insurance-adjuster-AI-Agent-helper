from langchain_openai import ChatOpenAI

from app.config import Settings
from app.constants.llm.triage_llm_config import REASONING_MODEL_DEFAULT_TEMPERATURE


def build_triage_chat_model(settings: Settings) -> ChatOpenAI:
    """Chat model for the triage agent, served through OpenRouter's OpenAI-compatible API."""
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        temperature=REASONING_MODEL_DEFAULT_TEMPERATURE,
    )
