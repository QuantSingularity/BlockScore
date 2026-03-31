"""
Comprehensive API Test Suite for BlockScore Backend
Tests for all API endpoints, authentication, and error handling
"""

import json
import os
import sys
import threading
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import Mock, patch

import jwt
import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app


class TestAPIEndpoints:
    """Test suite for API endpoints"""

    @pytest.fixture
    def app(self) -> Any:
        """Create test Flask application"""
        app = create_app("testing")
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        return app

    @pytest.fixture
    def client(self, app: Any) -> Any:
        """Create test client"""
        return app.test_client()

    @pytest.fixture
    def auth_headers(self, app: Any) -> Any:
        """Create authentication headers for testing"""
        with app.app_context():
            token = jwt.encode(
                {
                    "user_id": 1,
                    "email": "test@example.com",
                    "exp": datetime.utcnow() + timedelta(hours=1),
                },
                app.config["SECRET_KEY"],
                algorithm="HS256",
            )
            return {"Authorization": f"Bearer {token}"}

    def test_health_check(self, client: Any) -> Any:
        """Test health check endpoint"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data

    def test_score_calculation_original(self, client: Any) -> Any:
        """Test original score calculation endpoint"""
        response = client.post("/calculate-score", json={"walletAddress": "0x123"})
        assert response.status_code == 200
        assert "score" in response.json

    def test_user_registration_success(self, client: Any) -> Any:
        """Test successful user registration"""
        user_data = {
            "email": "newuser@example.com",
            "password": "SecurePassword123!",
            "first_name": "John",
            "last_name": "Doe",
            "phone": "+1234567890",
        }
        with patch("app.User") as MockUser, patch(
            "app.ComplianceService"
        ) as MockCompliance:
            MockUser.query.filter_by.return_value.first.return_value = None
            mock_user = Mock()
            mock_user.id = 1
            MockUser.return_value = mock_user
            mock_compliance = Mock()
            mock_compliance.perform_kyc_verification.return_value = {
                "success": True,
                "status": "approved",
            }
            MockCompliance.return_value = mock_compliance
            response = client.post(
                "/api/auth/register",
                data=json.dumps(user_data),
                content_type="application/json",
            )
            assert response.status_code == 201
            data = json.loads(response.data)
            assert data["success"] is True
            assert "user_id" in data
            assert "access_token" in data

    def test_user_registration_duplicate_email(self, client: Any) -> Any:
        """Test user registration with duplicate email"""
        user_data = {
            "email": "existing@example.com",
            "password": "SecurePassword123!",
            "first_name": "John",
            "last_name": "Doe",
        }
        with patch("app.User") as MockUser:
            existing_user = Mock()
            MockUser.query.filter_by.return_value.first.return_value = existing_user
            response = client.post(
                "/api/auth/register",
                data=json.dumps(user_data),
                content_type="application/json",
            )
            assert response.status_code == 400
            data = json.loads(response.data)
            assert data["success"] is False
            assert "already exists" in data["error"]

    def test_user_registration_invalid_data(self, client: Any) -> Any:
        """Test user registration with invalid data"""
        invalid_data = {"email": "invalid-email", "password": "123", "first_name": ""}
        response = client.post(
            "/api/auth/register",
            data=json.dumps(invalid_data),
            content_type="application/json",
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "validation_errors" in data

    def test_user_login_success(self, client: Any) -> Any:
        """Test successful user login"""
        login_data = {"email": "test@example.com", "password": "password123"}
        with patch("app.User") as MockUser, patch(
            "app.check_password_hash"
        ) as mock_check_password:
            mock_user = Mock()
            mock_user.id = 1
            mock_user.email = "test@example.com"
            mock_user.profile.mfa_enabled = False
            MockUser.query.filter_by.return_value.first.return_value = mock_user
            mock_check_password.return_value = True
            response = client.post(
                "/api/auth/login",
                data=json.dumps(login_data),
                content_type="application/json",
            )
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert "access_token" in data
            assert "user" in data

    def test_user_login_mfa_required(self, client: Any) -> Any:
        """Test user login when MFA is required"""
        login_data = {"email": "test@example.com", "password": "password123"}
        with patch("app.User") as MockUser, patch(
            "app.check_password_hash"
        ) as mock_check_password:
            mock_user = Mock()
            mock_user.id = 1
            mock_user.email = "test@example.com"
            mock_user.profile.mfa_enabled = True
            MockUser.query.filter_by.return_value.first.return_value = mock_user
            mock_check_password.return_value = True
            response = client.post(
                "/api/auth/login",
                data=json.dumps(login_data),
                content_type="application/json",
            )
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert data["mfa_required"] is True
            assert "mfa_token" in data

    def test_user_login_invalid_credentials(self, client: Any) -> Any:
        """Test user login with invalid credentials"""
        login_data = {"email": "test@example.com", "password": "wrongpassword"}
        with patch("app.User") as MockUser, patch(
            "app.check_password_hash"
        ) as mock_check_password:
            mock_user = Mock()
            MockUser.query.filter_by.return_value.first.return_value = mock_user
            mock_check_password.return_value = False
            response = client.post(
                "/api/auth/login",
                data=json.dumps(login_data),
                content_type="application/json",
            )
            assert response.status_code == 401
            data = json.loads(response.data)
            assert data["success"] is False
            assert "Invalid credentials" in data["error"]

    def test_mfa_verification_success(self, client: Any) -> Any:
        """Test successful MFA verification"""
        mfa_data = {
            "mfa_token": "valid_mfa_token",
            "mfa_code": "123456",
            "method": "totp",
        }
        with patch("app.jwt.decode") as mock_decode, patch(
            "app.MFAService"
        ) as MockMFAService:
            mock_decode.return_value = {"user_id": 1, "type": "mfa"}
            mock_mfa = Mock()
            mock_mfa.verify_mfa.return_value = {"success": True, "method_used": "totp"}
            MockMFAService.return_value = mock_mfa
            response = client.post(
                "/api/auth/mfa/verify",
                data=json.dumps(mfa_data),
                content_type="application/json",
            )
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert "access_token" in data

    def test_mfa_verification_invalid_code(self, client: Any) -> Any:
        """Test MFA verification with invalid code"""
        mfa_data = {
            "mfa_token": "valid_mfa_token",
            "mfa_code": "000000",
            "method": "totp",
        }
        with patch("app.jwt.decode") as mock_decode, patch(
            "app.MFAService"
        ) as MockMFAService:
            mock_decode.return_value = {"user_id": 1, "type": "mfa"}
            mock_mfa = Mock()
            mock_mfa.verify_mfa.return_value = {
                "success": False,
                "error": "Invalid MFA code",
            }
            MockMFAService.return_value = mock_mfa
            response = client.post(
                "/api/auth/mfa/verify",
                data=json.dumps(mfa_data),
                content_type="application/json",
            )
            assert response.status_code == 400
            data = json.loads(response.data)
            assert data["success"] is False
            assert "Invalid MFA code" in data["error"]

    def test_get_user_profile(self, client: Any, auth_headers: Any) -> Any:
        """Test getting user profile"""
        with patch("app.User") as MockUser:
            mock_user = Mock()
            mock_user.id = 1
            mock_user.email = "test@example.com"
            mock_user.profile.first_name = "John"
            mock_user.profile.last_name = "Doe"
            MockUser.query.get.return_value = mock_user
            response = client.get("/api/user/profile", headers=auth_headers)
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert data["user"]["email"] == "test@example.com"

    def test_update_user_profile(self, client: Any, auth_headers: Any) -> Any:
        """Test updating user profile"""
        update_data = {
            "first_name": "Jane",
            "last_name": "Smith",
            "phone": "+1987654321",
        }
        with patch("app.User") as MockUser:
            mock_user = Mock()
            mock_user.id = 1
            mock_user.profile = Mock()
            MockUser.query.get.return_value = mock_user
            response = client.put(
                "/api/user/profile",
                data=json.dumps(update_data),
                content_type="application/json",
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert "Profile updated successfully" in data["message"]

    def test_credit_score_calculation(self, client: Any, auth_headers: Any) -> Any:
        """Test credit score calculation endpoint"""
        score_data = {
            "income": 75000,
            "debt_ratio": 0.3,
            "payment_history": 0.95,
            "credit_utilization": 0.25,
            "loan_count": 2,
        }
        with patch("app.CreditScoringModel") as MockModel:
            mock_model = Mock()
            mock_model.predict.return_value = [720]
            MockModel.load_model.return_value = mock_model
            response = client.post(
                "/api/credit/calculate",
                data=json.dumps(score_data),
                content_type="application/json",
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert "credit_score" in data
            assert data["credit_score"] == 720

    def test_credit_score_calculation_invalid_data(
        self, client: Any, auth_headers: Any
    ) -> Any:
        """Test credit score calculation with invalid data"""
        invalid_data = {"income": -1000, "debt_ratio": 1.5}
        response = client.post(
            "/api/credit/calculate",
            data=json.dumps(invalid_data),
            content_type="application/json",
            headers=auth_headers,
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "validation_errors" in data

    def test_loan_application_submission(self, client: Any, auth_headers: Any) -> Any:
        """Test loan application submission"""
        loan_data = {
            "amount": 50000,
            "purpose": "home_improvement",
            "term_months": 60,
            "employment_info": {
                "employer": "Tech Corp",
                "position": "Software Engineer",
                "annual_income": 80000,
                "employment_length": 36,
            },
            "financial_info": {
                "monthly_income": 6667,
                "monthly_expenses": 3000,
                "existing_debt": 15000,
            },
        }
        with patch("app.LoanService") as MockLoanService:
            mock_loan_service = Mock()
            mock_loan_service.submit_application.return_value = {
                "success": True,
                "application_id": "APP123",
                "status": "submitted",
            }
            MockLoanService.return_value = mock_loan_service
            response = client.post(
                "/api/loans/apply",
                data=json.dumps(loan_data),
                content_type="application/json",
                headers=auth_headers,
            )
            assert response.status_code == 201
            data = json.loads(response.data)
            assert data["success"] is True
            assert "application_id" in data

    def test_get_loan_applications(self, client: Any, auth_headers: Any) -> Any:
        """Test getting user's loan applications"""
        with patch("app.LoanApplication") as MockLoanApplication:
            mock_applications = [
                Mock(id=1, amount=50000, status="approved"),
                Mock(id=2, amount=25000, status="pending"),
            ]
            MockLoanApplication.query.filter_by.return_value.all.return_value = (
                mock_applications
            )
            response = client.get("/api/loans/applications", headers=auth_headers)
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert len(data["applications"]) == 2

    def test_kyc_verification_initiation(self, client: Any, auth_headers: Any) -> Any:
        """Test KYC verification initiation"""
        kyc_data = {
            "document_type": "passport",
            "document_number": "P123456789",
            "date_of_birth": "1990-01-01",
            "address": {
                "street": "123 Main St",
                "city": "New York",
                "state": "NY",
                "zip_code": "10001",
                "country": "US",
            },
        }
        with patch("app.ComplianceService") as MockComplianceService:
            mock_compliance = Mock()
            mock_compliance.perform_kyc_verification.return_value = {
                "success": True,
                "verification_id": "VER123",
                "status": "approved",
            }
            MockComplianceService.return_value = mock_compliance
            response = client.post(
                "/api/compliance/kyc/verify",
                data=json.dumps(kyc_data),
                content_type="application/json",
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert "verification_id" in data

    def test_mfa_setup_totp(self, client: Any, auth_headers: Any) -> Any:
        """Test TOTP MFA setup"""
        with patch("app.MFAService") as MockMFAService:
            mock_mfa = Mock()
            mock_mfa.setup_totp.return_value = {
                "success": True,
                "secret": "JBSWY3DPEHPK3PXP",
                "qr_code": "base64_qr_data",
                "provisioning_uri": "otpauth://totp/...",
            }
            MockMFAService.return_value = mock_mfa
            response = client.post("/api/auth/mfa/setup/totp", headers=auth_headers)
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert "secret" in data
            assert "qr_code" in data

    def test_mfa_setup_sms(self, client: Any, auth_headers: Any) -> Any:
        """Test SMS MFA setup"""
        sms_data = {"phone_number": "+1234567890"}
        with patch("app.MFAService") as MockMFAService:
            mock_mfa = Mock()
            mock_mfa.setup_sms_mfa.return_value = {
                "success": True,
                "message": "Verification code sent to your phone",
            }
            MockMFAService.return_value = mock_mfa
            response = client.post(
                "/api/auth/mfa/setup/sms",
                data=json.dumps(sms_data),
                content_type="application/json",
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert "Verification code sent" in data["message"]

    def test_risk_assessment(self, client: Any, auth_headers: Any) -> Any:
        """Test risk assessment endpoint"""
        risk_data = {
            "transaction_amount": 10000,
            "transaction_type": "wire_transfer",
            "counterparty_country": "US",
            "user_risk_factors": {
                "account_age_days": 365,
                "previous_transactions": 50,
                "kyc_status": "approved",
            },
        }
        with patch("app.RiskAnalytics") as MockRiskAnalytics:
            mock_risk = Mock()
            mock_risk.assess_transaction_risk.return_value = {
                "risk_score": 0.25,
                "risk_level": "low",
                "risk_factors": [],
                "recommendation": "approve",
            }
            MockRiskAnalytics.return_value = mock_risk
            response = client.post(
                "/api/risk/assess",
                data=json.dumps(risk_data),
                content_type="application/json",
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert "risk_score" in data
            assert data["risk_level"] == "low"

    def test_unauthorized_access(self, client: Any) -> Any:
        """Test unauthorized access to protected endpoints"""
        response = client.get("/api/user/profile")
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data["success"] is False
        assert "Authorization required" in data["error"]

    def test_invalid_token(self, client: Any) -> Any:
        """Test access with invalid token"""
        invalid_headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/user/profile", headers=invalid_headers)
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data["success"] is False
        assert "Invalid token" in data["error"]

    def test_expired_token(self, client: Any, app: Any) -> Any:
        """Test access with expired token"""
        with app.app_context():
            expired_token = jwt.encode(
                {
                    "user_id": 1,
                    "email": "test@example.com",
                    "exp": datetime.utcnow() - timedelta(hours=1),
                },
                app.config["SECRET_KEY"],
                algorithm="HS256",
            )
            expired_headers = {"Authorization": f"Bearer {expired_token}"}
            response = client.get("/api/user/profile", headers=expired_headers)
            assert response.status_code == 401
            data = json.loads(response.data)
            assert data["success"] is False
            assert "Token expired" in data["error"]

    def test_rate_limiting(self, client: Any) -> Any:
        """Test API rate limiting"""

    def test_input_validation_sql_injection(
        self, client: Any, auth_headers: Any
    ) -> Any:
        """Test protection against SQL injection"""
        malicious_data = {
            "email": "'; DROP TABLE users; --",
            "first_name": '<script>alert("xss")</script>',
        }
        response = client.put(
            "/api/user/profile",
            data=json.dumps(malicious_data),
            content_type="application/json",
            headers=auth_headers,
        )
        assert response.status_code in [400, 200]
        if response.status_code == 200:
            data = json.loads(response.data)
            assert "<script>" not in str(data)

    def test_cors_headers(self, client: Any) -> Any:
        """Test CORS headers are present"""
        response = client.options("/api/health")
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Methods" in response.headers
        assert "Access-Control-Allow-Headers" in response.headers

    def test_content_type_validation(self, client: Any, auth_headers: Any) -> Any:
        """Test content type validation"""
        response = client.post(
            "/api/user/profile", data='{"test": "data"}', headers=auth_headers
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "Content-Type must be application/json" in data["error"]

    def test_request_size_limit(self, client: Any, auth_headers: Any) -> Any:
        """Test request size limits"""
        large_data = {"data": "x" * (1024 * 1024 * 10)}
        response = client.post(
            "/api/user/profile",
            data=json.dumps(large_data),
            content_type="application/json",
            headers=auth_headers,
        )
        assert response.status_code == 413

    def test_api_versioning(self, client: Any) -> Any:
        """Test API versioning"""
        response = client.get("/api/v1/health")
        assert response.status_code in [200, 404]
        response = client.get("/api/health")
        assert response.status_code == 200

    def test_error_response_format(self, client: Any) -> Any:
        """Test consistent error response format"""
        response = client.get("/api/nonexistent")
        assert response.status_code == 404
        data = json.loads(response.data)
        assert "success" in data
        assert "error" in data
        assert "timestamp" in data
        assert data["success"] is False

    def test_logging_and_monitoring(self, client: Any, auth_headers: Any) -> Any:
        """Test that requests are properly logged"""
        with patch("app.logger") as mock_logger:
            client.get("/api/user/profile", headers=auth_headers)
            assert mock_logger.info.called or mock_logger.debug.called

    def test_security_headers(self, client: Any) -> Any:
        """Test security headers are present"""
        response = client.get("/api/health")
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"


class TestAPIPerformance:
    """Performance tests for API endpoints"""

    def test_response_time_health_check(self, client: Any) -> Any:
        """Test health check response time"""
        import time

        start_time = time.time()
        response = client.get("/api/health")
        end_time = time.time()
        assert response.status_code == 200
        assert end_time - start_time < 0.1

    def test_concurrent_requests(self, client: Any, auth_headers: Any) -> Any:
        """Test handling of concurrent requests"""

        results = []

        def make_request():
            response = client.get("/api/user/profile", headers=auth_headers)
            results.append(response.status_code)

        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()
        assert len(results) == 10
        success_count = sum((1 for status in results if status in [200, 401]))
        assert success_count >= 8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
