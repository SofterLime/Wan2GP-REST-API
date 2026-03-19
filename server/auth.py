from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, api_key: str) -> None:  # noqa: ANN001
        super().__init__(app)
        self._api_key = api_key

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not self._api_key:
            return await call_next(request)

        if request.url.path == "/api/health":
            return await call_next(request)

        auth_header = request.headers.get("authorization", "")
        if not auth_header:
            return JSONResponse({"error": "Missing authorization header"}, status_code=401)

        scheme, _, token = auth_header.partition(" ")
        if scheme.lower() != "bearer" or not token:
            return JSONResponse({"error": "Missing authorization header"}, status_code=401)

        if token != self._api_key:
            return JSONResponse({"error": "Invalid API key"}, status_code=403)

        return await call_next(request)
