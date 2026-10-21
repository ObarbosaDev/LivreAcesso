"""Configurações lidas exclusivamente das variáveis do processo."""

import os
from dataclasses import dataclass, field
from functools import lru_cache


def _as_bool(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str
    version: str
    environment: str
    host: str
    port: int
    debug: bool
    api_prefix: str
    cors_origins: tuple[str, ...]
    supabase_url: str | None = None
    supabase_publishable_key: str | None = field(default=None, repr=False)

    @classmethod
    def from_environment(cls) -> "Settings":
        origins = os.getenv("APP_CORS_ORIGINS", "http://localhost:5173")
        return cls(
            app_name=os.getenv("APP_NAME", "Livre Acesso API"),
            version=os.getenv("APP_VERSION", "0.1.0"),
            environment=os.getenv("APP_ENV", "development"),
            host=os.getenv("APP_HOST", "127.0.0.1"),
            port=int(os.getenv("APP_PORT", "8000")),
            debug=_as_bool(os.getenv("APP_DEBUG")),
            api_prefix="/api/v1",
            cors_origins=tuple(origin.strip() for origin in origins.split(",") if origin.strip()),
            supabase_url=os.getenv("SUPABASE_URL") or None,
            supabase_publishable_key=os.getenv("SUPABASE_PUBLISHABLE_KEY") or None,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_environment()
