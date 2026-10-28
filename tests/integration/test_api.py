"""Testes de integração da camada HTTP."""

from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.core.config import Settings
from backend.app.core.container import ApplicationContainer, build_container
from backend.app.main import create_app
from backend.app.modules.identity.application.authentication import (
    AccessToken,
    AuthenticatedUser,
    InvalidAccessTokenError,
    TokenVerifier,
    UnavailableTokenVerifier,
)
from backend.app.modules.identity.domain.entities import UserProfile, UserRole

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


def build_application(
    token_verifier: TokenVerifier | None = None,
    *,
    role: UserRole = UserRole.COORDINATOR,
    active: bool = True,
) -> FastAPI:
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
    container = build_container(settings)
    assert container.in_memory_profile_store is not None
    now = datetime.now(UTC)
    container.in_memory_profile_store.seed(
        UserProfile(
            id=_TEST_USER_ID,
            full_name="Coordenação Teste",
            role=role,
            active=active,
            created_at=now,
            updated_at=now,
        )
    )
    return create_app(
        settings=settings,
        container=container,
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


def test_health_endpoint_has_traceable_request_id(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level("INFO", logger="livre_acesso.api")
    with build_client() as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "alive"
    assert UUID(response.headers["X-Request-ID"])
    records = [record.message for record in caplog.records if record.name == "livre_acesso.api"]
    assert any("request_completed" in message for message in records)
    assert all(_TEST_TOKEN not in message for message in records)


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
    assert str(payload["cpf"]) not in serialized_response


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
    assert updated.json()["guardian"]["phone"] == "61999991234"
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


def seed_profile(
    application: FastAPI,
    *,
    full_name: str,
    role: UserRole,
    active: bool,
) -> UserProfile:
    container = cast(ApplicationContainer, application.state.container)
    assert container.in_memory_profile_store is not None
    now = datetime.now(UTC)
    profile = UserProfile(
        id=uuid4(),
        full_name=full_name,
        role=role,
        active=active,
        created_at=now,
        updated_at=now,
    )
    container.in_memory_profile_store.seed(profile)
    return profile


def test_my_profile_returns_role_state_and_capabilities() -> None:
    with build_client() as client:
        response = client.get("/api/v1/me")

    assert response.status_code == 200
    assert response.json()["id"] == str(_TEST_USER_ID)
    assert response.json()["role"] == "coordenador"
    assert response.json()["active"] is True
    assert "profiles:manage" in response.json()["capabilities"]


def test_my_profile_can_update_own_display_name() -> None:
    with build_client() as client:
        current = client.get("/api/v1/me").json()
        updated = client.put(
            "/api/v1/me",
            json={
                "expected_updated_at": current["updated_at"],
                "full_name": "Coordenação Principal",
            },
        )

    assert updated.status_code == 200
    assert updated.json()["full_name"] == "Coordenação Principal"
    assert updated.json()["role"] == "coordenador"


def test_coordinator_lists_and_assigns_pending_profile() -> None:
    application = build_application()
    pending = seed_profile(
        application,
        full_name="Nova Recepção",
        role=UserRole.PENDING,
        active=False,
    )

    with TestClient(
        application,
        headers={"Authorization": f"Bearer {_TEST_TOKEN}"},
    ) as client:
        listed = client.get("/api/v1/profiles?role=pendente")
        assigned = client.post(
            f"/api/v1/profiles/{pending.id}/role",
            json={
                "expected_updated_at": pending.updated_at.isoformat(),
                "role": "recepcao",
                "reason": "Acesso aprovado pela coordenação responsável",
            },
        )
        activated = client.post(
            f"/api/v1/profiles/{pending.id}/activate",
            json={
                "expected_updated_at": assigned.json()["updated_at"],
                "reason": "Acesso aprovado pela coordenação responsável",
            },
        )

    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert assigned.status_code == 200
    assert assigned.json()["role"] == "recepcao"
    assert assigned.json()["active"] is False
    assert activated.status_code == 200
    assert activated.json()["active"] is True


def test_receptionist_cannot_list_or_manage_profiles() -> None:
    application = build_application(role=UserRole.RECEPTIONIST)
    target = seed_profile(
        application,
        full_name="Consulta Teste",
        role=UserRole.READ_ONLY,
        active=True,
    )

    with TestClient(
        application,
        headers={"Authorization": f"Bearer {_TEST_TOKEN}"},
    ) as client:
        listed = client.get("/api/v1/profiles")
        changed = client.post(
            f"/api/v1/profiles/{target.id}/deactivate",
            json={
                "expected_updated_at": target.updated_at.isoformat(),
                "reason": "Bloqueio solicitado pela coordenação responsável",
            },
        )

    assert listed.status_code == 403
    assert listed.json()["code"] == "permission_denied"
    assert changed.status_code == 403


def test_last_active_coordinator_cannot_be_deactivated() -> None:
    with build_client() as client:
        current = client.get("/api/v1/me").json()
        response = client.post(
            f"/api/v1/profiles/{_TEST_USER_ID}/deactivate",
            json={
                "expected_updated_at": current["updated_at"],
                "reason": "Bloqueio solicitado pela coordenação responsável",
            },
        )

    assert response.status_code == 409
    assert response.json()["code"] == "last_active_coordinator"


def test_manage_multiple_guardians_with_masking_and_versions() -> None:
    with build_client() as client:
        created = client.post("/api/v1/students", json=student_payload()).json()
        student_id = created["id"]
        initial_list = client.get(f"/api/v1/students/{student_id}/guardians")
        initial_guardian_id = initial_list.json()["items"][0]["id"]

        added = client.post(
            f"/api/v1/students/{student_id}/guardians",
            json={
                "expected_student_updated_at": initial_list.json()["student_updated_at"],
                "relationship": "responsavel_legal",
                "receives_communications": True,
                "guardian": {
                    "full_name": "Roberto Almeida",
                    "phone": "(61) 98888-1234",
                    "email": "roberto@example.com",
                },
            },
        )
        guardian_id = added.json()["id"]
        updated = client.put(
            f"/api/v1/students/{student_id}/guardians/{guardian_id}",
            json={
                "expected_student_updated_at": added.json()["student_updated_at"],
                "expected_guardian_updated_at": added.json()["guardian_updated_at"],
                "full_name": "Roberto Almeida Silva",
                "phone": "(61) 97777-4321",
                "email": "roberto.silva@example.com",
                "relationship": "pai_ou_mae",
                "receives_communications": True,
            },
        )
        promoted = client.post(
            f"/api/v1/students/{student_id}/guardians/{guardian_id}/primary",
            json={"expected_student_updated_at": updated.json()["student_updated_at"]},
        )
        unlinked = client.post(
            f"/api/v1/students/{student_id}/guardians/{initial_guardian_id}/unlink",
            json={
                "expected_student_updated_at": promoted.json()["student_updated_at"],
                "reason": "Vínculo anterior confirmado como incorreto",
            },
        )
        final_list = client.get(f"/api/v1/students/{student_id}/guardians")
        detail = client.get(f"/api/v1/students/{student_id}/guardians/{guardian_id}")

    assert initial_list.status_code == 200
    assert initial_list.json()["items"][0]["phone_masked"] == "(61) *****-1234"
    assert "61999991234" not in initial_list.text
    assert added.status_code == 201
    assert updated.status_code == 200
    assert updated.json()["relationship"] == "pai_ou_mae"
    assert promoted.status_code == 200
    assert promoted.json()["is_primary"] is True
    assert unlinked.status_code == 200
    assert final_list.json()["student_updated_at"] == unlinked.json()["student_updated_at"]
    assert [item["id"] for item in final_list.json()["items"]] == [guardian_id]
    assert detail.status_code == 200
    assert detail.json()["phone"] == "61977774321"


def test_primary_guardian_and_ambiguous_source_return_accessible_errors() -> None:
    with build_client() as client:
        created = client.post("/api/v1/students", json=student_payload()).json()
        student_id = created["id"]
        listed = client.get(f"/api/v1/students/{student_id}/guardians").json()
        primary_id = listed["items"][0]["id"]

        primary_unlink = client.post(
            f"/api/v1/students/{student_id}/guardians/{primary_id}/unlink",
            json={
                "expected_student_updated_at": listed["student_updated_at"],
                "reason": "Contato não deve mais permanecer vinculado",
            },
        )
        ambiguous = client.post(
            f"/api/v1/students/{student_id}/guardians",
            json={
                "expected_student_updated_at": listed["student_updated_at"],
                "relationship": "outro",
            },
        )

    assert primary_unlink.status_code == 409
    assert primary_unlink.json()["code"] == "primary_guardian_required"
    assert ambiguous.status_code == 422
    assert ambiguous.json()["code"] == "validation_error"


def class_payload(modality_id: str, instructor_id: str) -> dict[str, object]:
    return {
        "modality_id": modality_id,
        "name": "Turma Infantil A",
        "capacity": 20,
        "location": "Sala 1",
        "minimum_age": 7,
        "maximum_age": 12,
        "schedules": [
            {"weekday": "segunda", "starts_at": "14:00", "ends_at": "15:00"},
            {"weekday": "quarta", "starts_at": "14:00", "ends_at": "15:00"},
        ],
        "instructor_ids": [instructor_id],
    }


def test_coordinator_manages_versioned_modalities_and_classes() -> None:
    application = build_application()
    instructor = seed_profile(
        application,
        full_name="Instrutora Ana Silva",
        role=UserRole.INSTRUCTOR,
        active=True,
    )

    with TestClient(
        application,
        headers={"Authorization": f"Bearer {_TEST_TOKEN}"},
    ) as client:
        modality = client.post(
            "/api/v1/modalities",
            json={"name": "Capoeira", "description": "Atividade corporal e cultural"},
        )
        created_class = client.post(
            "/api/v1/classes",
            json=class_payload(modality.json()["id"], str(instructor.id)),
        )
        listed = client.get("/api/v1/classes?query=infantil&active=true")
        updated_payload = class_payload(modality.json()["id"], str(instructor.id))
        updated_payload.update(
            {
                "expected_updated_at": created_class.json()["updated_at"],
                "capacity": 24,
                "location": "Quadra coberta",
            }
        )
        updated = client.put(
            f"/api/v1/classes/{created_class.json()['id']}",
            json=updated_payload,
        )
        blocked_modality = client.post(
            f"/api/v1/modalities/{modality.json()['id']}/deactivate",
            json={
                "expected_updated_at": modality.json()["updated_at"],
                "reason": "Reorganização confirmada pela coordenação",
            },
        )
        inactive_class = client.post(
            f"/api/v1/classes/{created_class.json()['id']}/deactivate",
            json={
                "expected_updated_at": updated.json()["updated_at"],
                "reason": "Pausa confirmada pela coordenação responsável",
            },
        )
        inactive_modality = client.post(
            f"/api/v1/modalities/{modality.json()['id']}/deactivate",
            json={
                "expected_updated_at": modality.json()["updated_at"],
                "reason": "Reorganização confirmada pela coordenação",
            },
        )

    assert modality.status_code == 201
    assert created_class.status_code == 201
    assert created_class.json()["schedules"][0]["weekday"] == "segunda"
    assert created_class.json()["instructors"][0]["id"] == str(instructor.id)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert updated.status_code == 200
    assert updated.json()["capacity"] == 24
    assert blocked_modality.status_code == 409
    assert blocked_modality.json()["code"] == "active_classes_exist"
    assert inactive_class.status_code == 200
    assert inactive_class.json()["active"] is False
    assert inactive_modality.status_code == 200
    assert inactive_modality.json()["active"] is False


def test_class_validation_and_permissions_return_accessible_problems() -> None:
    coordinator_app = build_application()
    instructor = seed_profile(
        coordinator_app,
        full_name="Instrutora Ana Silva",
        role=UserRole.INSTRUCTOR,
        active=True,
    )

    with TestClient(
        coordinator_app,
        headers={"Authorization": f"Bearer {_TEST_TOKEN}"},
    ) as client:
        modality = client.post("/api/v1/modalities", json={"name": "Capoeira"}).json()
        invalid_payload = class_payload(modality["id"], str(instructor.id))
        invalid_payload["schedules"] = [
            {"weekday": "segunda", "starts_at": "14:00", "ends_at": "15:30"},
            {"weekday": "segunda", "starts_at": "15:00", "ends_at": "16:00"},
        ]
        invalid = client.post("/api/v1/classes", json=invalid_payload)

    receptionist_app = build_application(role=UserRole.RECEPTIONIST)
    with TestClient(
        receptionist_app,
        headers={"Authorization": f"Bearer {_TEST_TOKEN}"},
    ) as client:
        denied = client.post("/api/v1/modalities", json={"name": "Capoeira"})
        allowed_list = client.get("/api/v1/classes")

    assert invalid.status_code == 422
    assert invalid.json()["code"] == "invalid_class_schedule"
    assert invalid.json()["errors"][0]["field"] == "schedules"
    assert denied.status_code == 403
    assert denied.json()["code"] == "permission_denied"
    assert allowed_list.status_code == 200
