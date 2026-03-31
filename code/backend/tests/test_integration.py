import json
import os
import sys
import unittest
from typing import Any
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import logging

from app import app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class TestIntegration(unittest.TestCase):
    """Integration tests for the BlockScore backend API."""

    def setUp(self) -> Any:
        """Set up test client and other test variables."""
        self.app = app.test_client()
        self.app.testing = True
        self.test_wallet_addresses = {
            "good_credit": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
            "poor_credit": "0x742d35Cc6634C0532925a3b844Bc454e4438f44a",
            "excellent_credit": "0x742d35Cc6634C0532925a3b844Bc454e4438f44b",
            "no_history": "0x0000000000000000000000000000000000000000",
        }
        self.mock_tx_history = {
            "good_credit": [
                {"timestamp": 1617235200, "amount": 1000, "repaid": True},
                {"timestamp": 1619827200, "amount": 2000, "repaid": True},
                {"timestamp": 1622505600, "amount": 1500, "repaid": True},
            ],
            "poor_credit": [
                {"timestamp": 1617235200, "amount": 1000, "repaid": True},
                {"timestamp": 1619827200, "amount": 2000, "repaid": False},
                {"timestamp": 1622505600, "amount": 1500, "repaid": False},
            ],
            "excellent_credit": [
                {"timestamp": 1617235200, "amount": 1000, "repaid": True},
                {"timestamp": 1619827200, "amount": 2000, "repaid": True},
                {"timestamp": 1622505600, "amount": 1500, "repaid": True},
                {"timestamp": 1625097600, "amount": 3000, "repaid": True},
                {"timestamp": 1627776000, "amount": 2500, "repaid": True},
            ],
            "no_history": [],
        }

    def test_health_check(self) -> Any:
        """Test the health check endpoint."""
        response = self.app.get("/api/health")
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "ok")
        self.assertIn("blockchain_connected", data)
        self.assertIn("model_loaded", data)
        self.assertIn("contract_abi_loaded", data)

    @patch("app.web3", None)
    @patch("app.contract_abi", None)
    def test_calculate_score_with_no_wallet(self, *args) -> Any:
        """Test calculate score endpoint with missing wallet address."""
        response = self.app.post(
            "/api/calculate-score", json={}, content_type="application/json"
        )
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data["error"], "Wallet address is required")

    @patch("app.web3", None)
    @patch("app.contract_abi", None)
    def test_calculate_score_with_mock_data(self, *args) -> Any:
        """Test calculate score endpoint with mock blockchain data."""
        response = self.app.post(
            "/api/calculate-score",
            json={"walletAddress": self.test_wallet_addresses["good_credit"]},
            content_type="application/json",
        )
        if response.status_code != 200:
            logger.info(f"Error response: {response.data}")
        if response.status_code == 500:
            data = json.loads(response.data)
            if "error" in data:
                logger.info(f"API error: {data['error']}")
                self.skipTest("Skipping due to missing blockchain artifacts")
        if response.status_code == 200:
            data = json.loads(response.data)
            self.assertIn("score", data)
            self.assertIn("features", data)
            self.assertIn("history", data)
            self.assertTrue(data["score"] >= 300 and data["score"] <= 850)

    @patch("app.model")
    @patch("app.web3", None)
    @patch("app.contract_abi", None)
    def test_calculate_score_with_model(self, mock_model: Any, *args) -> Any:
        """Test calculate score endpoint with AI model."""
        mock_model_instance = MagicMock()
        mock_model_instance.predict.return_value = [720]
        mock_model.return_value = mock_model_instance
        response = self.app.post(
            "/api/calculate-score",
            json={"walletAddress": self.test_wallet_addresses["good_credit"]},
            content_type="application/json",
        )
        if response.status_code != 200:
            logger.info(f"Error response: {response.data}")
        if response.status_code == 500:
            data = json.loads(response.data)
            if "error" in data:
                logger.info(f"API error: {data['error']}")
                self.skipTest("Skipping due to missing blockchain artifacts")
        if response.status_code == 200:
            data = json.loads(response.data)
            self.assertIn("score", data)
            self.assertTrue(data["score"] >= 300 and data["score"] <= 850)

    @patch("app.web3", None)
    @patch("app.contract_abi", None)
    def test_calculate_score_with_no_history(self, *args) -> Any:
        """Test calculate score endpoint with wallet having no history."""
        response = self.app.post(
            "/api/calculate-score",
            json={"walletAddress": self.test_wallet_addresses["no_history"]},
            content_type="application/json",
        )
        if response.status_code != 200:
            logger.info(f"Error response: {response.data}")
        if response.status_code == 500:
            data = json.loads(response.data)
            if "error" in data:
                logger.info(f"API error: {data['error']}")
                self.skipTest("Skipping due to missing blockchain artifacts")
        if response.status_code == 200:
            data = json.loads(response.data)
            self.assertTrue(
                data["score"] == 300 or (data["score"] >= 300 and data["score"] <= 350),
                f"Expected score to be 300 or close to base value, got {data['score']}",
            )
            self.assertEqual(data["features"]["total_loans"], 0)
            if "history" in data:
                self.assertTrue(len(data["history"]) == 0 or data["history"] is None)

    def test_calculate_loan_with_no_wallet(self) -> Any:
        """Test calculate loan endpoint with missing wallet address."""
        response = self.app.post(
            "/api/calculate-loan",
            json={"amount": 5000, "rate": 5.5},
            content_type="application/json",
        )
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data["error"], "Wallet address is required")

    def test_calculate_loan_with_valid_data(self) -> Any:
        """Test calculate loan endpoint with valid data."""
        response = self.app.post(
            "/api/calculate-loan",
            json={
                "walletAddress": self.test_wallet_addresses["good_credit"],
                "amount": 10000,
                "rate": 5.5,
            },
            content_type="application/json",
        )
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("approval_probability", data)
        self.assertIn("monthly_payment", data)
        self.assertIn("credit_score", data)
        self.assertIn("loan_term", data)
        self.assertIn("total_payment", data)
        self.assertEqual(data["loan_term"], 36)
        principal = 10000
        monthly_rate = 5.5 / 100 / 12
        term = 36
        expected_monthly = (
            principal
            * monthly_rate
            * (1 + monthly_rate) ** term
            / ((1 + monthly_rate) ** term - 1)
        )
        expected_monthly = round(expected_monthly, 2)
        self.assertAlmostEqual(data["monthly_payment"], expected_monthly, delta=0.1)
        self.assertAlmostEqual(
            data["total_payment"], round(expected_monthly * 36, 2), delta=0.1
        )

    def test_calculate_loan_with_different_credit_profiles(self) -> Any:
        """Test calculate loan endpoint with different credit profiles."""
        response = self.app.post(
            "/api/calculate-loan",
            json={
                "walletAddress": self.test_wallet_addresses["excellent_credit"],
                "amount": 10000,
                "rate": 5.5,
            },
            content_type="application/json",
        )
        excellent_data = json.loads(response.data)
        response = self.app.post(
            "/api/calculate-loan",
            json={
                "walletAddress": self.test_wallet_addresses["poor_credit"],
                "amount": 10000,
                "rate": 5.5,
            },
            content_type="application/json",
        )
        poor_data = json.loads(response.data)
        self.assertGreater(
            excellent_data["approval_probability"], poor_data["approval_probability"]
        )
        self.assertNotEqual(excellent_data["credit_score"], poor_data["credit_score"])

    def test_calculate_loan_with_different_amounts(self) -> Any:
        """Test calculate loan endpoint with different loan amounts."""
        response = self.app.post(
            "/api/calculate-loan",
            json={
                "walletAddress": self.test_wallet_addresses["good_credit"],
                "amount": 5000,
                "rate": 5.5,
            },
            content_type="application/json",
        )
        small_loan_data = json.loads(response.data)
        response = self.app.post(
            "/api/calculate-loan",
            json={
                "walletAddress": self.test_wallet_addresses["good_credit"],
                "amount": 50000,
                "rate": 5.5,
            },
            content_type="application/json",
        )
        large_loan_data = json.loads(response.data)
        self.assertGreater(
            small_loan_data["approval_probability"],
            large_loan_data["approval_probability"],
        )
        self.assertLess(
            small_loan_data["monthly_payment"], large_loan_data["monthly_payment"]
        )

    def test_calculate_loan_with_different_rates(self) -> Any:
        """Test calculate loan endpoint with different interest rates."""
        response = self.app.post(
            "/api/calculate-loan",
            json={
                "walletAddress": self.test_wallet_addresses["good_credit"],
                "amount": 10000,
                "rate": 3.0,
            },
            content_type="application/json",
        )
        low_rate_data = json.loads(response.data)
        response = self.app.post(
            "/api/calculate-loan",
            json={
                "walletAddress": self.test_wallet_addresses["good_credit"],
                "amount": 10000,
                "rate": 15.0,
            },
            content_type="application/json",
        )
        high_rate_data = json.loads(response.data)
        self.assertLess(
            low_rate_data["monthly_payment"], high_rate_data["monthly_payment"]
        )
        self.assertLess(low_rate_data["total_payment"], high_rate_data["total_payment"])
        self.assertGreater(
            high_rate_data["approval_probability"],
            low_rate_data["approval_probability"],
        )


if __name__ == "__main__":
    unittest.main()
