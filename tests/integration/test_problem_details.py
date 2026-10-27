"""Testes dos contratos HTTP de erro, incluindo todos os caminhos de domínio."""

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from backend.app.shared.application.exceptions import (
    PermissionDeniedError,
    PersistenceRejectedError,
    PersistenceUnavailableError,
    ServiceNotReadyError,
)
from tests.integration.test_api import build_application


def _client_for(exception_type: type[Exception]) -> TestClient:
    application = build_application()

    @application.get("/test-problem")
    async def raise_problem() -> None:
        raise exception_type()

    return TestClient(application)


@pytest.mark.parametrize(
    "exception_type",
    [
        PermissionDeniedError,
        ServiceNotReadyError,
        PersistenceUnavailableError,
        PersistenceRejectedError,
    ],
)
def test_application_errors_return_stable_problem_details(
    exception_type: type[Exception],
) -> None:
    response = _client_for(exception_type).get("/test-problem")
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["status"] in {400, 403, 422, 503}
    assert response.json()["request_id"]


def test_problem_details_preserve_request_id_only_when_it_is_a_uuid() -> None:
    application = build_application()

    @application.get("/test-request-id")
    async def request_id(request: Request) -> dict[str, str]:
        return {"request_id": str(request.state.request_id)}

    client = TestClient(application)
    valid = "00000000-0000-4000-8000-000000000123"
    assert client.get("/test-request-id", headers={"X-Request-ID": valid}).json() == {
        "request_id": valid
    }
    invalid = client.get("/test-request-id", headers={"X-Request-ID": "texto-livre"})
    assert invalid.status_code == 200
    assert invalid.json()["request_id"] != "texto-livre"
