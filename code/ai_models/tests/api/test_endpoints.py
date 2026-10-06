import json

import pytest
from blockscore_ai.api import create_app
from blockscore_ai.config import Settings


@pytest.fixture()
def client(settings, registry):
    app = create_app(settings, registry)
    app.config["TESTING"] = True
    return app.test_client()


def test_health_check(client):
    response = client.get("/health")
    data = response.get_json()
    assert response.status_code == 200
    assert data["status"] == "ok"
    assert data["modelLoaded"] is True
    assert "timestamp" in data


def test_model_info(client):
    data = client.get("/model-info").get_json()
    assert data["modelName"] == "blockscore-xgboost"
    assert data["source"] == "model"
    assert data["metrics"]["rmse"] > 0


def test_predict_success(client, good_history):
    response = client.post("/predict", json={"creditHistory": good_history})
    data = response.get_json()
    assert response.status_code == 200
    assert 300 <= data["score"] <= 850
    assert 0 < data["confidence"] <= 0.95
    assert data["factors"]
    assert data["modelVersion"] == "test-1"
    assert data["source"] == "model"
    assert data["recordCount"] == len(good_history)


def test_predict_rejects_bad_payloads(client):
    assert client.post("/predict", json={"invalid": 1}).status_code == 400
    assert client.post("/predict", json={"creditHistory": "nope"}).status_code == 400
    assert (
        client.post(
            "/predict", data="not json", content_type="application/json"
        ).status_code
        == 400
    )
    assert client.post("/predict", json=[1, 2]).status_code == 400


def test_predict_empty_history(client):
    data = client.post("/predict", json={"creditHistory": []}).get_json()
    assert data["score"] == 500
    assert data["confidence"] == 0
    assert data["source"] == "none"


def test_predict_ignores_garbage_records(client, good_history):
    response = client.post(
        "/predict",
        json={"creditHistory": good_history + [None, "x", {"timestamp": "bad"}]},
    )
    assert response.status_code == 200
    assert response.get_json()["recordCount"] == len(good_history)


def test_batch_predict(client, good_history, bad_history):
    payload = {
        "batch": [
            {"userId": "u1", "creditHistory": good_history},
            {"userId": "u2", "creditHistory": []},
            {"userId": "u3", "creditHistory": bad_history},
            {"userId": "u4", "creditHistory": "bad"},
            "oops",
        ]
    }
    response = client.post("/batch-predict", json=payload)
    results = response.get_json()["results"]
    assert response.status_code == 200
    assert [r.get("userId") for r in results] == ["u1", "u2", "u3", "u4", None]
    assert results[0]["score"] > results[2]["score"]
    assert results[1]["score"] == 500
    assert "error" in results[3] and "error" in results[4]


def test_batch_predict_validation(settings, registry):
    small = Settings(model_path=settings.model_path, max_batch_size=2)
    client = create_app(small, registry).test_client()
    assert client.post("/batch-predict", json={"x": 1}).status_code == 400
    assert client.post("/batch-predict", json={"batch": "x"}).status_code == 400
    assert (
        client.post("/batch-predict", json={"batch": [{}, {}, {}]}).status_code == 413
    )


def test_unknown_route_and_method_return_json(client):
    assert client.get("/missing").get_json()["error"]
    assert client.get("/predict").status_code == 405


def test_api_key_enforced(settings, registry, good_history):
    secured = Settings(model_path=settings.model_path, api_key="secret-key")
    client = create_app(secured, registry).test_client()
    payload = {"creditHistory": good_history}
    assert client.get("/health").status_code == 200
    assert client.post("/predict", json=payload).status_code == 401
    assert client.get("/model-info").status_code == 401
    assert (
        client.post("/predict", json=payload, headers={"X-API-Key": "nope"}).status_code
        == 401
    )
    assert (
        client.post(
            "/predict", json=payload, headers={"X-API-Key": "secret-key"}
        ).status_code
        == 200
    )


def test_error_response_is_json_dumpable(client):
    json.dumps(client.post("/predict", json={"invalid": 1}).get_json())


def test_rules_fallback_when_no_model(settings, empty_registry, good_history):
    client = create_app(settings, empty_registry).test_client()
    data = client.post("/predict", json={"creditHistory": good_history}).get_json()
    assert data["source"] == "rules"
    assert data["confidence"] <= 0.6
