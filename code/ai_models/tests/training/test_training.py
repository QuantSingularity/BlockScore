import json

import joblib
import numpy as np
from blockscore_ai.scoring import FEATURE_COLUMNS
from blockscore_ai.training import MODEL_NAME, TARGET_COLUMN, generate_synthetic_data
from blockscore_ai.training.cli import main


def test_synthetic_data_schema_and_range():
    data = generate_synthetic_data(n_samples=300, seed=1)
    assert list(data.columns) == FEATURE_COLUMNS + [TARGET_COLUMN]
    assert len(data) == 300
    assert data[TARGET_COLUMN].between(300, 850).all()
    assert np.isfinite(data.to_numpy()).all()


def test_synthetic_data_is_deterministic():
    first = generate_synthetic_data(n_samples=100, seed=3)
    second = generate_synthetic_data(n_samples=100, seed=3)
    assert first.equals(second)


def test_artifact_and_metadata(trained_model_path):
    metadata = json.loads(trained_model_path.with_suffix(".json").read_text())
    assert metadata["feature_columns"] == FEATURE_COLUMNS
    assert metadata["model_name"] == MODEL_NAME
    assert metadata["model_version"] == "test-1"
    assert metadata["metrics"]["r2"] > 0.3
    assert hasattr(joblib.load(trained_model_path), "predict")


def test_cli_writes_artifact(tmp_path):
    output = tmp_path / "out" / "model.pkl"
    main(["--samples", "300", "--output", str(output), "--model-version", "9.9.9"])
    assert output.exists()
    assert (
        json.loads(output.with_suffix(".json").read_text())["model_version"] == "9.9.9"
    )
