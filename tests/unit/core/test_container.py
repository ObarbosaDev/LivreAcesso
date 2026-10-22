"""Testes da seleção segura de infraestrutura no composition root."""

import asyncio

import pytest

from backend.app.core.config import Settings
from backend.app.core.container import build_container


def settings(
    *,
    environment: str = "test",
    supabase_url: str | None = None,
    publishable_key: str | None = None,
) -> Settings:
    return Settings(
        app_name="Livre Acesso Test",
        version="test",
        environment=environment,
        host="127.0.0.1",
        port=8000,
        debug=False,
        api_prefix="/api/v1",
        cors_origins=(),
        supabase_url=supabase_url,
        supabase_publishable_key=publishable_key,
    )


def test_without_supabase_uses_memory_in_test_environment() -> None:
    container = build_container(settings())

    assert container.in_memory_student_store is not None
    assert container.supabase_gateway is None


def test_complete_supabase_configuration_uses_remote_gateway() -> None:
    container = build_container(
        settings(
            environment="production",
            supabase_url="https://project-ref.supabase.co",
            publishable_key="publishable-key",
        )
    )

    assert container.in_memory_student_store is None
    assert container.supabase_gateway is not None
    asyncio.run(container.close())


@pytest.mark.parametrize(
    ("url", "key"),
    [
        ("https://project-ref.supabase.co", None),
        (None, "publishable-key"),
    ],
)
def test_partial_supabase_configuration_is_rejected(
    url: str | None,
    key: str | None,
) -> None:
    with pytest.raises(ValueError, match="em conjunto"):
        build_container(settings(supabase_url=url, publishable_key=key))


def test_production_never_falls_back_to_memory() -> None:
    with pytest.raises(ValueError, match="obrigatório"):
        build_container(settings(environment="production"))
