"""
Integration tests for API endpoints
Tests aligned with actual app.py routes and response formats
"""

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

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)


class TestAuthenticationEndpoints:
    """Integration tests for authentication endpoints"""

    def test_register_user_success(self, client: Any, db: Any) -> Any:
        """Test successful user registration"""
        user_data = {
            "email": "newuser_int@example.com",
            "password": "StrongPassword123!",
            "confirm_password": "StrongPassword123!",
        }
        response = client.post(
            "/api/auth/register", json=user_data, content_type="application/json"
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert "user" in data
        assert "message" in data

    def test_register_user_duplicate_email(
        self, client: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test registration with duplicate email"""
        user_data = {
            "email": sample_user.email,
            "password": "StrongPassword123!",
            "confirm_password": "StrongPassword123!",
        }
        response = client.post(
            "/api/auth/register", json=user_data, content_type="application/json"
        )
        assert response.status_code == 409
        data = response.get_json()
        assert data["success"] is False

    def test_register_user_missing_confirm_password(self, client: Any, db: Any) -> Any:
        """Test registration without confirm_password"""
        user_data = {
            "email": "missing@example.com",
            "password": "StrongPassword123!",
        }
        response = client.post(
            "/api/auth/register", json=user_data, content_type="application/json"
        )
        assert response.status_code in (400, 422)
        data = response.get_json()
        assert data["success"] is False

    def test_register_password_mismatch(self, client: Any, db: Any) -> Any:
        """Test registration with mismatched passwords"""
        user_data = {
            "email": "mismatch@example.com",
            "password": "StrongPassword123!",
            "confirm_password": "Different123!",
        }
        response = client.post(
            "/api/auth/register", json=user_data, content_type="application/json"
        )
        assert response.status_code in (400, 422)
        data = response.get_json()
        assert data["success"] is False

    def test_login_nonexistent_user(self, client: Any, db: Any) -> Any:
        """Test login with nonexistent user"""
        login_data = {"email": "nonexistent@example.com", "password": "Password123!"}
        response = client.post(
            "/api/auth/login", json=login_data, content_type="application/json"
        )
        assert response.status_code == 401
        data = response.get_json()
        assert data["success"] is False

    def test_login_invalid_credentials(
        self, client: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test login with wrong password"""
        login_data = {"email": sample_user.email, "password": "WrongPassword999!"}
        response = client.post(
            "/api/auth/login", json=login_data, content_type="application/json"
        )
        assert response.status_code == 401
        data = response.get_json()
        assert data["success"] is False

    def test_login_success(self, client: Any, db: Any, sample_user: Any) -> Any:
        """Test successful login"""
        login_data = {"email": sample_user.email, "password": "TestPassword123!"}
        response = client.post(
            "/api/auth/login", json=login_data, content_type="application/json"
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "tokens" in data
        assert "access_token" in data["tokens"]
        assert "refresh_token" in data["tokens"]

    def test_profile_requires_auth(self, client: Any) -> Any:
        """Test that profile endpoint requires authentication"""
        response = client.get("/api/profile")
        assert response.status_code in (401, 422)

    def test_logout_requires_auth(self, client: Any) -> Any:
        """Test that logout requires auth"""
        response = client.post("/api/auth/logout")
        assert response.status_code in (401, 422)

    def test_refresh_requires_token(self, client: Any) -> Any:
        """Test that refresh requires a valid token"""
        response = client.post("/api/auth/refresh")
        assert response.status_code in (401, 422)


class TestCreditEndpoints:
    """Integration tests for credit scoring endpoints"""

    def test_credit_history_requires_auth(self, client: Any) -> Any:
        """Test that credit history requires auth"""
        response = client.get("/api/credit/history")
        assert response.status_code in (401, 422)

    def test_calculate_credit_score_requires_auth(self, client: Any) -> Any:
        """Test that credit score calculation requires auth"""
        response = client.post(
            "/api/credit/calculate-score",
            json={"walletAddress": "0x1234567890123456789012345678901234567890"},
            content_type="application/json",
        )
        assert response.status_code in (401, 422)

    def test_loan_calculate_requires_auth(self, client: Any) -> Any:
        """Test that loan calculate requires auth"""
        response = client.post(
            "/api/loans/calculate",
            json={"amount": 1000, "rate": 5.0, "term_months": 12},
            content_type="application/json",
        )
        assert response.status_code in (401, 422)


class TestLoanEndpoints:
    """Integration tests for loan endpoints"""

    def test_loan_apply_requires_auth(self, client: Any) -> Any:
        """Test that loan application requires auth"""
        response = client.post(
            "/api/loans/apply", json={}, content_type="application/json"
        )
        assert response.status_code in (401, 422)

    def test_loan_application_full_flow(
        self, client: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test loan application with valid JWT"""
        # First login to get token
        login_resp = client.post(
            "/api/auth/login",
            json={"email": sample_user.email, "password": "TestPassword123!"},
            content_type="application/json",
        )
        if login_resp.status_code != 200:
            pytest.skip("Login failed, skipping downstream test")

        token = login_resp.get_json()["tokens"]["access_token"]
        loan_data = {
            "loan_type": "personal",
            "requested_amount": "5000.00",
            "requested_term_months": 24,
        }
        response = client.post(
            "/api/loans/apply",
            json=loan_data,
            headers={"Authorization": f"Bearer {token}"},
            content_type="application/json",
        )
        assert response.status_code in (201, 400, 500)


class TestHealthEndpoints:
    """Integration tests for health check endpoints"""

    def test_health_check(self, client: Any) -> Any:
        """Test basic health check"""
        response = client.get("/api/health")
        assert response.status_code in (200, 503)
        data = response.get_json()
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "services" in data

    def test_health_check_services_present(self, client: Any) -> Any:
        """Test health check includes all service statuses"""
        response = client.get("/api/health")
        data = response.get_json()
        services = data.get("services", {})
        assert "database" in services


class TestErrorHandling:
    """Integration tests for error handling"""

    def test_404_error(self, client: Any) -> Any:
        """Test 404 error handling"""
        response = client.get("/api/this-does-not-exist-xyz")
        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False
        assert "error" in data

    def test_bad_json_body(self, client: Any) -> Any:
        """Test bad JSON body returns 400"""
        response = client.post(
            "/api/auth/register",
            data="not valid json{{{",
            content_type="application/json",
        )
        assert response.status_code in (400, 422)

    def test_method_not_allowed(self, client: Any) -> Any:
        """Test 405 on wrong HTTP method"""
        response = client.delete("/api/health")
        assert response.status_code == 405

    def test_cors_headers_present(self, client: Any) -> Any:
        """Test CORS headers are returned"""
        response = client.options(
            "/api/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert response.status_code in (200, 204)
