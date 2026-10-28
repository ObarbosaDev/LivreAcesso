"""Valida a configuração mínima para executar o stack em produção."""

from __future__ import annotations

import os
import sys
from urllib.parse import urlparse

REQUIRED = (
    "APP_ENV",
    "APP_HOST",
    "APP_PORT",
    "APP_CORS_ORIGINS",
    "SUPABASE_URL",
    "SUPABASE_PUBLISHABLE_KEY",
)
WORKER_REQUIRED = ("SUPABASE_SERVICE_ROLE_KEY", "COMMUNICATION_WEBHOOK_URL")


def validate(environ: dict[str, str], *, worker: bool = False) -> list[str]:
    errors = [f"variável ausente: {name}" for name in REQUIRED if not environ.get(name)]
    if worker:
        errors.extend(
            f"variável ausente: {name}" for name in WORKER_REQUIRED if not environ.get(name)
        )
    if environ.get("APP_ENV") != "production":
        errors.append("APP_ENV deve ser production")
    if environ.get("APP_DEBUG", "false").lower() != "false":
        errors.append("APP_DEBUG deve ser false")
    if environ.get("APP_HOST") != "0.0.0.0":
        errors.append("APP_HOST deve ser 0.0.0.0")
    supabase_url = environ.get("SUPABASE_URL", "")
    if supabase_url and urlparse(supabase_url).scheme != "https":
        errors.append("SUPABASE_URL deve usar HTTPS")
    if not environ.get("APP_CORS_ORIGINS", "").strip():
        errors.append("APP_CORS_ORIGINS não pode ser vazio")
    if "*" in environ.get("APP_CORS_ORIGINS", ""):
        errors.append("APP_CORS_ORIGINS não pode usar wildcard em produção")
    return errors


def main() -> int:
    errors = validate(dict(os.environ), worker="--worker" in sys.argv[1:])
    if errors:
        for error in errors:
            print(f"FAIL {error}")
        return 1
    print("PASS configuração Oracle válida")
    return 0


if __name__ == "__main__":
    sys.exit(main())
