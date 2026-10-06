import pytest
from blockscore_ai.research.credit_ensemble import (
    AdvancedCreditScoringModel,
    ModelConfig,
)


@pytest.fixture(scope="module")
def trained():
    config = ModelConfig(explainability_required=False, cv_folds=2)
    model = AdvancedCreditScoringModel(config)
    raw = model._generate_comprehensive_synthetic_data(n_samples=1200)
    df = model.load_and_preprocess_data(data=raw)
    X, y = model.prepare_features_and_target(df)
    model.train_models(X, y)
    return model, raw


def test_protected_attributes_are_not_features(trained):
    model, _ = trained
    for attribute in ("gender", "race"):
        assert attribute not in model.feature_names
    assert set(model.audit_frame.columns) == {"gender", "race"}


def test_target_is_not_saturated(trained):
    _, raw = trained
    assert raw["credit_score"].between(300, 850).all()
    assert (raw["credit_score"] == 850).mean() < 0.2


def test_late_payments_survive_preprocessing(trained):
    model, raw = trained
    df = model.load_and_preprocess_data(data=raw)
    assert df["late_payments_12m"].max() > 0


def test_predict_on_raw_rows(trained):
    model, raw = trained
    predictions = model.predict(raw.drop(columns=["credit_score"]).head(5))
    assert len(predictions) == 5
    assert ((predictions >= 300) & (predictions <= 850)).all()


def test_predict_handles_unseen_category(trained):
    model, raw = trained
    frame = raw.drop(columns=["credit_score"]).head(2).copy()
    frame["state"] = "ZZ"
    assert len(model.predict(frame)) == 2


def test_fairness_report_structure(trained):
    model, _ = trained
    for attribute in ("gender", "race"):
        report = model.fairness_metrics[attribute]
        assert 0 <= report["disparate_impact_ratio"] <= 1
        assert "groups" in report


def test_ensemble_weights_are_non_negative(trained):
    model, _ = trained
    assert (model.ensemble_model.coef_ >= 0).all()


def test_save_and_load_roundtrip(trained, tmp_path):
    model, raw = trained
    path = tmp_path / "advanced.pkl"
    model.save_model(str(path))
    restored = AdvancedCreditScoringModel.load_model(str(path))
    sample = raw.drop(columns=["credit_score"]).head(3)
    assert list(restored.predict(sample)) == pytest.approx(list(model.predict(sample)))
