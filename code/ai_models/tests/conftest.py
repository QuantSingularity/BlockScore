import pytest
from blockscore_ai.config import Settings
from blockscore_ai.scoring import ModelRegistry, ScoringService
from blockscore_ai.training import (
    evaluate_model,
    generate_synthetic_data,
    save_model,
    split_data,
    train_model,
)

DAY = 86400
BASE = 1_700_000_000


@pytest.fixture(scope="session")
def trained_model_path(tmp_path_factory):
    path = tmp_path_factory.mktemp("model") / "credit_scoring_model.pkl"
    data = generate_synthetic_data(n_samples=800, seed=7)
    X_train, X_test, y_train, y_test = split_data(data, seed=7)
    model = train_model(X_train, y_train, seed=7)
    metrics = evaluate_model(model, X_test, y_test)
    save_model(model, metrics, path, "test-1")
    return path


@pytest.fixture()
def registry(trained_model_path):
    return ModelRegistry(trained_model_path)


@pytest.fixture()
def empty_registry(tmp_path):
    return ModelRegistry(tmp_path / "missing.pkl")


@pytest.fixture()
def service(registry):
    return ScoringService(registry)


@pytest.fixture()
def rules_service(empty_registry):
    return ScoringService(empty_registry)


@pytest.fixture()
def settings(trained_model_path):
    return Settings(model_path=trained_model_path, api_key="", max_batch_size=500)


@pytest.fixture()
def good_history():
    return [
        {
            "timestamp": BASE,
            "amount": 5000,
            "repaid": True,
            "repaymentTimestamp": BASE + 40 * DAY,
            "recordType": "loan",
            "scoreImpact": 0,
        },
        {
            "timestamp": BASE + 200 * DAY,
            "amount": 8000,
            "repaid": True,
            "repaymentTimestamp": BASE + 240 * DAY,
            "recordType": "loan",
            "scoreImpact": 0,
        },
        {
            "timestamp": BASE + 300 * DAY,
            "amount": 300,
            "repaid": True,
            "repaymentTimestamp": BASE + 300 * DAY,
            "recordType": "payment",
            "scoreImpact": 5,
        },
        {
            "timestamp": BASE + 400 * DAY,
            "amount": 300,
            "repaid": True,
            "repaymentTimestamp": BASE + 400 * DAY,
            "recordType": "payment",
            "scoreImpact": 5,
        },
        {
            "timestamp": BASE + 900 * DAY,
            "amount": 300,
            "repaid": True,
            "repaymentTimestamp": BASE + 900 * DAY,
            "recordType": "payment",
            "scoreImpact": 5,
        },
    ]


@pytest.fixture()
def bad_history():
    return [
        {
            "timestamp": BASE,
            "amount": 9000,
            "repaid": False,
            "repaymentTimestamp": 0,
            "recordType": "loan",
            "scoreImpact": 0,
        },
        {
            "timestamp": BASE + 20 * DAY,
            "amount": 9000,
            "repaid": False,
            "repaymentTimestamp": 0,
            "recordType": "loan",
            "scoreImpact": 0,
        },
        {
            "timestamp": BASE + 40 * DAY,
            "amount": 300,
            "repaid": False,
            "repaymentTimestamp": 0,
            "recordType": "payment",
            "scoreImpact": -10,
        },
        {
            "timestamp": BASE + 60 * DAY,
            "amount": 300,
            "repaid": False,
            "repaymentTimestamp": 0,
            "recordType": "payment",
            "scoreImpact": -10,
        },
    ]
