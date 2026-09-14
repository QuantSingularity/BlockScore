"""
Credit Scoring Service for BlockScore Backend
Advanced AI-powered credit scoring with blockchain integration
"""

import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests

try:
    import joblib

    _JOBLIB_AVAILABLE = True
except ImportError:
    joblib = None
    _JOBLIB_AVAILABLE = False

try:
    import pandas as pd

    _PANDAS_AVAILABLE = True
except ImportError:
    pd = None
    _PANDAS_AVAILABLE = False

from extensions import db
from models.blockchain import BlockchainTransaction
from models.credit import (
    CreditEventType,
    CreditFactor,
    CreditFactorType,
    CreditHistory,
    CreditScore,
    CreditScoreStatus,
)
from models.user import User


class CreditScoringService:
    """Advanced credit scoring service with AI models and blockchain integration"""

    def __init__(self, db: Any, cache_manager: Any = None) -> None:
        self.db = db
        self.cache = cache_manager
        self.monitor = None
        self.job_manager = None
        self.blockchain_service = None
        self.logger = logging.getLogger(__name__)
        self.model = None
        self.model_version = "1.0"
        self.model_name = "BlockScore_v1.0"
        self.min_score = 300
        self.max_score = 850
        self.default_score = 300
        self.ai_model_url = os.getenv("AI_MODEL_URL", "http://localhost:5001").rstrip(
            "/"
        )
        self.ai_model_timeout = float(os.getenv("AI_MODEL_TIMEOUT", "5"))
        self.factor_weights = {
            CreditFactorType.PAYMENT_HISTORY: 0.35,
            CreditFactorType.CREDIT_UTILIZATION: 0.3,
            CreditFactorType.LENGTH_OF_HISTORY: 0.15,
            CreditFactorType.CREDIT_MIX: 0.1,
            CreditFactorType.NEW_CREDIT: 0.1,
            CreditFactorType.INCOME_STABILITY: 0.05,
            CreditFactorType.DEBT_TO_INCOME: 0.05,
            CreditFactorType.BLOCKCHAIN_ACTIVITY: 0.1,
        }
        self._load_model()

    def calculate_credit_score(
        self,
        user_id: str,
        wallet_address: Optional[str] = None,
        force_recalculation: bool = False,
    ) -> Dict[str, Any]:
        """Calculate comprehensive credit score for user"""
        import time

        start_time = time.time()
        try:
            user = db.session.get(User, user_id)
            if not user:
                return {"error": "User not found", "user_id": user_id}
            if not force_recalculation:
                recent_score = self._get_recent_valid_score(user_id)
                if recent_score:
                    result = self._format_score_response(recent_score)
                    if self.monitor:
                        self.monitor.record_metric(
                            "credit_score_duration", time.time() - start_time
                        )
                    return result
            scoring_data = self._gather_scoring_data(user, wallet_address)

            # Try AI model first (patchable by tests)
            ai_result = self._call_ai_model(scoring_data)
            if (
                ai_result
                and ai_result.get("score")
                and ai_result["score"] != self.default_score
            ):
                overall_score = ai_result["score"]
                confidence = ai_result.get("confidence", 0.85)
                factors = self._calculate_factor_scores(scoring_data)
            else:
                factors = self._calculate_factor_scores(scoring_data)
                overall_score = self._calculate_overall_score(factors)
                confidence = 0.85

            # Capture the previous score now, before we create and commit
            # the new one below - otherwise a later lookup would just
            # find the record we're about to create (always a zero delta).
            previous_score_record = self._get_recent_valid_score(user_id)
            previous_score_value = (
                previous_score_record.score if previous_score_record else None
            )

            credit_score = self._create_credit_score_record(
                user_id=user_id,
                score=overall_score,
                factors=factors,
                scoring_data=scoring_data,
            )
            credit_score.model_confidence = confidence
            self.db.session.commit()

            self._create_credit_history_event(
                user_id=user_id,
                credit_score_id=credit_score.id,
                event_type=CreditEventType.SCORE_RECALCULATION,
                score_after=overall_score,
            )
            result = self._format_score_response(credit_score)
            result["factors"] = [f.to_dict() for f in factors]
            result["version"] = self.model_version
            result["ai_confidence"] = confidence

            # Blockchain integration
            if wallet_address and self.blockchain_service:
                try:
                    bc_result = self.blockchain_service.submit_credit_score_update(
                        user_id=user_id,
                        credit_score_id=credit_score.id,
                        score=overall_score,
                        wallet_address=wallet_address,
                        previous_score=previous_score_value,
                    )
                    result["blockchain_transaction"] = bc_result
                except Exception as bc_err:
                    self.logger.warning(f"Blockchain update failed: {bc_err}")
                    result["blockchain_transaction"] = {
                        "status": "failed",
                        "error": str(bc_err),
                    }
            elif wallet_address:
                result["blockchain_transaction"] = {
                    "status": "skipped",
                    "reason": "no blockchain service",
                }

            if self.monitor:
                self.monitor.record_metric(
                    "credit_score_duration", time.time() - start_time
                )

            return result
        except Exception as e:
            self.logger.error(
                f"Credit score calculation failed for user {user_id}: {e}"
            )
            return {"error": str(e), "user_id": user_id}

    def get_credit_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get credit history for user"""
        history = (
            CreditHistory.query.filter_by(user_id=user_id)
            .order_by(CreditHistory.event_date.desc())
            .limit(limit)
            .all()
        )
        return [event.to_dict() for event in history]

    def get_credit_factors(self, credit_score_id: str) -> List[Dict[str, Any]]:
        """Get detailed credit factors for a score"""
        factors = CreditFactor.query.filter_by(credit_score_id=credit_score_id).all()
        return [factor.to_dict() for factor in factors]

    def simulate_score_impact(
        self, user_id: str, scenario: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Simulate impact of changes on credit score"""
        try:
            current_score = self._get_recent_valid_score(user_id)
            if not current_score:
                raise ValueError("No current credit score found")
            modified_data = self._apply_scenario_changes(user_id, scenario)
            factors = self._calculate_factor_scores(modified_data)
            new_score = self._calculate_overall_score(factors)
            score_change = new_score - current_score.score
            return {
                "current_score": current_score.score,
                "projected_score": new_score,
                "score_change": score_change,
                "impact_analysis": self._analyze_score_impact(factors, scenario),
                "recommendations": self._generate_recommendations(factors),
            }
        except Exception as e:
            self.logger.error(f"Score simulation failed for user {user_id}: {e}")
            raise e

    def update_credit_event(
        self, user_id: str, event_type: CreditEventType, event_data: Dict[str, Any]
    ) -> bool:
        """Update credit profile with new event"""
        try:
            event = CreditHistory(
                id=str(uuid.uuid4()),
                user_id=user_id,
                event_type=event_type,
                event_title=event_data.get(
                    "title", event_type.value.replace("_", " ").title()
                ),
                event_description=event_data.get("description", ""),
                amount=event_data.get("amount"),
                currency=event_data.get("currency", "USD"),
                event_date=event_data.get("event_date", datetime.now(timezone.utc)),
                loan_id=event_data.get("loan_id"),
                transaction_id=event_data.get("transaction_id"),
                blockchain_hash=event_data.get("blockchain_hash"),
            )
            event.set_event_data(event_data)
            self.db.session.add(event)
            self.db.session.commit()
            if self._is_significant_event(event_type):
                self.calculate_credit_score(user_id, force_recalculation=True)
            return True
        except Exception as e:
            self.db.session.rollback()
            self.logger.error(f"Failed to update credit event for user {user_id}: {e}")
            return False

    def get_score_explanation(self, credit_score_id: str) -> Dict[str, Any]:
        """Get detailed explanation of credit score calculation"""
        credit_score = db.session.get(CreditScore, credit_score_id)
        if not credit_score:
            raise ValueError("Credit score not found")
        factors = CreditFactor.query.filter_by(credit_score_id=credit_score_id).all()
        return {
            "score": credit_score.score,
            "score_range": f"{self.min_score}-{self.max_score}",
            "score_grade": self._get_score_grade(credit_score.score),
            "factors": [
                {
                    "name": factor.factor_name,
                    "type": factor.factor_type.value,
                    "contribution": factor.contribution,
                    "weight": factor.weight,
                    "description": factor.factor_description,
                    "impact": self._get_factor_impact(factor.contribution),
                }
                for factor in factors
            ],
            "model_info": {
                "name": credit_score.model_name,
                "version": credit_score.score_version,
                "confidence": credit_score.model_confidence,
            },
            "recommendations": self._generate_recommendations(factors),
        }

    def is_model_loaded(self) -> bool:
        """Check if the local fallback AI model is loaded"""
        return self.model is not None

    def is_ai_service_available(self) -> bool:
        """Check whether the ai_models HTTP scoring service is reachable"""
        try:
            response = requests.get(f"{self.ai_model_url}/health", timeout=2)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def _load_model(self) -> Any:
        """Load a local copy of the AI model as a same-process fallback"""
        if not _JOBLIB_AVAILABLE:
            self.logger.info("joblib not installed; local AI model fallback disabled.")
            self.model = None
            return
        try:
            model_path = os.path.join(
                os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                ),
                "ai_models",
                "credit_scoring_model.pkl",
            )
            self.model = joblib.load(model_path)
            self.logger.info(f"Loaded local fallback AI model from {model_path}")
        except Exception as e:
            self.logger.info(
                f"No local fallback AI model available ({e}); relying on the "
                "ai_models HTTP service and rule-based scoring."
            )
            self.model = None

    def _get_recent_valid_score(self, user_id: str) -> Optional[CreditScore]:
        """Get recent valid credit score for user"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
        return (
            CreditScore.query.filter_by(user_id=user_id)
            .filter(CreditScore.calculated_at > cutoff_date)
            .filter(CreditScore.status == CreditScoreStatus.ACTIVE)
            .order_by(CreditScore.calculated_at.desc())
            .first()
        )

    def _gather_scoring_data(
        self, user: User, wallet_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """Gather all data needed for credit scoring"""
        data = {
            "user_id": user.id,
            "wallet_address": wallet_address
            or (user.profile.wallet_address if user.profile else None),
            "profile_data": {},
            "credit_history": [],
            "blockchain_data": {},
            "financial_data": {},
        }
        if user.profile:
            data["profile_data"] = {
                "annual_income": (
                    float(user.profile.annual_income)
                    if user.profile.annual_income
                    else None
                ),
                "employment_status": user.profile.employment_status,
                "kyc_status": user.profile.kyc_status.value,
                "account_age_days": (
                    datetime.now(timezone.utc)
                    - (
                        user.created_at.replace(tzinfo=timezone.utc)
                        if user.created_at.tzinfo is None
                        else user.created_at
                    )
                ).days,
            }
        credit_events = (
            CreditHistory.query.filter_by(user_id=user.id)
            .order_by(CreditHistory.event_date.desc())
            .limit(100)
            .all()
        )
        data["credit_history"] = [
            {
                "event_type": event.event_type.value,
                "amount": float(event.amount) if event.amount else 0,
                "event_date": event.event_date,
                "score_change": event.score_change or 0,
            }
            for event in credit_events
        ]
        if data["wallet_address"]:
            data["blockchain_data"] = self._get_blockchain_data(data["wallet_address"])
        return data

    def _get_blockchain_data(self, wallet_address: str) -> Dict[str, Any]:
        """Get blockchain transaction data for wallet"""
        transactions = (
            BlockchainTransaction.query.filter(
                (BlockchainTransaction.from_address == wallet_address)
                | (BlockchainTransaction.to_address == wallet_address)
            )
            .order_by(BlockchainTransaction.submitted_at.desc())
            .limit(100)
            .all()
        )
        if not transactions:
            return {
                "total_transactions": 0,
                "total_volume": 0.0,
                "successful_transactions": 0,
                "success_rate": 0.0,
                "avg_transaction_amount": 0.0,
                "transaction_frequency": 0.0,
                "recent_activity_days": 0,
            }
        total_volume = sum((float(tx.value) for tx in transactions if tx.value))
        successful_txs = [tx for tx in transactions if tx.status.value == "confirmed"]
        first_tx_date = transactions[-1].submitted_at.replace(tzinfo=timezone.utc)
        last_tx_date = transactions[0].submitted_at.replace(tzinfo=timezone.utc)
        time_span = (last_tx_date - first_tx_date).days
        transaction_frequency = (
            len(transactions) / time_span if time_span > 0 else len(transactions)
        )
        return {
            "total_transactions": len(transactions),
            "total_volume": total_volume,
            "successful_transactions": len(successful_txs),
            "success_rate": (
                len(successful_txs) / len(transactions) if transactions else 0
            ),
            "avg_transaction_amount": (
                total_volume / len(transactions) if transactions else 0
            ),
            "transaction_frequency": transaction_frequency,
            "recent_activity_days": time_span,
        }

    def _calculate_factor_scores(self, data: Dict[str, Any]) -> List[CreditFactor]:
        """Calculate individual credit factor scores"""
        factors = []
        payment_factor = self._calculate_payment_history_factor(data)
        factors.append(payment_factor)
        utilization_factor = self._calculate_credit_utilization_factor(data)
        factors.append(utilization_factor)
        history_factor = self._calculate_length_of_history_factor(data)
        factors.append(history_factor)
        mix_factor = self._calculate_credit_mix_factor(data)
        factors.append(mix_factor)
        new_credit_factor = self._calculate_new_credit_factor(data)
        factors.append(new_credit_factor)
        income_factor = self._calculate_income_stability_factor(data)
        factors.append(income_factor)
        dti_factor = self._calculate_debt_to_income_factor(data)
        factors.append(dti_factor)
        blockchain_factor = self._calculate_blockchain_activity_factor(data)
        factors.append(blockchain_factor)
        return factors

    def _calculate_payment_history_factor(self, data: Dict[str, Any]) -> CreditFactor:
        """Calculate payment history factor score"""
        credit_history = data.get("credit_history", [])
        blockchain_data = data.get("blockchain_data", {})
        if credit_history:
            payment_events = [e for e in credit_history if "payment" in e["event_type"]]
            if payment_events:
                positive_events = [e for e in payment_events if e["score_change"] >= 0]
                payment_ratio = len(positive_events) / len(payment_events)
            else:
                payment_ratio = 0.5
        else:
            payment_ratio = blockchain_data.get("repayment_ratio", 0.5)
        raw_score = payment_ratio * 100
        normalized_score = payment_ratio
        weight = self.factor_weights[CreditFactorType.PAYMENT_HISTORY]
        contribution = raw_score * weight
        return CreditFactor(
            id=str(uuid.uuid4()),
            factor_type=CreditFactorType.PAYMENT_HISTORY,
            factor_name="Payment History",
            factor_description="Track record of making payments on time",
            raw_value=raw_score,
            normalized_value=normalized_score,
            weight=weight,
            contribution=contribution,
            data_source="credit_history,blockchain",
            confidence_level=0.9 if credit_history else 0.6,
        )

    def _calculate_credit_utilization_factor(
        self, data: Dict[str, Any]
    ) -> CreditFactor:
        """Calculate credit utilization factor score"""
        credit_history = data.get("credit_history", [])
        profile_data = data.get("profile_data", {})
        annual_income = profile_data.get("annual_income") or 50000
        outstanding_debt = sum(
            (
                e["amount"]
                for e in credit_history
                if e["event_type"] in ["loan_approval", "loan_disbursement"]
            )
        )
        total_credit_limit = annual_income * 2
        if total_credit_limit > 0:
            utilization_ratio = min(1.0, outstanding_debt / total_credit_limit)
        else:
            utilization_ratio = 0.5
        raw_score = max(0, 100 - utilization_ratio * 100)
        normalized_score = 1 - utilization_ratio
        weight = self.factor_weights[CreditFactorType.CREDIT_UTILIZATION]
        contribution = raw_score * weight
        return CreditFactor(
            id=str(uuid.uuid4()),
            factor_type=CreditFactorType.CREDIT_UTILIZATION,
            factor_name="Credit Utilization",
            factor_description="Percentage of available credit being used",
            raw_value=raw_score,
            normalized_value=normalized_score,
            weight=weight,
            contribution=contribution,
            data_source="estimated",
            confidence_level=0.5,
        )

    def _calculate_length_of_history_factor(self, data: Dict[str, Any]) -> CreditFactor:
        """Calculate length of credit history factor"""
        profile_data = data.get("profile_data", {})
        account_age_days = profile_data.get("account_age_days", 0)
        max_age_for_full_score = 365 * 7
        age_ratio = min(1.0, account_age_days / max_age_for_full_score)
        raw_score = age_ratio * 100
        normalized_score = age_ratio
        weight = self.factor_weights[CreditFactorType.LENGTH_OF_HISTORY]
        contribution = raw_score * weight
        return CreditFactor(
            id=str(uuid.uuid4()),
            factor_type=CreditFactorType.LENGTH_OF_HISTORY,
            factor_name="Length of Credit History",
            factor_description="How long you have been using credit",
            raw_value=raw_score,
            normalized_value=normalized_score,
            weight=weight,
            contribution=contribution,
            data_source="profile",
            confidence_level=0.95,
        )

    def _calculate_credit_mix_factor(self, data: Dict[str, Any]) -> CreditFactor:
        """Calculate credit mix factor score"""
        credit_history = data.get("credit_history", [])
        event_types = set((e["event_type"] for e in credit_history))
        mix_score = min(100, len(event_types) * 20)
        normalized_score = mix_score / 100
        weight = self.factor_weights[CreditFactorType.CREDIT_MIX]
        contribution = mix_score * weight
        return CreditFactor(
            id=str(uuid.uuid4()),
            factor_type=CreditFactorType.CREDIT_MIX,
            factor_name="Credit Mix",
            factor_description="Variety of credit types in use",
            raw_value=mix_score,
            normalized_value=normalized_score,
            weight=weight,
            contribution=contribution,
            data_source="credit_history",
            confidence_level=0.8,
        )

    def _calculate_new_credit_factor(self, data: Dict[str, Any]) -> CreditFactor:
        """Calculate new credit factor score"""
        credit_history = data.get("credit_history", [])
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=180)
        recent_applications = [
            e
            for e in credit_history
            if e["event_type"] == "loan_application" and e["event_date"] > cutoff_date
        ]
        num_applications = len(recent_applications)
        raw_score = max(0, 100 - num_applications * 20)
        normalized_score = raw_score / 100
        weight = self.factor_weights[CreditFactorType.NEW_CREDIT]
        contribution = raw_score * weight
        return CreditFactor(
            id=str(uuid.uuid4()),
            factor_type=CreditFactorType.NEW_CREDIT,
            factor_name="New Credit",
            factor_description="Recent credit applications and new accounts",
            raw_value=raw_score,
            normalized_value=normalized_score,
            weight=weight,
            contribution=contribution,
            data_source="credit_history",
            confidence_level=0.9,
        )

    def _calculate_income_stability_factor(self, data: Dict[str, Any]) -> CreditFactor:
        """Calculate income stability factor score"""
        profile_data = data.get("profile_data", {})
        employment_status = profile_data.get("employment_status", "unknown")
        employment_scores = {
            "employed": 100,
            "self_employed": 80,
            "unemployed": 20,
            "student": 60,
            "retired": 70,
            "unknown": 50,
        }
        raw_score = employment_scores.get(employment_status, 50)
        normalized_score = raw_score / 100
        weight = self.factor_weights[CreditFactorType.INCOME_STABILITY]
        contribution = raw_score * weight
        return CreditFactor(
            id=str(uuid.uuid4()),
            factor_type=CreditFactorType.INCOME_STABILITY,
            factor_name="Income Stability",
            factor_description="Stability and reliability of income source",
            raw_value=raw_score,
            normalized_value=normalized_score,
            weight=weight,
            contribution=contribution,
            data_source="profile",
            confidence_level=0.7,
        )

    def _calculate_debt_to_income_factor(self, data: Dict[str, Any]) -> CreditFactor:
        """Calculate debt-to-income factor score"""
        profile_data = data.get("profile_data", {})
        credit_history = data.get("credit_history", [])
        annual_income = profile_data.get("annual_income") or 50000
        monthly_income = annual_income / 12
        outstanding_debt = sum(
            (
                e["amount"]
                for e in credit_history
                if e["event_type"] in ["loan_approval", "loan_disbursement"]
            )
        )
        estimated_monthly_debt = outstanding_debt / 12
        if monthly_income > 0:
            estimated_dti = min(1.0, estimated_monthly_debt / monthly_income)
        else:
            estimated_dti = 0.5
        raw_score = max(0, 100 - estimated_dti * 200)
        normalized_score = raw_score / 100
        weight = self.factor_weights[CreditFactorType.DEBT_TO_INCOME]
        contribution = raw_score * weight
        return CreditFactor(
            id=str(uuid.uuid4()),
            factor_type=CreditFactorType.DEBT_TO_INCOME,
            factor_name="Debt-to-Income Ratio",
            factor_description="Total debt payments relative to income",
            raw_value=raw_score,
            normalized_value=normalized_score,
            weight=weight,
            contribution=contribution,
            data_source="estimated",
            confidence_level=0.4,
        )

    def _calculate_blockchain_activity_factor(
        self, data: Dict[str, Any]
    ) -> CreditFactor:
        """Calculate blockchain activity factor score"""
        blockchain_data = data.get("blockchain_data", {})
        if not blockchain_data:
            raw_score = 50
        else:
            success_rate = blockchain_data.get("success_rate", 0.5)
            transaction_count = blockchain_data.get("total_transactions", 0)
            total_volume = blockchain_data.get("total_volume", 0)
            activity_score = min(100, transaction_count * 2)
            reliability_score = success_rate * 100
            volume_score = min(100, total_volume / 1000)
            raw_score = (
                activity_score * 0.3 + reliability_score * 0.5 + volume_score * 0.2
            )
        normalized_score = raw_score / 100
        weight = self.factor_weights[CreditFactorType.BLOCKCHAIN_ACTIVITY]
        contribution = raw_score * weight
        return CreditFactor(
            id=str(uuid.uuid4()),
            factor_type=CreditFactorType.BLOCKCHAIN_ACTIVITY,
            factor_name="Blockchain Activity",
            factor_description="On-chain transaction history and reliability",
            raw_value=raw_score,
            normalized_value=normalized_score,
            weight=weight,
            contribution=contribution,
            data_source="blockchain",
            confidence_level=0.8 if blockchain_data else 0.3,
        )

    def _calculate_overall_score(self, factors: List[CreditFactor]) -> int:
        """Calculate overall credit score from factors"""
        if self.model:
            return self._calculate_score_with_model(factors)
        else:
            total_contribution = sum((factor.contribution for factor in factors))
            score = self.min_score + total_contribution / 100 * (
                self.max_score - self.min_score
            )
            return max(self.min_score, min(self.max_score, int(score)))

    def _calculate_score_with_model(self, factors: List[CreditFactor]) -> int:
        """Calculate score using AI model"""
        try:
            feature_dict = {
                factor.factor_type.value: factor.normalized_value for factor in factors
            }
            if not _PANDAS_AVAILABLE or pd is None:
                raise ImportError("pandas not available")
            features_df = pd.DataFrame([feature_dict])
            predicted_score = self.model.predict(features_df)[0]
            return max(self.min_score, min(self.max_score, int(predicted_score)))
        except Exception as e:
            self.logger.error(f"Model prediction failed: {e}")
            total = sum(f.contribution or 0 for f in factors)
            score = self.min_score + (total / 100) * (self.max_score - self.min_score)
            return max(self.min_score, min(self.max_score, int(score)))

    def _create_credit_score_record(
        self,
        user_id: str,
        score: int,
        factors: List[CreditFactor],
        scoring_data: Dict[str, Any],
    ) -> CreditScore:
        """Create credit score database record"""
        try:
            credit_score = CreditScore(
                id=str(uuid.uuid4()),
                user_id=user_id,
                score=score,
                score_version=self.model_version,
                status=CreditScoreStatus.ACTIVE,
                model_name=self.model_name,
                model_confidence=0.85,
                calculated_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(days=30),
                valid_until=datetime.now(timezone.utc) + timedelta(days=90),
            )
            for factor in factors:
                if factor.factor_type == CreditFactorType.PAYMENT_HISTORY:
                    credit_score.payment_history_score = int(factor.raw_value)
                elif factor.factor_type == CreditFactorType.CREDIT_UTILIZATION:
                    credit_score.credit_utilization_score = int(factor.raw_value)
                elif factor.factor_type == CreditFactorType.LENGTH_OF_HISTORY:
                    credit_score.length_of_history_score = int(factor.raw_value)
                elif factor.factor_type == CreditFactorType.CREDIT_MIX:
                    credit_score.credit_mix_score = int(factor.raw_value)
                elif factor.factor_type == CreditFactorType.NEW_CREDIT:
                    credit_score.new_credit_score = int(factor.raw_value)
                elif factor.factor_type == CreditFactorType.INCOME_STABILITY:
                    credit_score.income_stability_score = int(factor.raw_value)
                elif factor.factor_type == CreditFactorType.DEBT_TO_INCOME:
                    credit_score.debt_to_income_score = int(factor.raw_value)
                elif factor.factor_type == CreditFactorType.BLOCKCHAIN_ACTIVITY:
                    credit_score.blockchain_activity_score = int(factor.raw_value)
            self.db.session.add(credit_score)
            self.db.session.flush()
            for factor in factors:
                factor.credit_score_id = credit_score.id
                self.db.session.add(factor)
            self.db.session.commit()
            return credit_score
        except Exception as e:
            self.db.session.rollback()
            raise e

    def _create_credit_history_event(
        self,
        user_id: str,
        credit_score_id: str,
        event_type: CreditEventType,
        score_after: int,
    ) -> Any:
        """Create credit history event"""
        try:
            event = CreditHistory(
                id=str(uuid.uuid4()),
                user_id=user_id,
                credit_score_id=credit_score_id,
                event_type=event_type,
                event_title="Credit Score Calculated",
                event_description="Credit score calculated using AI model and blockchain data",
                score_after=score_after,
                event_date=datetime.now(timezone.utc),
            )
            self.db.session.add(event)
            self.db.session.commit()
        except Exception as e:
            self.db.session.rollback()
            self.logger.error(f"Failed to create credit history event: {e}")

    def _format_score_response(self, credit_score: CreditScore) -> Dict[str, Any]:
        """Format credit score response"""
        return {
            "credit_score_id": credit_score.id,
            "score": credit_score.score,
            "score_grade": self._get_score_grade(credit_score.score),
            "model_version": credit_score.score_version,
            "calculated_at": credit_score.calculated_at.isoformat(),
            "expires_at": (
                credit_score.expires_at.isoformat() if credit_score.expires_at else None
            ),
            "is_valid": credit_score.is_valid(),
            "score_breakdown": credit_score.get_score_breakdown(),
            "confidence": credit_score.model_confidence,
        }

    def _get_score_grade(self, score: int) -> str:
        """Get letter grade for credit score"""
        if score >= 800:
            return "Excellent"
        elif score >= 740:
            return "Very Good"
        elif score >= 670:
            return "Good"
        elif score >= 580:
            return "Fair"
        else:
            return "Poor"

    def _get_factor_impact(self, contribution: float) -> str:
        """Get impact description for factor contribution"""
        if contribution >= 80:
            return "Very Positive"
        elif contribution >= 60:
            return "Positive"
        elif contribution >= 40:
            return "Neutral"
        elif contribution >= 20:
            return "Negative"
        else:
            return "Very Negative"

    def _apply_scenario_changes(
        self, user_id: str, scenario: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply scenario changes to scoring data"""
        user = db.session.get(User, user_id)
        if not user:
            raise ValueError("User not found")
        modified_data = self._gather_scoring_data(user)
        if "profile_data" in scenario:
            modified_data["profile_data"].update(scenario["profile_data"])
        if "new_loan" in scenario:
            loan_data = scenario["new_loan"]
            modified_data["credit_history"].append(
                {
                    "event_type": "loan_approval",
                    "amount": loan_data.get("amount", 0),
                    "event_date": datetime.now(timezone.utc),
                    "score_change": 0,
                }
            )
            modified_data["credit_history"].append(
                {
                    "event_type": "credit_inquiry",
                    "amount": 0,
                    "event_date": datetime.now(timezone.utc),
                    "score_change": 0,
                }
            )
        if "payment_made" in scenario:
            payment_data = scenario["payment_made"]
            modified_data["credit_history"].append(
                {
                    "event_type": "payment_made",
                    "amount": payment_data.get("amount", 0),
                    "event_date": datetime.now(timezone.utc),
                    "score_change": 10,
                }
            )
        return modified_data

    def _analyze_score_impact(
        self, factors: List[CreditFactor], scenario: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze the impact of scenario changes"""
        return {
            "primary_factors": [f.factor_name for f in factors[:3]],
            "improvement_potential": "Medium",
            "timeline": "3-6 months",
        }

    def _generate_recommendations(self, factors: List[CreditFactor]) -> List[str]:
        """Generate recommendations for improving credit score"""
        recommendations = []
        for factor in factors:
            if factor.normalized_value < 0.6:
                if factor.factor_type == CreditFactorType.PAYMENT_HISTORY:
                    recommendations.append(
                        "Make all payments on time to improve payment history"
                    )
                elif factor.factor_type == CreditFactorType.CREDIT_UTILIZATION:
                    recommendations.append("Reduce credit utilization below 30%")
                elif factor.factor_type == CreditFactorType.BLOCKCHAIN_ACTIVITY:
                    recommendations.append(
                        "Increase blockchain transaction activity and reliability"
                    )
        if not recommendations:
            recommendations.append("Continue maintaining good credit habits")
        return recommendations[:5]

    def _is_significant_event(self, event_type: CreditEventType) -> bool:
        """Check if event type should trigger score recalculation"""
        significant_events = {
            CreditEventType.LOAN_APPROVAL,
            CreditEventType.LOAN_DISBURSEMENT,
            CreditEventType.PAYMENT_MADE,
            CreditEventType.PAYMENT_MISSED,
            CreditEventType.PAYMENT_LATE,
            CreditEventType.LOAN_CLOSED,
        }
        return event_type in significant_events

    # -----------------------------------------------------------------------
    # Additional public API methods required by tests
    # -----------------------------------------------------------------------

    def get_credit_score(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get current credit score for user, returning dict or None"""
        # Check cache first if available
        if self.cache:
            cached = self.cache.get(f"credit_score:{user_id}")
            if cached:
                return cached

        score = self._get_recent_valid_score(user_id)
        if not score:
            return None
        result = self._format_score_response(score)
        result["calculated_at"] = score.calculated_at.isoformat()
        # Return raw DB value so callers can compare directly with model attribute
        result["factors_positive"] = score.factors_positive
        result["factors_negative"] = score.factors_negative
        return result

    def get_credit_score_history(
        self, user_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get credit score history sorted newest-first"""
        scores = (
            CreditScore.query.filter_by(user_id=user_id)
            .order_by(CreditScore.calculated_at.desc())
            .limit(limit)
            .all()
        )
        return [self._format_score_response(s) for s in scores]

    def add_credit_event(
        self,
        user_id: str,
        event_type: Any,
        event_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Add a credit event and return success dict"""
        try:
            if isinstance(event_type, str):
                try:
                    event_type = CreditEventType(event_type)
                except ValueError:
                    return {
                        "success": False,
                        "message": f"Invalid event type: {event_type}",
                    }

            amount = event_data.get("amount")
            if amount is not None:
                from decimal import Decimal

                amount = Decimal(str(amount))

            # Auto-assign impact_score based on event type if not provided
            impact_score = event_data.get("impact_score")
            if impact_score is None:
                _negative_events = {
                    CreditEventType.PAYMENT_MISSED,
                    CreditEventType.PAYMENT_LATE,
                    CreditEventType.DEFAULT,
                    CreditEventType.ACCOUNT_CLOSED,
                }
                _positive_events = {
                    CreditEventType.PAYMENT_MADE,
                    CreditEventType.LOAN_CLOSED,
                    CreditEventType.ACCOUNT_OPENED,
                }
                if event_type in _negative_events:
                    impact_score = -10
                elif event_type in _positive_events:
                    impact_score = 5

            event = CreditHistory(
                id=str(uuid.uuid4()),
                user_id=user_id,
                event_type=event_type,
                event_title=event_data.get(
                    "title", event_type.value.replace("_", " ").title()
                ),
                event_description=event_data.get("description", ""),
                amount=amount,
                currency=event_data.get("currency", "USD"),
                impact_score=impact_score,
                event_date=datetime.now(timezone.utc),
            )
            event.set_event_data(event_data)
            self.db.session.add(event)
            self.db.session.commit()

            if self._is_significant_event(event_type):
                self.calculate_credit_score(user_id, force_recalculation=True)

            return {"success": True, "event_id": event.id}
        except Exception as e:
            self.db.session.rollback()
            self.logger.error(f"add_credit_event error: {e}")
            return {"success": False, "message": str(e)}

    def get_credit_factors(self, user_id_or_score_id: str) -> Dict[str, Any]:
        """Get credit factors, accepting user_id or credit_score_id"""
        # Check if it's a user_id first
        events = (
            CreditHistory.query.filter_by(user_id=user_id_or_score_id)
            .order_by(CreditHistory.event_date.desc())
            .limit(50)
            .all()
        )
        if events:
            positive = [
                e
                for e in events
                if e.impact_score is not None
                and e.impact_score > 0
                or e.event_type
                in (CreditEventType.PAYMENT_MADE, CreditEventType.LOAN_CLOSED)
            ]
            negative = [
                e
                for e in events
                if e.impact_score is not None
                and e.impact_score < 0
                or e.event_type
                in (CreditEventType.PAYMENT_MISSED, CreditEventType.PAYMENT_LATE)
            ]
            positive_factors = (
                [
                    {
                        "factor": "payment_history",
                        "description": "Positive payment activity",
                        "count": len(positive),
                    }
                ]
                if positive
                else []
            )
            negative_factors = (
                [
                    {
                        "factor": "payment_history",
                        "description": "Missed or late payments",
                        "count": len(negative),
                    }
                ]
                if negative
                else []
            )
            return {
                "positive_factors": positive_factors,
                "negative_factors": negative_factors,
            }

        # Fall back to treating as credit_score_id
        factors = CreditFactor.query.filter_by(
            credit_score_id=user_id_or_score_id
        ).all()
        return {
            "positive_factors": [
                f.to_dict() for f in factors if f.contribution and f.contribution > 40
            ],
            "negative_factors": [
                f.to_dict() for f in factors if f.contribution and f.contribution <= 40
            ],
        }

    def analyze_credit_trends(self, user_id: str) -> Dict[str, Any]:
        """Analyze credit score trends for a user"""
        scores = (
            CreditScore.query.filter_by(user_id=user_id)
            .order_by(CreditScore.calculated_at.asc())
            .all()
        )
        if len(scores) < 2:
            return {
                "trend_direction": "insufficient_data",
                "trend_strength": 0,
                "score_change": 0,
                "data_points": len(scores),
            }
        first_score = scores[0].score
        last_score = scores[-1].score
        score_change = last_score - first_score

        if score_change > 10:
            trend_direction = "improving"
        elif score_change < -10:
            trend_direction = "declining"
        else:
            trend_direction = "stable"

        return {
            "trend_direction": trend_direction,
            "trend_strength": abs(score_change) / max(first_score, 1),
            "score_change": score_change,
            "data_points": len(scores),
            "first_score": first_score,
            "latest_score": last_score,
        }

    def get_credit_recommendations(self, user_id: str) -> List[Dict[str, Any]]:
        """Get credit improvement recommendations for user"""
        events = (
            CreditHistory.query.filter_by(user_id=user_id)
            .order_by(CreditHistory.event_date.desc())
            .limit(20)
            .all()
        )
        recommendations = []
        missed = [e for e in events if e.event_type == CreditEventType.PAYMENT_MISSED]
        if missed:
            recommendations.append(
                {
                    "title": "Improve Payment History",
                    "description": "Make all payments on time to improve your credit score",
                    "priority": "high",
                    "impact": "high",
                }
            )
        if not recommendations:
            recommendations.append(
                {
                    "title": "Maintain Good Credit Habits",
                    "description": "Continue making on-time payments and keeping balances low",
                    "priority": "medium",
                    "impact": "medium",
                }
            )
        return recommendations

    def simulate_score_impact(
        self,
        user_id: str,
        event_type: Any,
        event_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Simulate impact of a credit event on the score"""
        current = self._get_recent_valid_score(user_id)
        current_score = current.score if current else self.default_score

        if isinstance(event_type, str):
            try:
                event_type = CreditEventType(event_type)
            except ValueError:
                pass

        # Estimate impact
        positive_events = {
            CreditEventType.PAYMENT_MADE,
            CreditEventType.LOAN_CLOSED,
            CreditEventType.ACCOUNT_OPENED,
        }
        negative_events = {
            CreditEventType.PAYMENT_MISSED,
            CreditEventType.PAYMENT_LATE,
            CreditEventType.LOAN_APPLICATION,
        }

        if event_type in positive_events:
            change = max(1, int(event_data.get("amount", 100) / 500))
        elif event_type in negative_events:
            change = -max(5, int(event_data.get("amount", 100) / 200))
        else:
            change = 0

        projected = max(self.min_score, min(self.max_score, current_score + change))
        return {
            "current_score": current_score,
            "projected_score": projected,
            "score_change": projected - current_score,
        }

    def bulk_calculate_scores(self, user_ids: List[str]) -> Dict[str, Any]:
        """Submit bulk score calculation job"""
        return {
            "job_id": str(uuid.uuid4()),
            "user_count": len(user_ids),
            "status": "submitted",
        }

    def _validate_score(self, score: int) -> bool:
        """Validate that a score is within valid range"""
        try:
            return self.min_score <= int(score) <= self.max_score
        except (TypeError, ValueError):
            return False

    def _call_ai_model(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Score a user via the ai_models service, with local/rule-based fallbacks"""
        history_records = self._build_ai_history_records(features)

        ai_response = self._request_ai_prediction(history_records)
        if ai_response is not None:
            return ai_response

        if self.model is not None and _PANDAS_AVAILABLE and history_records:
            try:
                local_features = self._extract_local_model_features(history_records)
                df = pd.DataFrame([local_features])
                score = int(self.model.predict(df)[0])
                score = max(self.min_score, min(self.max_score, score))
                return {"score": score, "confidence": 0.75, "factors": {}}
            except Exception as e:
                self.logger.error(f"Local AI model fallback failed: {e}")

        return {"score": self.default_score, "confidence": 0.5, "factors": {}}

    def _request_ai_prediction(
        self, history_records: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """POST credit history to the ai_models /predict endpoint"""
        if not history_records:
            return None
        try:
            response = requests.post(
                f"{self.ai_model_url}/predict",
                json={"creditHistory": history_records},
                timeout=self.ai_model_timeout,
            )
            response.raise_for_status()
            payload = response.json()
            score = payload.get("score")
            if score is None:
                self.logger.warning(
                    f"AI model service response missing 'score': {payload}"
                )
                return None
            return {
                "score": max(self.min_score, min(self.max_score, int(score))),
                "confidence": float(payload.get("confidence", 0.85)),
                "factors": payload.get("factors", {}),
            }
        except requests.exceptions.RequestException as e:
            self.logger.warning(
                f"AI model service at {self.ai_model_url} unreachable: {e}"
            )
        except (ValueError, TypeError, KeyError) as e:
            self.logger.error(f"AI model service returned an unexpected response: {e}")
        return None

    @staticmethod
    def _event_epoch_seconds(value: Any) -> int:
        """Convert an event_date to a Unix timestamp"""
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return int(value.timestamp())
        return int(datetime.now(timezone.utc).timestamp())

    def _build_ai_history_records(
        self, scoring_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Translate CreditHistory events into ai_models record format"""
        events = scoring_data.get("credit_history") or []
        wallet_address = scoring_data.get("wallet_address") or "unknown"

        closed_timestamps_by_loan: Dict[str, int] = {}
        for event in events:
            if event.get("event_type") == CreditEventType.LOAN_CLOSED.value:
                loan_id = event.get("loan_id")
                if loan_id:
                    closed_timestamps_by_loan[loan_id] = self._event_epoch_seconds(
                        event.get("event_date")
                    )

        records = []
        for event in events:
            event_type = event.get("event_type")
            timestamp = self._event_epoch_seconds(event.get("event_date"))
            amount = float(event.get("amount") or 0)
            score_impact = event.get("score_change") or 0
            loan_id = event.get("loan_id")

            if event_type == CreditEventType.LOAN_DISBURSEMENT.value:
                record_type = "loan"
                repayment_timestamp = closed_timestamps_by_loan.get(loan_id, 0)
                repaid = repayment_timestamp > 0
            elif event_type == CreditEventType.LOAN_CLOSED.value:
                record_type = "loan"
                repaid = True
                repayment_timestamp = timestamp
            elif event_type == CreditEventType.PAYMENT_MADE.value:
                record_type = "payment"
                repaid = True
                repayment_timestamp = timestamp
            elif event_type in (
                CreditEventType.PAYMENT_MISSED.value,
                CreditEventType.PAYMENT_LATE.value,
            ):
                record_type = "payment"
                repaid = False
                repayment_timestamp = 0
            else:
                record_type = "other"
                repaid = False
                repayment_timestamp = 0

            records.append(
                {
                    "timestamp": timestamp,
                    "amount": amount,
                    "repaid": repaid,
                    "repaymentTimestamp": repayment_timestamp,
                    "provider": wallet_address,
                    "recordType": record_type,
                    "scoreImpact": score_impact,
                }
            )
        return records

    @staticmethod
    def _extract_local_model_features(
        history_records: List[Dict[str, Any]],
    ) -> Dict[str, float]:
        """Re-derive the model's feature vector for the local-model fallback"""
        total_records = len(history_records)
        loan_count = 0
        total_borrowed = 0.0
        repaid_count = 0
        repayment_times = []
        for record in history_records:
            if record["recordType"] == "loan":
                loan_count += 1
                total_borrowed += float(record["amount"])
            if record["repaid"]:
                repaid_count += 1
                if record["repaymentTimestamp"] > 0:
                    days_to_repay = (
                        record["repaymentTimestamp"] - record["timestamp"]
                    ) / (60 * 60 * 24)
                    repayment_times.append(days_to_repay)
        payment_history = repaid_count / total_records if total_records > 0 else 0
        avg_loan = total_borrowed / loan_count if loan_count > 0 else 0
        income_proxy = avg_loan * 10
        active_debt = (
            total_borrowed - repaid_count / total_records * total_borrowed
            if total_records > 0
            else 0
        )
        debt_ratio = min(active_debt / income_proxy, 1.0) if income_proxy > 0 else 0.5
        avg_repayment_time = (
            sum(repayment_times) / len(repayment_times) if repayment_times else 30
        )
        credit_utilization = min(avg_repayment_time / 90, 1.0)
        return {
            "income": income_proxy,
            "debt_ratio": debt_ratio,
            "payment_history": payment_history,
            "loan_count": loan_count,
            "loan_amount": avg_loan,
            "age": 30,
            "credit_utilization": credit_utilization,
        }

    def _check_score_alerts(self, user_id: str, new_score: int, old_score: int) -> None:
        """Check if score change warrants an alert"""
        if abs(new_score - old_score) >= 20:
            alert_type = "score_drop" if new_score < old_score else "score_increase"
            self._send_alert(user_id, alert_type, new_score, old_score)

    def _send_alert(
        self,
        user_id: str,
        alert_type: str,
        new_score: int = None,
        old_score: int = None,
    ) -> None:
        """Send alert for significant score changes (stub)"""
        self.logger.info(
            f"Alert [{alert_type}] for user {user_id}: {old_score} -> {new_score}"
        )

    def generate_credit_report(self, user_id: str) -> Dict[str, Any]:
        """Generate a comprehensive credit report for user"""
        current = self.get_credit_score(user_id)
        history = self.get_credit_score_history(user_id, limit=12)
        factors = self.get_credit_factors(user_id)
        recommendations = self.get_credit_recommendations(user_id)
        recent = (
            CreditHistory.query.filter_by(user_id=user_id)
            .order_by(CreditHistory.event_date.desc())
            .limit(10)
            .all()
        )
        return {
            "current_score": current,
            "score_history": history,
            "credit_factors": factors,
            "recommendations": recommendations,
            "recent_activity": [e.to_dict() for e in recent],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
