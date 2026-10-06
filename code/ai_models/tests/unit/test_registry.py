import json
import shutil

from blockscore_ai.scoring import (
    FEATURE_COLUMNS,
    ModelRegistry,
    transform_blockchain_data,
)


def test_loads_model_and_metadata(registry):
    info = registry.info()
    assert info["modelLoaded"] is True
    assert info["source"] == "model"
    assert info["modelVersion"] == "test-1"
    assert info["featureColumns"] == FEATURE_COLUMNS
    assert info["metrics"]["r2"] > 0.3


def test_missing_model_reports_rules(empty_registry):
    info = empty_registry.info()
    assert info["modelLoaded"] is False
    assert info["source"] == "rules"
    assert empty_registry.predict({c: 0.0 for c in FEATURE_COLUMNS}) is None


def test_mismatched_feature_columns_are_rejected(tmp_path, trained_model_path):
    target = tmp_path / "credit_scoring_model.pkl"
    shutil.copy(trained_model_path, target)
    metadata = json.loads(trained_model_path.with_suffix(".json").read_text())
    metadata["feature_columns"] = ["wrong"]
    target.with_suffix(".json").write_text(json.dumps(metadata))
    assert ModelRegistry(target).load() is None


def test_corrupt_model_file_falls_back(tmp_path):
    target = tmp_path / "credit_scoring_model.pkl"
    target.write_bytes(b"not a pickle")
    registry = ModelRegistry(target)
    assert registry.load() is None
    assert registry.info()["source"] == "rules"


def test_force_reload_picks_up_new_artifact(tmp_path, trained_model_path):
    target = tmp_path / "credit_scoring_model.pkl"
    registry = ModelRegistry(target)
    assert registry.load() is None
    shutil.copy(trained_model_path, target)
    shutil.copy(trained_model_path.with_suffix(".json"), target.with_suffix(".json"))
    assert registry.load() is None
    assert registry.load(force=True) is not None


def test_predict_returns_float(registry, good_history):
    assert isinstance(registry.predict(transform_blockchain_data(good_history)), float)
