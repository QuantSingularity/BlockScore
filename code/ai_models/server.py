"""
BlockScore Model API Server

This module provides a Flask API server for the BlockScore credit scoring model.
It exposes endpoints for health checks and credit score prediction.
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from flask import Flask, jsonify, request
from model_integration import (
    calculate_score_factors,
    predict_score,
    transform_blockchain_data,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health_check() -> Any:
    """Health check endpoint"""
    return jsonify(
        {
            "status": "ok",
            "service": "BlockScore Model API",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


@app.route("/predict", methods=["POST"])
def predict() -> Dict[str, Any]:
    """
    Endpoint for credit score prediction

    Expected JSON input:
    {
        "creditHistory": [
            {
                "timestamp": 1621500000,
                "amount": 5000,
                "repaid": true,
                "repaymentTimestamp": 1623500000,
                "provider": "0x123...",
                "recordType": "loan",
                "scoreImpact": 5
            },
            ...
        ]
    }
    """
    try:
        data = request.get_json()
        logger.info(f"Received prediction request: {data}")
        if not data or "creditHistory" not in data:
            logger.warning("Invalid input data: missing creditHistory field")
            return (
                jsonify(
                    {"error": 'Invalid input data. Expected "creditHistory" field.'}
                ),
                400,
            )
        credit_history = data["creditHistory"]
        if not credit_history:
            logger.info("Empty credit history, returning default score")
            return jsonify(
                {
                    "score": 500,
                    "confidence": 0,
                    "factors": [
                        {
                            "factor": "No credit history",
                            "impact": "neutral",
                            "description": "No credit records found",
                        }
                    ],
                }
            )
        features = transform_blockchain_data(credit_history)
        if features is None:
            logger.warning("Failed to process credit history data")
            return (jsonify({"error": "Failed to process credit history data"}), 400)
        prediction = predict_score(features)
        confidence = min(0.5 + len(credit_history) * 0.05, 0.95)
        factors = calculate_score_factors(features, prediction)
        result = {
            "score": prediction,
            "confidence": round(confidence, 2),
            "factors": factors,
        }
        logger.info(f"Prediction result: {result}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Prediction failed: {str(e)}", exc_info=True)
        return (jsonify({"error": f"Prediction failed: {str(e)}"}), 500)


@app.route("/batch-predict", methods=["POST"])
def batch_predict() -> Dict[str, Any]:
    """
    Endpoint for batch credit score prediction

    Expected JSON input:
    {
        "batch": [
            {
                "userId": "user1",
                "creditHistory": [...]
            },
            {
                "userId": "user2",
                "creditHistory": [...]
            }
        ]
    }
    """
    try:
        data = request.get_json()
        logger.info(
            f"Received batch prediction request with {len(data.get('batch', []))} items"
        )
        if not data or "batch" not in data:
            logger.warning("Invalid input data: missing batch field")
            return (
                jsonify({"error": 'Invalid input data. Expected "batch" field.'}),
                400,
            )
        batch = data["batch"]
        results = []
        for item in batch:
            user_id = item.get("userId", "unknown")
            credit_history = item.get("creditHistory", [])
            if not credit_history:
                results.append(
                    {
                        "userId": user_id,
                        "score": 500,
                        "confidence": 0,
                        "factors": [
                            {
                                "factor": "No credit history",
                                "impact": "neutral",
                                "description": "No credit records found",
                            }
                        ],
                    }
                )
                continue
            features = transform_blockchain_data(credit_history)
            if features is None:
                results.append(
                    {
                        "userId": user_id,
                        "error": "Failed to process credit history data",
                    }
                )
                continue
            prediction = predict_score(features)
            confidence = min(0.5 + len(credit_history) * 0.05, 0.95)
            factors = calculate_score_factors(features, prediction)
            results.append(
                {
                    "userId": user_id,
                    "score": prediction,
                    "confidence": round(confidence, 2),
                    "factors": factors,
                }
            )
        logger.info(f"Batch prediction completed for {len(results)} users")
        return jsonify({"results": results})
    except Exception as e:
        logger.error(f"Batch prediction failed: {str(e)}", exc_info=True)
        return (jsonify({"error": f"Batch prediction failed: {str(e)}"}), 500)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    debug = os.environ.get("FLASK_ENV") == "development"
    logger.info(f"Starting BlockScore Model API on port {port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
