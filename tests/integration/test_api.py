"""Testes de integração da camada HTTP."""

from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.core.config import Settings
from backend.app.core.container import build_container
from backend.app.main import create_app
from backend.app.modules.identity.application.authentication import (
    AccessToken,
    AuthenticatedUser,
    InvalidAccessTokenError,
    TokenVerifier,
    UnavailableTokenVerifier,
)

_TEST_TOKEN = "token-sintetico-de-teste"
_TEST_USER_ID = UUID("00000000-0000-4000-8000-000000000001")
_TEST_SESSION_ID = UUID("00000000-0000-4000-8000-000000000002")


class TestTokenVerifier:
    """Double que autentica somente o token sintético conhecido pelos testes."""

    async def verify(self, raw_access_token: str) -> AuthenticatedUser:
        if raw_access_token != _TEST_TOKEN:
            raise InvalidAccessTokenError
        return AuthenticatedUser(
            user_id=_TEST_USER_ID,
            access_token=AccessToken(raw_access_token),
            session_id=_TEST_SESSION_ID,
            assurance_level="aal1",
        )


def build_application(token_verifier: TokenVerifier | None = None) -> FastAPI:
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
    return create_app(
        settings=settings,
        container=build_container(settings),
        token_verifier=token_verifier or TestTokenVerifier(),
    )


def build_client() -> TestClient:
    return TestClient(
        build_application(),
        headers={"Authorization": f"Bearer {_TEST_TOKEN}"},
    )


def student_payload(
    *,
    full_name: str = "Sophia Almeida Ramos",
    cpf: str = "529.982.247-25",
) -> dict[str, object]:
    return {
        "full_name": full_name,
        "cpf": cpf,
        "birth_date": "2015-05-10",
        "guardian": {
            "full_name": "Camila Ramos",
            "phone": "(61) 99999-1234",
            "email": "camila@example.com",
        },
    }


def test_health_endpoint_has_traceable_request_id() -> None:
    with build_client() as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "alive"
    assert UUID(response.headers["X-Request-ID"])


def test_valid_request_id_is_preserved() -> None:
    request_id = uuid4()

    with build_client() as client:
        response = client.get("/health", headers={"X-Request-ID": str(request_id)})

    assert response.headers["X-Request-ID"] == str(request_id)


def test_invalid_request_id_is_replaced() -> None:
    with build_client() as client:
        response = client.get("/health", headers={"X-Request-ID": "texto-nao-confiavel"})

    assert response.headers["X-Request-ID"] != "texto-nao-confiavel"
    assert UUID(response.headers["X-Request-ID"])


def test_register_list_and_reject_duplicate_cpf() -> None:
    with build_client() as client:
        created = client.post("/api/v1/students", json=student_payload())
        listed = client.get("/api/v1/students")
        duplicate = client.post("/api/v1/students", json=student_payload())

    assert created.status_code == 201
    assert created.json()["cpf_masked"] == "***.***.***-25"
    assert "modality" not in created.json()

    assert listed.status_code == 200
    assert len(listed.json()["items"]) == 1
    assert listed.json()["total"] == 1
    assert listed.json()["page"] == 1
    assert listed.json()["has_next"] is False

    assert duplicate.status_code == 409
    assert duplicate.headers["content-type"].startswith("application/problem+json")
    assert duplicate.json()["code"] == "duplicate_cpf"
    assert duplicate.json()["errors"][0]["field"] == "cpf"
    assert duplicate.json()["request_id"] == duplicate.headers["X-Request-ID"]


def test_search_is_accent_insensitive_and_paginated() -> None:
    with build_client() as client:
        client.post(
            "/api/v1/students",
            json=student_payload(full_name="João da Silva", cpf="52998224725"),
        )
        client.post(
            "/api/v1/students",
            json=student_payload(full_name="Maria de Souza", cpf="11144477735"),
        )
        response = client.get("/api/v1/students?query=joao&page=1&page_size=1")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["total_pages"] == 1
    assert response.json()["items"][0]["full_name"] == "João da Silva"


def test_registration_rejects_enrollment_fields_with_field_messages() -> None:
    payload = student_payload() | {"modality": "bale", "status": "inativo"}

    with build_client() as client:
        response = client.post("/api/v1/students", json=payload)

    # Campos extras são rejeitados para não permitir que o cliente misture
    # cadastro, matrícula e mudança de ciclo em uma única operação implícita.
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "validation_error"
    assert {error["field"] for error in response.json()["errors"]} == {
        "modality",
        "status",
    }
    assert all(error["message"] for error in response.json()["errors"])


def test_invalid_cpf_points_to_the_field_without_echoing_value() -> None:
    payload = student_payload() | {"cpf": "111.111.111-11"}

    with build_client() as client:
        response = client.post("/api/v1/students", json=payload)

    serialized_response = response.text
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_cpf"
    assert response.json()["errors"][0]["field"] == "cpf"
    assert payload["cpf"] not in serialized_response


def test_unexpected_error_hides_exception_content(
    caplog: pytest.LogCaptureFixture,
) -> None:
    application = build_application()
    sensitive_exception_text = "cpf-nao-pode-aparecer-52998224725"

    @application.get("/test/unexpected", include_in_schema=False)
    def raise_unexpected_error() -> None:
        raise RuntimeError(sensitive_exception_text)

    with (
        caplog.at_level("ERROR", logger="livre_acesso.api"),
        TestClient(application, raise_server_exceptions=False) as client,
    ):
        response = client.get("/test/unexpected")

    assert response.status_code == 500
    assert response.json()["code"] == "internal_error"
    assert sensitive_exception_text not in response.text
    assert sensitive_exception_text not in caplog.text


def test_students_require_bearer_authentication() -> None:
    with TestClient(build_application()) as client:
        response = client.get("/api/v1/students")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.json()["code"] == "authentication_required"


def test_invalid_bearer_token_is_rejected_without_echoing_it() -> None:
    invalid_token = "token-invalido-nao-pode-vazar"

    with TestClient(build_application()) as client:
        response = client.get(
            "/api/v1/students",
            headers={"Authorization": f"Bearer {invalid_token}"},
        )

    assert response.status_code == 401
    assert response.json()["code"] == "invalid_access_token"
    assert invalid_token not in response.text


def test_unconfigured_authentication_fails_closed() -> None:
    application = build_application(token_verifier=UnavailableTokenVerifier())

    with TestClient(application) as client:
        response = client.get(
            "/api/v1/students",
            headers={"Authorization": f"Bearer {_TEST_TOKEN}"},
        )

    assert response.status_code == 503
    assert response.headers["Retry-After"] == "30"
    assert response.json()["code"] == "authentication_unavailable"


def test_manage_student_lifecycle_without_exposing_cpf() -> None:
    with build_client() as client:
        created = client.post("/api/v1/students", json=student_payload()).json()
        student_id = created["id"]

        detail = client.get(f"/api/v1/students/{student_id}")
        updated = client.put(
            f"/api/v1/students/{student_id}",
            json={
                "expected_updated_at": created["updated_at"],
                "full_name": "Sophia Almeida Ramos da Silva",
                "birth_date": "2015-05-10",
                "guardian": {
                    "full_name": "Camila Ramos",
                    "phone": "(61) 98888-1234",
                    "email": "camila@example.com",
                },
            },
        )
        inactive = client.post(
            f"/api/v1/students/{student_id}/deactivate",
            json={
                "expected_updated_at": updated.json()["updated_at"],
                "reason": "Solicitação confirmada pela coordenação responsável",
            },
        )
        active = client.post(
            f"/api/v1/students/{student_id}/activate",
            json={
                "expected_updated_at": inactive.json()["updated_at"],
                "reason": "Retorno confirmado pela coordenação responsável",
            },
        )

    assert detail.status_code == 200
    assert detail.json()["cpf_masked"] == "***.***.***-25"
    assert detail.json()["guardian"]["phone"] == "61999991234"
    assert "52998224725" not in detail.text

    assert updated.status_code == 200
    assert updated.json()["full_name"] == "Sophia Almeida Ramos da Silva"
    assert updated.json()["guardian"]["phone"] == "61988881234"
    assert updated.json()["updated_at"] != created["updated_at"]

    assert inactive.status_code == 200
    assert inactive.json()["status"] == "inativo"
    assert active.status_code == 200
    assert active.json()["status"] == "ativo"
    assert active.json()["id"] == student_id


def test_stale_student_update_returns_conflict() -> None:
    with build_client() as client:
        created = client.post("/api/v1/students", json=student_payload()).json()
        payload = {
            "expected_updated_at": created["updated_at"],
            "full_name": "Sophia Almeida Atualizada",
            "birth_date": "2015-05-10",
            "guardian": {
                "full_name": "Camila Ramos",
                "phone": "61999991234",
            },
        }
        first_update = client.put(f"/api/v1/students/{created['id']}", json=payload)
        stale_update = client.put(f"/api/v1/students/{created['id']}", json=payload)

    assert first_update.status_code == 200
    assert stale_update.status_code == 409
    assert stale_update.json()["code"] == "student_version_conflict"


def test_missing_student_and_physical_delete_have_clear_responses() -> None:
    missing_id = "00000000-0000-4000-8000-000000000099"

    with build_client() as client:
        missing = client.get(f"/api/v1/students/{missing_id}")
        physical_delete = client.delete(f"/api/v1/students/{missing_id}")

    assert missing.status_code == 404
    assert missing.json()["code"] == "student_not_found"
    assert physical_delete.status_code == 405
    assert physical_delete.json()["code"] == "http_405"


def test_local_liveness_and_readiness_have_distinct_contracts() -> None:
    with build_client() as client:
        live = client.get("/health/live")
        ready = client.get("/health/ready")

    assert live.status_code == 200
    assert live.json()["status"] == "alive"
    assert "persistence" not in live.json()
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"
    assert ready.json()["persistence"] == "up"
