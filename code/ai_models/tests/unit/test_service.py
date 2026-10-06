import pytest
from blockscore_ai.scoring import (
    MAX_SCORE,
    MIN_SCORE,
    NEUTRAL_SCORE,
    ScoringService,
    transform_blockchain_data,
)


class FixedRegistry:
    is_loaded = True

    def __init__(self, value):
        self.value = value

    def predict(self, features):
        return self.value


@pytest.mark.parametrize(
    "raw,expected", [(720, 720), (200, MIN_SCORE), (900, MAX_SCORE)]
)
def test_prediction_is_clamped(good_history, raw, expected):
    service = ScoringService(FixedRegistry(raw))
    assert service.predict_score(transform_blockchain_data(good_history)) == expected


@pytest.mark.parametrize("raw", [None, float("nan"), float("inf")])
def test_invalid_prediction_uses_rules(good_history, raw):
    service = ScoringService(FixedRegistry(raw))
    score = service.predict_score(transform_blockchain_data(good_history))
    assert MIN_SCORE <= score <= MAX_SCORE


def test_rule_based_service_orders_histories(rules_service, good_history, bad_history):
    good = rules_service.score_history(good_history)
    bad = rules_service.score_history(bad_history)
    assert good["score"] > bad["score"]
    assert good["confidence"] <= 0.6


def test_trained_service_orders_histories(service, good_history, bad_history):
    assert (
        service.score_history(good_history)["score"]
        > service.score_history(bad_history)["score"]
    )


def test_empty_history_is_neutral(service):
    result = service.score_history([])
    assert result["score"] == NEUTRAL_SCORE
    assert result["recordCount"] == 0


def test_batch_score_preserves_order(service, good_history, bad_history):
    results = service.batch_score([good_history, [], bad_history])
    assert len(results) == 3
    assert results[1]["score"] == NEUTRAL_SCORE
    assert results[0]["score"] > results[2]["score"]
