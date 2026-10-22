"""Configurações lidas exclusivamente das variáveis do processo."""

import os
from dataclasses import dataclass, field
from functools import lru_cache
from urllib.parse import urlparse

_ALLOWED_ENVIRONMENTS = frozenset({"development", "test", "preview", "staging", "production"})


def _as_bool(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    """Configuração validada antes que a aplicação aceite requisições."""

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

    def __post_init__(self) -> None:
        environment = self.environment.strip().lower()
        if environment not in _ALLOWED_ENVIRONMENTS:
            raise ValueError("APP_ENV possui um valor não reconhecido.")
        if not 1 <= self.port <= 65_535:
            raise ValueError("APP_PORT deve estar entre 1 e 65535.")
        if self.debug and environment in {"preview", "staging", "production"}:
            raise ValueError("APP_DEBUG não pode ser habilitado fora de development ou test.")

        normalized_origins = tuple(origin.strip().rstrip("/") for origin in self.cors_origins)
        for origin in normalized_origins:
            if origin == "*":
                # Credenciais e wildcard não podem coexistir com segurança.
                raise ValueError("APP_CORS_ORIGINS não aceita wildcard.")
            parsed_origin = urlparse(origin)
            if parsed_origin.scheme not in {"http", "https"} or not parsed_origin.netloc:
                raise ValueError("APP_CORS_ORIGINS contém uma origem inválida.")
            if environment not in {"development", "test"} and parsed_origin.scheme != "https":
                raise ValueError("APP_CORS_ORIGINS exige HTTPS fora do ambiente local.")

        supabase_url = self.supabase_url.strip().rstrip("/") if self.supabase_url else None
        publishable_key = (
            self.supabase_publishable_key.strip() if self.supabase_publishable_key else None
        )

        object.__setattr__(self, "environment", environment)
        object.__setattr__(self, "cors_origins", normalized_origins)
        object.__setattr__(self, "supabase_url", supabase_url)
        object.__setattr__(self, "supabase_publishable_key", publishable_key)

    @classmethod
    def from_environment(cls) -> "Settings":
        environment = os.getenv("APP_ENV", "development").strip().lower()
        default_origins = "http://localhost:5173" if environment in {"development", "test"} else ""
        origins = os.getenv("APP_CORS_ORIGINS", default_origins)
        return cls(
            app_name=os.getenv("APP_NAME", "Livre Acesso API"),
            version=os.getenv("APP_VERSION", "0.1.0"),
            environment=environment,
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
    """Mantém uma configuração imutável por instância quente do processo."""

    return Settings.from_environment()
