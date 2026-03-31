"""
Credit Scoring Service for BlockScore Backend
Advanced AI-powered credit scoring with blockchain integration
"""

import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import joblib
import pandas as pd
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

    def __init__(self, db: Any) -> None:
        self.db = db
        self.logger = logging.getLogger(__name__)
        self.model = None
        self.model_version = "1.0"
        self.model_name = "BlockScore_v1.0"
        self.min_score = 300
        self.max_score = 850
        self.default_score = 300
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
        try:
            user = db.session.get(User, user_id)
            if not user:
                raise ValueError("User not found")
            if not force_recalculation:
                recent_score = self._get_recent_valid_score(user_id)
                if recent_score:
                    return self._format_score_response(recent_score)
            scoring_data = self._gather_scoring_data(user, wallet_address)
            factors = self._calculate_factor_scores(scoring_data)
            overall_score = self._calculate_overall_score(factors)
            credit_score = self._create_credit_score_record(
                user_id=user_id,
                score=overall_score,
                factors=factors,
                scoring_data=scoring_data,
            )
            self._create_credit_history_event(
                user_id=user_id,
                credit_score_id=credit_score.id,
                event_type=CreditEventType.SCORE_RECALCULATION,
                score_after=overall_score,
            )
            return self._format_score_response(credit_score)
        except Exception as e:
            self.logger.error(
                f"Credit score calculation failed for user {user_id}: {e}"
            )
            raise e

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
        """Check if AI model is loaded"""
        return self.model is not None

    def _load_model(self) -> Any:
        """Load AI model for credit scoring"""
        try:
            model_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "ai_models",
                "credit_scoring_model.pkl",
            )
            self.model = joblib.load(model_path)
            self.logger.info("Credit scoring model loaded successfully")
        except Exception as e:
            self.logger.warning(
                f"Could not load AI model: {e}. Using rule-based scoring."
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
                "account_age_days": (datetime.now(timezone.utc) - user.created_at).days,
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
            features_df = pd.DataFrame([feature_dict])
            predicted_score = self.model.predict(features_df)[0]
            return max(self.min_score, min(self.max_score, int(predicted_score)))
        except Exception as e:
            self.logger.error(f"Model prediction failed: {e}")
            return self._calculate_overall_score(factors)

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
