import os
import sys

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

import pytest
from app import _parse_origins, _validate_production_secrets
from flask import Flask


def make_app(**config):
    app = Flask(__name__)
    app.config.update(config)
    return app


def test_production_rejects_placeholder_secrets():
    app = make_app(
        FLASK_ENV="production",
        SECRET_KEY="change-me-in-production",
        JWT_SECRET_KEY="x" * 40,
    )
    with pytest.raises(RuntimeError):
        _validate_production_secrets(app)


def test_production_rejects_short_secrets():
    app = make_app(FLASK_ENV="production", SECRET_KEY="short", JWT_SECRET_KEY="x" * 40)
    with pytest.raises(RuntimeError):
        _validate_production_secrets(app)


def test_production_accepts_strong_secrets():
    _validate_production_secrets(
        make_app(FLASK_ENV="production", SECRET_KEY="a" * 40, JWT_SECRET_KEY="b" * 40)
    )


def test_development_and_testing_skip_validation():
    _validate_production_secrets(
        make_app(FLASK_ENV="development", SECRET_KEY="x", JWT_SECRET_KEY="y")
    )
    _validate_production_secrets(
        make_app(
            FLASK_ENV="production", TESTING=True, SECRET_KEY="x", JWT_SECRET_KEY="y"
        )
    )


def test_parse_origins():
    assert _parse_origins("*") == "*"
    assert _parse_origins("http://a.com, http://b.com") == [
        "http://a.com",
        "http://b.com",
    ]
    assert _parse_origins("") == []
    assert _parse_origins(["http://a.com"]) == ["http://a.com"]
