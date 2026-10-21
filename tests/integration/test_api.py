"""Testes de integração da camada HTTP."""

from fastapi.testclient import TestClient

from backend.app.core.config import Settings
from backend.app.core.container import build_container
from backend.app.main import create_app


def build_client() -> TestClient:
    settings = Settings(
        app_name="Livre Acesso API - Test",
        version="test",
        environment="test",
        host="127.0.0.1",
        port=8000,
        debug=False,
        api_prefix="/api/v1",
        cors_origins=("http://localhost:5173",),
    )
    return TestClient(create_app(settings=settings, container=build_container()))


def student_payload() -> dict[str, object]:
    return {
        "full_name": "Sophia Almeida Ramos",
        "cpf": "529.982.247-25",
        "birth_date": "2015-05-10",
        "modality": "bale",
        "guardian": {
            "full_name": "Camila Ramos",
            "phone": "(61) 99999-1234",
            "email": "camila@example.com",
        },
    }


def test_health_endpoint() -> None:
    with build_client() as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_register_list_and_reject_duplicate_cpf() -> None:
    with build_client() as client:
        created = client.post("/api/v1/students", json=student_payload())
        listed = client.get("/api/v1/students")
        duplicate = client.post("/api/v1/students", json=student_payload())

    assert created.status_code == 201
    assert created.json()["cpf_masked"] == "***.***.***-25"
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "duplicate_cpf"
