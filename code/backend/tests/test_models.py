"""
Unit tests for all models - tests for fields, methods, and serialization
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
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import compat_stubs  # noqa

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestUserModel:
    """Tests for the User model"""

    def test_user_set_password(self, db: Any, sample_user: Any) -> Any:
        """Test password hashing"""
        old_hash = sample_user.password_hash
        sample_user.set_password("NewPassword99!")
        assert sample_user.password_hash != old_hash
        assert sample_user.check_password("NewPassword99!")
        assert not sample_user.check_password("WrongPassword")

    def test_user_is_locked_false(self, db: Any, sample_user: Any) -> Any:
        """Test is_locked returns False when no lockout"""
        assert sample_user.is_locked() is False

    def test_user_is_locked_true(self, db: Any, sample_user: Any) -> Any:
        """Test is_locked returns True when locked"""
        sample_user.lock_account(30)
        db.session.commit()
        assert sample_user.is_locked() is True

    def test_user_lock_expires(self, db: Any, sample_user: Any) -> Any:
        """Test lock expires correctly"""
        sample_user.locked_until = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.session.commit()
        assert sample_user.is_locked() is False

    def test_user_unlock(self, db: Any, sample_user: Any) -> Any:
        """Test unlocking a user"""
        sample_user.lock_account(30)
        sample_user.unlock_account()
        db.session.commit()
        assert sample_user.is_locked() is False
        assert sample_user.failed_login_attempts == 0

    def test_user_to_dict(self, db: Any, sample_user: Any) -> Any:
        """Test user to_dict serialization"""
        d = sample_user.to_dict()
        assert "id" in d
        assert "email" in d
        assert "status" in d
        assert "is_active" in d
        assert "email_verified" in d
        assert "password_hash" not in d

    def test_user_profile_full_name(self, db: Any, sample_user: Any) -> Any:
        """Test profile full name"""
        assert sample_user.profile.get_full_name() == "John Doe"

    def test_user_profile_to_dict(self, db: Any, sample_user: Any) -> Any:
        """Test profile to_dict"""
        d = sample_user.profile.to_dict()
        assert "first_name" in d
        assert "last_name" in d
        assert "address" in d
        assert "kyc_status" in d


class TestCreditScoreModel:
    """Tests for CreditScore model"""

    def test_credit_score_is_valid(self, db: Any, sample_credit_score: Any) -> Any:
        """Test is_valid with future valid_until"""
        sample_credit_score.valid_until = datetime.now(timezone.utc) + timedelta(
            days=30
        )
        assert sample_credit_score.is_valid() is True

    def test_credit_score_is_expired(self, db: Any, sample_credit_score: Any) -> Any:
        """Test is_expired with past expires_at"""
        sample_credit_score.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        assert sample_credit_score.is_expired() is True

    def test_credit_score_not_expired(self, db: Any, sample_credit_score: Any) -> Any:
        """Test is_expired with future expires_at"""
        sample_credit_score.expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        assert sample_credit_score.is_expired() is False

    def test_credit_score_factors_positive(
        self, db: Any, sample_credit_score: Any
    ) -> Any:
        """Test factors_positive JSON field"""
        factors = sample_credit_score.get_factors_positive()
        assert isinstance(factors, list)
        assert "payment_history" in factors

    def test_credit_score_factors_negative(
        self, db: Any, sample_credit_score: Any
    ) -> Any:
        """Test factors_negative JSON field"""
        factors = sample_credit_score.get_factors_negative()
        assert isinstance(factors, list)
        assert "credit_age" in factors

    def test_credit_score_breakdown(self, db: Any, sample_credit_score: Any) -> Any:
        """Test get_score_breakdown"""
        breakdown = sample_credit_score.get_score_breakdown()
        assert "total_score" in breakdown
        assert breakdown["total_score"] == 750

    def test_credit_score_to_dict(self, db: Any, sample_credit_score: Any) -> Any:
        """Test credit score serialization"""
        d = sample_credit_score.to_dict()
        assert "id" in d
        assert "score" in d
        assert "status" in d
        assert "is_valid" in d
        assert "is_expired" in d


class TestCreditHistoryModel:
    """Tests for CreditHistory model"""

    def test_create_credit_history(self, db: Any, sample_user: Any) -> Any:
        """Test creating credit history event"""
        from models.credit import CreditEventType, CreditHistory

        event = CreditHistory(
            user_id=sample_user.id,
            event_type=CreditEventType.PAYMENT_MADE,
            event_title="Test Payment",
            amount=Decimal("500.00"),
            event_date=datetime.now(timezone.utc),
        )
        db.session.add(event)
        db.session.commit()
        assert event.id is not None
        assert event.amount == Decimal("500.00")

    def test_credit_history_event_data(self, db: Any, sample_user: Any) -> Any:
        """Test event_data JSON field"""
        from models.credit import CreditEventType, CreditHistory

        event = CreditHistory(
            user_id=sample_user.id,
            event_type=CreditEventType.PAYMENT_MADE,
            event_date=datetime.now(timezone.utc),
        )
        event.set_event_data({"amount": 100, "description": "test"})
        db.session.add(event)
        db.session.commit()
        data = event.get_event_data()
        assert data["amount"] == 100

    def test_credit_history_to_dict(self, db: Any, sample_user: Any) -> Any:
        """Test history to_dict"""
        from models.credit import CreditEventType, CreditHistory

        event = CreditHistory(
            user_id=sample_user.id,
            event_type=CreditEventType.PAYMENT_MISSED,
            event_date=datetime.now(timezone.utc),
            impact_score=-10,
        )
        db.session.add(event)
        db.session.commit()
        d = event.to_dict()
        assert "event_type" in d
        assert d["event_type"] == "payment_missed"
        assert d["impact_score"] == -10


class TestLoanApplicationModel:
    """Tests for LoanApplication model"""

    def test_loan_application_creation(
        self, db: Any, sample_loan_application: Any
    ) -> Any:
        """Test loan application is created correctly"""
        assert sample_loan_application.id is not None
        assert sample_loan_application.application_number is not None
        assert sample_loan_application.loan_type.value == "personal"

    def test_generate_application_number(self) -> Any:
        """Test application number generation"""
        from models.loan import LoanApplication

        num1 = LoanApplication.generate_application_number()
        num2 = LoanApplication.generate_application_number()
        assert num1.startswith("APP")
        assert num1 != num2

    def test_loan_application_to_dict(
        self, db: Any, sample_loan_application: Any
    ) -> Any:
        """Test loan application serialization"""
        d = sample_loan_application.to_dict()
        assert "id" in d
        assert "loan_type" in d
        assert "requested_amount" in d
        assert "status" in d

    def test_loan_application_data_json(
        self, db: Any, sample_loan_application: Any
    ) -> Any:
        """Test application_data JSON field"""
        sample_loan_application.set_application_data({"notes": "test loan"})
        db.session.commit()
        data = sample_loan_application.get_application_data()
        assert data["notes"] == "test loan"

    def test_loan_is_not_expired(self, db: Any, sample_loan_application: Any) -> Any:
        """Test is_expired returns False when no expires_at"""
        assert sample_loan_application.is_expired() is False


class TestAuditLogModel:
    """Tests for AuditLog model"""

    def test_create_audit_log(self, db: Any, sample_user: Any) -> Any:
        """Test creating audit log entry"""
        from models.audit import AuditEventType, AuditLog, AuditSeverity

        log = AuditLog(
            event_type=AuditEventType.USER_LOGIN,
            event_category="auth",
            event_description="User logged in",
            severity=AuditSeverity.LOW,
            user_id=sample_user.id,
            ip_address="127.0.0.1",
        )
        db.session.add(log)
        db.session.commit()
        assert log.id is not None
        assert log.event_type == AuditEventType.USER_LOGIN

    def test_audit_log_event_data(self, db: Any, sample_user: Any) -> Any:
        """Test event_data JSON on audit log"""
        from models.audit import AuditEventType, AuditLog

        log = AuditLog(
            event_type=AuditEventType.DATA_ACCESS,
            event_category="data",
            event_description="Data accessed",
            user_id=sample_user.id,
        )
        log.set_event_data({"resource": "credit_score"})
        db.session.add(log)
        db.session.commit()
        assert log.get_event_data()["resource"] == "credit_score"

    def test_audit_log_to_dict(self, db: Any, sample_user: Any) -> Any:
        """Test audit log serialization"""
        from models.audit import AuditEventType, AuditLog

        log = AuditLog(
            event_type=AuditEventType.USER_REGISTRATION,
            event_category="auth",
            event_description="Registered",
            user_id=sample_user.id,
        )
        db.session.add(log)
        db.session.commit()
        d = log.to_dict()
        assert "event_type" in d
        assert "event_timestamp" in d
        assert "user_id" in d


class TestComplianceRecordModel:
    """Tests for ComplianceRecord model"""

    def test_create_compliance_record(self, db: Any, sample_user: Any) -> Any:
        """Test creating a compliance record"""
        from models.audit import ComplianceRecord, ComplianceStatus, ComplianceType

        record = ComplianceRecord(
            compliance_type=ComplianceType.KYC,
            regulation_name="KYC Basic",
            requirement_description="Identity verification",
            entity_type="user",
            entity_id=sample_user.id,
            status=ComplianceStatus.COMPLIANT,
            compliance_score=95.0,
        )
        db.session.add(record)
        db.session.commit()
        assert record.id is not None

    def test_compliance_record_is_valid(self, db: Any, sample_user: Any) -> Any:
        """Test compliance record validity"""
        from models.audit import ComplianceRecord, ComplianceStatus, ComplianceType

        record = ComplianceRecord(
            compliance_type=ComplianceType.AML,
            regulation_name="AML",
            requirement_description="AML check",
            entity_type="user",
            entity_id=sample_user.id,
            status=ComplianceStatus.COMPLIANT,
            valid_until=datetime.now(timezone.utc) + timedelta(days=90),
        )
        db.session.add(record)
        db.session.commit()
        assert record.is_valid() is True

    def test_compliance_record_to_dict(self, db: Any, sample_user: Any) -> Any:
        """Test compliance record serialization"""
        from models.audit import ComplianceRecord, ComplianceStatus, ComplianceType

        record = ComplianceRecord(
            compliance_type=ComplianceType.KYC,
            regulation_name="KYC",
            requirement_description="KYC check",
            entity_type="user",
            entity_id=sample_user.id,
            status=ComplianceStatus.PENDING_REVIEW,
        )
        db.session.add(record)
        db.session.commit()
        d = record.to_dict()
        assert "status" in d
        assert d["status"] == "pending_review"
