"""
BlockScore Model Integration Module

This module provides utilities for integrating the Python scoring model with the Node.js API.
It includes functions for data transformation, model inference, and API communication.
"""

import logging
import os
from typing import Any, Dict

import joblib
import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

model_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "credit_scoring_model.pkl"
)
try:
    model = joblib.load(model_path)
    logger.info("Credit scoring model loaded successfully")
except Exception as e:
    logger.warning(
        f"Could not load model from {model_path}: {e}. Using fallback scoring."
    )
    model = None


def transform_blockchain_data(credit_history: Any) -> Any:
    """
    Transform blockchain credit history data into features for model input

    Parameters:
    -----------
    credit_history : list
        List of credit record objects from blockchain

    Returns:
    --------
    dict
        Dictionary of extracted features
    """
    if not credit_history:
        return None
    income_proxy = 0
    debt_ratio = 0
    payment_history = 0
    loan_count = 0
    credit_utilization = 0
    repaid_count = 0
    total_records = len(credit_history)
    total_borrowed = 0
    repayment_times = []
    for record in credit_history:
        if record["recordType"] == "loan":
            loan_count += 1
            total_borrowed += int(record["amount"])
        if record["repaid"]:
            repaid_count += 1
            if record["repaymentTimestamp"] > 0:
                days_to_repay = (
                    int(record["repaymentTimestamp"]) - int(record["timestamp"])
                ) / (60 * 60 * 24)
                repayment_times.append(days_to_repay)
    payment_history = repaid_count / total_records if total_records > 0 else 0
    avg_loan = total_borrowed / loan_count if loan_count > 0 else 0
    income_proxy = avg_loan * 10
    active_debt = (
        total_borrowed - repaid_count / total_records * total_borrowed
        if total_records > 0
        else 0
    )
    debt_ratio = active_debt / income_proxy if income_proxy > 0 else 0.5
    debt_ratio = min(debt_ratio, 1.0)
    avg_repayment_time = np.mean(repayment_times) if repayment_times else 30
    credit_utilization = min(avg_repayment_time / 90, 1.0)
    features = {
        "income": income_proxy,
        "debt_ratio": debt_ratio,
        "payment_history": payment_history,
        "loan_count": loan_count,
        "loan_amount": avg_loan,
        "age": 30,
        "credit_utilization": credit_utilization,
    }
    return features


def predict_score(features: Any) -> int:
    """
    Predict credit score based on features

    Parameters:
    -----------
    features : dict
        Dictionary of features

    Returns:
    --------
    int
        Predicted credit score (300-850)
    """
    if model is not None:
        df = pd.DataFrame([features])
        prediction = model.predict(df)[0]
    else:
        # Rule-based fallback when model is not loaded
        payment_history = features.get("payment_history", 0.5)
        debt_ratio = features.get("debt_ratio", 0.5)
        prediction = 300 + (payment_history * 350) + ((1 - debt_ratio) * 200)
    prediction = max(300, min(850, prediction))
    return int(prediction)


def calculate_score_factors(features: Any, prediction: Any) -> Dict[str, Any]:
    """
    Calculate contributing factors to the credit score

    Parameters:
    -----------
    features : dict
        Input features used for prediction
    prediction : int
        Model prediction (credit score)

    Returns:
    --------
    list
        List of factors affecting the credit score
    """
    factors = []
    payment_history = features["payment_history"]
    if payment_history >= 0.9:
        factors.append(
            {
                "factor": "Excellent payment history",
                "impact": "positive",
                "description": "Consistently repaying debts on time",
            }
        )
    elif payment_history >= 0.7:
        factors.append(
            {
                "factor": "Good payment history",
                "impact": "positive",
                "description": "Generally repaying debts on time",
            }
        )
    elif payment_history <= 0.5:
        factors.append(
            {
                "factor": "Poor payment history",
                "impact": "negative",
                "description": "Frequently missing payments",
            }
        )
    debt_ratio = features["debt_ratio"]
    if debt_ratio <= 0.3:
        factors.append(
            {
                "factor": "Low debt ratio",
                "impact": "positive",
                "description": "Low amount of debt relative to income",
            }
        )
    elif debt_ratio >= 0.6:
        factors.append(
            {
                "factor": "High debt ratio",
                "impact": "negative",
                "description": "High amount of debt relative to income",
            }
        )
    credit_util = features["credit_utilization"]
    if credit_util <= 0.3:
        factors.append(
            {
                "factor": "Low credit utilization",
                "impact": "positive",
                "description": "Using a small portion of available credit",
            }
        )
    elif credit_util >= 0.7:
        factors.append(
            {
                "factor": "High credit utilization",
                "impact": "negative",
                "description": "Using a large portion of available credit",
            }
        )
    loan_count = features["loan_count"]
    if loan_count >= 5:
        factors.append(
            {
                "factor": "Multiple loans",
                "impact": "neutral",
                "description": "History of managing multiple loans",
            }
        )
    elif loan_count == 0:
        factors.append(
            {
                "factor": "Limited credit history",
                "impact": "neutral",
                "description": "Few or no previous loans on record",
            }
        )
    return factors


def batch_score(credit_histories: Any) -> float:
    """
    Process multiple credit histories for batch scoring

    Parameters:
    -----------
    credit_histories : list
        List of credit history lists, each for a different user

    Returns:
    --------
    list
        List of scoring results
    """
    results = []
    for history in credit_histories:
        features = transform_blockchain_data(history)
        if features is None:
            results.append(
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
            continue
        prediction = predict_score(features)
        confidence = min(0.5 + len(history) * 0.05, 0.95)
        factors = calculate_score_factors(features, prediction)
        results.append(
            {
                "score": prediction,
                "confidence": round(confidence, 2),
                "factors": factors,
            }
        )
    return results


if __name__ == "__main__":
    example_history = [
        {
            "timestamp": 1621500000,
            "amount": 5000,
            "repaid": True,
            "repaymentTimestamp": 1623500000,
            "provider": "0x123...",
            "recordType": "loan",
            "scoreImpact": 5,
        },
        {
            "timestamp": 1625500000,
            "amount": 10000,
            "repaid": True,
            "repaymentTimestamp": 1630500000,
            "provider": "0x456...",
            "recordType": "loan",
            "scoreImpact": 3,
        },
    ]
    features = transform_blockchain_data(example_history)
    score = predict_score(features)
    factors = calculate_score_factors(features, score)
    logger.info(f"Extracted features: {features}")
    logger.info(f"Predicted score: {score}")
    logger.info(f"Score factors: {factors}")
