from typing import List, Tuple

import numpy as np
import pandas as pd
from blockscore_ai.scoring.constants import FEATURE_COLUMNS, SECONDS_PER_DAY
from blockscore_ai.scoring.features import transform_blockchain_data

BASE_TIMESTAMP = 1_700_000_000
TARGET_COLUMN = "credit_score"


def _simulate_history(rng: np.random.Generator) -> Tuple[List[dict], float, float, int]:
    reliability = float(rng.beta(5, 2))
    span_days = float(rng.uniform(30, 1500))
    loan_count = int(min(rng.poisson(3), 12))
    payment_count = int(min(rng.poisson(6), 30))
    history = []
    for _ in range(loan_count):
        start = BASE_TIMESTAMP + int(rng.uniform(0, span_days) * SECONDS_PER_DAY)
        amount = float(rng.lognormal(8, 1))
        repaid = bool(rng.random() < min(reliability + 0.05, 1.0))
        repay_days = float(rng.lognormal(np.log(45 * (1.6 - reliability)), 0.4))
        history.append(
            {
                "timestamp": start,
                "amount": amount,
                "repaid": repaid,
                "repaymentTimestamp": (
                    start + int(repay_days * SECONDS_PER_DAY) if repaid else 0
                ),
                "recordType": "loan",
                "scoreImpact": 0,
            }
        )
    for _ in range(payment_count):
        moment = BASE_TIMESTAMP + int(rng.uniform(0, span_days) * SECONDS_PER_DAY)
        made = bool(rng.random() < reliability)
        history.append(
            {
                "timestamp": moment,
                "amount": float(rng.lognormal(6, 0.8)),
                "repaid": made,
                "repaymentTimestamp": moment if made else 0,
                "recordType": "payment",
                "scoreImpact": 5 if made else -10,
            }
        )
    return history, reliability, span_days, loan_count


def generate_synthetic_data(n_samples: int = 6000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    while len(rows) < n_samples:
        history, reliability, span_days, loan_count = _simulate_history(rng)
        features = transform_blockchain_data(history)
        if features is None:
            continue
        quality = (
            0.80 * reliability
            + 0.12 * min(span_days / 1095.0, 1.0)
            + 0.08 * min(loan_count / 6.0, 1.0)
        )
        score = 300 + 550 * quality + rng.normal(0, 20)
        features[TARGET_COLUMN] = float(np.clip(score, 300, 850))
        rows.append(features)
    return pd.DataFrame(rows, columns=FEATURE_COLUMNS + [TARGET_COLUMN])
