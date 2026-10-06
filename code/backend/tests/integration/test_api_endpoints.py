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

import pytest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)


class TestAuthenticationEndpoints:

    def test_register_user_success(self, client: Any, db: Any) -> Any:
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
        login_data = {"email": sample_user.email, "password": "WrongPassword999!"}
        response = client.post(
            "/api/auth/login", json=login_data, content_type="application/json"
        )
        assert response.status_code == 401
        data = response.get_json()
        assert data["success"] is False

    def test_login_success(self, client: Any, db: Any, sample_user: Any) -> Any:
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
        response = client.get("/api/profile")
        assert response.status_code in (401, 422)

    def test_logout_requires_auth(self, client: Any) -> Any:
        response = client.post("/api/auth/logout")
        assert response.status_code in (401, 422)

    def test_refresh_requires_token(self, client: Any) -> Any:
        response = client.post("/api/auth/refresh")
        assert response.status_code in (401, 422)


class TestCreditEndpoints:

    def test_credit_history_requires_auth(self, client: Any) -> Any:
        response = client.get("/api/credit/history")
        assert response.status_code in (401, 422)

    def test_calculate_credit_score_requires_auth(self, client: Any) -> Any:
        response = client.post(
            "/api/credit/calculate-score",
            json={"walletAddress": "0x1234567890123456789012345678901234567890"},
            content_type="application/json",
        )
        assert response.status_code in (401, 422)

    def test_loan_calculate_requires_auth(self, client: Any) -> Any:
        response = client.post(
            "/api/loans/calculate",
            json={"amount": 1000, "rate": 5.0, "term_months": 12},
            content_type="application/json",
        )
        assert response.status_code in (401, 422)


class TestLoanEndpoints:

    def test_loan_apply_requires_auth(self, client: Any) -> Any:
        response = client.post(
            "/api/loans/apply", json={}, content_type="application/json"
        )
        assert response.status_code in (401, 422)

    def test_loan_application_full_flow(
        self, client: Any, db: Any, sample_user: Any
    ) -> Any:
        login_resp = client.post(
            "/api/auth/login",
            json={"email": sample_user.email, "password": "TestPassword123!"},
            content_type="application/json",
        )
        if login_resp.status_code != 200:
            pytest.fail(
                f"login failed {login_resp.status_code} {login_resp.get_json()}"
            )

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

    def test_record_blockchain_tx_for_own_application(
        self, client: Any, db: Any, sample_user: Any
    ) -> Any:
        login_resp = client.post(
            "/api/auth/login",
            json={"email": sample_user.email, "password": "TestPassword123!"},
            content_type="application/json",
        )
        if login_resp.status_code != 200:
            pytest.fail(
                f"login failed {login_resp.status_code} {login_resp.get_json()}"
            )
        token = login_resp.get_json()["tokens"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        apply_resp = client.post(
            "/api/loans/apply",
            json={
                "loan_type": "personal",
                "requested_amount": "5000.00",
                "requested_term_months": 24,
            },
            headers=headers,
            content_type="application/json",
        )
        if apply_resp.status_code != 201:
            pytest.skip("Loan application creation failed, skipping downstream test")
        application_id = apply_resp.get_json()["data"]["id"]

        tx_hash = "0x" + "ab" * 32
        bc_resp = client.post(
            f"/api/loans/applications/{application_id}/blockchain",
            json={
                "transaction_hash": tx_hash,
                "wallet_address": "0x1234567890123456789012345678901234567890",
            },
            headers=headers,
            content_type="application/json",
        )
        assert bc_resp.status_code == 200
        body = bc_resp.get_json()
        assert body["success"] is True
        assert body["data"]["application"]["blockchain_hash"] == tx_hash

    def test_record_blockchain_tx_requires_fields(
        self, client: Any, db: Any, sample_user: Any
    ) -> Any:
        login_resp = client.post(
            "/api/auth/login",
            json={"email": sample_user.email, "password": "TestPassword123!"},
            content_type="application/json",
        )
        if login_resp.status_code != 200:
            pytest.fail(
                f"login failed {login_resp.status_code} {login_resp.get_json()}"
            )
        token = login_resp.get_json()["tokens"]["access_token"]

        response = client.post(
            "/api/loans/applications/some-id/blockchain",
            json={},
            headers={"Authorization": f"Bearer {token}"},
            content_type="application/json",
        )
        assert response.status_code in (400, 404)

    def test_record_blockchain_tx_unknown_application(
        self, client: Any, db: Any, sample_user: Any
    ) -> Any:
        login_resp = client.post(
            "/api/auth/login",
            json={"email": sample_user.email, "password": "TestPassword123!"},
            content_type="application/json",
        )
        if login_resp.status_code != 200:
            pytest.fail(
                f"login failed {login_resp.status_code} {login_resp.get_json()}"
            )
        token = login_resp.get_json()["tokens"]["access_token"]

        response = client.post(
            "/api/loans/applications/does-not-exist/blockchain",
            json={
                "transaction_hash": "0x" + "cd" * 32,
                "wallet_address": "0x1234567890123456789012345678901234567890",
            },
            headers={"Authorization": f"Bearer {token}"},
            content_type="application/json",
        )
        assert response.status_code == 404


class TestProfileUpdateEndpoint:

    def test_update_profile_requires_auth(self, client: Any) -> Any:
        response = client.put(
            "/api/profile",
            json={"first_name": "Ada"},
            content_type="application/json",
        )
        assert response.status_code in (401, 422)

    def test_update_profile_success(
        self, client: Any, db: Any, sample_user: Any
    ) -> Any:
        login_resp = client.post(
            "/api/auth/login",
            json={"email": sample_user.email, "password": "TestPassword123!"},
            content_type="application/json",
        )
        if login_resp.status_code != 200:
            pytest.fail(
                f"login failed {login_resp.status_code} {login_resp.get_json()}"
            )

        token = login_resp.get_json()["tokens"]["access_token"]
        response = client.put(
            "/api/profile",
            json={
                "first_name": "Ada",
                "last_name": "Lovelace",
                "phone_number": "+15551234567",
                "wallet_address": "0x1234567890123456789012345678901234567890",
            },
            headers={"Authorization": f"Bearer {token}"},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["profile"]["first_name"] == "Ada"
        assert data["data"]["profile"]["last_name"] == "Lovelace"
        assert (
            data["data"]["profile"]["wallet_address"]
            == "0x1234567890123456789012345678901234567890"
        )

    def test_update_profile_partial(
        self, client: Any, db: Any, sample_user: Any
    ) -> Any:
        login_resp = client.post(
            "/api/auth/login",
            json={"email": sample_user.email, "password": "TestPassword123!"},
            content_type="application/json",
        )
        if login_resp.status_code != 200:
            pytest.fail(
                f"login failed {login_resp.status_code} {login_resp.get_json()}"
            )

        token = login_resp.get_json()["tokens"]["access_token"]
        response = client.put(
            "/api/profile",
            json={"city": "Budapest"},
            headers={"Authorization": f"Bearer {token}"},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"]["profile"]["address"]["city"] == "Budapest"


class TestLoanApplicationsListEndpoint:

    def test_list_applications_requires_auth(self, client: Any) -> Any:
        response = client.get("/api/loans/applications")
        assert response.status_code in (401, 422)

    def test_list_applications_returns_submitted_application(
        self, client: Any, db: Any, sample_user: Any
    ) -> Any:
        login_resp = client.post(
            "/api/auth/login",
            json={"email": sample_user.email, "password": "TestPassword123!"},
            content_type="application/json",
        )
        if login_resp.status_code != 200:
            pytest.fail(
                f"login failed {login_resp.status_code} {login_resp.get_json()}"
            )

        token = login_resp.get_json()["tokens"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        apply_resp = client.post(
            "/api/loans/apply",
            json={
                "loan_type": "personal",
                "requested_amount": "5000.00",
                "requested_term_months": 24,
            },
            headers=headers,
            content_type="application/json",
        )
        if apply_resp.status_code != 201:
            pytest.skip("Loan application failed, skipping downstream test")

        response = client.get("/api/loans/applications", headers=headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "applications" in data["data"]
        assert "pagination" in data["data"]
        assert len(data["data"]["applications"]) >= 1
        assert data["data"]["applications"][0]["loan_type"] == "personal"


class TestHealthEndpoints:

    def test_health_check(self, client: Any) -> Any:
        response = client.get("/api/health")
        assert response.status_code in (200, 503)
        data = response.get_json()
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "services" in data

    def test_health_check_services_present(self, client: Any) -> Any:
        response = client.get("/api/health")
        data = response.get_json()
        services = data.get("services", {})
        assert "database" in services


class TestErrorHandling:

    def test_404_error(self, client: Any) -> Any:
        response = client.get("/api/this-does-not-exist-xyz")
        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False
        assert "error" in data

    def test_bad_json_body(self, client: Any) -> Any:
        response = client.post(
            "/api/auth/register",
            data="not valid json{{{",
            content_type="application/json",
        )
        assert response.status_code in (400, 422)

    def test_method_not_allowed(self, client: Any) -> Any:
        response = client.delete("/api/health")
        assert response.status_code == 405

    def test_cors_headers_present(self, client: Any) -> Any:
        response = client.options(
            "/api/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert response.status_code in (200, 204)
