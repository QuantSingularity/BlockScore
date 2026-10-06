import logging
from datetime import datetime, timezone
from typing import Any

from blockscore_ai import __version__
from blockscore_ai.api.errors import error_response
from blockscore_ai.scoring import ScoringService, empty_result
from flask import Blueprint, current_app, jsonify, request

logger = logging.getLogger(__name__)

SERVICE_NAME = "BlockScore Model API"

bp = Blueprint("scoring", __name__)


def _service() -> ScoringService:
    return current_app.extensions["scoring_service"]


def _decorate(result: dict, info: dict) -> dict:
    scored = result.get("recordCount", 0) > 0
    result["modelName"] = info["modelName"]
    result["modelVersion"] = info["modelVersion"]
    result["source"] = info["source"] if scored else "none"
    return result


def _score(service: ScoringService, history: Any) -> dict:
    return service.score_history(history) if history else empty_result()


@bp.route("/health", methods=["GET"])
def health_check() -> Any:
    info = _service().registry.info()
    return jsonify(
        {
            "status": "ok",
            "service": SERVICE_NAME,
            "apiVersion": __version__,
            "modelLoaded": info["modelLoaded"],
            "modelVersion": info["modelVersion"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


@bp.route("/model-info", methods=["GET"])
def model_info() -> Any:
    return jsonify(_service().registry.info())


@bp.route("/predict", methods=["POST"])
def predict() -> Any:
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or "creditHistory" not in data:
        return error_response(
            'Invalid input data. Expected "creditHistory" field.', 400
        )
    history = data["creditHistory"]
    if not isinstance(history, list):
        return error_response('"creditHistory" must be a list.', 400)
    service = _service()
    result = _score(service, history)
    logger.info("Prediction served: records=%s score=%s", len(history), result["score"])
    return jsonify(_decorate(result, service.registry.info()))


@bp.route("/batch-predict", methods=["POST"])
def batch_predict() -> Any:
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or "batch" not in data:
        return error_response('Invalid input data. Expected "batch" field.', 400)
    batch = data["batch"]
    if not isinstance(batch, list):
        return error_response('"batch" must be a list.', 400)
    limit = current_app.config["MAX_BATCH_SIZE"]
    if len(batch) > limit:
        return error_response(f"Batch size exceeds limit of {limit}.", 413)
    service = _service()
    info = service.registry.info()
    results = []
    for item in batch:
        if not isinstance(item, dict):
            results.append({"userId": None, "error": "Invalid batch item"})
            continue
        history = item.get("creditHistory")
        if history is not None and not isinstance(history, list):
            results.append(
                {
                    "userId": item.get("userId"),
                    "error": '"creditHistory" must be a list',
                }
            )
            continue
        result = _score(service, history)
        result["userId"] = item.get("userId")
        results.append(_decorate(result, info))
    logger.info("Batch prediction served: items=%s", len(results))
    return jsonify({"results": results})
