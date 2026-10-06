import hmac
from typing import Any, Optional, Tuple

from blockscore_ai.api.errors import error_response
from flask import Flask, request

PUBLIC_ENDPOINTS = frozenset({"scoring.health_check"})


def _authorized(expected: str) -> bool:
    if not expected:
        return True
    provided = request.headers.get("X-API-Key", "")
    return hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8"))


def register_auth(app: Flask) -> None:
    @app.before_request
    def require_api_key() -> Optional[Tuple[Any, int]]:
        if request.endpoint in PUBLIC_ENDPOINTS:
            return None
        if not _authorized(app.config.get("API_KEY", "")):
            return error_response("Unauthorized", 401)
        return None
