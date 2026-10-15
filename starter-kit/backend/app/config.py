from pydantic_settings import BaseSettings, SettingsConfigDict

from app.constants.llm.openrouter_gateway_config import OPENROUTER_BASE_URL_DEFAULT


class Settings(BaseSettings):
    # No env_file: real values are injected as container environment variables by
    # docker-compose (itself populated from starter-kit/.env) — the app never reads
    # a dotenv file directly. The API key gets no default so a missing value is an
    # obvious empty string rather than a plausible-looking fake credential.
    model_config = SettingsConfigDict(extra="ignore")

    openrouter_api_key: str = ""
    openrouter_base_url: str = OPENROUTER_BASE_URL_DEFAULT
    llm_model: str = ""
    qdrant_url: str = ""


def get_settings() -> Settings:
    return Settings()
