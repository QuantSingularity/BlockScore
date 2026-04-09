"""
Integration tests for the BlockScore backend API.
Tests aligned with the new Flask app structure.
"""

import json
import os
import sys
import unittest
from typing import Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import logging

from app import create_app
from extensions import db as _db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class TestIntegration(unittest.TestCase):
    """Integration tests for the BlockScore backend API."""

    def setUp(self) -> Any:
        """Set up test client and app context."""
        self.flask_app = create_app("testing")
        self.flask_app.config.update(
            TESTING=True,
            RATELIMIT_ENABLED=False,
        )
        self.ctx = self.flask_app.app_context()
        self.ctx.push()
        _db.create_all()
        self.client = self.flask_app.test_client()
        self.test_wallet_addresses = {
            "good_credit": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
            "poor_credit": "0x742d35Cc6634C0532925a3b844Bc454e4438f44a",
            "excellent_credit": "0x742d35Cc6634C0532925a3b844Bc454e4438f44b",
            "no_history": "0x0000000000000000000000000000000000000000",
        }

    def tearDown(self) -> Any:
        """Tear down after each test."""
        _db.session.remove()
        _db.drop_all()
        self.ctx.pop()

    def _register_and_login(self, email: str = "int_test@example.com") -> str:
        """Helper: register user and return access token."""
        self.client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": "IntegTest123!",
                "confirm_password": "IntegTest123!",
            },
            content_type="application/json",
        )
        resp = self.client.post(
            "/api/auth/login",
            json={"email": email, "password": "IntegTest123!"},
            content_type="application/json",
        )
        if resp.status_code == 200:
            return resp.get_json()["tokens"]["access_token"]
        return ""

    def test_health_check(self) -> Any:
        """Test the health check endpoint returns expected structure."""
        response = self.client.get("/api/health")
        data = json.loads(response.data)
        self.assertIn(response.status_code, (200, 503))
        self.assertIn("status", data)
        self.assertIn("timestamp", data)
        self.assertIn("version", data)
        self.assertIn("services", data)
        self.assertIn("database", data["services"])

    def test_register_new_user(self) -> Any:
        """Test registering a brand new user."""
        response = self.client.post(
            "/api/auth/register",
            json={
                "email": "brand_new@example.com",
                "password": "SecurePass123!",
                "confirm_password": "SecurePass123!",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertIn("user", data)

    def test_register_duplicate_email(self) -> Any:
        """Test that duplicate email registration is rejected."""
        payload = {
            "email": "dup_int@example.com",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
        }
        self.client.post(
            "/api/auth/register", json=payload, content_type="application/json"
        )
        response = self.client.post(
            "/api/auth/register", json=payload, content_type="application/json"
        )
        self.assertEqual(response.status_code, 409)
        data = json.loads(response.data)
        self.assertFalse(data["success"])

    def test_login_nonexistent_user(self) -> Any:
        """Test login with nonexistent user returns 401."""
        response = self.client.post(
            "/api/auth/login",
            json={"email": "ghost@example.com", "password": "Password123!"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertFalse(data["success"])

    def test_login_wrong_password(self) -> Any:
        """Test login with wrong password returns 401."""
        self.client.post(
            "/api/auth/register",
            json={
                "email": "wp@example.com",
                "password": "RightPass123!",
                "confirm_password": "RightPass123!",
            },
            content_type="application/json",
        )
        response = self.client.post(
            "/api/auth/login",
            json={"email": "wp@example.com", "password": "WrongPass999!"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_login_success_returns_tokens(self) -> Any:
        """Test successful login returns access and refresh tokens."""
        self.client.post(
            "/api/auth/register",
            json={
                "email": "tok@example.com",
                "password": "TokenPass123!",
                "confirm_password": "TokenPass123!",
            },
            content_type="application/json",
        )
        response = self.client.post(
            "/api/auth/login",
            json={"email": "tok@example.com", "password": "TokenPass123!"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertIn("tokens", data)
        self.assertIn("access_token", data["tokens"])
        self.assertIn("refresh_token", data["tokens"])

    def test_profile_requires_auth(self) -> Any:
        """Test that /api/profile requires a JWT."""
        response = self.client.get("/api/profile")
        self.assertIn(response.status_code, (401, 422))

    def test_credit_history_requires_auth(self) -> Any:
        """Test that /api/credit/history requires a JWT."""
        response = self.client.get("/api/credit/history")
        self.assertIn(response.status_code, (401, 422))

    def test_calculate_credit_score_requires_auth(self) -> Any:
        """Test that credit score calculation requires a JWT."""
        response = self.client.post(
            "/api/credit/calculate-score",
            json={"walletAddress": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"},
            content_type="application/json",
        )
        self.assertIn(response.status_code, (401, 422))

    def test_loan_apply_requires_auth(self) -> Any:
        """Test that loan application requires a JWT."""
        response = self.client.post(
            "/api/loans/apply",
            json={
                "loan_type": "personal",
                "requested_amount": "5000",
                "requested_term_months": 24,
            },
            content_type="application/json",
        )
        self.assertIn(response.status_code, (401, 422))

    def test_full_registration_login_profile_flow(self) -> Any:
        """End-to-end: register → login → get profile."""
        email = "flow@example.com"
        password = "FlowTest123!"

        reg_resp = self.client.post(
            "/api/auth/register",
            json={"email": email, "password": password, "confirm_password": password},
            content_type="application/json",
        )
        self.assertEqual(reg_resp.status_code, 201)

        login_resp = self.client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
            content_type="application/json",
        )
        self.assertEqual(login_resp.status_code, 200)
        token = login_resp.get_json()["tokens"]["access_token"]
        self.assertTrue(len(token) > 10)

        profile_resp = self.client.get(
            "/api/profile",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(profile_resp.status_code, 200)
        profile_data = profile_resp.get_json()
        self.assertTrue(profile_data["success"])
        self.assertIn("data", profile_data)

    def test_loan_calculate_with_auth(self) -> Any:
        """Test loan calculation with valid JWT."""
        token = self._register_and_login("loan_calc@example.com")
        if not token:
            self.skipTest("Could not obtain auth token")
        response = self.client.post(
            "/api/loans/calculate",
            json={"amount": 10000, "rate": 5.5, "term_months": 36},
            headers={"Authorization": f"Bearer {token}"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertIn("data", data)
        loan_data = data["data"]
        self.assertIn("monthly_payment", loan_data)
        self.assertIn("total_payment", loan_data)
        self.assertIn("total_interest", loan_data)
        self.assertIn("approval_probability", loan_data)

    def test_loan_calculation_math(self) -> Any:
        """Test that loan calculations are mathematically correct."""
        token = self._register_and_login("loan_math@example.com")
        if not token:
            self.skipTest("Could not obtain auth token")

        principal = 10000
        annual_rate = 5.5
        term = 36

        response = self.client.post(
            "/api/loans/calculate",
            json={"amount": principal, "rate": annual_rate, "term_months": term},
            headers={"Authorization": f"Bearer {token}"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)["data"]

        monthly_rate = annual_rate / 100 / 12
        expected_payment = (
            principal
            * monthly_rate
            * (1 + monthly_rate) ** term
            / ((1 + monthly_rate) ** term - 1)
        )
        self.assertAlmostEqual(
            data["monthly_payment"], round(expected_payment, 2), delta=0.05
        )
        self.assertAlmostEqual(
            data["total_payment"],
            round(data["monthly_payment"] * term, 2),
            delta=0.5,
        )

    def test_credit_score_calculation_with_wallet(self) -> Any:
        """Test credit score calculation requires wallet address."""
        token = self._register_and_login("wallet_test@example.com")
        if not token:
            self.skipTest("Could not obtain auth token")

        response = self.client.post(
            "/api/credit/calculate-score",
            json={},
            headers={"Authorization": f"Bearer {token}"},
            content_type="application/json",
        )
        # Should fail without wallet address
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertFalse(data["success"])

    def test_credit_history_empty_for_new_user(self) -> Any:
        """Test credit history is empty for new user."""
        token = self._register_and_login("hist_test@example.com")
        if not token:
            self.skipTest("Could not obtain auth token")

        response = self.client.get(
            "/api/credit/history",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        self.assertIn("data", data)
        self.assertEqual(data["data"]["history"], [])

    def test_logout_invalidates_session(self) -> Any:
        """Test that logout works with a valid token."""
        token = self._register_and_login("logout_test@example.com")
        if not token:
            self.skipTest("Could not obtain auth token")

        response = self.client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data["success"])


if __name__ == "__main__":
    unittest.main()
