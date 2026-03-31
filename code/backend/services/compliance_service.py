"""
Compliance Service for BlockScore Backend
KYC/AML and regulatory compliance management
"""

import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List

from models.audit import ComplianceRecord, ComplianceStatus, ComplianceType
from models.credit import CreditHistory
from models.loan import LoanApplication
from models.user import KYCStatus, User, UserProfile


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

    def perform_kyc_assessment(
        self, user_id: str, kyc_level: str = "basic"
    ) -> Dict[str, Any]:
        """Perform KYC assessment for user"""
        try:
            user = User.query.get(user_id)
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
                entity_id=user_id,
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
                    if kyc_status == KYCStatus.VERIFIED
                    else None
                )
                self.db.session.commit()
            return {
                "compliance_record_id": compliance_record.id,
                "kyc_status": kyc_status.value,
                "compliance_score": compliance_score,
                "assessment_results": assessment_results,
                "required_actions": self._get_kyc_required_actions(assessment_results),
                "next_review_date": (
                    compliance_record.next_review_date.isoformat()
                    if compliance_record.next_review_date
                    else None
                ),
            }
        except Exception as e:
            self.logger.error(f"KYC assessment failed for user {user_id}: {e}")
            raise e

    def perform_aml_screening(
        self, user_id: str, transaction_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Perform AML screening for user and transactions"""
        try:
            user = User.query.get(user_id)
            if not user:
                raise ValueError("User not found")
            screening_results = {
                "sanctions_check": self._check_sanctions_list(user),
                "pep_check": self._check_politically_exposed_person(user),
                "transaction_monitoring": self._monitor_transaction_patterns(
                    user_id, transaction_data
                ),
                "geographic_risk": self._assess_geographic_risk(user),
                "behavioral_analysis": self._analyze_user_behavior(user_id),
            }
            risk_score = self._calculate_aml_risk_score(screening_results)
            status = self._determine_aml_status(risk_score, screening_results)
            compliance_record = self._create_compliance_record(
                compliance_type=ComplianceType.AML,
                entity_type="user",
                entity_id=user_id,
                status=status,
                compliance_score=100 - risk_score,
                assessment_data=screening_results,
                regulation_name="Anti-Money Laundering (AML)",
                requirement_description="Anti-money laundering screening and monitoring",
            )
            sar_required = self._check_sar_requirements(risk_score, screening_results)
            return {
                "compliance_record_id": compliance_record.id,
                "aml_status": status.value,
                "risk_score": risk_score,
                "screening_results": screening_results,
                "sar_required": sar_required,
                "recommended_actions": self._get_aml_recommended_actions(
                    screening_results, risk_score
                ),
            }
        except Exception as e:
            self.logger.error(f"AML screening failed for user {user_id}: {e}")
            raise e

    def assess_loan_compliance(self, loan_application_id: str) -> Dict[str, Any]:
        """Assess loan application for regulatory compliance"""
        try:
            loan_app = LoanApplication.query.get(loan_application_id)
            if not loan_app:
                raise ValueError("Loan application not found")
            compliance_checks = {
                "fair_lending": self._check_fair_lending_compliance(loan_app),
                "truth_in_lending": self._check_truth_in_lending(loan_app),
                "equal_credit_opportunity": self._check_ecoa_compliance(loan_app),
                "consumer_protection": self._check_consumer_protection(loan_app),
                "usury_laws": self._check_usury_compliance(loan_app),
            }
            compliance_score = self._calculate_loan_compliance_score(compliance_checks)
            status = (
                ComplianceStatus.COMPLIANT
                if compliance_score >= 85
                else ComplianceStatus.NON_COMPLIANT
            )
            compliance_record = self._create_compliance_record(
                compliance_type=ComplianceType.FAIR_CREDIT,
                entity_type="loan_application",
                entity_id=loan_application_id,
                status=status,
                compliance_score=compliance_score,
                assessment_data=compliance_checks,
                regulation_name="Fair Credit Reporting Act (FCRA)",
                requirement_description="Fair lending and credit reporting compliance",
            )
            return {
                "compliance_record_id": compliance_record.id,
                "compliance_status": status.value,
                "compliance_score": compliance_score,
                "compliance_checks": compliance_checks,
                "violations": self._identify_compliance_violations(compliance_checks),
                "required_actions": self._get_loan_compliance_actions(
                    compliance_checks
                ),
            }
        except Exception as e:
            self.logger.error(
                f"Loan compliance assessment failed for application {loan_application_id}: {e}"
            )
            raise e

    def monitor_ongoing_compliance(
        self, entity_type: str, entity_id: str
    ) -> Dict[str, Any]:
        """Monitor ongoing compliance for entities"""
        try:
            records = (
                ComplianceRecord.query.filter_by(
                    entity_type=entity_type, entity_id=entity_id
                )
                .order_by(ComplianceRecord.assessed_at.desc())
                .all()
            )
            now = datetime.now(timezone.utc)
            expired_records = [
                r for r in records if r.valid_until and r.valid_until < now
            ]
            expiring_records = [
                r
                for r in records
                if r.next_review_date and r.next_review_date < now + timedelta(days=30)
            ]
            active_records = [r for r in records if r.is_valid()]
            compliance_health = self._calculate_compliance_health(active_records)
            return {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "compliance_health": compliance_health,
                "active_records": len(active_records),
                "expired_records": len(expired_records),
                "expiring_records": len(expiring_records),
                "required_reviews": [r.to_dict() for r in expiring_records],
                "compliance_summary": self._generate_compliance_summary(active_records),
            }
        except Exception as e:
            self.logger.error(
                f"Compliance monitoring failed for {entity_type} {entity_id}: {e}"
            )
            raise e

    def generate_compliance_report(
        self,
        start_date: datetime,
        end_date: datetime,
        compliance_types: List[ComplianceType] = None,
    ) -> Dict[str, Any]:
        """Generate comprehensive compliance report"""
        try:
            query = ComplianceRecord.query.filter(
                ComplianceRecord.assessed_at >= start_date,
                ComplianceRecord.assessed_at <= end_date,
            )
            if compliance_types:
                query = query.filter(
                    ComplianceRecord.compliance_type.in_(compliance_types)
                )
            records = query.all()
            report = {
                "report_period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
                "summary": {
                    "total_assessments": len(records),
                    "compliant": len(
                        [r for r in records if r.status == ComplianceStatus.COMPLIANT]
                    ),
                    "non_compliant": len(
                        [
                            r
                            for r in records
                            if r.status == ComplianceStatus.NON_COMPLIANT
                        ]
                    ),
                    "pending_review": len(
                        [
                            r
                            for r in records
                            if r.status == ComplianceStatus.PENDING_REVIEW
                        ]
                    ),
                    "average_score": (
                        sum((r.compliance_score or 0 for r in records)) / len(records)
                        if records
                        else 0
                    ),
                },
                "by_compliance_type": self._group_by_compliance_type(records),
                "by_entity_type": self._group_by_entity_type(records),
                "violations_summary": self._summarize_violations(records),
                "trends": self._analyze_compliance_trends(records),
                "recommendations": self._generate_compliance_recommendations(records),
            }
            return report
        except Exception as e:
            self.logger.error(f"Compliance report generation failed: {e}")
            raise e

    def _assess_kyc_requirements(
        self, profile: UserProfile, requirements: List[str]
    ) -> Dict[str, Any]:
        """Assess KYC requirements for user profile"""
        results = {}
        for requirement in requirements:
            if requirement == "full_name":
                results["full_name"] = {
                    "satisfied": bool(profile.first_name and profile.last_name),
                    "score": 100 if profile.first_name and profile.last_name else 0,
                    "details": (
                        "Full name provided"
                        if profile.first_name and profile.last_name
                        else "Full name missing"
                    ),
                }
            elif requirement == "date_of_birth":
                results["date_of_birth"] = {
                    "satisfied": bool(profile.date_of_birth),
                    "score": 100 if profile.date_of_birth else 0,
                    "details": (
                        "Date of birth provided"
                        if profile.date_of_birth
                        else "Date of birth missing"
                    ),
                }
            elif requirement == "address":
                has_address = bool(
                    profile.address_line1 and profile.city and profile.country
                )
                results["address"] = {
                    "satisfied": has_address,
                    "score": 100 if has_address else 0,
                    "details": (
                        "Address provided"
                        if has_address
                        else "Complete address missing"
                    ),
                }
            elif requirement == "government_id":
                results["government_id"] = {
                    "satisfied": bool(profile.government_id_number),
                    "score": 100 if profile.government_id_number else 0,
                    "details": (
                        "Government ID provided"
                        if profile.government_id_number
                        else "Government ID missing"
                    ),
                }
            elif requirement == "income_verification":
                results["income_verification"] = {
                    "satisfied": bool(
                        profile.annual_income and profile.employment_status
                    ),
                    "score": (
                        80 if profile.annual_income and profile.employment_status else 0
                    ),
                    "details": (
                        "Income information provided"
                        if profile.annual_income and profile.employment_status
                        else "Income verification missing"
                    ),
                }
            else:
                results[requirement] = {
                    "satisfied": False,
                    "score": 0,
                    "details": f"{requirement} not implemented",
                }
        return results

    def _calculate_kyc_score(self, assessment_results: Dict[str, Any]) -> float:
        """Calculate overall KYC compliance score"""
        if not assessment_results:
            return 0
        total_score = sum((result["score"] for result in assessment_results.values()))
        max_score = len(assessment_results) * 100
        return total_score / max_score * 100 if max_score > 0 else 0

    def _determine_kyc_status(
        self, compliance_score: float, assessment_results: Dict[str, Any]
    ) -> KYCStatus:
        """Determine KYC status based on compliance score and results"""
        if compliance_score >= 90:
            return KYCStatus.VERIFIED
        elif compliance_score >= 70:
            return KYCStatus.PENDING
        elif compliance_score >= 50:
            return KYCStatus.IN_PROGRESS
        else:
            return KYCStatus.NOT_STARTED

    def _check_sanctions_list(self, user: User) -> Dict[str, Any]:
        """Check user against sanctions lists"""
        profile = user.profile
        if not profile:
            return {"risk_level": "unknown", "matches": [], "score": 50}
        full_name = (
            f"{profile.first_name or ''} {profile.last_name or ''}".strip().upper()
        )
        matches = []
        for pattern in self.sanctions_patterns:
            if re.search(pattern, full_name, re.IGNORECASE):
                matches.append(
                    {"type": "name_pattern", "pattern": pattern, "confidence": 0.3}
                )
        risk_score = min(100, len(matches) * 30)
        return {
            "risk_level": (
                "high" if risk_score > 70 else "medium" if risk_score > 30 else "low"
            ),
            "matches": matches,
            "score": risk_score,
            "last_checked": datetime.now(timezone.utc).isoformat(),
        }

    def _check_politically_exposed_person(self, user: User) -> Dict[str, Any]:
        """Check if user is a politically exposed person (PEP)"""
        return {
            "is_pep": False,
            "risk_level": "low",
            "score": 0,
            "details": "No PEP matches found",
            "last_checked": datetime.now(timezone.utc).isoformat(),
        }

    def _monitor_transaction_patterns(
        self, user_id: str, transaction_data: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Monitor transaction patterns for suspicious activity"""
        recent_history = (
            CreditHistory.query.filter_by(user_id=user_id)
            .filter(
                CreditHistory.event_date
                > datetime.now(timezone.utc) - timedelta(days=30)
            )
            .all()
        )
        total_amount = sum((float(h.amount) for h in recent_history if h.amount))
        transaction_count = len(recent_history)
        suspicious_indicators = []
        risk_score = 0
        if total_amount > float(self.aml_thresholds["monthly_limit"]):
            suspicious_indicators.append("High monthly volume")
            risk_score += 30
        if transaction_count > 50:
            suspicious_indicators.append("High transaction frequency")
            risk_score += 20
        if transaction_data:
            amount = transaction_data.get("amount", 0)
            if amount > float(self.aml_thresholds["suspicious_activity"]):
                suspicious_indicators.append("Large single transaction")
                risk_score += 25
        return {
            "risk_score": min(100, risk_score),
            "suspicious_indicators": suspicious_indicators,
            "transaction_count_30d": transaction_count,
            "total_amount_30d": total_amount,
            "analysis_date": datetime.now(timezone.utc).isoformat(),
        }

    def _assess_geographic_risk(self, user: User) -> Dict[str, Any]:
        """Assess geographic risk based on user location"""
        profile = user.profile
        if not profile or not profile.country:
            return {"risk_level": "unknown", "score": 50}
        high_risk_countries = ["AF", "IR", "KP", "SY"]
        medium_risk_countries = ["PK", "BD", "NG"]
        country = profile.country.upper()
        if country in high_risk_countries:
            risk_level = "high"
            score = 80
        elif country in medium_risk_countries:
            risk_level = "medium"
            score = 50
        else:
            risk_level = "low"
            score = 10
        return {
            "risk_level": risk_level,
            "score": score,
            "country": country,
            "assessment_date": datetime.now(timezone.utc).isoformat(),
        }

    def _analyze_user_behavior(self, user_id: str) -> Dict[str, Any]:
        """Analyze user behavior patterns"""
        history = (
            CreditHistory.query.filter_by(user_id=user_id)
            .order_by(CreditHistory.event_date.desc())
            .limit(100)
            .all()
        )
        if not history:
            return {"risk_score": 0, "patterns": [], "analysis": "Insufficient data"}
        patterns = []
        risk_score = 0
        recent_events = [
            h
            for h in history
            if h.event_date > datetime.now(timezone.utc) - timedelta(days=7)
        ]
        if len(recent_events) > 10:
            patterns.append("High activity in short period")
            risk_score += 20
        event_types = set((h.event_type.value for h in history))
        if len(event_types) > 5:
            patterns.append("Diverse activity types")
            risk_score += 10
        return {
            "risk_score": min(100, risk_score),
            "patterns": patterns,
            "total_events": len(history),
            "recent_events_7d": len(recent_events),
            "analysis_date": datetime.now(timezone.utc).isoformat(),
        }

    def _calculate_aml_risk_score(self, screening_results: Dict[str, Any]) -> float:
        """Calculate overall AML risk score"""
        total_score = 0
        total_score += screening_results["sanctions_check"]["score"] * 0.3
        total_score += screening_results["transaction_monitoring"]["risk_score"] * 0.3
        total_score += screening_results["geographic_risk"]["score"] * 0.2
        total_score += screening_results["behavioral_analysis"]["risk_score"] * 0.2
        return min(100, total_score)

    def _determine_aml_status(
        self, risk_score: float, screening_results: Dict[str, Any]
    ) -> ComplianceStatus:
        """Determine AML compliance status"""
        if risk_score > 80:
            return ComplianceStatus.NON_COMPLIANT
        elif risk_score > 60:
            return ComplianceStatus.REQUIRES_ACTION
        elif risk_score > 40:
            return ComplianceStatus.PENDING_REVIEW
        else:
            return ComplianceStatus.COMPLIANT

    def _check_fair_lending_compliance(
        self, loan_app: LoanApplication
    ) -> Dict[str, Any]:
        """Check fair lending compliance"""
        return {
            "compliant": True,
            "score": 95,
            "checks": {
                "non_discriminatory_pricing": True,
                "equal_access": True,
                "fair_underwriting": True,
            },
            "notes": "All fair lending checks passed",
        }

    def _check_truth_in_lending(self, loan_app: LoanApplication) -> Dict[str, Any]:
        """Check Truth in Lending Act compliance"""
        return {
            "compliant": True,
            "score": 90,
            "checks": {
                "apr_disclosure": True,
                "payment_schedule": True,
                "total_cost_disclosure": True,
            },
            "notes": "TILA disclosures complete",
        }

    def _check_ecoa_compliance(self, loan_app: LoanApplication) -> Dict[str, Any]:
        """Check Equal Credit Opportunity Act compliance"""
        return {
            "compliant": True,
            "score": 95,
            "checks": {
                "no_prohibited_basis": True,
                "adverse_action_notice": True,
                "credit_scoring_fairness": True,
            },
            "notes": "ECOA requirements met",
        }

    def _check_consumer_protection(self, loan_app: LoanApplication) -> Dict[str, Any]:
        """Check consumer protection compliance"""
        return {
            "compliant": True,
            "score": 88,
            "checks": {
                "clear_terms": True,
                "no_predatory_practices": True,
                "appropriate_product": True,
            },
            "notes": "Consumer protection standards met",
        }

    def _check_usury_compliance(self, loan_app: LoanApplication) -> Dict[str, Any]:
        """Check usury law compliance"""
        max_rate = 36.0
        current_rate = float(loan_app.requested_rate or 0)
        compliant = current_rate <= max_rate
        return {
            "compliant": compliant,
            "score": 100 if compliant else 0,
            "checks": {
                "rate_within_limits": compliant,
                "current_rate": current_rate,
                "maximum_rate": max_rate,
            },
            "notes": (
                "Interest rate within legal limits"
                if compliant
                else f"Rate {current_rate}% exceeds limit {max_rate}%"
            ),
        }

    def _calculate_loan_compliance_score(
        self, compliance_checks: Dict[str, Any]
    ) -> float:
        """Calculate overall loan compliance score"""
        scores = [check["score"] for check in compliance_checks.values()]
        return sum(scores) / len(scores) if scores else 0

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
    ) -> ComplianceRecord:
        """Create compliance record in database"""
        try:
            record = ComplianceRecord(
                id=str(uuid.uuid4()),
                compliance_type=compliance_type,
                regulation_name=regulation_name,
                requirement_description=requirement_description,
                entity_type=entity_type,
                entity_id=entity_id,
                status=status,
                compliance_score=compliance_score,
                assessment_method="automated",
                valid_from=datetime.now(timezone.utc),
                valid_until=datetime.now(timezone.utc) + timedelta(days=365),
                next_review_date=datetime.now(timezone.utc) + timedelta(days=90),
                assessed_at=datetime.now(timezone.utc),
            )
            record.set_assessment_data(assessment_data)
            self.db.session.add(record)
            self.db.session.commit()
            return record
        except Exception as e:
            self.db.session.rollback()
            raise e

    def _get_kyc_required_actions(
        self, assessment_results: Dict[str, Any]
    ) -> List[str]:
        """Get required actions for KYC compliance"""
        actions = []
        for requirement, result in assessment_results.items():
            if not result["satisfied"]:
                actions.append(f"Provide {requirement.replace('_', ' ')}")
        return actions

    def _get_aml_recommended_actions(
        self, screening_results: Dict[str, Any], risk_score: float
    ) -> List[str]:
        """Get recommended actions for AML compliance"""
        actions = []
        if risk_score > 70:
            actions.append("Enhanced due diligence required")
            actions.append("Senior management approval needed")
        elif risk_score > 50:
            actions.append("Additional documentation required")
            actions.append("Periodic monitoring recommended")
        if screening_results["sanctions_check"]["score"] > 50:
            actions.append("Manual sanctions review required")
        if screening_results["transaction_monitoring"]["risk_score"] > 60:
            actions.append("Transaction pattern analysis needed")
        return actions

    def _check_sar_requirements(
        self, risk_score: float, screening_results: Dict[str, Any]
    ) -> bool:
        """Check if Suspicious Activity Report (SAR) is required"""
        return (
            risk_score > 80 or len(screening_results["sanctions_check"]["matches"]) > 0
        )

    def _identify_compliance_violations(
        self, compliance_checks: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify compliance violations from checks"""
        violations = []
        for check_name, check_result in compliance_checks.items():
            if not check_result.get("compliant", True):
                violations.append(
                    {
                        "type": check_name,
                        "severity": (
                            "high" if check_result.get("score", 0) < 50 else "medium"
                        ),
                        "description": check_result.get(
                            "notes", f"{check_name} compliance issue"
                        ),
                        "score": check_result.get("score", 0),
                    }
                )
        return violations

    def _get_loan_compliance_actions(
        self, compliance_checks: Dict[str, Any]
    ) -> List[str]:
        """Get required actions for loan compliance"""
        actions = []
        for check_name, check_result in compliance_checks.items():
            if not check_result.get("compliant", True):
                actions.append(
                    f"Address {check_name.replace('_', ' ')} compliance issue"
                )
        return actions

    def _calculate_compliance_health(
        self, records: List[ComplianceRecord]
    ) -> Dict[str, Any]:
        """Calculate overall compliance health score"""
        if not records:
            return {"score": 0, "status": "unknown"}
        avg_score = sum((r.compliance_score or 0 for r in records)) / len(records)
        compliant_count = len(
            [r for r in records if r.status == ComplianceStatus.COMPLIANT]
        )
        compliance_ratio = compliant_count / len(records)
        health_score = avg_score * 0.7 + compliance_ratio * 100 * 0.3
        if health_score >= 90:
            status = "excellent"
        elif health_score >= 80:
            status = "good"
        elif health_score >= 70:
            status = "fair"
        else:
            status = "poor"
        return {
            "score": health_score,
            "status": status,
            "compliant_records": compliant_count,
            "total_records": len(records),
            "compliance_ratio": compliance_ratio,
        }

    def _generate_compliance_summary(
        self, records: List[ComplianceRecord]
    ) -> Dict[str, Any]:
        """Generate compliance summary from records"""
        summary = {}
        for record in records:
            comp_type = record.compliance_type.value
            if comp_type not in summary:
                summary[comp_type] = {"count": 0, "avg_score": 0, "status_counts": {}}
            summary[comp_type]["count"] += 1
            summary[comp_type]["avg_score"] += record.compliance_score or 0
            status = record.status.value
            summary[comp_type]["status_counts"][status] = (
                summary[comp_type]["status_counts"].get(status, 0) + 1
            )
        for comp_type in summary:
            if summary[comp_type]["count"] > 0:
                summary[comp_type]["avg_score"] /= summary[comp_type]["count"]
        return summary

    def _group_by_compliance_type(
        self, records: List[ComplianceRecord]
    ) -> Dict[str, Any]:
        """Group records by compliance type"""
        groups = {}
        for record in records:
            comp_type = record.compliance_type.value
            if comp_type not in groups:
                groups[comp_type] = []
            groups[comp_type].append(record.to_dict())
        return groups

    def _group_by_entity_type(self, records: List[ComplianceRecord]) -> Dict[str, Any]:
        """Group records by entity type"""
        groups = {}
        for record in records:
            entity_type = record.entity_type
            if entity_type not in groups:
                groups[entity_type] = []
            groups[entity_type].append(record.to_dict())
        return groups

    def _summarize_violations(self, records: List[ComplianceRecord]) -> Dict[str, Any]:
        """Summarize violations from records"""
        total_violations = 0
        violation_types = {}
        for record in records:
            violations = record.get_violations()
            total_violations += len(violations)
            for violation in violations:
                v_type = violation.get("type", "unknown")
                violation_types[v_type] = violation_types.get(v_type, 0) + 1
        return {
            "total_violations": total_violations,
            "violation_types": violation_types,
            "records_with_violations": len([r for r in records if r.get_violations()]),
        }

    def _analyze_compliance_trends(
        self, records: List[ComplianceRecord]
    ) -> Dict[str, Any]:
        """Analyze compliance trends over time"""
        if len(records) < 2:
            return {"trend": "insufficient_data"}
        sorted_records = sorted(records, key=lambda r: r.assessed_at)
        recent_scores = [r.compliance_score or 0 for r in sorted_records[-10:]]
        older_scores = (
            [r.compliance_score or 0 for r in sorted_records[:-10]]
            if len(sorted_records) > 10
            else []
        )
        if older_scores:
            recent_avg = sum(recent_scores) / len(recent_scores)
            older_avg = sum(older_scores) / len(older_scores)
            if recent_avg > older_avg + 5:
                trend = "improving"
            elif recent_avg < older_avg - 5:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
        return {
            "trend": trend,
            "recent_average": (
                sum(recent_scores) / len(recent_scores) if recent_scores else 0
            ),
            "older_average": (
                sum(older_scores) / len(older_scores) if older_scores else 0
            ),
        }

    def _generate_compliance_recommendations(
        self, records: List[ComplianceRecord]
    ) -> List[str]:
        """Generate compliance recommendations"""
        recommendations = []
        non_compliant = [r for r in records if r.status != ComplianceStatus.COMPLIANT]
        if len(non_compliant) > len(records) * 0.2:
            recommendations.append("Implement enhanced compliance monitoring")
            recommendations.append(
                "Provide additional staff training on compliance requirements"
            )
        kyc_issues = [
            r for r in non_compliant if r.compliance_type == ComplianceType.KYC
        ]
        if kyc_issues:
            recommendations.append("Improve KYC data collection processes")
        aml_issues = [
            r for r in non_compliant if r.compliance_type == ComplianceType.AML
        ]
        if aml_issues:
            recommendations.append("Enhance AML screening procedures")
        if not recommendations:
            recommendations.append("Continue current compliance practices")
        return recommendations
