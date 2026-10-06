import numpy as np
import pytest
from blockscore_ai.scoring import (
    FEATURE_COLUMNS,
    normalize_records,
    transform_blockchain_data,
)


def test_normalize_records_drops_invalid_entries(good_history):
    noisy = good_history + [None, "x", {"timestamp": "bad"}, {"timestamp": -5}]
    records = normalize_records(noisy)
    assert len(records) == len(good_history)
    assert records == sorted(records, key=lambda r: r["timestamp"])


def test_normalize_records_rejects_non_list():
    assert normalize_records(None) == []
    assert normalize_records({"a": 1}) == []


def test_normalize_records_coerces_types():
    records = normalize_records(
        [
            {
                "timestamp": "1700000000",
                "amount": "50",
                "repaid": "true",
                "repaymentTimestamp": "1700086400",
                "recordType": "LOAN",
            }
        ]
    )
    assert records[0]["recordType"] == "loan"
    assert records[0]["repaid"] is True
    assert records[0]["amount"] == 50.0
    assert records[0]["repaymentTimestamp"] == 1700086400.0


def test_repayment_timestamp_before_start_is_ignored():
    records = normalize_records(
        [
            {
                "timestamp": 1700000000,
                "amount": 1,
                "repaid": True,
                "repaymentTimestamp": 1600000000,
                "recordType": "loan",
            }
        ]
    )
    assert records[0]["repaymentTimestamp"] == 0.0


def test_transform_good_history(good_history):
    features = transform_blockchain_data(good_history)
    assert set(features) == set(FEATURE_COLUMNS)
    assert features["loan_count"] == 2
    assert features["payment_ratio"] == 1.0
    assert features["late_ratio"] == 0.0
    assert features["outstanding_ratio"] == 0.0
    assert features["avg_repayment_days"] == pytest.approx(40.0)
    assert features["history_days"] == pytest.approx(900.0)


def test_transform_bad_history(bad_history):
    features = transform_blockchain_data(bad_history)
    assert features["payment_ratio"] == 0.0
    assert features["late_ratio"] == 1.0
    assert features["outstanding_ratio"] == 1.0


def test_other_record_types_do_not_dilute_payment_ratio(good_history):
    start = normalize_records(good_history)[0]["timestamp"] + 5
    other = {
        "timestamp": start,
        "amount": 0,
        "repaid": False,
        "repaymentTimestamp": 0,
        "recordType": "other",
        "scoreImpact": 0,
    }
    assert transform_blockchain_data(good_history + [other] * 5)["payment_ratio"] == 1.0


def test_transform_empty_and_unusable():
    assert transform_blockchain_data([]) is None
    assert transform_blockchain_data([{"timestamp": 0}]) is None


def test_features_are_finite(good_history, bad_history):
    for history in (good_history, bad_history):
        assert all(np.isfinite(v) for v in transform_blockchain_data(history).values())
