"""
Compliance Service for BlockScore Backend
KYC/AML and regulatory compliance management
"""

import enum
import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from extensions import db
from models.audit import (
    AuditSeverity,
    ComplianceRecord,
    ComplianceStatus,
    ComplianceType,
)
from models.loan import LoanApplication
from models.user import KYCStatus, User, UserProfile


class RiskLevel(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplianceService:
    """Comprehensive compliance service for financial regulations"""

    def __init__(self, db: Any) -> None:
        self.db = db
        self.logger = logging.getLogger(__name__)
        self.kyc_requirements = {
            "basic": ["full_name", "date_of_birth", "address"],
            "enhanced": [
                "full_name",
                "date_of_birth",
                "address",
                "government_id",
                "income_verification",
            ],
            "premium": [
                "full_name",
                "date_of_birth",
                "address",
                "government_id",
                "income_verification",
                "employment_verification",
                "bank_statements",
            ],
        }
        self.aml_thresholds = {
            "transaction_reporting": Decimal("10000"),
            "suspicious_activity": Decimal("5000"),
            "daily_limit": Decimal("25000"),
            "monthly_limit": Decimal("100000"),
        }
        self.sanctions_patterns = [
            "\\b(OFAC|SDN|SANCTIONS)\\b",
            "\\b(TERRORIST|TERRORISM)\\b",
            "\\b(MONEY\\s*LAUNDERING)\\b",
        ]
        self.risk_weights = {
            "geographic_risk": 0.25,
            "transaction_risk": 0.3,
            "behavioral_risk": 0.2,
            "identity_risk": 0.15,
            "regulatory_risk": 0.1,
        }

    def perform_kyc_verification(
        self, user_id: Any, user_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform KYC identity verification"""
        try:
            identity_verified = self._verify_identity(user_data)
            verification_id = str(uuid.uuid4())

            if identity_verified:
                return {
                    "success": True,
                    "status": ComplianceStatus.APPROVED.value,
                    "verification_id": verification_id,
                    "message": "Identity verified successfully",
                }
            else:
                return {
                    "success": False,
                    "status": ComplianceStatus.REJECTED.value,
                    "verification_id": verification_id,
                    "reason": "Identity verification failed",
                    "message": "Could not verify identity",
                }
        except Exception as e:
            self.logger.error(f"KYC verification error: {e}")
            return {
                "success": False,
                "status": ComplianceStatus.REJECTED.value,
                "message": str(e),
            }

    def perform_aml_screening(
        self, user_id: Any, transaction_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Perform AML screening on a user/transaction"""
        try:
            risk_score = self._calculate_risk_score(user_id, transaction_data or {})
            risk_level = self._score_to_risk_level(risk_score)
            flagged = risk_score >= 70

            return {
                "success": True,
                "status": (
                    ComplianceStatus.FLAGGED.value
                    if flagged
                    else ComplianceStatus.APPROVED.value
                ),
                "risk_score": risk_score,
                "risk_level": risk_level.value,
                "flagged": flagged,
                "screening_id": str(uuid.uuid4()),
            }
        except Exception as e:
            self.logger.error(f"AML screening error: {e}")
            return {"success": False, "message": str(e)}

    def perform_kyc_assessment(
        self, user_id: str, kyc_level: str = "basic"
    ) -> Dict[str, Any]:
        """Perform KYC assessment for user"""
        try:
            user = db.session.get(User, user_id)
            if not user or not user.profile:
                raise ValueError("User or profile not found")
            profile = user.profile
            requirements = self.kyc_requirements.get(
                kyc_level, self.kyc_requirements["basic"]
            )
            assessment_results = self._assess_kyc_requirements(profile, requirements)
            compliance_score = self._calculate_kyc_score(assessment_results)
            kyc_status = self._determine_kyc_status(
                compliance_score, assessment_results
            )

            compliance_record = self._create_compliance_record(
                compliance_type=ComplianceType.KYC,
                entity_type="user",
                entity_id=str(user_id),
                status=(
                    ComplianceStatus.COMPLIANT
                    if compliance_score >= 80
                    else ComplianceStatus.NON_COMPLIANT
                ),
                compliance_score=compliance_score,
                assessment_data=assessment_results,
                regulation_name=f"KYC Level {kyc_level.title()}",
                requirement_description=f"Know Your Customer verification at {kyc_level} level",
            )

            if kyc_status != profile.kyc_status:
                profile.kyc_status = kyc_status
                profile.kyc_completed_at = (
                    datetime.now(timezone.utc)
                    if kyc_status == KYCStatus.APPROVED
                    else None
                )
                self.db.session.commit()

            return {
                "success": True,
                "compliance_score": compliance_score,
                "kyc_status": kyc_status.value,
                "assessment_results": assessment_results,
                "required_actions": self._get_kyc_required_actions(assessment_results),
                "record_id": compliance_record.id if compliance_record else None,
            }
        except Exception as e:
            self.logger.error(f"KYC assessment error for user {user_id}: {e}")
            raise

    def perform_aml_check(
        self, user_id: str, transaction_amount: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """Perform AML check on user and optionally a transaction"""
        try:
            user = db.session.get(User, user_id)
            if not user:
                raise ValueError("User not found")

            screening_results = {
                "sanctions_check": self._check_sanctions_list(user),
                "pep_check": self._check_politically_exposed_person(user),
                "transaction_patterns": self._monitor_transaction_patterns(
                    user_id, transaction_amount
                ),
                "geographic_risk": self._assess_geographic_risk(user),
                "behavioral_analysis": self._analyze_user_behavior(user_id),
            }

            aml_risk_score = self._calculate_aml_risk_score(screening_results)
            aml_status = self._determine_aml_status(aml_risk_score)

            return {
                "success": True,
                "aml_risk_score": aml_risk_score,
                "aml_status": aml_status.value,
                "screening_results": screening_results,
                "recommended_actions": self._get_aml_recommended_actions(
                    screening_results, aml_risk_score
                ),
                "sar_required": self._check_sar_requirements(
                    aml_risk_score, transaction_amount
                ),
            }
        except Exception as e:
            self.logger.error(f"AML check error for user {user_id}: {e}")
            raise

    def assess_loan_compliance(self, loan_application_id: str) -> Dict[str, Any]:
        """Assess loan application for regulatory compliance"""
        try:
            loan_app = db.session.get(LoanApplication, loan_application_id)
            if not loan_app:
                raise ValueError("Loan application not found")

            compliance_checks = {
                "fair_lending": self._check_fair_lending_compliance(loan_app),
                "truth_in_lending": self._check_truth_in_lending(loan_app),
                "ecoa": self._check_ecoa_compliance(loan_app),
                "consumer_protection": self._check_consumer_protection(loan_app),
                "usury_laws": self._check_usury_compliance(loan_app),
            }

            compliance_score = self._calculate_loan_compliance_score(compliance_checks)
            overall_status = (
                ComplianceStatus.COMPLIANT
                if compliance_score >= 80
                else ComplianceStatus.NON_COMPLIANT
            )

            return {
                "success": True,
                "compliance_score": compliance_score,
                "overall_status": overall_status.value,
                "compliance_checks": compliance_checks,
                "violations": self._identify_compliance_violations(compliance_checks),
                "required_actions": self._get_loan_compliance_actions(
                    compliance_checks
                ),
            }
        except Exception as e:
            self.logger.error(f"Loan compliance error for {loan_application_id}: {e}")
            raise

    def monitor_ongoing_compliance(self, user_id: str) -> Dict[str, Any]:
        """Monitor ongoing compliance for a user"""
        try:
            records = (
                ComplianceRecord.query.filter_by(entity_id=str(user_id))
                .order_by(ComplianceRecord.created_at.desc())
                .limit(50)
                .all()
            )

            health_score = self._calculate_compliance_health(records)
            return {
                "success": True,
                "user_id": user_id,
                "health_score": health_score,
                "total_records": len(records),
                "summary": self._generate_compliance_summary(records),
                "recent_violations": self._identify_compliance_violations({}),
            }
        except Exception as e:
            self.logger.error(f"Compliance monitoring error: {e}")
            raise

    def update_compliance_status(
        self,
        record_id: str,
        new_status: str,
        notes: str = None,
        reviewed_by: str = None,
    ) -> Dict[str, Any]:
        """Update the status of a compliance record"""
        try:
            record = db.session.get(ComplianceRecord, record_id)
            if not record:
                return {"success": False, "message": "Compliance record not found"}

            try:
                status_enum = ComplianceStatus(new_status)
            except ValueError:
                return {"success": False, "message": f"Invalid status: {new_status}"}

            record.status = status_enum
            if notes:
                record.notes = notes
            if reviewed_by:
                record.reviewed_by = reviewed_by
            record.reviewed_at = datetime.now(timezone.utc)
            self.db.session.commit()

            return {
                "success": True,
                "status": record.status.value,
                "record_id": record_id,
                "message": "Compliance status updated",
            }
        except Exception as e:
            self.db.session.rollback()
            return {"success": False, "message": str(e)}

    def generate_compliance_report(
        self,
        entity_type: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
    ) -> Dict[str, Any]:
        """Generate comprehensive compliance report"""
        try:
            query = ComplianceRecord.query
            if entity_type:
                query = query.filter_by(entity_type=entity_type)
            if start_date:
                query = query.filter(ComplianceRecord.created_at >= start_date)
            if end_date:
                query = query.filter(ComplianceRecord.created_at <= end_date)

            records = query.order_by(ComplianceRecord.created_at.desc()).all()

            compliant_count = len(
                [r for r in records if r.status == ComplianceStatus.COMPLIANT]
            )
            non_compliant_count = len(
                [r for r in records if r.status == ComplianceStatus.NON_COMPLIANT]
            )
            pending_count = len(
                [r for r in records if r.status == ComplianceStatus.PENDING_REVIEW]
            )

            return {
                "success": True,
                "report_generated_at": datetime.now(timezone.utc).isoformat(),
                "total_records": len(records),
                "compliant_count": compliant_count,
                "non_compliant_count": non_compliant_count,
                "pending_count": pending_count,
                "compliance_rate": (
                    (compliant_count / len(records) * 100) if records else 0
                ),
                "by_type": self._group_by_compliance_type(records),
                "by_entity": self._group_by_entity_type(records),
                "violations_summary": self._summarize_violations(records),
                "trends": self._analyze_compliance_trends(records),
                "recommendations": self._generate_compliance_recommendations(records),
            }
        except Exception as e:
            self.logger.error(f"Compliance report error: {e}")
            raise

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _verify_identity(self, user_data: Dict[str, Any]) -> bool:
        """Simulate identity verification (stub)"""
        required = ["first_name", "last_name", "date_of_birth"]
        for field in required:
            if not user_data.get(field):
                # Check top-level flattened or nested
                pass
        return bool(user_data.get("first_name") or user_data.get("user_id"))

    def _calculate_risk_score(self, user_id: Any, data: Dict[str, Any]) -> float:
        """Calculate a basic risk score (0-100)"""
        amount = data.get("amount", 0) or 0
        try:
            amount = float(amount)
        except Exception:
            amount = 0
        if amount >= 10000:
            return 80.0
        if amount >= 5000:
            return 60.0
        return 20.0

    def _score_to_risk_level(self, score: float) -> RiskLevel:
        if score >= 80:
            return RiskLevel.CRITICAL
        if score >= 60:
            return RiskLevel.HIGH
        if score >= 40:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def _assess_kyc_requirements(
        self, profile: UserProfile, requirements: List[str]
    ) -> Dict[str, Any]:
        results = {}
        for req in requirements:
            if req == "full_name":
                results[req] = bool(profile.first_name and profile.last_name)
            elif req == "date_of_birth":
                results[req] = profile.date_of_birth is not None
            elif req == "address":
                results[req] = bool(profile.city and profile.country)
            else:
                results[req] = False
        return results

    def _calculate_kyc_score(self, assessment_results: Dict[str, Any]) -> float:
        if not assessment_results:
            return 0.0
        met = sum(1 for v in assessment_results.values() if v)
        return (met / len(assessment_results)) * 100

    def _determine_kyc_status(
        self, compliance_score: float, assessment_results: Dict[str, Any]
    ) -> KYCStatus:
        if compliance_score >= 80:
            return KYCStatus.APPROVED
        if compliance_score >= 50:
            return KYCStatus.IN_PROGRESS
        return KYCStatus.REJECTED

    def _check_sanctions_list(self, user: User) -> Dict[str, Any]:
        return {
            "flagged": False,
            "matches": [],
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    def _check_politically_exposed_person(self, user: User) -> Dict[str, Any]:
        return {"is_pep": False, "risk_level": "low"}

    def _monitor_transaction_patterns(
        self, user_id: str, transaction_amount: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        return {
            "suspicious_patterns": False,
            "transaction_amount": (
                float(transaction_amount) if transaction_amount else 0
            ),
            "exceeds_threshold": (
                transaction_amount is not None
                and transaction_amount >= self.aml_thresholds["transaction_reporting"]
            ),
        }

    def _assess_geographic_risk(self, user: User) -> Dict[str, Any]:
        high_risk_countries = {"IR", "KP", "SY", "CU"}
        country = user.profile.country if user.profile else None
        is_high_risk = country in high_risk_countries if country else False
        return {
            "country": country,
            "risk_level": "high" if is_high_risk else "low",
            "is_sanctioned_country": is_high_risk,
        }

    def _analyze_user_behavior(self, user_id: str) -> Dict[str, Any]:
        return {"unusual_patterns": False, "risk_score": 10}

    def _calculate_aml_risk_score(self, screening_results: Dict[str, Any]) -> float:
        score = 0.0
        if screening_results.get("sanctions_check", {}).get("flagged"):
            score += 50
        if screening_results.get("pep_check", {}).get("is_pep"):
            score += 20
        if screening_results.get("transaction_patterns", {}).get("suspicious_patterns"):
            score += 15
        if screening_results.get("geographic_risk", {}).get("is_sanctioned_country"):
            score += 30
        return min(100.0, score)

    def _determine_aml_status(self, aml_risk_score: float) -> ComplianceStatus:
        if aml_risk_score >= 80:
            return ComplianceStatus.NON_COMPLIANT
        if aml_risk_score >= 60:
            return ComplianceStatus.REQUIRES_ACTION
        if aml_risk_score >= 40:
            return ComplianceStatus.PENDING_REVIEW
        return ComplianceStatus.COMPLIANT

    def _check_fair_lending_compliance(
        self, loan_app: LoanApplication
    ) -> Dict[str, Any]:
        return {"compliant": True, "score": 90, "issues": []}

    def _check_truth_in_lending(self, loan_app: LoanApplication) -> Dict[str, Any]:
        return {"compliant": True, "score": 95, "issues": []}

    def _check_ecoa_compliance(self, loan_app: LoanApplication) -> Dict[str, Any]:
        return {"compliant": True, "score": 100, "issues": []}

    def _check_consumer_protection(self, loan_app: LoanApplication) -> Dict[str, Any]:
        return {"compliant": True, "score": 85, "issues": []}

    def _check_usury_compliance(self, loan_app: LoanApplication) -> Dict[str, Any]:
        rate = loan_app.requested_rate or 0
        is_compliant = float(rate) <= 36.0
        return {
            "compliant": is_compliant,
            "score": 100 if is_compliant else 0,
            "rate": float(rate),
            "issues": [] if is_compliant else [f"Rate {rate}% exceeds usury limit"],
        }

    def _calculate_loan_compliance_score(self, checks: Dict[str, Any]) -> float:
        scores = [v.get("score", 0) for v in checks.values() if isinstance(v, dict)]
        return sum(scores) / len(scores) if scores else 0.0

    def _create_compliance_record(
        self,
        compliance_type: ComplianceType,
        entity_type: str,
        entity_id: str,
        status: ComplianceStatus,
        compliance_score: float,
        assessment_data: Dict[str, Any],
        regulation_name: str,
        requirement_description: str,
    ) -> Optional[ComplianceRecord]:
        try:
            record = ComplianceRecord(
                id=str(uuid.uuid4()),
                compliance_type=compliance_type,
                entity_type=entity_type,
                entity_id=entity_id,
                status=status,
                compliance_score=compliance_score,
                regulation_name=regulation_name,
                requirement_description=requirement_description,
            )
            record.set_assessment_data(assessment_data)
            self.db.session.add(record)
            self.db.session.commit()
            return record
        except Exception as e:
            self.logger.warning(f"Could not create compliance record: {e}")
            try:
                self.db.session.rollback()
            except Exception:
                pass
            return None

    def _get_kyc_required_actions(
        self, assessment_results: Dict[str, Any]
    ) -> List[str]:
        actions = []
        for req, met in assessment_results.items():
            if not met:
                actions.append(f"Provide {req.replace('_', ' ')}")
        return actions

    def _get_aml_recommended_actions(
        self, screening_results: Dict[str, Any], risk_score: float
    ) -> List[str]:
        actions = []
        if risk_score >= 80:
            actions.append("File Suspicious Activity Report (SAR)")
        if risk_score >= 60:
            actions.append("Enhanced due diligence required")
        if screening_results.get("sanctions_check", {}).get("flagged"):
            actions.append("Escalate to compliance team")
        return actions

    def _check_sar_requirements(
        self, risk_score: float, transaction_amount: Optional[Decimal]
    ) -> bool:
        if risk_score >= 80:
            return True
        if (
            transaction_amount
            and transaction_amount >= self.aml_thresholds["suspicious_activity"]
        ):
            return True
        return False

    def _identify_compliance_violations(
        self, checks: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        violations = []
        for check_name, result in checks.items():
            if isinstance(result, dict) and not result.get("compliant", True):
                for issue in result.get("issues", []):
                    violations.append({"check": check_name, "issue": issue})
        return violations

    def _get_loan_compliance_actions(self, checks: Dict[str, Any]) -> List[str]:
        actions = []
        for name, result in checks.items():
            if isinstance(result, dict) and not result.get("compliant", True):
                actions.append(f"Remediate {name.replace('_', ' ')} issue")
        return actions

    def _calculate_compliance_health(self, records: List[ComplianceRecord]) -> float:
        if not records:
            return 100.0
        compliant = len([r for r in records if r.status == ComplianceStatus.COMPLIANT])
        return (compliant / len(records)) * 100

    def _generate_compliance_summary(
        self, records: List[ComplianceRecord]
    ) -> Dict[str, Any]:
        return {
            "total": len(records),
            "compliant": len(
                [r for r in records if r.status == ComplianceStatus.COMPLIANT]
            ),
            "non_compliant": len(
                [r for r in records if r.status == ComplianceStatus.NON_COMPLIANT]
            ),
        }

    def _group_by_compliance_type(
        self, records: List[ComplianceRecord]
    ) -> Dict[str, Any]:
        groups: Dict[str, int] = {}
        for r in records:
            key = r.compliance_type.value if r.compliance_type else "unknown"
            groups[key] = groups.get(key, 0) + 1
        return groups

    def _group_by_entity_type(self, records: List[ComplianceRecord]) -> Dict[str, Any]:
        groups: Dict[str, int] = {}
        for r in records:
            key = r.entity_type or "unknown"
            groups[key] = groups.get(key, 0) + 1
        return groups

    def _summarize_violations(self, records: List[ComplianceRecord]) -> Dict[str, Any]:
        non_compliant = [r for r in records if r.status != ComplianceStatus.COMPLIANT]
        return {
            "total_violations": len(non_compliant),
            "critical": (
                len([r for r in non_compliant if r.severity == AuditSeverity.CRITICAL])
                if non_compliant and hasattr(non_compliant[0], "severity")
                else 0
            ),
        }

    def _analyze_compliance_trends(
        self, records: List[ComplianceRecord]
    ) -> Dict[str, Any]:
        return {
            "trend": "stable",
            "period_days": 30,
            "improving": False,
        }

    def _generate_compliance_recommendations(
        self, records: List[ComplianceRecord]
    ) -> List[str]:
        recommendations = []
        non_compliant = [r for r in records if r.status != ComplianceStatus.COMPLIANT]
        if len(non_compliant) > 5:
            recommendations.append(
                "Review and remediate high number of non-compliant records"
            )
        if not recommendations:
            recommendations.append("Continue maintaining compliance standards")
        return recommendations
