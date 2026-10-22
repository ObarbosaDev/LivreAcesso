"""Testes das barreiras de configuração da aplicação."""

import pytest

from backend.app.core.config import Settings


def settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "app_name": "Livre Acesso Test",
        "version": "test",
        "environment": "test",
        "host": "127.0.0.1",
        "port": 8000,
        "debug": False,
        "api_prefix": "/api/v1",
        "cors_origins": ("http://localhost:5173",),
        "supabase_url": None,
        "supabase_publishable_key": None,
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


def test_publishable_key_is_not_exposed_by_repr() -> None:
    secret_value = "publishable-value-must-not-appear"
    current_settings = settings(supabase_publishable_key=secret_value)

    assert secret_value not in repr(current_settings)


@pytest.mark.parametrize("port", [0, 65_536])
def test_invalid_port_is_rejected(port: int) -> None:
    with pytest.raises(ValueError, match="APP_PORT"):
        settings(port=port)


def test_unknown_environment_is_rejected() -> None:
    with pytest.raises(ValueError, match="APP_ENV"):
        settings(environment="unknown")


def test_debug_is_rejected_in_production() -> None:
    with pytest.raises(ValueError, match="APP_DEBUG"):
        settings(environment="production", debug=True, cors_origins=())


def test_cors_wildcard_is_always_rejected() -> None:
    with pytest.raises(ValueError, match="wildcard"):
        settings(cors_origins=("*",))


def test_production_cors_requires_https() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        settings(
            environment="production",
            cors_origins=("http://example.org",),
        )


def test_origins_and_supabase_values_are_normalized() -> None:
    current_settings = settings(
        cors_origins=(" http://localhost:5173/ ",),
        supabase_url=" https://project-ref.supabase.co/ ",
        supabase_publishable_key=" publishable-key ",
    )

    assert current_settings.cors_origins == ("http://localhost:5173",)
    assert current_settings.supabase_url == "https://project-ref.supabase.co"
    assert current_settings.supabase_publishable_key == "publishable-key"
