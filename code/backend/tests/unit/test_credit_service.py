import os
import sys

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
import compat_stubs  # noqa

"""
Unit tests for Credit Scoring Service
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import patch

from models.credit import CreditEventType, CreditHistory, CreditScore
from models.user import User, UserProfile


class TestCreditScoringService:
    """Test cases for CreditScoringService"""

    def test_calculate_credit_score_new_user(
        self, credit_service: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test credit score calculation for new user"""
        result = credit_service.calculate_credit_score(sample_user.id)
        assert "score" in result
        assert "factors" in result
        assert "version" in result
        assert isinstance(result["score"], int)
        assert 300 <= result["score"] <= 850
        credit_score = CreditScore.query.filter_by(user_id=sample_user.id).first()
        assert credit_score is not None
        assert credit_score.score == result["score"]

    def test_calculate_credit_score_existing_user(
        self, credit_service: Any, db: Any, sample_user: Any, sample_credit_score: Any
    ) -> Any:
        """Test credit score calculation for user with existing score"""
        sample_credit_score.score
        credit_history = CreditHistory(
            user_id=sample_user.id,
            event_type=CreditEventType.PAYMENT_MADE,
            amount=Decimal("500.00"),
            description="On-time payment",
            event_date=datetime.now(timezone.utc),
        )
        db.session.add(credit_history)
        db.session.commit()
        result = credit_service.calculate_credit_score(
            sample_user.id, force_recalculation=True
        )
        assert "score" in result
        assert isinstance(result["score"], int)
        new_score = (
            CreditScore.query.filter_by(user_id=sample_user.id)
            .order_by(CreditScore.calculated_at.desc())
            .first()
        )
        assert new_score is not None

    def test_calculate_credit_score_with_blockchain(
        self, credit_service: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test credit score calculation with blockchain integration"""
        wallet_address = "0x1234567890123456789012345678901234567890"
        with patch.object(credit_service, "blockchain_service") as mock_blockchain:
            mock_blockchain.submit_credit_score_update.return_value = {
                "transaction_id": "test_tx_id",
                "transaction_hash": "0xabcdef",
                "status": "submitted",
            }
            result = credit_service.calculate_credit_score(
                sample_user.id, wallet_address=wallet_address
            )
        assert "score" in result
        assert "blockchain_transaction" in result
        assert result["blockchain_transaction"]["status"] == "submitted"

    def test_get_credit_score_current(
        self, credit_service: Any, db: Any, sample_user: Any, sample_credit_score: Any
    ) -> Any:
        """Test getting current credit score"""
        result = credit_service.get_credit_score(sample_user.id)
        assert result is not None
        assert result["score"] == sample_credit_score.score
        assert result["calculated_at"] is not None
        assert result["factors_positive"] == sample_credit_score.factors_positive
        assert result["factors_negative"] == sample_credit_score.factors_negative

    def test_get_credit_score_nonexistent(
        self, credit_service: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test getting credit score for user without score"""
        result = credit_service.get_credit_score(sample_user.id)
        assert result is None

    def test_get_credit_score_history(
        self, credit_service: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test getting credit score history"""
        scores = []
        for i, score_value in enumerate([700, 720, 750]):
            credit_score = CreditScore(
                user_id=sample_user.id,
                score=score_value,
                score_version="v2.0",
                calculated_at=datetime.now(timezone.utc) - timedelta(days=30 - i * 10),
            )
            scores.append(credit_score)
            db.session.add(credit_score)
        db.session.commit()
        history = credit_service.get_credit_score_history(sample_user.id, limit=5)
        assert len(history) == 3
        assert history[0]["score"] == 750
        assert history[-1]["score"] == 700

    def test_add_credit_event_payment(
        self, credit_service: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test adding payment credit event"""
        event_data = {
            "amount": 500.0,
            "description": "Monthly payment",
            "payment_date": datetime.now(timezone.utc).isoformat(),
        }
        result = credit_service.add_credit_event(
            sample_user.id, CreditEventType.PAYMENT_MADE, event_data
        )
        assert result["success"] is True
        assert "event_id" in result
        event = CreditHistory.query.filter_by(user_id=sample_user.id).first()
        assert event is not None
        assert event.event_type == CreditEventType.PAYMENT_MADE
        assert event.amount == Decimal("500.00")

    def test_add_credit_event_missed_payment(
        self, credit_service: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test adding missed payment event"""
        event_data = {
            "amount": 200.0,
            "description": "Missed payment",
            "due_date": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
        }
        result = credit_service.add_credit_event(
            sample_user.id, CreditEventType.PAYMENT_MISSED, event_data
        )
        assert result["success"] is True
        event = CreditHistory.query.filter_by(user_id=sample_user.id).first()
        assert event is not None
        assert event.event_type == CreditEventType.PAYMENT_MISSED
        assert event.impact_score < 0

    def test_add_credit_event_new_account(
        self, credit_service: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test adding new account event"""
        event_data = {
            "account_type": "credit_card",
            "credit_limit": 5000.0,
            "description": "New credit card account",
        }
        result = credit_service.add_credit_event(
            sample_user.id, CreditEventType.ACCOUNT_OPENED, event_data
        )
        assert result["success"] is True
        event = CreditHistory.query.filter_by(user_id=sample_user.id).first()
        assert event is not None
        assert event.event_type == CreditEventType.ACCOUNT_OPENED

    def test_get_credit_factors_positive(
        self, credit_service: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test getting positive credit factors"""
        events = [
            CreditHistory(
                user_id=sample_user.id,
                event_type=CreditEventType.PAYMENT_MADE,
                amount=Decimal("300.00"),
                impact_score=5,
                event_date=datetime.now(timezone.utc) - timedelta(days=i),
            )
            for i in range(5)
        ]
        db.session.add_all(events)
        db.session.commit()
        factors = credit_service.get_credit_factors(sample_user.id)
        assert "positive_factors" in factors
        assert "negative_factors" in factors
        assert len(factors["positive_factors"]) > 0
        assert "payment_history" in [f["factor"] for f in factors["positive_factors"]]

    def test_get_credit_factors_negative(
        self, credit_service: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test getting negative credit factors"""
        events = [
            CreditHistory(
                user_id=sample_user.id,
                event_type=CreditEventType.PAYMENT_MISSED,
                amount=Decimal("200.00"),
                impact_score=-10,
                event_date=datetime.now(timezone.utc) - timedelta(days=i),
            )
            for i in range(3)
        ]
        db.session.add_all(events)
        db.session.commit()
        factors = credit_service.get_credit_factors(sample_user.id)
        assert "negative_factors" in factors
        assert len(factors["negative_factors"]) > 0
        assert "payment_history" in [f["factor"] for f in factors["negative_factors"]]

    def test_analyze_credit_trends(
        self, credit_service: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test credit trend analysis"""
        base_date = datetime.now(timezone.utc) - timedelta(days=180)
        scores = [680, 690, 710, 720, 750]
        for i, score in enumerate(scores):
            credit_score = CreditScore(
                user_id=sample_user.id,
                score=score,
                score_version="v2.0",
                calculated_at=base_date + timedelta(days=i * 30),
            )
            db.session.add(credit_score)
        db.session.commit()
        trends = credit_service.analyze_credit_trends(sample_user.id)
        assert "trend_direction" in trends
        assert "trend_strength" in trends
        assert "score_change" in trends
        assert trends["trend_direction"] == "improving"
        assert trends["score_change"] > 0

    def test_get_credit_recommendations(
        self, credit_service: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test getting credit improvement recommendations"""
        credit_history = CreditHistory(
            user_id=sample_user.id,
            event_type=CreditEventType.PAYMENT_MISSED,
            amount=Decimal("150.00"),
            impact_score=-15,
            event_date=datetime.now(timezone.utc) - timedelta(days=10),
        )
        db.session.add(credit_history)
        db.session.commit()
        recommendations = credit_service.get_credit_recommendations(sample_user.id)
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        payment_rec = next(
            (r for r in recommendations if "payment" in r["title"].lower()), None
        )
        assert payment_rec is not None
        assert "priority" in payment_rec
        assert "description" in payment_rec

    def test_simulate_score_impact(
        self, credit_service: Any, db: Any, sample_user: Any, sample_credit_score: Any
    ) -> Any:
        """Test simulating impact of credit events"""
        current_score = sample_credit_score.score
        positive_simulation = credit_service.simulate_score_impact(
            sample_user.id, CreditEventType.PAYMENT_MADE, {"amount": 500.0}
        )
        assert "projected_score" in positive_simulation
        assert "score_change" in positive_simulation
        assert positive_simulation["projected_score"] >= current_score
        negative_simulation = credit_service.simulate_score_impact(
            sample_user.id, CreditEventType.PAYMENT_MISSED, {"amount": 200.0}
        )
        assert negative_simulation["projected_score"] <= current_score
        assert negative_simulation["score_change"] < 0

    def test_bulk_score_calculation(self, credit_service: Any, db: Any) -> Any:
        """Test bulk credit score calculation"""
        users = []
        for i in range(3):
            user = User(
                email=f"user{i}@example.com",
                password_hash="hashed_password",
                is_active=True,
                email_verified=True,
            )
            profile = UserProfile(user=user, first_name=f"User{i}", last_name="Test")
            users.append(user)
            db.session.add(user)
            db.session.add(profile)
        db.session.commit()
        user_ids = [user.id for user in users]
        with patch.object(credit_service, "job_manager") as mock_job_manager:
            mock_job_manager.submit_job.return_value = "job_id_123"
            result = credit_service.bulk_calculate_scores(user_ids)
        assert "job_id" in result
        assert result["user_count"] == 3
        assert result["status"] == "submitted"

    def test_credit_score_caching(
        self, credit_service: Any, db: Any, sample_user: Any, sample_credit_score: Any
    ) -> Any:
        """Test credit score caching functionality"""
        credit_service.get_credit_score(sample_user.id)
        with patch.object(credit_service.cache, "get") as mock_cache_get:
            mock_cache_get.return_value = {
                "score": sample_credit_score.score,
                "calculated_at": sample_credit_score.calculated_at.isoformat(),
                "cached": True,
            }
            result2 = credit_service.get_credit_score(sample_user.id)
        assert result2["cached"] is True
        assert result2["score"] == sample_credit_score.score

    def test_credit_score_validation(self, credit_service: Any) -> Any:
        """Test credit score validation"""
        assert credit_service._validate_score(750) is True
        assert credit_service._validate_score(300) is True
        assert credit_service._validate_score(850) is True
        assert credit_service._validate_score(299) is False
        assert credit_service._validate_score(851) is False
        assert credit_service._validate_score(-100) is False

    def test_ai_model_integration(
        self, credit_service: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test AI model integration for scoring"""
        with patch.object(credit_service, "_call_ai_model") as mock_ai:
            mock_ai.return_value = {
                "score": 725,
                "confidence": 0.85,
                "factors": {
                    "payment_history": 0.35,
                    "credit_utilization": 0.3,
                    "credit_age": 0.15,
                    "credit_mix": 0.1,
                    "new_credit": 0.1,
                },
            }
            result = credit_service.calculate_credit_score(sample_user.id)
        assert result["score"] == 725
        assert "ai_confidence" in result
        assert result["ai_confidence"] == 0.85

    def test_credit_monitoring_alerts(
        self, credit_service: Any, db: Any, sample_user: Any, sample_credit_score: Any
    ) -> Any:
        """Test credit monitoring and alerts"""
        original_score = sample_credit_score.score
        new_score = original_score - 50
        with patch.object(credit_service, "_send_alert") as mock_alert:
            credit_service._check_score_alerts(
                sample_user.id, new_score, original_score
            )
        mock_alert.assert_called_once()
        alert_call = mock_alert.call_args[0]
        assert "score_drop" in alert_call[1]

    def test_credit_report_generation(
        self, credit_service: Any, db: Any, sample_user: Any, sample_credit_score: Any
    ) -> Any:
        """Test comprehensive credit report generation"""
        events = [
            CreditHistory(
                user_id=sample_user.id,
                event_type=CreditEventType.PAYMENT_MADE,
                amount=Decimal("300.00"),
                event_date=datetime.now(timezone.utc) - timedelta(days=30),
            ),
            CreditHistory(
                user_id=sample_user.id,
                event_type=CreditEventType.ACCOUNT_OPENED,
                description="New credit card",
                event_date=datetime.now(timezone.utc) - timedelta(days=60),
            ),
        ]
        db.session.add_all(events)
        db.session.commit()
        report = credit_service.generate_credit_report(sample_user.id)
        assert "current_score" in report
        assert "score_history" in report
        assert "credit_factors" in report
        assert "recommendations" in report
        assert "recent_activity" in report
        assert report["current_score"]["score"] == sample_credit_score.score

    def test_error_handling(self, credit_service: Any, db: Any) -> Any:
        """Test error handling for invalid inputs"""
        result = credit_service.calculate_credit_score("non-existent-user-id")
        assert "error" in result
        result = credit_service.add_credit_event("user-id", "invalid_event_type", {})
        assert result["success"] is False

    def test_performance_monitoring(
        self, credit_service: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test performance monitoring integration"""
        with patch.object(credit_service, "monitor") as mock_monitor:
            credit_service.calculate_credit_score(sample_user.id)
        mock_monitor.record_metric.assert_called()
        metric_calls = mock_monitor.record_metric.call_args_list
        timing_call = next(
            (call for call in metric_calls if "duration" in call[0][0]), None
        )
        assert timing_call is not None
