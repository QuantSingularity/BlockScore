"""
Integration tests for API endpoints
"""

from typing import Any
from unittest.mock import patch

from models.loan import LoanApplication
from models.user import User


class TestAuthenticationEndpoints:
    """Integration tests for authentication endpoints"""

    def test_register_user_success(self, client: Any, db: Any) -> Any:
        """Test successful user registration"""
        user_data = {
            "email": "newuser@example.com",
            "password": "StrongPassword123!",
            "first_name": "New",
            "last_name": "User",
            "date_of_birth": "1990-01-01",
            "phone_number": "+1234567890",
        }
        response = client.post(
            "/api/auth/register", json=user_data, content_type="application/json"
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert "user_id" in data
        assert "message" in data
        user = User.query.filter_by(email=user_data["email"]).first()
        assert user is not None
        assert user.profile.first_name == user_data["first_name"]

    def test_register_user_duplicate_email(
        self, client: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test registration with duplicate email"""
        user_data = {
            "email": sample_user.email,
            "password": "StrongPassword123!",
            "first_name": "Duplicate",
            "last_name": "User",
        }
        response = client.post(
            "/api/auth/register", json=user_data, content_type="application/json"
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "already exists" in data["message"].lower()

    def test_register_user_invalid_data(self, client: Any, db: Any) -> Any:
        """Test registration with invalid data"""
        user_data = {
            "email": "invalid-email",
            "password": "123",
            "first_name": "",
            "last_name": "User",
        }
        response = client.post(
            "/api/auth/register", json=user_data, content_type="application/json"
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "errors" in data

    def test_login_success(self, client: Any, db: Any, sample_user: Any) -> Any:
        """Test successful user login"""
        login_data = {"email": sample_user.email, "password": "TestPassword123!"}
        with patch(
            "services.auth_service.AuthenticationService._verify_password",
            return_value=True,
        ):
            response = client.post(
                "/api/auth/login", json=login_data, content_type="application/json"
            )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data

    def test_login_invalid_credentials(
        self, client: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test login with invalid credentials"""
        login_data = {"email": sample_user.email, "password": "WrongPassword"}
        with patch(
            "services.auth_service.AuthenticationService._verify_password",
            return_value=False,
        ):
            response = client.post(
                "/api/auth/login", json=login_data, content_type="application/json"
            )
        assert response.status_code == 401
        data = response.get_json()
        assert data["success"] is False
        assert "invalid" in data["message"].lower()

    def test_login_nonexistent_user(self, client: Any, db: Any) -> Any:
        """Test login with nonexistent user"""
        login_data = {"email": "nonexistent@example.com", "password": "Password123!"}
        response = client.post(
            "/api/auth/login", json=login_data, content_type="application/json"
        )
        assert response.status_code == 401
        data = response.get_json()
        assert data["success"] is False

    def test_refresh_token_success(self, client: Any, db: Any, sample_user: Any) -> Any:
        """Test successful token refresh"""
        login_data = {"email": sample_user.email, "password": "TestPassword123!"}
        with patch(
            "services.auth_service.AuthenticationService._verify_password",
            return_value=True,
        ):
            login_response = client.post(
                "/api/auth/login", json=login_data, content_type="application/json"
            )
        refresh_token = login_response.get_json()["refresh_token"]
        refresh_data = {"refresh_token": refresh_token}
        with patch(
            "services.auth_service.AuthenticationService.refresh_token"
        ) as mock_refresh:
            mock_refresh.return_value = {
                "success": True,
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
            }
            response = client.post(
                "/api/auth/refresh", json=refresh_data, content_type="application/json"
            )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "access_token" in data

    def test_logout_success(self, client: Any, db: Any, sample_user: Any) -> Any:
        """Test successful logout"""
        with patch("app.jwt_required"), patch(
            "app.get_jwt_identity", return_value=sample_user.id
        ), patch(
            "services.auth_service.AuthenticationService.logout_user"
        ) as mock_logout:
            mock_logout.return_value = {
                "success": True,
                "message": "Logged out successfully",
            }
            response = client.post(
                "/api/auth/logout", headers={"Authorization": "Bearer fake_token"}
            )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True


class TestCreditScoringEndpoints:
    """Integration tests for credit scoring endpoints"""

    def test_get_credit_score_success(
        self, client: Any, db: Any, sample_user: Any, sample_credit_score: Any
    ) -> Any:
        """Test getting credit score"""
        with patch("app.jwt_required"), patch(
            "app.get_jwt_identity", return_value=sample_user.id
        ):
            response = client.get(
                "/api/credit/score", headers={"Authorization": "Bearer fake_token"}
            )
        assert response.status_code == 200
        data = response.get_json()
        assert "score" in data
        assert data["score"] == sample_credit_score.score

    def test_get_credit_score_not_found(
        self, client: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test getting credit score when none exists"""
        with patch("app.jwt_required"), patch(
            "app.get_jwt_identity", return_value=sample_user.id
        ):
            response = client.get(
                "/api/credit/score", headers={"Authorization": "Bearer fake_token"}
            )
        assert response.status_code == 404
        data = response.get_json()
        assert "not found" in data["message"].lower()

    def test_calculate_credit_score_success(
        self, client: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test credit score calculation"""
        with patch("app.jwt_required"), patch(
            "app.get_jwt_identity", return_value=sample_user.id
        ), patch(
            "services.credit_service.CreditScoringService.calculate_credit_score"
        ) as mock_calc:
            mock_calc.return_value = {
                "score": 720,
                "factors": ["payment_history", "credit_utilization"],
                "version": "v2.0",
            }
            response = client.post(
                "/api/credit/calculate", headers={"Authorization": "Bearer fake_token"}
            )
        assert response.status_code == 200
        data = response.get_json()
        assert data["score"] == 720
        assert "factors" in data

    def test_get_credit_history_success(
        self, client: Any, db: Any, sample_user: Any, sample_credit_score: Any
    ) -> Any:
        """Test getting credit score history"""
        with patch("app.jwt_required"), patch(
            "app.get_jwt_identity", return_value=sample_user.id
        ):
            response = client.get(
                "/api/credit/history", headers={"Authorization": "Bearer fake_token"}
            )
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        if data:
            assert "score" in data[0]
            assert "calculated_at" in data[0]

    def test_add_credit_event_success(
        self, client: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test adding credit event"""
        event_data = {
            "event_type": "payment_made",
            "amount": 500.0,
            "description": "Monthly payment",
        }
        with patch("app.jwt_required"), patch(
            "app.get_jwt_identity", return_value=sample_user.id
        ), patch(
            "services.credit_service.CreditScoringService.add_credit_event"
        ) as mock_add:
            mock_add.return_value = {
                "success": True,
                "event_id": "test_event_id",
                "message": "Event added successfully",
            }
            response = client.post(
                "/api/credit/events",
                json=event_data,
                headers={"Authorization": "Bearer fake_token"},
                content_type="application/json",
            )
        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert "event_id" in data

    def test_get_credit_recommendations(
        self, client: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test getting credit recommendations"""
        with patch("app.jwt_required"), patch(
            "app.get_jwt_identity", return_value=sample_user.id
        ), patch(
            "services.credit_service.CreditScoringService.get_credit_recommendations"
        ) as mock_rec:
            mock_rec.return_value = [
                {
                    "title": "Make on-time payments",
                    "description": "Payment history is the most important factor",
                    "priority": "high",
                    "impact": "+20 points",
                }
            ]
            response = client.get(
                "/api/credit/recommendations",
                headers={"Authorization": "Bearer fake_token"},
            )
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "title" in data[0]
        assert "priority" in data[0]


class TestLoanEndpoints:
    """Integration tests for loan endpoints"""

    def test_submit_loan_application_success(
        self, client: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test successful loan application submission"""
        loan_data = {
            "loan_type": "personal",
            "requested_amount": 10000.0,
            "requested_term_months": 36,
            "purpose": "debt_consolidation",
            "employment_status": "employed",
            "annual_income": 75000.0,
            "monthly_expenses": 3000.0,
        }
        with patch("app.jwt_required"), patch(
            "app.get_jwt_identity", return_value=sample_user.id
        ):
            response = client.post(
                "/api/loans/apply",
                json=loan_data,
                headers={"Authorization": "Bearer fake_token"},
                content_type="application/json",
            )
        assert response.status_code == 201
        data = response.get_json()
        assert "application_id" in data
        assert data["status"] == "submitted"
        application = LoanApplication.query.filter_by(user_id=sample_user.id).first()
        assert application is not None
        assert application.requested_amount == loan_data["requested_amount"]

    def test_submit_loan_application_invalid_data(
        self, client: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test loan application with invalid data"""
        loan_data = {
            "loan_type": "invalid_type",
            "requested_amount": -1000,
            "requested_term_months": 0,
        }
        with patch("app.jwt_required"), patch(
            "app.get_jwt_identity", return_value=sample_user.id
        ):
            response = client.post(
                "/api/loans/apply",
                json=loan_data,
                headers={"Authorization": "Bearer fake_token"},
                content_type="application/json",
            )
        assert response.status_code == 400
        data = response.get_json()
        assert "errors" in data

    def test_get_loan_applications(
        self, client: Any, db: Any, sample_user: Any, sample_loan_application: Any
    ) -> Any:
        """Test getting user's loan applications"""
        with patch("app.jwt_required"), patch(
            "app.get_jwt_identity", return_value=sample_user.id
        ):
            response = client.get(
                "/api/loans/applications",
                headers={"Authorization": "Bearer fake_token"},
            )
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert data[0]["id"] == sample_loan_application.id
        assert data[0]["loan_type"] == sample_loan_application.loan_type

    def test_get_loan_application_details(
        self, client: Any, db: Any, sample_user: Any, sample_loan_application: Any
    ) -> Any:
        """Test getting specific loan application details"""
        with patch("app.jwt_required"), patch(
            "app.get_jwt_identity", return_value=sample_user.id
        ):
            response = client.get(
                f"/api/loans/applications/{sample_loan_application.id}",
                headers={"Authorization": "Bearer fake_token"},
            )
        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == sample_loan_application.id
        assert data["requested_amount"] == float(
            sample_loan_application.requested_amount
        )

    def test_get_loan_application_unauthorized(
        self, client: Any, db: Any, sample_user: Any, sample_loan_application: Any
    ) -> Any:
        """Test getting loan application from different user"""
        other_user = User(
            email="other@example.com",
            password_hash="hashed_password",
            is_active=True,
            email_verified=True,
        )
        db.session.add(other_user)
        db.session.commit()
        with patch("app.jwt_required"), patch(
            "app.get_jwt_identity", return_value=other_user.id
        ):
            response = client.get(
                f"/api/loans/applications/{sample_loan_application.id}",
                headers={"Authorization": "Bearer fake_token"},
            )
        assert response.status_code == 404


class TestComplianceEndpoints:
    """Integration tests for compliance endpoints"""

    def test_kyc_assessment_success(
        self, client: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test KYC assessment"""
        with patch("app.jwt_required"), patch(
            "app.get_jwt_identity", return_value=sample_user.id
        ), patch(
            "services.compliance_service.ComplianceService.perform_kyc_assessment"
        ) as mock_kyc:
            mock_kyc.return_value = {
                "compliance_record_id": "test_record_id",
                "kyc_status": "verified",
                "compliance_score": 95,
                "assessment_results": {},
                "required_actions": [],
            }
            response = client.post(
                "/api/compliance/kyc", headers={"Authorization": "Bearer fake_token"}
            )
        assert response.status_code == 200
        data = response.get_json()
        assert data["kyc_status"] == "verified"
        assert data["compliance_score"] == 95

    def test_aml_screening_success(self, client: Any, db: Any, sample_user: Any) -> Any:
        """Test AML screening"""
        screening_data = {
            "transaction_amount": 5000.0,
            "transaction_type": "loan_disbursement",
        }
        with patch("app.jwt_required"), patch(
            "app.get_jwt_identity", return_value=sample_user.id
        ), patch(
            "services.compliance_service.ComplianceService.perform_aml_screening"
        ) as mock_aml:
            mock_aml.return_value = {
                "compliance_record_id": "test_aml_record",
                "aml_status": "compliant",
                "risk_score": 15,
                "screening_results": {},
                "sar_required": False,
            }
            response = client.post(
                "/api/compliance/aml",
                json=screening_data,
                headers={"Authorization": "Bearer fake_token"},
                content_type="application/json",
            )
        assert response.status_code == 200
        data = response.get_json()
        assert data["aml_status"] == "compliant"
        assert data["risk_score"] == 15


class TestBlockchainEndpoints:
    """Integration tests for blockchain endpoints"""

    def test_submit_credit_score_to_blockchain(
        self, client: Any, db: Any, sample_user: Any, sample_credit_score: Any
    ) -> Any:
        """Test submitting credit score to blockchain"""
        blockchain_data = {
            "wallet_address": "0x1234567890123456789012345678901234567890"
        }
        with patch("app.jwt_required"), patch(
            "app.get_jwt_identity", return_value=sample_user.id
        ), patch(
            "services.blockchain_service.BlockchainService.submit_credit_score_update"
        ) as mock_blockchain:
            mock_blockchain.return_value = {
                "transaction_id": "test_tx_id",
                "transaction_hash": "0xabcdef",
                "status": "submitted",
            }
            response = client.post(
                "/api/blockchain/credit-score",
                json=blockchain_data,
                headers={"Authorization": "Bearer fake_token"},
                content_type="application/json",
            )
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "submitted"
        assert "transaction_hash" in data

    def test_get_blockchain_transaction_status(
        self, client: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test getting blockchain transaction status"""
        transaction_hash = "0x1234567890abcdef"
        with patch("app.jwt_required"), patch(
            "app.get_jwt_identity", return_value=sample_user.id
        ), patch(
            "services.blockchain_service.BlockchainService.get_transaction_status"
        ) as mock_status:
            mock_status.return_value = {
                "status": "confirmed",
                "block_number": 1000001,
                "confirmations": 12,
            }
            response = client.get(
                f"/api/blockchain/transactions/{transaction_hash}",
                headers={"Authorization": "Bearer fake_token"},
            )
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "confirmed"
        assert data["confirmations"] == 12


class TestHealthEndpoints:
    """Integration tests for health check endpoints"""

    def test_health_check(self, client: Any) -> Any:
        """Test basic health check"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.get_json()
        assert "status" in data
        assert "timestamp" in data

    def test_health_check_detailed(self, client: Any) -> Any:
        """Test detailed health check"""
        with patch(
            "utils.monitoring.PerformanceMonitor.get_health_status"
        ) as mock_health:
            mock_health.return_value = {
                "status": "healthy",
                "health_score": 95,
                "issues": [],
                "system_metrics": {},
                "application_metrics": {},
            }
            response = client.get("/api/health/detailed")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "healthy"
        assert data["health_score"] == 95


class TestErrorHandling:
    """Integration tests for error handling"""

    def test_404_error(self, client: Any) -> Any:
        """Test 404 error handling"""
        response = client.get("/api/nonexistent-endpoint")
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data
        assert "not found" in data["error"].lower()

    def test_405_method_not_allowed(self, client: Any) -> Any:
        """Test 405 error handling"""
        response = client.delete("/api/auth/login")
        assert response.status_code == 405
        data = response.get_json()
        assert "error" in data
        assert "method not allowed" in data["error"].lower()

    def test_401_unauthorized(self, client: Any) -> Any:
        """Test 401 error handling"""
        response = client.get("/api/credit/score")
        assert response.status_code == 401
        data = response.get_json()
        assert "error" in data
        assert "unauthorized" in data["error"].lower()

    def test_400_bad_request(self, client: Any) -> Any:
        """Test 400 error handling"""
        response = client.post(
            "/api/auth/register", data="invalid json", content_type="application/json"
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_500_internal_server_error(
        self, client: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test 500 error handling"""
        with patch("app.jwt_required"), patch(
            "app.get_jwt_identity", return_value=sample_user.id
        ), patch(
            "services.credit_service.CreditScoringService.get_credit_score",
            side_effect=Exception("Test error"),
        ):
            response = client.get(
                "/api/credit/score", headers={"Authorization": "Bearer fake_token"}
            )
        assert response.status_code == 500
        data = response.get_json()
        assert "error" in data
        assert "internal server error" in data["error"].lower()


class TestRateLimiting:
    """Integration tests for rate limiting"""

    def test_rate_limiting_login(self, client: Any, db: Any, sample_user: Any) -> Any:
        """Test rate limiting on login endpoint"""
        login_data = {"email": sample_user.email, "password": "WrongPassword"}
        for _ in range(6):
            with patch(
                "services.auth_service.AuthenticationService._verify_password",
                return_value=False,
            ):
                response = client.post(
                    "/api/auth/login", json=login_data, content_type="application/json"
                )
        assert response.status_code == 429
        data = response.get_json()
        assert "rate limit" in data["error"].lower()


class TestCORS:
    """Integration tests for CORS handling"""

    def test_cors_preflight(self, client: Any) -> Any:
        """Test CORS preflight request"""
        response = client.options(
            "/api/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Methods" in response.headers

    def test_cors_actual_request(self, client: Any, db: Any) -> Any:
        """Test CORS on actual request"""
        user_data = {
            "email": "test@example.com",
            "password": "StrongPassword123!",
            "first_name": "Test",
            "last_name": "User",
        }
        response = client.post(
            "/api/auth/register",
            json=user_data,
            headers={"Origin": "http://localhost:3000"},
            content_type="application/json",
        )
        assert "Access-Control-Allow-Origin" in response.headers
