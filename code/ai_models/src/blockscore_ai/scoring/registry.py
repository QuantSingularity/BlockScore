import json
import logging
import threading
from pathlib import Path
from typing import Any, Dict, Optional

import joblib
import pandas as pd
from blockscore_ai.scoring.constants import FEATURE_COLUMNS

logger = logging.getLogger(__name__)

RULES_MODEL_NAME = "blockscore-rules"
RULES_MODEL_VERSION = "rules-1"


class ModelRegistry:
    def __init__(self, model_path: Path, metadata_path: Optional[Path] = None) -> None:
        self.model_path = Path(model_path)
        self.metadata_path = (
            Path(metadata_path)
            if metadata_path
            else self.model_path.with_suffix(".json")
        )
        self._lock = threading.Lock()
        self._loaded = False
        self._model: Any = None
        self._metadata: Dict[str, Any] = {}

    def _read_metadata(self) -> Dict[str, Any]:
        if not self.metadata_path.exists():
            return {}
        try:
            return json.loads(self.metadata_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            logger.warning(
                "Could not read model metadata %s: %s", self.metadata_path, exc
            )
            return {}

    def load(self, force: bool = False) -> Optional[Any]:
        with self._lock:
            if self._loaded and not force:
                return self._model
            model = None
            metadata: Dict[str, Any] = {}
            if self.model_path.exists():
                try:
                    candidate = joblib.load(self.model_path)
                    metadata = self._read_metadata()
                    columns = metadata.get("feature_columns")
                    if columns is not None and list(columns) != FEATURE_COLUMNS:
                        raise ValueError(
                            "model feature columns do not match service schema"
                        )
                    model = candidate
                    logger.info("Credit scoring model loaded from %s", self.model_path)
                except Exception as exc:
                    logger.error(
                        "Could not load model from %s: %s", self.model_path, exc
                    )
                    model = None
                    metadata = {}
            else:
                logger.warning(
                    "No trained model at %s, using rule-based scoring", self.model_path
                )
            self._model = model
            self._metadata = metadata
            self._loaded = True
            return model

    @property
    def is_loaded(self) -> bool:
        return self.load() is not None

    def info(self) -> Dict[str, Any]:
        model = self.load()
        metadata = self._metadata
        return {
            "modelLoaded": model is not None,
            "modelName": metadata.get("model_name", RULES_MODEL_NAME),
            "modelVersion": str(metadata.get("model_version", RULES_MODEL_VERSION)),
            "source": "model" if model is not None else "rules",
            "featureColumns": FEATURE_COLUMNS,
            "trainedAt": metadata.get("trained_at"),
            "metrics": metadata.get("metrics", {}),
        }

    def predict(self, features: Dict[str, float]) -> Optional[float]:
        model = self.load()
        if model is None:
            return None
        try:
            frame = pd.DataFrame(
                [[features[c] for c in FEATURE_COLUMNS]], columns=FEATURE_COLUMNS
            )
            return float(model.predict(frame)[0])
        except Exception as exc:
            logger.error("Model inference failed, using rule-based scoring: %s", exc)
            return None
