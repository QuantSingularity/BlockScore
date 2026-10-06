import math
from typing import Any, Dict, Iterable, List

from blockscore_ai.scoring.constants import MAX_SCORE, MIN_SCORE
from blockscore_ai.scoring.features import normalize_records, transform_blockchain_data
from blockscore_ai.scoring.registry import ModelRegistry
from blockscore_ai.scoring.rules import (
    calculate_confidence,
    calculate_score_factors,
    empty_result,
    rule_based_score,
)


class ScoringService:
    def __init__(self, registry: ModelRegistry) -> None:
        self.registry = registry

    def predict_score(self, features: Dict[str, float]) -> int:
        prediction = self.registry.predict(features)
        if prediction is None or not math.isfinite(prediction):
            prediction = rule_based_score(features)
        return int(round(max(MIN_SCORE, min(MAX_SCORE, prediction))))

    def score_history(self, credit_history: Any) -> Dict[str, Any]:
        features = transform_blockchain_data(credit_history)
        if features is None:
            return empty_result()
        record_count = len(normalize_records(credit_history))
        return {
            "score": self.predict_score(features),
            "confidence": calculate_confidence(record_count, self.registry.is_loaded),
            "factors": calculate_score_factors(features),
            "recordCount": record_count,
        }

    def batch_score(self, credit_histories: Iterable[Any]) -> List[Dict[str, Any]]:
        return [self.score_history(history) for history in credit_histories]
