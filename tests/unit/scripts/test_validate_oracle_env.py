from scripts.validate_oracle_env import validate


def valid_env() -> dict[str, str]:
    return {
        "APP_ENV": "production",
        "APP_HOST": "0.0.0.0",
        "APP_PORT": "8000",
        "APP_CORS_ORIGINS": "https://app.example.org",
        "SUPABASE_URL": "https://project.supabase.co",
        "SUPABASE_PUBLISHABLE_KEY": "public-key",
        "APP_DEBUG": "false",
    }


def test_accepts_valid_api_environment() -> None:
    assert validate(valid_env()) == []


def test_requires_worker_secrets_only_for_worker() -> None:
    errors = validate(valid_env(), worker=True)
    assert "variável ausente: SUPABASE_SERVICE_ROLE_KEY" in errors
    assert "variável ausente: COMMUNICATION_WEBHOOK_URL" in errors


def test_rejects_insecure_production_configuration() -> None:
    environment = valid_env()
    environment["APP_CORS_ORIGINS"] = "*"
    environment["SUPABASE_URL"] = "http://project.supabase.co"
    errors = validate(environment)
    assert "APP_CORS_ORIGINS não pode usar wildcard em produção" in errors
    assert "SUPABASE_URL deve usar HTTPS" in errors
