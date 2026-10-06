import os
import sys

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from unittest.mock import MagicMock

import requests
from services.ai_client import AIModelClient


def make_client(**kwargs):
    client = AIModelClient("http://ai.test:5001/", timeout=1, retries=0, **kwargs)
    client.session = MagicMock()
    return client


def ok_response(payload, status=200):
    response = MagicMock()
    response.status_code = status
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def test_base_url_is_normalised():
    assert AIModelClient("http://x:1///").base_url == "http://x:1"


def test_predict_posts_history_and_returns_payload():
    client = make_client(api_key="k")
    client.session.request.return_value = ok_response({"score": 700})
    result = client.predict([{"timestamp": 1}])
    assert result == {"score": 700}
    args, kwargs = client.session.request.call_args
    assert args == ("POST", "http://ai.test:5001/predict")
    assert kwargs["json"] == {"creditHistory": [{"timestamp": 1}]}
    assert kwargs["headers"]["X-API-Key"] == "k"


def test_predict_skips_empty_history():
    client = make_client()
    assert client.predict([]) is None
    client.session.request.assert_not_called()


def test_network_error_returns_none():
    client = make_client()
    client.session.request.side_effect = requests.exceptions.ConnectionError("down")
    assert client.predict([{"timestamp": 1}]) is None


def test_invalid_json_returns_none():
    client = make_client()
    response = ok_response(None)
    response.json.side_effect = ValueError("bad json")
    client.session.request.return_value = response
    assert client.predict([{"timestamp": 1}]) is None


def test_non_object_payload_returns_none():
    client = make_client()
    client.session.request.return_value = ok_response([1, 2, 3])
    assert client.predict([{"timestamp": 1}]) is None


def test_circuit_opens_after_repeated_failures_and_recovers():
    client = make_client(failure_threshold=2, cooldown_seconds=60)
    client.session.request.side_effect = requests.exceptions.Timeout("slow")
    client.predict([{"timestamp": 1}])
    client.predict([{"timestamp": 1}])
    calls_before = client.session.request.call_count
    assert client.predict([{"timestamp": 1}]) is None
    assert client.session.request.call_count == calls_before
    client._open_until = 0.0
    client.session.request.side_effect = None
    client.session.request.return_value = ok_response({"score": 650})
    assert client.predict([{"timestamp": 1}]) == {"score": 650}


def test_batch_predict_returns_results_list():
    client = make_client()
    client.session.request.return_value = ok_response({"results": [{"score": 1}]})
    assert client.batch_predict([{"userId": "a", "creditHistory": []}]) == [
        {"score": 1}
    ]
    assert client.batch_predict([]) == []


def test_is_available_checks_health():
    client = make_client()
    client.session.get.return_value = MagicMock(status_code=200)
    assert client.is_available() is True
    client.session.get.return_value = MagicMock(status_code=500)
    assert client.is_available() is False
    client.session.get.side_effect = requests.exceptions.ConnectionError()
    assert client.is_available() is False


def test_empty_base_url_disables_client():
    client = AIModelClient("")
    assert client.is_available() is False
    assert client.predict([{"timestamp": 1}]) is None


def test_from_config_reads_settings():
    client = AIModelClient.from_config(
        {
            "AI_MODEL_URL": "http://cfg:9",
            "AI_MODEL_TIMEOUT": "3",
            "AI_MODEL_API_KEY": "abc",
        }
    )
    assert client.base_url == "http://cfg:9"
    assert client.timeout == 3.0
    assert client.api_key == "abc"
