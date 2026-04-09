"""
Comprehensive Test Suite for Compliance Service
Tests for KYC/AML, audit trails, and regulatory compliance features
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
from unittest.mock import patch

import compat_stubs  # noqa
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.audit import ComplianceStatus
from services.compliance_service import ComplianceService, RiskLevel


class TestComplianceService:
    """Test suite for ComplianceService"""

    @pytest.fixture
    def compliance(self, db: Any) -> Any:
        """Create a ComplianceService using the test Flask db"""
        from extensions import db as ext_db

        return ComplianceService(ext_db)

    @pytest.fixture
    def sample_user_data(self) -> Any:
        return {
            "user_id": 1,
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "phone": "+1234567890",
            "date_of_birth": "1990-01-01",
            "address": {
                "street": "123 Main St",
                "city": "New York",
                "state": "NY",
                "zip_code": "10001",
                "country": "US",
            },
        }

    def test_kyc_verification_success(
        self, compliance: Any, sample_user_data: Any
    ) -> Any:
        """Test successful KYC verification"""
        with patch.object(compliance, "_verify_identity", return_value=True):
            result = compliance.perform_kyc_verification(
                sample_user_data["user_id"], sample_user_data
            )
        assert result["success"] is True
        assert result["status"] == ComplianceStatus.APPROVED.value
        assert "verification_id" in result

    def test_kyc_verification_failure(
        self, compliance: Any, sample_user_data: Any
    ) -> Any:
        """Test KYC verification failure"""
        with patch.object(compliance, "_verify_identity", return_value=False):
            result = compliance.perform_kyc_verification(
                sample_user_data["user_id"], sample_user_data
            )
        assert result["success"] is False
        assert result["status"] == ComplianceStatus.REJECTED.value
        assert "reason" in result

    def test_kyc_verification_returns_id(
        self, compliance: Any, sample_user_data: Any
    ) -> Any:
        """Test KYC verification always returns a verification_id"""
        with patch.object(compliance, "_verify_identity", return_value=True):
            result = compliance.perform_kyc_verification(
                sample_user_data["user_id"], sample_user_data
            )
        assert "verification_id" in result
        assert len(result["verification_id"]) > 0

    def test_aml_screening_low_risk(
        self, compliance: Any, sample_user_data: Any
    ) -> Any:
        """Test AML screening with low-risk transaction"""
        result = compliance.perform_aml_screening(
            sample_user_data["user_id"], {"amount": 100}
        )
        assert result["success"] is True
        assert result["risk_level"] == RiskLevel.LOW.value

    def test_aml_screening_high_risk(
        self, compliance: Any, sample_user_data: Any
    ) -> Any:
        """Test AML screening with high-risk transaction amount"""
        result = compliance.perform_aml_screening(
            sample_user_data["user_id"], {"amount": 15000}
        )
        assert result["success"] is True
        assert result["risk_level"] in (RiskLevel.HIGH.value, RiskLevel.CRITICAL.value)

    def test_aml_screening_returns_risk_score(
        self, compliance: Any, sample_user_data: Any
    ) -> Any:
        """Test AML screening returns a numeric risk score"""
        result = compliance.perform_aml_screening(
            sample_user_data["user_id"], {"amount": 500}
        )
        assert "risk_score" in result
        assert isinstance(result["risk_score"], (int, float))

    def test_risk_level_enum_values(self) -> Any:
        """Test RiskLevel enum has expected values"""
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.CRITICAL.value == "critical"

    def test_compliance_status_approved(self) -> Any:
        """Test ComplianceStatus.APPROVED exists"""
        assert ComplianceStatus.APPROVED.value == "approved"

    def test_compliance_status_rejected(self) -> Any:
        """Test ComplianceStatus.REJECTED exists"""
        assert ComplianceStatus.REJECTED.value == "rejected"

    def test_compliance_status_flagged(self) -> Any:
        """Test ComplianceStatus.FLAGGED exists"""
        assert ComplianceStatus.FLAGGED.value == "flagged"

    def test_transaction_monitoring_normal(self, compliance: Any) -> Any:
        """Test transaction monitoring for normal amounts"""
        result = compliance._monitor_transaction_patterns("user_1", None)
        assert "suspicious_patterns" in result
        assert result["suspicious_patterns"] is False

    def test_transaction_monitoring_large(self, compliance: Any) -> Any:
        """Test transaction monitoring flags large amounts"""
        from decimal import Decimal

        result = compliance._monitor_transaction_patterns("user_1", Decimal("15000"))
        assert "exceeds_threshold" in result
        assert result["exceeds_threshold"] is True

    def test_calculate_risk_score_low(self, compliance: Any) -> Any:
        """Test risk score calculation for small amounts"""
        score = compliance._calculate_risk_score("user_1", {"amount": 100})
        assert isinstance(score, float)
        assert score < 60

    def test_calculate_risk_score_high(self, compliance: Any) -> Any:
        """Test risk score calculation for large amounts"""
        score = compliance._calculate_risk_score("user_1", {"amount": 50000})
        assert score >= 60

    def test_compliance_service_init(self, db: Any) -> Any:
        """Test ComplianceService initializes correctly"""
        from extensions import db as ext_db

        svc = ComplianceService(ext_db)
        assert svc.aml_thresholds is not None
        assert "transaction_reporting" in svc.aml_thresholds

    def test_determine_aml_status_compliant(self, compliance: Any) -> Any:
        """Test AML status determination for low risk"""
        status = compliance._determine_aml_status(10.0)
        assert status == ComplianceStatus.COMPLIANT

    def test_determine_aml_status_non_compliant(self, compliance: Any) -> Any:
        """Test AML status determination for very high risk"""
        status = compliance._determine_aml_status(90.0)
        assert status == ComplianceStatus.NON_COMPLIANT

    def test_update_compliance_status(
        self, compliance: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test updating compliance record status"""
        from models.audit import ComplianceRecord, ComplianceStatus, ComplianceType

        record = ComplianceRecord(
            compliance_type=ComplianceType.KYC,
            regulation_name="KYC",
            requirement_description="Test",
            entity_type="user",
            entity_id=sample_user.id,
            status=ComplianceStatus.PENDING_REVIEW,
        )
        db.session.add(record)
        db.session.commit()

        result = compliance.update_compliance_status(
            record.id,
            ComplianceStatus.APPROVED.value,
            notes="Manually approved",
        )
        assert result["success"] is True
        assert result["status"] == ComplianceStatus.APPROVED.value

    def test_update_compliance_status_invalid_id(self, compliance: Any) -> Any:
        """Test updating nonexistent compliance record"""
        result = compliance.update_compliance_status(
            "nonexistent-id-xyz", ComplianceStatus.APPROVED.value
        )
        assert result["success"] is False

    def test_update_compliance_invalid_status(
        self, compliance: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test updating with invalid status value"""
        from models.audit import ComplianceRecord, ComplianceStatus, ComplianceType

        record = ComplianceRecord(
            compliance_type=ComplianceType.AML,
            regulation_name="AML",
            requirement_description="Test",
            entity_type="user",
            entity_id=sample_user.id,
            status=ComplianceStatus.PENDING_REVIEW,
        )
        db.session.add(record)
        db.session.commit()

        result = compliance.update_compliance_status(record.id, "invalid_status_xyz")
        assert result["success"] is False

    def test_generate_compliance_report(self, compliance: Any, db: Any) -> Any:
        """Test compliance report generation"""
        report = compliance.generate_compliance_report()
        assert "success" in report
        assert report["success"] is True
        assert "total_records" in report
        assert "compliance_rate" in report

    def test_kyc_requirements_structure(self, compliance: Any) -> Any:
        """Test KYC requirements are properly structured"""
        assert "basic" in compliance.kyc_requirements
        assert "enhanced" in compliance.kyc_requirements
        assert "premium" in compliance.kyc_requirements
        assert isinstance(compliance.kyc_requirements["basic"], list)

    def test_sanctions_patterns_present(self, compliance: Any) -> Any:
        """Test AML sanctions patterns are configured"""
        assert len(compliance.sanctions_patterns) > 0

    def test_risk_weights_sum(self, compliance: Any) -> Any:
        """Test risk weights are properly defined"""
        total = sum(compliance.risk_weights.values())
        assert abs(total - 1.0) < 0.01

    def test_full_onboarding_flow(self, compliance: Any, sample_user_data: Any) -> Any:
        """Test full KYC onboarding flow"""
        with patch.object(compliance, "_verify_identity", return_value=True):
            kyc_result = compliance.perform_kyc_verification(
                sample_user_data["user_id"], sample_user_data
            )
        assert kyc_result["success"] is True

        aml_result = compliance.perform_aml_screening(
            sample_user_data["user_id"], {"amount": 1000}
        )
        assert aml_result["success"] is True

    def test_error_handling_invalid_user(self, compliance: Any) -> Any:
        """Test error handling for invalid inputs"""
        result = compliance.perform_aml_screening(None, {})
        assert "success" in result

    def test_compliance_configuration_validation(self, compliance: Any) -> Any:
        """Test compliance configuration is valid"""
        assert compliance.aml_thresholds["transaction_reporting"] > 0
        assert compliance.aml_thresholds["suspicious_activity"] > 0
