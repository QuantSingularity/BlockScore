"""
Comprehensive API Test Suite for BlockScore Backend
"""

import json
import os
import sys

sys.path.insert(
    0,
    (
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if "tests" in __file__
        else os.path.abspath(".")
    ),
)
from typing import Any

import compat_stubs  # noqa
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app


class TestAPIEndpoints:
    """Test suite for API endpoints"""

    @pytest.fixture
    def app(self) -> Any:
        """Create test Flask application"""
        _app = create_app("testing")
        _app.config.update(
            TESTING=True,
            WTF_CSRF_ENABLED=False,
            RATELIMIT_ENABLED=False,
        )
        return _app

    @pytest.fixture
    def client(self, app: Any) -> Any:
        """Create test client inside app context"""
        with app.app_context():
            from extensions import db

            db.create_all()
            yield app.test_client()
            db.session.remove()
            db.drop_all()

    def _json(self, response: Any) -> Any:
        return json.loads(response.data)

    def test_health_check(self, client: Any) -> Any:
        """Test health check endpoint"""
        response = client.get("/api/health")
        assert response.status_code in (200, 503)
        data = self._json(response)
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data

    def test_health_check_services(self, client: Any) -> Any:
        """Test health check lists services"""
        response = client.get("/api/health")
        data = self._json(response)
        assert "services" in data
        services = data["services"]
        assert "database" in services

    def test_user_registration_success(self, client: Any) -> Any:
        """Test successful user registration"""
        user_data = {
            "email": "newuser@example.com",
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!",
        }
        response = client.post(
            "/api/auth/register",
            data=json.dumps(user_data),
            content_type="application/json",
        )
        data = self._json(response)
        assert response.status_code == 201
        assert data["success"] is True
        assert "user" in data

    def test_user_registration_duplicate_email(self, client: Any) -> Any:
        """Test registration with duplicate email"""
        user_data = {
            "email": "dup@example.com",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
        }
        client.post(
            "/api/auth/register",
            data=json.dumps(user_data),
            content_type="application/json",
        )
        response = client.post(
            "/api/auth/register",
            data=json.dumps(user_data),
            content_type="application/json",
        )
        data = self._json(response)
        assert response.status_code == 409
        assert data["success"] is False

    def test_user_registration_missing_fields(self, client: Any) -> Any:
        """Test registration with missing required fields"""
        response = client.post(
            "/api/auth/register",
            data=json.dumps({"email": "test@example.com"}),
            content_type="application/json",
        )
        assert response.status_code in (400, 422)
        data = self._json(response)
        assert data["success"] is False

    def test_user_login_invalid_credentials(self, client: Any) -> Any:
        """Test login with invalid credentials"""
        response = client.post(
            "/api/auth/login",
            data=json.dumps(
                {"email": "nosuchuser@example.com", "password": "WrongPass123!"}
            ),
            content_type="application/json",
        )
        data = self._json(response)
        assert response.status_code == 401
        assert data["success"] is False

    def test_login_success(self, client: Any) -> Any:
        """Test successful login flow"""
        reg_data = {
            "email": "loginuser@example.com",
            "password": "GoodPass123!",
            "confirm_password": "GoodPass123!",
        }
        client.post(
            "/api/auth/register",
            data=json.dumps(reg_data),
            content_type="application/json",
        )
        response = client.post(
            "/api/auth/login",
            data=json.dumps(
                {"email": "loginuser@example.com", "password": "GoodPass123!"}
            ),
            content_type="application/json",
        )
        data = self._json(response)
        assert response.status_code == 200
        assert data["success"] is True
        assert "tokens" in data
        assert "access_token" in data["tokens"]
        assert "refresh_token" in data["tokens"]

    def test_profile_requires_auth(self, client: Any) -> Any:
        """Test that profile endpoint requires authentication"""
        response = client.get("/api/profile")
        assert response.status_code in (401, 422)

    def test_credit_calculate_requires_auth(self, client: Any) -> Any:
        """Test that credit score calculation requires auth"""
        response = client.post(
            "/api/credit/calculate-score",
            data=json.dumps({"walletAddress": "0x123"}),
            content_type="application/json",
        )
        assert response.status_code in (401, 422)

    def test_loan_apply_requires_auth(self, client: Any) -> Any:
        """Test that loan apply requires auth"""
        response = client.post(
            "/api/loans/apply",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert response.status_code in (401, 422)

    def test_404_error_handler(self, client: Any) -> Any:
        """Test 404 error handler"""
        response = client.get("/api/nonexistent-endpoint-xyz")
        assert response.status_code == 404
        data = self._json(response)
        assert data["success"] is False

    def test_registration_password_mismatch(self, client: Any) -> Any:
        """Test registration with mismatched passwords"""
        response = client.post(
            "/api/auth/register",
            data=json.dumps(
                {
                    "email": "pm@example.com",
                    "password": "GoodPass123!",
                    "confirm_password": "Different123!",
                }
            ),
            content_type="application/json",
        )
        assert response.status_code in (400, 422)
        data = self._json(response)
        assert data["success"] is False

    def test_credit_history_requires_auth(self, client: Any) -> Any:
        """Test that credit history requires auth"""
        response = client.get("/api/credit/history")
        assert response.status_code in (401, 422)

    def test_loan_calculate_requires_auth(self, client: Any) -> Any:
        """Test that loan calculate requires auth"""
        response = client.post(
            "/api/loans/calculate",
            data=json.dumps({"amount": 1000, "rate": 5.0, "term_months": 12}),
            content_type="application/json",
        )
        assert response.status_code in (401, 422)

    def test_logout_requires_auth(self, client: Any) -> Any:
        """Test that logout requires auth"""
        response = client.post("/api/auth/logout")
        assert response.status_code in (401, 422)

    def test_refresh_token_requires_auth(self, client: Any) -> Any:
        """Test that token refresh requires a refresh token"""
        response = client.post("/api/auth/refresh")
        assert response.status_code in (401, 422)
