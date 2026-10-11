import logging
from typing import Any, Tuple

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


def error_response(message: str, status: int) -> Tuple[Any, int]:
    return jsonify({"error": message}), status


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException) -> Tuple[Any, int]:
        return error_response(error.description or error.name, error.code or 500)

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception) -> Tuple[Any, int]:
        logger.error("Unhandled error: %s", error, exc_info=True)
        return error_response("Internal server error", 500)
