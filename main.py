"""Ponto de entrada local da API do Livre Acesso.

A aplicação real é construída em ``backend.app.main``. Este arquivo permanece
na raiz para oferecer o comando simples ``python main.py`` durante o projeto.
"""

import uvicorn

from backend.app.core.config import get_settings
from backend.app.main import app


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "backend.app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )


if __name__ == "__main__":
    main()
