from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.shared.presentation.rate_limit import FixedWindowRateLimitMiddleware


def test_rate_limit_returns_problem_detail_after_limit() -> None:
    application = FastAPI()
    application.add_middleware(FixedWindowRateLimitMiddleware, limit=1)

    @application.get("/resource")
    def resource() -> dict[str, bool]:
        return {"ok": True}

    client = TestClient(application)
    assert client.get("/resource").status_code == 200
    response = client.get("/resource")
    assert response.status_code == 429
    assert response.json()["code"] == "RATE_LIMIT_EXCEEDED"
    assert response.headers["retry-after"] == "60"


def test_healthcheck_is_not_rate_limited() -> None:
    application = FastAPI()
    application.add_middleware(FixedWindowRateLimitMiddleware, limit=1)

    @application.get("/health/live")
    def health() -> dict[str, bool]:
        return {"ok": True}

    client = TestClient(application)
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/live").status_code == 200
