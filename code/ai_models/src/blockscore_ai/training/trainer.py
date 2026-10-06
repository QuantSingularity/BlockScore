import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Tuple

import joblib
import numpy as np
import pandas as pd
from blockscore_ai.scoring.constants import FEATURE_COLUMNS
from blockscore_ai.training.synthetic import TARGET_COLUMN
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor

logger = logging.getLogger(__name__)

MODEL_NAME = "blockscore-xgboost"


def split_data(df: pd.DataFrame, seed: int = 42) -> Tuple[Any, Any, Any, Any]:
    return train_test_split(
        df[FEATURE_COLUMNS], df[TARGET_COLUMN], test_size=0.2, random_state=seed
    )


def train_model(
    X_train: pd.DataFrame, y_train: pd.Series, seed: int = 42
) -> XGBRegressor:
    model = XGBRegressor(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=4,
        subsample=0.9,
        colsample_bytree=0.9,
        reg_lambda=1.0,
        objective="reg:squarederror",
        random_state=seed,
        n_jobs=1,
    )
    model.fit(X_train, y_train)
    return model


def evaluate_model(
    model: XGBRegressor, X_test: pd.DataFrame, y_test: pd.Series
) -> Dict[str, float]:
    predictions = np.clip(model.predict(X_test), 300, 850)
    mse = float(mean_squared_error(y_test, predictions))
    metrics = {
        "mse": round(mse, 4),
        "rmse": round(float(np.sqrt(mse)), 4),
        "mae": round(float(mean_absolute_error(y_test, predictions)), 4),
        "r2": round(float(r2_score(y_test, predictions)), 4),
    }
    logger.info("Model performance: %s", metrics)
    return metrics


def _atomic_write(path: Path, writer: Callable[[str], None]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    os.close(handle)
    try:
        writer(temp_name)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.remove(temp_name)


def save_model(
    model: XGBRegressor,
    metrics: Dict[str, float],
    model_path: Path,
    model_version: str,
) -> None:
    metadata = {
        "model_name": MODEL_NAME,
        "model_version": model_version,
        "feature_columns": FEATURE_COLUMNS,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
    }
    _atomic_write(model_path, lambda name: joblib.dump(model, name))
    _atomic_write(
        model_path.with_suffix(".json"),
        lambda name: Path(name).write_text(
            json.dumps(metadata, indent=2), encoding="utf-8"
        ),
    )
    logger.info("Model saved to %s", model_path)
