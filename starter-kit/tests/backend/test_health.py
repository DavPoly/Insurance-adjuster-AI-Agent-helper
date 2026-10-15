from fake_health_check_credentials import FAKE_LLM_MODEL, FAKE_OPENROUTER_API_KEY
from fastapi import status
from fastapi.testclient import TestClient

from app.constants.api.health_check_status_labels import (
    HEALTHY_STATUS,
    LLM_CONFIGURED,
    LLM_NOT_CONFIGURED,
    VECTOR_DB_CONNECTED,
    VECTOR_DB_DISCONNECTED,
)
from app.constants.api.unexpected_error_response import (
    UNEXPECTED_ERROR_CODE,
    UNEXPECTED_ERROR_MESSAGE,
)
from app.main import app
from app.routers.health import get_qdrant_client


class FakeQdrantClient:
    def __init__(self, healthy: bool):
        self._healthy = healthy

    def get_collections(self):
        if not self._healthy:
            raise ConnectionError("qdrant unreachable")
        return []


def test_health_endpoint_reports_connected_and_configured(client, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", FAKE_OPENROUTER_API_KEY)
    monkeypatch.setenv("LLM_MODEL", FAKE_LLM_MODEL)
    app.dependency_overrides[get_qdrant_client] = lambda: FakeQdrantClient(healthy=True)

    response = client.get("/api/v1/health")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == HEALTHY_STATUS
    assert body["services"]["vector_db"] == VECTOR_DB_CONNECTED
    assert body["services"]["llm"] == LLM_CONFIGURED


def test_health_endpoint_reports_disconnected_vector_db(client):
    app.dependency_overrides[get_qdrant_client] = lambda: FakeQdrantClient(healthy=False)

    response = client.get("/api/v1/health")
    app.dependency_overrides.clear()

    assert response.json()["services"]["vector_db"] == VECTOR_DB_DISCONNECTED


def test_health_endpoint_reports_llm_not_configured_without_credentials(client, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    monkeypatch.setenv("LLM_MODEL", "")
    app.dependency_overrides[get_qdrant_client] = lambda: FakeQdrantClient(healthy=True)

    response = client.get("/api/v1/health")
    app.dependency_overrides.clear()

    assert response.json()["services"]["llm"] == LLM_NOT_CONFIGURED


def test_health_endpoint_returns_structured_500_on_unexpected_failure():
    def raise_unexpectedly():
        raise RuntimeError("qdrant client construction blew up")

    app.dependency_overrides[get_qdrant_client] = raise_unexpectedly

    # Starlette's ServerErrorMiddleware re-raises after responding, purely so dev
    # servers/tests can see the traceback; a real client still receives the body
    # built below. raise_server_exceptions=False reflects what a real client sees.
    with TestClient(app, raise_server_exceptions=False) as unraising_client:
        response = unraising_client.get("/api/v1/health")
    app.dependency_overrides.clear()

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {
        "error": UNEXPECTED_ERROR_CODE,
        "message": UNEXPECTED_ERROR_MESSAGE,
    }
