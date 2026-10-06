from typing import Any, Dict, List

from blockscore_ai.scoring.constants import NEUTRAL_SCORE


def rule_based_score(features: Dict[str, float]) -> float:
    score = 300.0
    score += features["payment_ratio"] * 330.0
    score += (1.0 - features["late_ratio"]) * 60.0
    score += (1.0 - features["outstanding_ratio"]) * 90.0
    score += min(features["history_days"] / 730.0, 1.0) * 40.0
    score += min(features["loan_count"], 10.0) * 3.0
    score -= min(max(features["avg_repayment_days"] - 90.0, 0.0) / 90.0, 1.0) * 30.0
    score += features["impact_sum"] * 0.3
    return score


def calculate_confidence(record_count: int, model_loaded: bool) -> float:
    base = min(0.5 + record_count * 0.05, 0.95)
    if not model_loaded:
        base = min(base, 0.6)
    return round(base, 2)


def _factor(name: str, impact: str, description: str, value: float) -> Dict[str, Any]:
    return {
        "factor": name,
        "impact": impact,
        "description": description,
        "value": round(float(value), 4),
    }


def calculate_score_factors(features: Dict[str, float]) -> List[Dict[str, Any]]:
    factors = []
    ratio = features["payment_ratio"]
    if ratio >= 0.9:
        factors.append(
            _factor(
                "Excellent payment history",
                "positive",
                "Consistently repaying obligations",
                ratio,
            )
        )
    elif ratio >= 0.7:
        factors.append(
            _factor(
                "Good payment history",
                "positive",
                "Generally repaying obligations on time",
                ratio,
            )
        )
    elif ratio <= 0.5:
        factors.append(
            _factor(
                "Poor payment history",
                "negative",
                "Frequently missing repayments",
                ratio,
            )
        )
    if features["late_ratio"] >= 0.25:
        factors.append(
            _factor(
                "Missed or late payments",
                "negative",
                "A significant share of payments were missed or late",
                features["late_ratio"],
            )
        )
    outstanding = features["outstanding_ratio"]
    if features["loan_count"] > 0:
        if outstanding <= 0.3:
            factors.append(
                _factor(
                    "Low outstanding debt",
                    "positive",
                    "Most borrowed principal has been repaid",
                    outstanding,
                )
            )
        elif outstanding >= 0.6:
            factors.append(
                _factor(
                    "High outstanding debt",
                    "negative",
                    "A large share of borrowed principal is unpaid",
                    outstanding,
                )
            )
    if features["avg_repayment_days"] > 180:
        factors.append(
            _factor(
                "Slow repayment",
                "negative",
                "Loans take a long time to repay on average",
                features["avg_repayment_days"],
            )
        )
    if features["history_days"] >= 730:
        factors.append(
            _factor(
                "Established history",
                "positive",
                "Credit activity spans multiple years",
                features["history_days"],
            )
        )
    elif features["history_days"] < 90:
        factors.append(
            _factor(
                "Short history",
                "neutral",
                "Limited time span of credit activity",
                features["history_days"],
            )
        )
    if features["loan_count"] >= 5:
        factors.append(
            _factor(
                "Multiple loans",
                "neutral",
                "Experience managing multiple loans",
                features["loan_count"],
            )
        )
    elif features["loan_count"] == 0:
        factors.append(
            _factor("Limited loan history", "neutral", "No previous loans on record", 0)
        )
    return factors


def empty_result() -> Dict[str, Any]:
    return {
        "score": NEUTRAL_SCORE,
        "confidence": 0.0,
        "factors": [
            {
                "factor": "No credit history",
                "impact": "neutral",
                "description": "No usable credit records found",
                "value": 0.0,
            }
        ],
        "recordCount": 0,
    }
