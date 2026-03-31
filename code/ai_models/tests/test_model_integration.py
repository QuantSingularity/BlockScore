import os
import sys
import unittest
from typing import Any, Dict
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from model_integration import (
    batch_score,
    calculate_score_factors,
    predict_score,
    transform_blockchain_data,
)


class TestModelIntegration(unittest.TestCase):
    """Test cases for the model integration module"""

    def setUp(self) -> Any:
        """Set up test fixtures"""
        self.sample_history = [
            {
                "timestamp": 1621500000,
                "amount": 5000,
                "repaid": True,
                "repaymentTimestamp": 1623500000,
                "provider": "0x123...",
                "recordType": "loan",
                "scoreImpact": 5,
            },
            {
                "timestamp": 1625500000,
                "amount": 10000,
                "repaid": True,
                "repaymentTimestamp": 1630500000,
                "provider": "0x456...",
                "recordType": "loan",
                "scoreImpact": 3,
            },
        ]
        self.empty_history = []
        self.no_repayment_history = [
            {
                "timestamp": 1621500000,
                "amount": 5000,
                "repaid": False,
                "repaymentTimestamp": 0,
                "provider": "0x123...",
                "recordType": "loan",
                "scoreImpact": 5,
            }
        ]

    def test_transform_blockchain_data(self) -> Any:
        """Test transformation of blockchain data to features"""
        features = transform_blockchain_data(self.sample_history)
        self.assertIsNotNone(features)
        self.assertIn("income", features)
        self.assertIn("debt_ratio", features)
        self.assertIn("payment_history", features)
        self.assertIn("loan_count", features)
        self.assertIn("loan_amount", features)
        self.assertIn("credit_utilization", features)
        self.assertEqual(features["loan_count"], 2)
        self.assertEqual(features["payment_history"], 1.0)
        empty_features = transform_blockchain_data(self.empty_history)
        self.assertIsNone(empty_features)
        no_repay_features = transform_blockchain_data(self.no_repayment_history)
        self.assertEqual(no_repay_features["payment_history"], 0.0)

    @patch("model_integration.model")
    def test_predict_score(self, mock_model: Any) -> Dict[str, Any]:
        """Test credit score prediction"""
        mock_model.predict.return_value = [720]
        features = transform_blockchain_data(self.sample_history)
        score = predict_score(features)
        self.assertGreaterEqual(score, 300)
        self.assertLessEqual(score, 850)
        self.assertEqual(score, 720)
        mock_model.predict.return_value = [200]
        score = predict_score(features)
        self.assertEqual(score, 300)
        mock_model.predict.return_value = [900]
        score = predict_score(features)
        self.assertEqual(score, 850)

    def test_calculate_score_factors(self) -> float:
        """Test calculation of score factors"""
        features = {
            "payment_history": 0.95,
            "debt_ratio": 0.2,
            "credit_utilization": 0.25,
            "loan_count": 6,
            "income": 50000,
            "loan_amount": 5000,
            "age": 30,
        }
        factors = calculate_score_factors(features, 750)
        self.assertIsInstance(factors, list)
        self.assertGreater(len(factors), 0)
        payment_factor = next(
            (f for f in factors if f["factor"] == "Excellent payment history"), None
        )
        self.assertIsNotNone(payment_factor)
        self.assertEqual(payment_factor["impact"], "positive")
        debt_factor = next(
            (f for f in factors if f["factor"] == "Low debt ratio"), None
        )
        self.assertIsNotNone(debt_factor)
        self.assertEqual(debt_factor["impact"], "positive")
        features["payment_history"] = 0.4
        features["debt_ratio"] = 0.7
        factors = calculate_score_factors(features, 600)
        payment_factor = next(
            (f for f in factors if f["factor"] == "Poor payment history"), None
        )
        self.assertIsNotNone(payment_factor)
        self.assertEqual(payment_factor["impact"], "negative")
        debt_factor = next(
            (f for f in factors if f["factor"] == "High debt ratio"), None
        )
        self.assertIsNotNone(debt_factor)
        self.assertEqual(debt_factor["impact"], "negative")

    @patch("model_integration.transform_blockchain_data")
    @patch("model_integration.predict_score")
    @patch("model_integration.calculate_score_factors")
    def test_batch_score(
        self, mock_factors: Any, mock_predict: Any, mock_transform: Any
    ) -> float:
        """Test batch scoring functionality"""
        mock_transform.return_value = {
            "payment_history": 0.9,
            "debt_ratio": 0.3,
            "credit_utilization": 0.4,
            "loan_count": 3,
            "income": 40000,
            "loan_amount": 5000,
            "age": 30,
        }
        mock_predict.return_value = 720
        mock_factors.return_value = [
            {
                "factor": "Good payment history",
                "impact": "positive",
                "description": "Generally repaying debts on time",
            }
        ]
        batch_histories = [self.sample_history, self.no_repayment_history]
        results = batch_score(batch_histories)
        self.assertEqual(len(results), 2)
        self.assertIn("score", results[0])
        self.assertIn("confidence", results[0])
        self.assertIn("factors", results[0])
        mock_transform.return_value = None
        results = batch_score([self.empty_history])
        self.assertEqual(results[0]["score"], 500)
        self.assertEqual(results[0]["confidence"], 0)


if __name__ == "__main__":
    unittest.main()
