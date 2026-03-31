import json
import os
import sys
import unittest
from typing import Any, Dict
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server


class TestModelAPI(unittest.TestCase):
    """Test cases for the model API server"""

    def setUp(self) -> Any:
        """Set up test fixtures"""
        server.app.config["TESTING"] = True
        self.client = server.app.test_client()
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
        self.batch_request = {
            "batch": [
                {"userId": "user1", "creditHistory": self.sample_history},
                {"userId": "user2", "creditHistory": []},
            ]
        }

    def test_health_check(self) -> Any:
        """Test health check endpoint"""
        response = self.client.get("/health")
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "ok")
        self.assertIn("timestamp", data)

    @patch("server.transform_blockchain_data")
    @patch("server.predict_score")
    @patch("server.calculate_score_factors")
    def test_predict_endpoint(
        self, mock_factors: Any, mock_predict: Any, mock_transform: Any
    ) -> Dict[str, Any]:
        """Test prediction endpoint"""
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
        response = self.client.post(
            "/predict",
            data=json.dumps({"creditHistory": self.sample_history}),
            content_type="application/json",
        )
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["score"], 720)
        self.assertGreater(data["confidence"], 0)
        self.assertGreater(len(data["factors"]), 0)
        response = self.client.post(
            "/predict",
            data=json.dumps({"creditHistory": []}),
            content_type="application/json",
        )
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["score"], 500)
        self.assertEqual(data["confidence"], 0)
        response = self.client.post(
            "/predict",
            data=json.dumps({"invalid": "data"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    @patch("server.transform_blockchain_data")
    @patch("server.predict_score")
    @patch("server.calculate_score_factors")
    def test_batch_predict_endpoint(
        self, mock_factors: Any, mock_predict: Any, mock_transform: Any
    ) -> Dict[str, Any]:
        """Test batch prediction endpoint"""
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
        response = self.client.post(
            "/batch-predict",
            data=json.dumps(self.batch_request),
            content_type="application/json",
        )
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("results", data)
        self.assertEqual(len(data["results"]), 2)
        self.assertEqual(data["results"][0]["userId"], "user1")
        self.assertEqual(data["results"][0]["score"], 720)
        self.assertEqual(data["results"][1]["userId"], "user2")
        self.assertEqual(data["results"][1]["score"], 500)
        response = self.client.post(
            "/batch-predict",
            data=json.dumps({"invalid": "data"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
