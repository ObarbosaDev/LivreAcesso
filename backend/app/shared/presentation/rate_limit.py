"""Rate limit local para proteger uma instância da API contra abuso acidental."""

from __future__ import annotations

from collections import defaultdict
from threading import Lock
from time import monotonic
from typing import Any
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


class FixedWindowRateLimitMiddleware(BaseHTTPMiddleware):
    """Limita requisições por IP em uma janela fixa e não registra o IP em logs."""

    def __init__(self, app: Any, *, limit: int, window_seconds: int = 60) -> None:
        super().__init__(app)
        self.limit = limit
        self.window_seconds = window_seconds
        self._windows: defaultdict[str, tuple[float, int]] = defaultdict(lambda: (0.0, 0))
        self._lock = Lock()

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.method == "OPTIONS" or request.url.path.startswith("/health"):
            return await call_next(request)

        key = request.client.host if request.client else "unknown"
        now = monotonic()
        with self._lock:
            started, count = self._windows[key]
            if now - started >= self.window_seconds:
                started, count = now, 0
            count += 1
            self._windows[key] = (started, count)

        if count > self.limit:
            request_id = getattr(request.state, "request_id", uuid4())
            limited_response = JSONResponse(
                status_code=429,
                content={
                    "type": "https://livre-acesso.org/problems/rate-limit",
                    "title": "Muitas requisições",
                    "status": 429,
                    "detail": "Aguarde alguns instantes antes de tentar novamente.",
                    "code": "RATE_LIMIT_EXCEEDED",
                    "request_id": str(request_id),
                    "errors": [],
                },
                headers={"Retry-After": str(self.window_seconds)},
            )
            return limited_response

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, self.limit - count))
        return response
