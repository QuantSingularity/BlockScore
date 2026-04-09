#!/usr/bin/env python3
"""
BlockScore Backend Test Runner
Runs all tests using Python's built-in unittest framework.
Handles pytest-style fixture-based tests by providing a compatibility layer.
"""

import json
import os
import sys
import unittest
from datetime import datetime, timezone
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compat_stubs  # noqa - must be first

# ─────────────────────────────────────────────────────────────────────────────
# Fixture infrastructure
# ─────────────────────────────────────────────────────────────────────────────

_FIXTURES = {}


def fixture(fn):
    """Minimal pytest fixture decorator stub."""
    _FIXTURES[fn.__name__] = fn
    return fn


def _resolve_fixtures(fn, test_instance):
    """Call a fixture function, resolving its own fixture dependencies."""
    import inspect

    sig = inspect.signature(fn)
    kwargs = {}
    for param_name in sig.parameters:
        if param_name in _FIXTURES:
            dep = _FIXTURES[param_name]
            val = _resolve_fixtures(dep, test_instance)
            # handle generator fixtures
            if hasattr(val, "__next__"):
                val = next(val)
            kwargs[param_name] = val
        elif hasattr(test_instance, param_name):
            kwargs[param_name] = getattr(test_instance, param_name)
    result = fn(**kwargs)
    if hasattr(result, "__next__"):
        result = next(result)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Shared test fixtures
# ─────────────────────────────────────────────────────────────────────────────

from app import create_app
from extensions import bcrypt
from extensions import db as _db


def _make_app():
    app = create_app("testing")
    app.config["RATELIMIT_ENABLED"] = False
    return app


def _setup_db(app):
    with app.app_context():
        _db.create_all()
    return _db


def _get_sample_user(db_session, app):
    from models.user import KYCStatus, User, UserProfile, UserStatus

    with app.app_context():
        email = f"sample_{id(db_session)}@example.com"
        existing = User.query.filter_by(email=email).first()
        if existing:
            return existing
        user = User(
            email=email,
            status=UserStatus.ACTIVE,
            is_active=True,
            email_verified=True,
            failed_login_attempts=0,
        )
        user.set_password("TestPassword123!")
        db_session.session.add(user)
        db_session.session.flush()
        profile = UserProfile(
            user_id=user.id,
            first_name="John",
            last_name="Doe",
            date_of_birth=datetime(1990, 1, 1).date(),
            phone_number="+1234567890",
            street_address="123 Test Street",
            address_line1="123 Test Street",
            city="Test City",
            state="TS",
            postal_code="12345",
            country="US",
            kyc_status=KYCStatus.APPROVED,
        )
        db_session.session.add(profile)
        db_session.session.commit()
        return user


def _get_sample_credit_score(db_session, user, app):
    from models.credit import CreditScore, CreditScoreStatus

    with app.app_context():
        score = CreditScore(
            user_id=user.id,
            score=750,
            score_version="v2.0",
            status=CreditScoreStatus.ACTIVE,
            calculated_at=datetime.now(timezone.utc),
        )
        score.set_factors_positive(["payment_history", "credit_utilization"])
        score.set_factors_negative(["credit_age"])
        db_session.session.add(score)
        db_session.session.commit()
        return score


def _get_sample_loan(db_session, user, app):
    from models.loan import LoanApplication, LoanStatus, LoanType

    with app.app_context():
        loan = LoanApplication(
            user_id=user.id,
            application_number=LoanApplication.generate_application_number(),
            loan_type=LoanType.PERSONAL,
            requested_amount=Decimal("10000.00"),
            requested_term_months=36,
            requested_rate=12.5,
            purpose="debt_consolidation",
            employment_status="employed",
            annual_income=Decimal("75000.00"),
            monthly_expenses=Decimal("3000.00"),
            status=LoanStatus.SUBMITTED,
        )
        db_session.session.add(loan)
        db_session.session.commit()
        return loan


# ─────────────────────────────────────────────────────────────────────────────
# Base test case with fixture support
# ─────────────────────────────────────────────────────────────────────────────


class BaseTestCase(unittest.TestCase):
    """Base test case providing Flask app context and common fixtures."""

    @classmethod
    def setUpClass(cls):
        cls.flask_app = _make_app()
        cls.ctx = cls.flask_app.app_context()
        cls.ctx.push()
        _db.create_all()
        cls.client = cls.flask_app.test_client()

    @classmethod
    def tearDownClass(cls):
        _db.session.remove()
        _db.drop_all()
        cls.ctx.pop()

    def setUp(self):
        self._cleanup_users = []

    def tearDown(self):
        try:
            _db.session.rollback()
        except Exception:
            pass

    @property
    def db(self):
        return _db

    def get_user(self):
        return _get_sample_user(_db, self.flask_app)

    def get_credit_score(self, user=None):
        u = user or self.get_user()
        return _get_sample_credit_score(_db, u, self.flask_app)

    def get_loan(self, user=None):
        u = user or self.get_user()
        return _get_sample_loan(_db, u, self.flask_app)

    def register_and_login(self, email=None, password="Pass123!"):
        email = email or f"user_{id(self)}@test.com"
        self.client.post(
            "/api/auth/register",
            data=json.dumps(
                {"email": email, "password": password, "confirm_password": password}
            ),
            content_type="application/json",
        )
        r = self.client.post(
            "/api/auth/login",
            data=json.dumps({"email": email, "password": password}),
            content_type="application/json",
        )
        data = json.loads(r.data)
        return data.get("tokens", {}).get("access_token", "")

    def auth_headers(self, token):
        return {"Authorization": f"Bearer {token}"}


# ─────────────────────────────────────────────────────────────────────────────
# Integration Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestAPIEndpoints(BaseTestCase):
    """API endpoint integration tests."""

    def test_health_check(self):
        r = self.client.get("/api/health")
        self.assertIn(r.status_code, (200, 503))
        data = json.loads(r.data)
        self.assertIn("status", data)
        self.assertIn("timestamp", data)
        self.assertIn("version", data)
        self.assertIn("services", data)

    def test_health_check_has_database_service(self):
        r = self.client.get("/api/health")
        data = json.loads(r.data)
        self.assertIn("database", data["services"])

    def test_register_success(self):
        r = self.client.post(
            "/api/auth/register",
            data=json.dumps(
                {
                    "email": "reg_test@example.com",
                    "password": "Secure123!",
                    "confirm_password": "Secure123!",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 201)
        data = json.loads(r.data)
        self.assertTrue(data["success"])
        self.assertIn("user", data)
        self.assertIn("user_id", data)

    def test_register_duplicate_email(self):
        payload = {
            "email": "dup_test@example.com",
            "password": "Secure123!",
            "confirm_password": "Secure123!",
        }
        self.client.post(
            "/api/auth/register",
            data=json.dumps(payload),
            content_type="application/json",
        )
        r = self.client.post(
            "/api/auth/register",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 409)
        self.assertFalse(json.loads(r.data)["success"])

    def test_register_password_mismatch(self):
        r = self.client.post(
            "/api/auth/register",
            data=json.dumps(
                {
                    "email": "mm@example.com",
                    "password": "Secure123!",
                    "confirm_password": "Different1!",
                }
            ),
            content_type="application/json",
        )
        self.assertIn(r.status_code, (400, 422))
        self.assertFalse(json.loads(r.data)["success"])

    def test_login_nonexistent_user(self):
        r = self.client.post(
            "/api/auth/login",
            data=json.dumps({"email": "ghost@example.com", "password": "Pass123!"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 401)
        self.assertFalse(json.loads(r.data)["success"])

    def test_login_wrong_password(self):
        self.client.post(
            "/api/auth/register",
            data=json.dumps(
                {
                    "email": "wp@example.com",
                    "password": "Right123!",
                    "confirm_password": "Right123!",
                }
            ),
            content_type="application/json",
        )
        r = self.client.post(
            "/api/auth/login",
            data=json.dumps({"email": "wp@example.com", "password": "Wrong999!"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 401)

    def test_login_success_returns_tokens(self):
        self.client.post(
            "/api/auth/register",
            data=json.dumps(
                {
                    "email": "tok@example.com",
                    "password": "Token123!",
                    "confirm_password": "Token123!",
                }
            ),
            content_type="application/json",
        )
        r = self.client.post(
            "/api/auth/login",
            data=json.dumps({"email": "tok@example.com", "password": "Token123!"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.data)
        self.assertTrue(data["success"])
        self.assertIn("tokens", data)
        self.assertIn("access_token", data["tokens"])
        self.assertIn("refresh_token", data["tokens"])

    def test_profile_requires_auth(self):
        r = self.client.get("/api/profile")
        self.assertIn(r.status_code, (401, 422))

    def test_profile_with_auth(self):
        token = self.register_and_login("prof@example.com")
        r = self.client.get("/api/profile", headers=self.auth_headers(token))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(json.loads(r.data)["success"])

    def test_logout_success(self):
        token = self.register_and_login("lgout@example.com")
        r = self.client.post("/api/auth/logout", headers=self.auth_headers(token))
        self.assertEqual(r.status_code, 200)
        self.assertTrue(json.loads(r.data)["success"])

    def test_credit_history_requires_auth(self):
        r = self.client.get("/api/credit/history")
        self.assertIn(r.status_code, (401, 422))

    def test_credit_history_empty_for_new_user(self):
        token = self.register_and_login("chist@example.com")
        r = self.client.get("/api/credit/history", headers=self.auth_headers(token))
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["history"], [])

    def test_loan_calculate_requires_auth(self):
        r = self.client.post(
            "/api/loans/calculate",
            data=json.dumps({"amount": 1000, "rate": 5.0, "term_months": 12}),
            content_type="application/json",
        )
        self.assertIn(r.status_code, (401, 422))

    def test_loan_calculate_with_auth(self):
        token = self.register_and_login("lcalc@example.com")
        r = self.client.post(
            "/api/loans/calculate",
            data=json.dumps({"amount": 10000, "rate": 5.5, "term_months": 36}),
            headers=self.auth_headers(token),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.data)
        self.assertTrue(data["success"])
        self.assertIn("monthly_payment", data["data"])
        self.assertIn("total_payment", data["data"])
        self.assertIn("total_interest", data["data"])
        self.assertIn("approval_probability", data["data"])

    def test_loan_calculation_math(self):
        token = self.register_and_login("lmath@example.com")
        r = self.client.post(
            "/api/loans/calculate",
            data=json.dumps({"amount": 10000, "rate": 5.5, "term_months": 36}),
            headers=self.auth_headers(token),
            content_type="application/json",
        )
        data = json.loads(r.data)["data"]
        monthly_rate = 5.5 / 100 / 12
        expected = (
            10000
            * monthly_rate
            * (1 + monthly_rate) ** 36
            / ((1 + monthly_rate) ** 36 - 1)
        )
        self.assertAlmostEqual(data["monthly_payment"], round(expected, 2), delta=0.05)

    def test_credit_score_requires_wallet(self):
        token = self.register_and_login("cswallet@example.com")
        r = self.client.post(
            "/api/credit/calculate-score",
            data=json.dumps({}),
            headers=self.auth_headers(token),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertFalse(json.loads(r.data)["success"])

    def test_loan_apply_requires_auth(self):
        r = self.client.post(
            "/api/loans/apply", data=json.dumps({}), content_type="application/json"
        )
        self.assertIn(r.status_code, (401, 422))

    def test_404_returns_json(self):
        r = self.client.get("/api/this-does-not-exist-xyz")
        self.assertEqual(r.status_code, 404)
        data = json.loads(r.data)
        self.assertFalse(data["success"])
        self.assertIn("error", data)

    def test_405_method_not_allowed(self):
        r = self.client.delete("/api/health")
        self.assertEqual(r.status_code, 405)

    def test_cors_headers_on_response(self):
        r = self.client.get("/api/health", headers={"Origin": "http://localhost:3000"})
        self.assertIn("Access-Control-Allow-Origin", r.headers)

    def test_full_flow_register_login_profile(self):
        email = "fullflow@example.com"
        password = "FlowTest123!"
        r1 = self.client.post(
            "/api/auth/register",
            data=json.dumps(
                {"email": email, "password": password, "confirm_password": password}
            ),
            content_type="application/json",
        )
        self.assertEqual(r1.status_code, 201)
        r2 = self.client.post(
            "/api/auth/login",
            data=json.dumps({"email": email, "password": password}),
            content_type="application/json",
        )
        self.assertEqual(r2.status_code, 200)
        token = json.loads(r2.data)["tokens"]["access_token"]
        r3 = self.client.get("/api/profile", headers=self.auth_headers(token))
        self.assertEqual(r3.status_code, 200)
        r4 = self.client.post("/api/auth/logout", headers=self.auth_headers(token))
        self.assertEqual(r4.status_code, 200)


# ─────────────────────────────────────────────────────────────────────────────
# Auth Service Unit Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestAuthService(BaseTestCase):
    """Unit tests for AuthService."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from services.auth_service import AuthService

        cls.auth_svc = AuthService(_db, bcrypt)

    def test_register_success(self):
        result = self.auth_svc.register_user(
            {
                "email": f"ar_{id(self)}@example.com",
                "password": "Strong123!",
                "first_name": "Test",
                "last_name": "User",
            }
        )
        self.assertTrue(result["success"])
        self.assertIn("user_id", result)

    def test_register_duplicate_email(self):
        email = f"ard_{id(self)}@example.com"
        self.auth_svc.register_user({"email": email, "password": "Strong123!"})
        result = self.auth_svc.register_user({"email": email, "password": "Strong123!"})
        self.assertFalse(result["success"])
        self.assertIn("already exists", result["message"].lower())

    def test_register_invalid_email(self):
        result = self.auth_svc.register_user(
            {"email": "not-an-email", "password": "Strong123!"}
        )
        self.assertFalse(result["success"])
        self.assertIn("invalid", result["message"].lower())

    def test_register_weak_password(self):
        result = self.auth_svc.register_user(
            {"email": "pw@example.com", "password": "123"}
        )
        self.assertFalse(result["success"])
        self.assertIn("password", result["message"].lower())

    def test_authenticate_success(self):
        email = f"auth_{id(self)}@example.com"
        self.auth_svc.register_user({"email": email, "password": "Strong123!"})
        result = self.auth_svc.authenticate_user(email, "Strong123!")
        self.assertTrue(result["success"])
        self.assertIn("access_token", result)
        self.assertIn("refresh_token", result)

    def test_authenticate_wrong_password(self):
        email = f"awp_{id(self)}@example.com"
        self.auth_svc.register_user({"email": email, "password": "Strong123!"})
        result = self.auth_svc.authenticate_user(email, "WrongPass!")
        self.assertFalse(result["success"])
        self.assertIn("invalid", result["message"].lower())

    def test_authenticate_nonexistent_user(self):
        result = self.auth_svc.authenticate_user("nobody@example.com", "Pass123!")
        self.assertFalse(result["success"])

    def test_validate_password_valid(self):
        result = self.auth_svc._validate_password("StrongPass123!")
        self.assertTrue(result["valid"])

    def test_validate_password_too_short(self):
        result = self.auth_svc._validate_password("Ab1!")
        self.assertFalse(result["valid"])

    def test_validate_password_no_uppercase(self):
        result = self.auth_svc._validate_password("nouppercase123!")
        self.assertFalse(result["valid"])

    def test_validate_password_no_number(self):
        result = self.auth_svc._validate_password("NoNumbers!")
        self.assertFalse(result["valid"])

    def test_validate_password_no_special(self):
        result = self.auth_svc._validate_password("NoSpecial123")
        self.assertFalse(result["valid"])

    def test_validate_email_valid(self):
        self.assertTrue(self.auth_svc._validate_email("user@example.com"))

    def test_validate_email_invalid(self):
        self.assertFalse(self.auth_svc._validate_email("not-an-email"))
        self.assertFalse(self.auth_svc._validate_email("@domain.com"))
        self.assertFalse(self.auth_svc._validate_email("user@"))

    def test_request_password_reset(self):
        email = f"pr_{id(self)}@example.com"
        self.auth_svc.register_user({"email": email, "password": "Strong123!"})
        result = self.auth_svc.request_password_reset(email)
        self.assertTrue(result["success"])
        self.assertIn("reset_token", result)

    def test_request_password_reset_invalid_email(self):
        result = self.auth_svc.request_password_reset("notfound@example.com")
        self.assertFalse(result["success"])
        self.assertIn("not found", result["message"].lower())

    def test_reset_password_success(self):
        email = f"rp_{id(self)}@example.com"
        self.auth_svc.register_user({"email": email, "password": "Strong123!"})
        pr = self.auth_svc.request_password_reset(email)
        result = self.auth_svc.reset_password(pr["reset_token"], "NewStrong456!")
        self.assertTrue(result["success"])

    def test_reset_password_invalid_token(self):
        result = self.auth_svc.reset_password("bad-token-xyz", "NewPass123!")
        self.assertFalse(result["success"])
        self.assertIn("invalid", result["message"].lower())

    def test_logout_user(self):
        email = f"lo_{id(self)}@example.com"
        self.auth_svc.register_user({"email": email, "password": "Strong123!"})
        auth = self.auth_svc.authenticate_user(email, "Strong123!")
        user_id = auth["user_id"]
        sess = self.auth_svc.create_session(
            user_id, auth["access_token"], auth["refresh_token"]
        )
        result = self.auth_svc.logout_user(user_id, sess.session_token)
        self.assertTrue(result["success"])

    def test_change_password_success(self):
        email = f"cp_{id(self)}@example.com"
        self.auth_svc.register_user({"email": email, "password": "Strong123!"})
        auth = self.auth_svc.authenticate_user(email, "Strong123!")
        result = self.auth_svc.change_password(
            auth["user_id"], "Strong123!", "NewStrong456!"
        )
        self.assertTrue(result["success"])

    def test_change_password_wrong_current(self):
        email = f"cpw_{id(self)}@example.com"
        self.auth_svc.register_user({"email": email, "password": "Strong123!"})
        auth = self.auth_svc.authenticate_user(email, "Strong123!")
        result = self.auth_svc.change_password(
            auth["user_id"], "WrongPass!", "NewStrong456!"
        )
        self.assertFalse(result["success"])
        self.assertIn("current password", result["message"].lower())

    def test_get_user_sessions(self):
        email = f"gs_{id(self)}@example.com"
        self.auth_svc.register_user({"email": email, "password": "Strong123!"})
        auth = self.auth_svc.authenticate_user(email, "Strong123!")
        self.auth_svc.create_session(
            auth["user_id"], auth["access_token"], auth["refresh_token"]
        )
        sessions = self.auth_svc.get_user_sessions(auth["user_id"])
        self.assertIsInstance(sessions, list)
        self.assertGreater(len(sessions), 0)

    def test_enable_mfa_returns_secret(self):
        email = f"mfa_{id(self)}@example.com"
        self.auth_svc.register_user({"email": email, "password": "Strong123!"})
        auth = self.auth_svc.authenticate_user(email, "Strong123!")
        result = self.auth_svc.enable_mfa(auth["user_id"])
        self.assertTrue(result["success"])
        self.assertIn("secret", result)

    def test_disable_mfa(self):
        email = f"dmfa_{id(self)}@example.com"
        self.auth_svc.register_user({"email": email, "password": "Strong123!"})
        auth = self.auth_svc.authenticate_user(email, "Strong123!")
        result = self.auth_svc.disable_mfa(auth["user_id"])
        self.assertTrue(result["success"])

    def test_rate_limiting_locks_account(self):
        email = f"rl_{id(self)}@example.com"
        self.auth_svc.register_user({"email": email, "password": "Strong123!"})
        for _ in range(6):
            self.auth_svc.authenticate_user(email, "WrongPass!")
        result = self.auth_svc.authenticate_user(email, "Strong123!")
        self.assertFalse(result["success"])
        self.assertTrue(
            any(
                w in result["message"].lower()
                for w in ("lock", "temporarily", "attempt")
            )
        )


# ─────────────────────────────────────────────────────────────────────────────
# Credit Service Unit Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestCreditService(BaseTestCase):
    """Unit tests for CreditScoringService."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from services.credit_service import CreditScoringService

        cls.credit_svc = CreditScoringService(_db)

    def test_validate_score_valid(self):
        self.assertTrue(self.credit_svc._validate_score(750))
        self.assertTrue(self.credit_svc._validate_score(300))
        self.assertTrue(self.credit_svc._validate_score(850))

    def test_validate_score_invalid(self):
        self.assertFalse(self.credit_svc._validate_score(299))
        self.assertFalse(self.credit_svc._validate_score(851))
        self.assertFalse(self.credit_svc._validate_score(-100))

    def test_get_score_grade(self):
        self.assertEqual(self.credit_svc._get_score_grade(820), "Excellent")
        self.assertEqual(self.credit_svc._get_score_grade(745), "Very Good")
        self.assertEqual(self.credit_svc._get_score_grade(680), "Good")
        self.assertEqual(self.credit_svc._get_score_grade(590), "Fair")
        self.assertEqual(self.credit_svc._get_score_grade(400), "Poor")

    def test_calculate_credit_score_new_user(self):
        user = self.get_user()
        result = self.credit_svc.calculate_credit_score(user.id)
        self.assertIn("score", result)
        self.assertIsInstance(result["score"], int)
        self.assertTrue(300 <= result["score"] <= 850)

    def test_calculate_credit_score_invalid_user(self):
        result = self.credit_svc.calculate_credit_score("nonexistent-user-id")
        self.assertIn("error", result)

    def test_get_credit_score_none_for_new_user(self):
        user = self.get_user()
        # New user with no calculated score yet
        result = self.credit_svc.get_credit_score(user.id + "unique")
        self.assertIsNone(result)

    def test_get_credit_score_history(self):
        user = self.get_user()
        self.credit_svc.calculate_credit_score(user.id, force_recalculation=True)
        history = self.credit_svc.get_credit_score_history(user.id)
        self.assertIsInstance(history, list)

    def test_add_credit_event_payment(self):
        user = self.get_user()
        result = self.credit_svc.add_credit_event(
            user.id, "payment_made", {"amount": 500.0, "description": "Monthly"}
        )
        self.assertTrue(result["success"])
        self.assertIn("event_id", result)

    def test_add_credit_event_invalid_type(self):
        user = self.get_user()
        result = self.credit_svc.add_credit_event(user.id, "invalid_type", {})
        self.assertFalse(result["success"])

    def test_get_credit_factors(self):
        user = self.get_user()
        factors = self.credit_svc.get_credit_factors(user.id)
        self.assertIn("positive_factors", factors)
        self.assertIn("negative_factors", factors)

    def test_analyze_credit_trends_no_data(self):
        user = self.get_user()
        trends = self.credit_svc.analyze_credit_trends(user.id + "new")
        self.assertIn("trend_direction", trends)
        self.assertEqual(trends["trend_direction"], "insufficient_data")

    def test_get_credit_recommendations(self):
        user = self.get_user()
        recs = self.credit_svc.get_credit_recommendations(user.id)
        self.assertIsInstance(recs, list)
        self.assertGreater(len(recs), 0)
        self.assertIn("title", recs[0])
        self.assertIn("priority", recs[0])

    def test_simulate_score_impact_positive(self):
        user = self.get_user()
        self.credit_svc.calculate_credit_score(user.id, force_recalculation=True)
        result = self.credit_svc.simulate_score_impact(
            user.id, "payment_made", {"amount": 500.0}
        )
        self.assertIn("projected_score", result)
        self.assertIn("score_change", result)
        self.assertIn("current_score", result)

    def test_simulate_score_impact_negative(self):
        user = self.get_user()
        self.credit_svc.calculate_credit_score(user.id, force_recalculation=True)
        result = self.credit_svc.simulate_score_impact(
            user.id, "payment_missed", {"amount": 200.0}
        )
        self.assertLessEqual(result["score_change"], 0)

    def test_bulk_calculate_scores(self):
        users = [self.get_user() for _ in range(3)]
        user_ids = [u.id for u in users]
        result = self.credit_svc.bulk_calculate_scores(user_ids)
        self.assertIn("job_id", result)
        self.assertEqual(result["user_count"], 3)
        self.assertEqual(result["status"], "submitted")

    def test_generate_credit_report(self):
        user = self.get_user()
        self.credit_svc.calculate_credit_score(user.id, force_recalculation=True)
        report = self.credit_svc.generate_credit_report(user.id)
        self.assertIn("current_score", report)
        self.assertIn("score_history", report)
        self.assertIn("credit_factors", report)
        self.assertIn("recommendations", report)
        self.assertIn("recent_activity", report)

    def test_is_model_loaded(self):
        # Model won't be loaded in test env but method should return bool
        result = self.credit_svc.is_model_loaded()
        self.assertIsInstance(result, bool)

    def test_check_score_alerts(self):
        user = self.get_user()
        # Should not raise
        self.credit_svc._check_score_alerts(user.id, 700, 750)
        self.credit_svc._check_score_alerts(user.id, 650, 700)


# ─────────────────────────────────────────────────────────────────────────────
# Compliance Service Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestComplianceService(BaseTestCase):
    """Unit tests for ComplianceService."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from services.compliance_service import ComplianceService
        from services.compliance_service import ComplianceStatus as CS
        from services.compliance_service import RiskLevel

        cls.compliance_svc = ComplianceService(_db)
        cls.RiskLevel = RiskLevel
        cls.CS = CS

    def test_risk_level_values(self):
        self.assertEqual(self.RiskLevel.LOW.value, "low")
        self.assertEqual(self.RiskLevel.HIGH.value, "high")
        self.assertEqual(self.RiskLevel.CRITICAL.value, "critical")

    def test_compliance_status_approved(self):
        from models.audit import ComplianceStatus

        self.assertEqual(ComplianceStatus.APPROVED.value, "approved")

    def test_compliance_status_rejected(self):
        from models.audit import ComplianceStatus

        self.assertEqual(ComplianceStatus.REJECTED.value, "rejected")

    def test_kyc_verification_success(self):
        from unittest.mock import patch

        with patch.object(self.compliance_svc, "_verify_identity", return_value=True):
            result = self.compliance_svc.perform_kyc_verification(
                1, {"first_name": "John"}
            )
        self.assertTrue(result["success"])
        self.assertIn("verification_id", result)

    def test_kyc_verification_failure(self):
        from unittest.mock import patch

        with patch.object(self.compliance_svc, "_verify_identity", return_value=False):
            result = self.compliance_svc.perform_kyc_verification(
                1, {"first_name": "John"}
            )
        self.assertFalse(result["success"])
        self.assertIn("reason", result)

    def test_aml_screening_low_risk(self):
        result = self.compliance_svc.perform_aml_screening(1, {"amount": 100})
        self.assertTrue(result["success"])
        self.assertEqual(result["risk_level"], self.RiskLevel.LOW.value)

    def test_aml_screening_high_risk(self):
        result = self.compliance_svc.perform_aml_screening(1, {"amount": 50000})
        self.assertTrue(result["success"])
        self.assertIn(
            result["risk_level"],
            (self.RiskLevel.HIGH.value, self.RiskLevel.CRITICAL.value),
        )

    def test_generate_compliance_report(self):
        report = self.compliance_svc.generate_compliance_report()
        self.assertTrue(report["success"])
        self.assertIn("total_records", report)
        self.assertIn("compliance_rate", report)

    def test_kyc_requirements_structure(self):
        self.assertIn("basic", self.compliance_svc.kyc_requirements)
        self.assertIn("enhanced", self.compliance_svc.kyc_requirements)

    def test_calculate_risk_score(self):
        score = self.compliance_svc._calculate_risk_score("user1", {"amount": 100})
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    def test_update_compliance_status_invalid_id(self):
        result = self.compliance_svc.update_compliance_status("bad-id", "approved")
        self.assertFalse(result["success"])


# ─────────────────────────────────────────────────────────────────────────────
# Model Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestModels(BaseTestCase):
    """Unit tests for database models."""

    def test_user_set_and_check_password(self):
        user = self.get_user()
        user.set_password("NewPass456!")
        self.assertTrue(user.check_password("NewPass456!"))
        self.assertFalse(user.check_password("WrongPass"))

    def test_user_is_locked_false(self):
        user = self.get_user()
        self.assertFalse(user.is_locked())

    def test_user_lock_and_unlock(self):
        user = self.get_user()
        user.lock_account(30)
        self.assertTrue(user.is_locked())
        user.unlock_account()
        self.assertFalse(user.is_locked())

    def test_user_to_dict(self):
        user = self.get_user()
        d = user.to_dict()
        self.assertIn("id", d)
        self.assertIn("email", d)
        self.assertNotIn("password_hash", d)

    def test_user_profile_full_name(self):
        user = self.get_user()
        self.assertEqual(user.profile.get_full_name(), "John Doe")

    def test_credit_score_is_valid(self):
        score = self.get_credit_score()
        score.valid_until = datetime(2099, 1, 1, tzinfo=timezone.utc)
        self.assertTrue(score.is_valid())

    def test_credit_score_is_expired(self):
        score = self.get_credit_score()
        score.expires_at = datetime(2000, 1, 1, tzinfo=timezone.utc)
        self.assertTrue(score.is_expired())

    def test_credit_score_factors(self):
        score = self.get_credit_score()
        self.assertIsInstance(score.get_factors_positive(), list)
        self.assertIn("payment_history", score.get_factors_positive())

    def test_loan_application_number(self):
        from models.loan import LoanApplication

        n1 = LoanApplication.generate_application_number()
        n2 = LoanApplication.generate_application_number()
        self.assertTrue(n1.startswith("APP"))
        self.assertNotEqual(n1, n2)

    def test_loan_application_to_dict(self):
        loan = self.get_loan()
        d = loan.to_dict()
        self.assertIn("loan_type", d)
        self.assertIn("requested_amount", d)
        self.assertIn("status", d)

    def test_audit_log_creation(self):
        from models.audit import AuditEventType, AuditLog, AuditSeverity

        user = self.get_user()
        log = AuditLog(
            event_type=AuditEventType.USER_LOGIN,
            event_category="auth",
            event_description="Test login",
            severity=AuditSeverity.LOW,
            user_id=user.id,
        )
        self.db.session.add(log)
        self.db.session.commit()
        self.assertIsNotNone(log.id)

    def test_compliance_record_creation(self):
        from models.audit import ComplianceRecord, ComplianceStatus, ComplianceType

        user = self.get_user()
        record = ComplianceRecord(
            compliance_type=ComplianceType.KYC,
            regulation_name="KYC Basic",
            requirement_description="Identity verification",
            entity_type="user",
            entity_id=user.id,
            status=ComplianceStatus.COMPLIANT,
        )
        self.db.session.add(record)
        self.db.session.commit()
        self.assertIsNotNone(record.id)

    def test_credit_history_event_data(self):
        from models.credit import CreditEventType, CreditHistory

        user = self.get_user()
        event = CreditHistory(
            user_id=user.id,
            event_type=CreditEventType.PAYMENT_MADE,
            event_date=datetime.now(timezone.utc),
        )
        event.set_event_data({"amount": 500})
        self.db.session.add(event)
        self.db.session.commit()
        self.assertEqual(event.get_event_data()["amount"], 500)


# ─────────────────────────────────────────────────────────────────────────────
# MFA Service Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestMFAService(BaseTestCase):
    """Unit tests for MFAService."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from unittest.mock import Mock

        from services.mfa_service import MFAMethod, MFAService

        mock_db = Mock()
        mock_db.commit = Mock()
        mock_db.add = Mock()
        cls.mfa_svc = MFAService(mock_db)
        cls.MFAMethod = MFAMethod

    def test_mfa_method_constants(self):
        self.assertEqual(self.MFAMethod.TOTP, "totp")
        self.assertEqual(self.MFAMethod.SMS, "sms")

    def test_generate_backup_codes(self):
        codes = self.mfa_svc._generate_backup_codes(10)
        self.assertEqual(len(codes), 10)
        self.assertEqual(len(set(codes)), 10)

    def test_totp_is_time_based(self):
        import pyotp

        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        code = totp.now()
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())

    def test_verify_totp_valid(self):
        from unittest.mock import Mock, patch

        import pyotp

        secret = pyotp.random_base32()
        mock_user = Mock()
        mock_user.mfa_secret = secret
        mock_user.totp_secret = secret
        mock_user.mfa_enabled = True
        totp = pyotp.TOTP(secret)
        with patch("services.mfa_service.db") as mock_db:
            mock_db.session.get.return_value = mock_user
            result = self.mfa_svc.verify_totp(1, totp.now())
        self.assertTrue(result["valid"])

    def test_verify_totp_invalid(self):
        from unittest.mock import Mock, patch

        import pyotp

        secret = pyotp.random_base32()
        mock_user = Mock()
        mock_user.mfa_secret = secret
        mock_user.totp_secret = secret
        with patch("services.mfa_service.db") as mock_db:
            mock_db.session.get.return_value = mock_user
            result = self.mfa_svc.verify_totp(1, "000000")
        self.assertFalse(result["valid"])

    def test_verify_backup_code(self):
        import json as _json
        from unittest.mock import Mock, patch

        mock_user = Mock()
        mock_user.backup_codes = _json.dumps(["ABCD1234", "EFGH5678"])
        with patch("services.mfa_service.db") as mock_db:
            mock_db.session.get.return_value = mock_user
            result = self.mfa_svc.verify_backup_code(1, "ABCD1234")
        self.assertTrue(result["valid"])

    def test_verify_backup_code_invalid(self):
        import json as _json
        from unittest.mock import Mock, patch

        mock_user = Mock()
        mock_user.backup_codes = _json.dumps(["ABCD1234"])
        with patch("services.mfa_service.db") as mock_db:
            mock_db.session.get.return_value = mock_user
            result = self.mfa_svc.verify_backup_code(1, "INVALID0")
        self.assertFalse(result["valid"])

    def test_setup_totp_user_not_found(self):
        from unittest.mock import patch

        with patch("services.mfa_service.db") as mock_db:
            mock_db.session.get.return_value = None
            result = self.mfa_svc.setup_totp(999)
        self.assertFalse(result["success"])
        self.assertIn("not found", result["message"].lower())


# ─────────────────────────────────────────────────────────────────────────────
# Main runner
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 70)
    print("BlockScore Backend Test Suite")
    print("=" * 70)
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in [
        TestAPIEndpoints,
        TestAuthService,
        TestCreditService,
        TestComplianceService,
        TestModels,
        TestMFAService,
    ]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
