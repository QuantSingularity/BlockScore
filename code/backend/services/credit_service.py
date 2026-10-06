import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

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
from services.ai_client import AIModelClient

RULES_MODEL_NAME = "blockscore-rules"
RULES_MODEL_VERSION = "1.0"
LEGACY_MODEL_PREFIX = "BlockScore_v"
MAX_INLINE_BULK_USERS = 100


class CreditScoringService:

    def __init__(
        self,
        db: Any,
        cache_manager: Any = None,
        ai_client: Optional[AIModelClient] = None,
    ) -> None:
        self.db = db
        self.cache = cache_manager
        self.monitor = None
        self.job_manager = None
        self.blockchain_service = None
        self.logger = logging.getLogger(__name__)
        self.model_version = RULES_MODEL_VERSION
        self.model_name = RULES_MODEL_NAME
        self.min_score = 300
        self.max_score = 850
        self.default_score = 300
        self.ai_client = ai_client or AIModelClient(
            base_url=os.getenv("AI_MODEL_URL", "http://localhost:5001"),
            timeout=float(os.getenv("AI_MODEL_TIMEOUT", "5")),
            api_key=os.getenv("AI_MODEL_API_KEY", ""),
        )
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

    def calculate_credit_score(
        self,
        user_id: str,
        wallet_address: Optional[str] = None,
        force_recalculation: bool = False,
    ) -> Dict[str, Any]:
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
            factors = self._calculate_factor_scores(scoring_data)
            ai_result = self._call_ai_model(scoring_data)
            if ai_result and self._validate_score(ai_result.get("score")):
                overall_score = int(ai_result["score"])
                confidence = float(ai_result.get("confidence", 0.85))
                scoring_source = "ai_model"
                scoring_model_name = ai_result.get("model_name") or self.model_name
                scoring_model_version = ai_result.get("model_version") or "unknown"
                insights = self._normalize_insights(ai_result.get("factors"))
            else:
                overall_score = self._calculate_overall_score(factors)
                confidence = self._rule_based_confidence(factors)
                scoring_source = "rule_based"
                scoring_model_name = RULES_MODEL_NAME
                scoring_model_version = RULES_MODEL_VERSION
                insights = []

            previous_score_record = self._get_recent_valid_score(user_id)
            previous_score_value = (
                previous_score_record.score if previous_score_record else None
            )

            credit_score = self._create_credit_score_record(
                user_id=user_id,
                score=overall_score,
                factors=factors,
                scoring_data=scoring_data,
                model_name=scoring_model_name,
                model_version=scoring_model_version,
                confidence=confidence,
            )
            credit_score.calculation_method = scoring_source
            credit_score.set_factors_positive(
                [i for i in insights if i["impact"] == "positive"]
            )
            credit_score.set_factors_negative(
                [i for i in insights if i["impact"] == "negative"]
            )
            self.db.session.commit()

            self._create_credit_history_event(
                user_id=user_id,
                credit_score_id=credit_score.id,
                event_type=CreditEventType.SCORE_RECALCULATION,
                score_after=overall_score,
            )
            result = self._format_score_response(credit_score)
            result["factors"] = [f.to_dict() for f in factors]
            result["version"] = credit_score.score_version
            result["ai_confidence"] = confidence
            result["scoring"] = {
                "source": scoring_source,
                "model_name": credit_score.model_name,
                "model_version": credit_score.score_version,
                "confidence": confidence,
                "insights": insights,
            }
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
        history = (
            CreditHistory.query.filter_by(user_id=user_id)
            .order_by(CreditHistory.event_date.desc())
            .limit(limit)
            .all()
        )
        return [event.to_dict() for event in history]

    def update_credit_event(
        self, user_id: str, event_type: CreditEventType, event_data: Dict[str, Any]
    ) -> bool:
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

    def is_ai_service_available(self) -> bool:
        return self.ai_client.is_available()

    def _get_recent_valid_score(self, user_id: str) -> Optional[CreditScore]:
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
                "event_date": self._as_utc(event.event_date),
                "score_change": event.score_change or 0,
                "loan_id": event.loan_id,
            }
            for event in credit_events
        ]
        if data["wallet_address"]:
            data["blockchain_data"] = self._get_blockchain_data(data["wallet_address"])
        return data

    @staticmethod
    def _as_utc(value: Any) -> Any:
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    @staticmethod
    def _outstanding_debt(credit_history: List[Dict[str, Any]]) -> float:
        opened: Dict[str, float] = {}
        closed = set()
        anonymous = 0.0
        for event in credit_history:
            event_type = event["event_type"]
            amount = float(event.get("amount") or 0)
            loan_id = event.get("loan_id")
            if event_type in ("loan_approval", "loan_disbursement"):
                if loan_id:
                    opened[loan_id] = max(opened.get(loan_id, 0.0), amount)
                else:
                    anonymous += amount
            elif event_type == "loan_closed":
                if loan_id:
                    closed.add(loan_id)
                else:
                    anonymous = max(0.0, anonymous - amount)
        return sum(a for key, a in opened.items() if key not in closed) + anonymous

    def _get_blockchain_data(self, wallet_address: str) -> Dict[str, Any]:
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
        credit_history = data.get("credit_history", [])
        blockchain_data = data.get("blockchain_data", {})
        if credit_history:
            payment_events = [
                e
                for e in credit_history
                if e["event_type"] in ("payment_made", "payment_missed", "payment_late")
            ]
            if payment_events:
                positive_events = [
                    e for e in payment_events if e["event_type"] == "payment_made"
                ]
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
        credit_history = data.get("credit_history", [])
        profile_data = data.get("profile_data", {})
        annual_income = profile_data.get("annual_income") or 50000
        outstanding_debt = self._outstanding_debt(credit_history)
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
        profile_data = data.get("profile_data", {})
        credit_history = data.get("credit_history", [])
        annual_income = profile_data.get("annual_income") or 50000
        monthly_income = annual_income / 12
        outstanding_debt = self._outstanding_debt(credit_history)
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
        total_contribution = sum(factor.contribution or 0 for factor in factors)
        score = self.min_score + total_contribution / 100 * (
            self.max_score - self.min_score
        )
        return max(self.min_score, min(self.max_score, int(score)))

    @staticmethod
    def _rule_based_confidence(factors: List[CreditFactor]) -> float:
        total_weight = sum(f.weight or 0 for f in factors)
        if total_weight <= 0:
            return 0.5
        weighted = sum((f.confidence_level or 0) * (f.weight or 0) for f in factors)
        return round(weighted / total_weight, 2)

    @staticmethod
    def _normalize_insights(raw: Any) -> List[Dict[str, Any]]:
        if not isinstance(raw, list):
            return []
        insights = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            insights.append(
                {
                    "factor": str(item.get("factor", "")),
                    "impact": str(item.get("impact", "neutral")),
                    "description": str(item.get("description", "")),
                }
            )
        return insights

    def _create_credit_score_record(
        self,
        user_id: str,
        score: int,
        factors: List[CreditFactor],
        scoring_data: Dict[str, Any],
        model_name: Optional[str] = None,
        model_version: Optional[str] = None,
        confidence: float = 0.5,
    ) -> CreditScore:
        try:
            credit_score = CreditScore(
                id=str(uuid.uuid4()),
                user_id=user_id,
                score=score,
                score_version=str(model_version or self.model_version)[:10],
                status=CreditScoreStatus.ACTIVE,
                model_name=str(model_name or self.model_name)[:100],
                model_confidence=confidence,
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
            "model_name": credit_score.model_name,
            "scoring_source": self._scoring_source(credit_score),
            "insights": {
                "positive": credit_score.get_factors_positive(),
                "negative": credit_score.get_factors_negative(),
            },
        }

    @staticmethod
    def _scoring_source(credit_score: CreditScore) -> str:
        if credit_score.calculation_method in ("ai_model", "rule_based"):
            return credit_score.calculation_method
        model_name = credit_score.model_name
        if not model_name or model_name.startswith(LEGACY_MODEL_PREFIX):
            return "unknown"
        return "rule_based" if model_name == RULES_MODEL_NAME else "ai_model"

    def _get_score_grade(self, score: int) -> str:
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

    def _generate_recommendations(self, factors: List[CreditFactor]) -> List[str]:
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
        significant_events = {
            CreditEventType.LOAN_APPROVAL,
            CreditEventType.LOAN_DISBURSEMENT,
            CreditEventType.PAYMENT_MADE,
            CreditEventType.PAYMENT_MISSED,
            CreditEventType.PAYMENT_LATE,
            CreditEventType.LOAN_CLOSED,
        }
        return event_type in significant_events

    def get_credit_score(self, user_id: str) -> Optional[Dict[str, Any]]:
        if self.cache:
            cached = self.cache.get(f"credit_score:{user_id}")
            if cached:
                return cached

        score = self._get_recent_valid_score(user_id)
        if not score:
            return None
        result = self._format_score_response(score)
        result["calculated_at"] = score.calculated_at.isoformat()
        result["factors_positive"] = score.factors_positive
        result["factors_negative"] = score.factors_negative
        return result

    def get_credit_score_history(
        self, user_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
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
        current = self._get_recent_valid_score(user_id)
        current_score = current.score if current else self.default_score

        if isinstance(event_type, str):
            try:
                event_type = CreditEventType(event_type)
            except ValueError:
                pass

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
        unique_ids = list(dict.fromkeys(user_ids))
        if self.job_manager is not None:
            try:
                job_id = self.job_manager.submit_job(
                    "blockscore_jobs.credit_scoring.batch_calculate",
                    args=[unique_ids],
                )
                return {
                    "job_id": job_id,
                    "user_count": len(unique_ids),
                    "status": "submitted",
                }
            except Exception as exc:
                self.logger.warning(f"Background job submission failed: {exc}")
        if len(unique_ids) > MAX_INLINE_BULK_USERS:
            return {
                "job_id": None,
                "user_count": len(unique_ids),
                "status": "rejected",
                "error": "Background job manager unavailable for large batches",
            }
        results = {}
        for user_id in unique_ids:
            outcome = self.calculate_credit_score(user_id, force_recalculation=True)
            results[user_id] = outcome.get("score") if "error" not in outcome else None
        return {
            "job_id": str(uuid.uuid4()),
            "user_count": len(unique_ids),
            "status": "completed",
            "results": results,
        }

    def _validate_score(self, score: int) -> bool:
        try:
            return self.min_score <= int(score) <= self.max_score
        except (TypeError, ValueError):
            return False

    def _call_ai_model(self, features: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        history_records = self._build_ai_history_records(features)
        if not history_records:
            return None
        payload = self.ai_client.predict(history_records)
        return self._parse_ai_payload(payload)

    def _parse_ai_payload(
        self, payload: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        if not payload:
            return None
        try:
            if int(payload.get("recordCount", 1)) <= 0:
                return None
            score = int(payload["score"])
            confidence = float(payload.get("confidence", 0.85))
        except (KeyError, TypeError, ValueError) as exc:
            self.logger.error(
                f"AI model service returned an unexpected response: {exc}"
            )
            return None
        if not self._validate_score(score):
            self.logger.error(
                f"AI model service returned an out-of-range score: {score}"
            )
            return None
        return {
            "score": score,
            "confidence": max(0.0, min(1.0, confidence)),
            "factors": payload.get("factors", []),
            "model_name": payload.get("modelName"),
            "model_version": payload.get("modelVersion"),
        }

    @staticmethod
    def _event_epoch_seconds(value: Any) -> int:
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return int(value.timestamp())
        return int(datetime.now(timezone.utc).timestamp())

    def _build_ai_history_records(
        self, scoring_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        events = scoring_data.get("credit_history") or []
        wallet_address = scoring_data.get("wallet_address") or "unknown"

        closed_at: Dict[str, int] = {}
        disbursed_loans = set()
        for event in events:
            loan_id = event.get("loan_id")
            if not loan_id:
                continue
            event_type = event.get("event_type")
            if event_type == CreditEventType.LOAN_CLOSED.value:
                closed_at[loan_id] = self._event_epoch_seconds(event.get("event_date"))
            elif event_type == CreditEventType.LOAN_DISBURSEMENT.value:
                disbursed_loans.add(loan_id)

        records = []
        for event in events:
            event_type = event.get("event_type")
            timestamp = self._event_epoch_seconds(event.get("event_date"))
            amount = float(event.get("amount") or 0)
            score_impact = event.get("score_change") or 0
            loan_id = event.get("loan_id")

            if event_type == CreditEventType.LOAN_DISBURSEMENT.value:
                record_type = "loan"
                repayment_timestamp = closed_at.get(loan_id, 0) if loan_id else 0
                repaid = repayment_timestamp > 0
            elif event_type == CreditEventType.LOAN_CLOSED.value:
                if loan_id and loan_id in disbursed_loans:
                    continue
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
                continue

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

    def _check_score_alerts(self, user_id: str, new_score: int, old_score: int) -> None:
        if abs(new_score - old_score) >= 20:
            alert_type = "score_drop" if new_score < old_score else "score_increase"
            self._send_alert(user_id, alert_type, new_score, old_score)

    def _send_alert(
        self,
        user_id: str,
        alert_type: str,
        new_score: Optional[int] = None,
        old_score: Optional[int] = None,
    ) -> None:
        self.logger.info(
            f"Alert [{alert_type}] for user {user_id}: {old_score} -> {new_score}"
        )

    def generate_credit_report(self, user_id: str) -> Dict[str, Any]:
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
