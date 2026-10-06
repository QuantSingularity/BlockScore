from blockscore_ai.scoring import (
    NEUTRAL_SCORE,
    calculate_confidence,
    calculate_score_factors,
    empty_result,
    rule_based_score,
    transform_blockchain_data,
)


def test_rule_score_orders_histories(good_history, bad_history):
    good = rule_based_score(transform_blockchain_data(good_history))
    bad = rule_based_score(transform_blockchain_data(bad_history))
    assert good > bad


def test_confidence_scales_with_records():
    assert calculate_confidence(1, True) < calculate_confidence(8, True)
    assert calculate_confidence(100, True) == 0.95
    assert calculate_confidence(100, False) == 0.6


def test_factors_reflect_history(good_history, bad_history):
    good = {
        f["factor"]: f
        for f in calculate_score_factors(transform_blockchain_data(good_history))
    }
    bad = {
        f["factor"]: f
        for f in calculate_score_factors(transform_blockchain_data(bad_history))
    }
    assert good["Excellent payment history"]["impact"] == "positive"
    assert bad["Poor payment history"]["impact"] == "negative"
    assert bad["High outstanding debt"]["impact"] == "negative"


def test_empty_result_is_neutral():
    result = empty_result()
    assert result["score"] == NEUTRAL_SCORE
    assert result["confidence"] == 0.0
    assert result["recordCount"] == 0
