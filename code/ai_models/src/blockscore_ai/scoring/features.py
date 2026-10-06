from typing import Any, Dict, List, Optional

import numpy as np
from blockscore_ai.scoring.constants import (
    MAX_RECORDS,
    REPAYABLE_TYPES,
    SECONDS_PER_DAY,
    TRUE_VALUES,
)


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not np.isfinite(number):
        return default
    return number


def _to_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in TRUE_VALUES
    return bool(value)


def normalize_records(credit_history: Any) -> List[Dict[str, Any]]:
    if not isinstance(credit_history, (list, tuple)):
        return []
    records = []
    for raw in list(credit_history)[:MAX_RECORDS]:
        if not isinstance(raw, dict):
            continue
        timestamp = _to_float(raw.get("timestamp"))
        if timestamp <= 0:
            continue
        repaid = _to_bool(raw.get("repaid"))
        repayment_timestamp = _to_float(raw.get("repaymentTimestamp"))
        if not repaid or repayment_timestamp < timestamp:
            repayment_timestamp = 0.0
        records.append(
            {
                "timestamp": timestamp,
                "amount": max(0.0, _to_float(raw.get("amount"))),
                "repaid": repaid,
                "repaymentTimestamp": repayment_timestamp,
                "recordType": str(raw.get("recordType") or "other").strip().lower(),
                "scoreImpact": _to_float(raw.get("scoreImpact")),
            }
        )
    records.sort(key=lambda item: item["timestamp"])
    return records


def transform_blockchain_data(credit_history: Any) -> Optional[Dict[str, float]]:
    records = normalize_records(credit_history)
    if not records:
        return None
    loans = [r for r in records if r["recordType"] == "loan"]
    payments = [r for r in records if r["recordType"] == "payment"]
    repayable = [r for r in records if r["recordType"] in REPAYABLE_TYPES]

    repaid_count = sum(1 for r in repayable if r["repaid"])
    payment_ratio = repaid_count / len(repayable) if repayable else 0.5
    missed_payments = sum(1 for r in payments if not r["repaid"])
    late_ratio = missed_payments / len(payments) if payments else 0.0

    total_borrowed = sum(r["amount"] for r in loans)
    outstanding = sum(r["amount"] for r in loans if not r["repaid"])
    outstanding_ratio = outstanding / total_borrowed if total_borrowed > 0 else 0.0
    avg_loan = total_borrowed / len(loans) if loans else 0.0

    repayment_days = [
        (r["repaymentTimestamp"] - r["timestamp"]) / SECONDS_PER_DAY
        for r in loans
        if r["repaid"] and r["repaymentTimestamp"] > 0
    ]
    avg_repayment_days = float(np.mean(repayment_days)) if repayment_days else 0.0

    history_days = (
        records[-1]["timestamp"] - records[0]["timestamp"]
    ) / SECONDS_PER_DAY
    impact_sum = float(np.clip(sum(r["scoreImpact"] for r in records), -100, 100))

    return {
        "payment_ratio": float(payment_ratio),
        "late_ratio": float(late_ratio),
        "loan_count": float(len(loans)),
        "log_avg_loan": float(np.log1p(avg_loan)),
        "log_total_borrowed": float(np.log1p(total_borrowed)),
        "outstanding_ratio": float(min(max(outstanding_ratio, 0.0), 1.0)),
        "avg_repayment_days": float(min(avg_repayment_days, 3650.0)),
        "history_days": float(max(history_days, 0.0)),
        "impact_sum": impact_sum,
    }
