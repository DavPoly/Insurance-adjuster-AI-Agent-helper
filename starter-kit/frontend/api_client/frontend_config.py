import os

DEFAULT_API_BASE_URL = "http://localhost:8000"
API_BASE_URL_ENV_VAR = "API_BASE_URL"


def get_api_base_url() -> str:
    return os.environ.get(API_BASE_URL_ENV_VAR, DEFAULT_API_BASE_URL)
