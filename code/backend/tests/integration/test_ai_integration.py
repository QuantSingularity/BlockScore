import os
import sys
import threading
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock

import pytest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from models.credit import CreditEventType, CreditHistory, CreditScore
from services.ai_client import AIModelClient
from services.credit_service import CreditScoringService

AI_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "ai_models", "src")
)


def add_events(db: Any, user_id: str, specs: Any) -> None:
    now = datetime.now(timezone.utc)
    for index, (event_type, amount, days_ago, loan_id, score_change) in enumerate(
        specs
    ):
        db.session.add(
            CreditHistory(
                id=str(uuid.uuid4()),
                user_id=user_id,
                event_type=event_type,
                event_title=event_type.value,
                amount=Decimal(str(amount)),
                event_date=now - timedelta(days=days_ago, seconds=index),
                loan_id=loan_id,
                score_change=score_change,
            )
        )
    db.session.commit()


GOOD = [
    (CreditEventType.LOAN_DISBURSEMENT, 5000, 400, "loan-a", 0),
    (CreditEventType.LOAN_CLOSED, 5000, 300, "loan-a", 0),
    (CreditEventType.PAYMENT_MADE, 300, 200, None, 5),
    (CreditEventType.PAYMENT_MADE, 300, 100, None, 5),
]
BAD = [
    (CreditEventType.LOAN_DISBURSEMENT, 9000, 300, "loan-b", 0),
    (CreditEventType.PAYMENT_MISSED, 300, 200, None, -10),
    (CreditEventType.PAYMENT_LATE, 300, 100, None, -10),
]


def stub_client(payload: Any) -> AIModelClient:
    client = AIModelClient("http://ai.test", retries=0)
    client.predict = MagicMock(return_value=payload)
    return client


class TestHistoryTranslation:
    def test_disbursement_with_matching_close_is_one_repaid_loan(
        self, credit_service: Any
    ) -> Any:
        now = datetime.now(timezone.utc)
        data = {
            "wallet_address": "0xabc",
            "credit_history": [
                {
                    "event_type": "loan_disbursement",
                    "amount": 100.0,
                    "event_date": now - timedelta(days=30),
                    "score_change": 0,
                    "loan_id": "L1",
                },
                {
                    "event_type": "loan_closed",
                    "amount": 100.0,
                    "event_date": now - timedelta(days=5),
                    "score_change": 0,
                    "loan_id": "L1",
                },
                {
                    "event_type": "credit_inquiry",
                    "amount": 0,
                    "event_date": now,
                    "score_change": 0,
                    "loan_id": None,
                },
            ],
        }
        records = credit_service._build_ai_history_records(data)
        assert len(records) == 1
        assert records[0]["recordType"] == "loan"
        assert records[0]["repaid"] is True
        assert records[0]["repaymentTimestamp"] > records[0]["timestamp"]

    def test_unrelated_events_are_not_sent(self, credit_service: Any) -> Any:
        data = {
            "credit_history": [
                {
                    "event_type": "score_recalculation",
                    "amount": 0,
                    "event_date": datetime.now(timezone.utc),
                    "score_change": 0,
                }
            ]
        }
        assert credit_service._build_ai_history_records(data) == []

    def test_missed_payment_is_unrepaid_payment(self, credit_service: Any) -> Any:
        data = {
            "credit_history": [
                {
                    "event_type": "payment_missed",
                    "amount": 50,
                    "event_date": datetime.now(timezone.utc),
                    "score_change": -10,
                }
            ]
        }
        record = credit_service._build_ai_history_records(data)[0]
        assert record["recordType"] == "payment"
        assert record["repaid"] is False
        assert record["repaymentTimestamp"] == 0


class TestAiScoringPath:
    def test_ai_score_is_persisted_with_model_metadata(
        self, db: Any, sample_user: Any
    ) -> Any:
        add_events(db, sample_user.id, GOOD)
        service = CreditScoringService(
            db,
            ai_client=stub_client(
                {
                    "score": 777,
                    "confidence": 0.9,
                    "factors": [
                        {
                            "factor": "Excellent payment history",
                            "impact": "positive",
                            "description": "d",
                            "value": 1,
                        }
                    ],
                    "recordCount": 3,
                    "modelName": "blockscore-xgboost",
                    "modelVersion": "2.0.0",
                }
            ),
        )
        result = service.calculate_credit_score(
            sample_user.id, force_recalculation=True
        )
        assert result["score"] == 777
        assert result["scoring"]["source"] == "ai_model"
        assert result["scoring"]["model_name"] == "blockscore-xgboost"
        assert result["scoring"]["insights"][0]["factor"] == "Excellent payment history"
        assert result["ai_confidence"] == 0.9
        assert (
            result["insights"]["positive"][0]["factor"] == "Excellent payment history"
        )
        assert result["insights"]["negative"] == []
        assert result["scoring_source"] == "ai_model"
        stored = (
            CreditScore.query.filter_by(user_id=sample_user.id)
            .order_by(CreditScore.calculated_at.desc())
            .first()
        )
        assert stored.score == 777
        assert stored.model_name == "blockscore-xgboost"
        assert stored.score_version == "2.0.0"
        assert stored.model_confidence == 0.9
        assert len(result["factors"]) == 8

    def test_cached_response_exposes_scoring_source(
        self, db: Any, sample_user: Any
    ) -> Any:
        add_events(db, sample_user.id, GOOD)
        service = CreditScoringService(
            db,
            ai_client=stub_client(
                {
                    "score": 700,
                    "confidence": 0.8,
                    "factors": [],
                    "recordCount": 3,
                    "modelName": "m",
                    "modelVersion": "1",
                }
            ),
        )
        service.calculate_credit_score(sample_user.id, force_recalculation=True)
        cached = service.calculate_credit_score(sample_user.id)
        assert cached["score"] == 700
        assert cached["scoring_source"] == "ai_model"
        assert set(cached["insights"]) == {"positive", "negative"}

    @pytest.mark.parametrize(
        "payload",
        [
            None,
            {"score": 99999, "confidence": 0.9},
            {"score": "abc"},
            {"confidence": 0.9},
            {"score": 500, "recordCount": 0},
        ],
    )
    def test_invalid_or_missing_ai_response_falls_back_to_rules(
        self, db: Any, sample_user: Any, payload: Any
    ) -> Any:
        add_events(db, sample_user.id, GOOD)
        service = CreditScoringService(db, ai_client=stub_client(payload))
        result = service.calculate_credit_score(
            sample_user.id, force_recalculation=True
        )
        assert "error" not in result
        assert result["scoring"]["source"] == "rule_based"
        assert result["scoring"]["model_name"] == "blockscore-rules"
        assert 300 <= result["score"] <= 850

    def test_ai_score_equal_to_floor_is_accepted(
        self, db: Any, sample_user: Any
    ) -> Any:
        add_events(db, sample_user.id, BAD)
        service = CreditScoringService(
            db,
            ai_client=stub_client(
                {
                    "score": 300,
                    "confidence": 0.7,
                    "factors": [],
                    "recordCount": 3,
                    "modelName": "m",
                    "modelVersion": "1",
                }
            ),
        )
        result = service.calculate_credit_score(
            sample_user.id, force_recalculation=True
        )
        assert result["score"] == 300
        assert result["scoring"]["source"] == "ai_model"

    def test_user_without_history_uses_rules_without_calling_ai(
        self, db: Any, sample_user: Any
    ) -> Any:
        client = stub_client({"score": 700})
        service = CreditScoringService(db, ai_client=client)
        result = service.calculate_credit_score(
            sample_user.id, force_recalculation=True
        )
        assert result["scoring"]["source"] == "rule_based"
        client.predict.assert_not_called()


class TestRuleBasedFactors:
    def test_closed_loans_do_not_count_as_outstanding_debt(self) -> Any:
        events = [
            {"event_type": "loan_disbursement", "amount": 1000.0, "loan_id": "a"},
            {"event_type": "loan_approval", "amount": 1000.0, "loan_id": "a"},
            {"event_type": "loan_closed", "amount": 1000.0, "loan_id": "a"},
            {"event_type": "loan_disbursement", "amount": 400.0, "loan_id": "b"},
        ]
        assert CreditScoringService._outstanding_debt(events) == 400.0

    def test_payment_ratio_ignores_unrelated_events(self, credit_service: Any) -> Any:
        data = {
            "credit_history": [
                {
                    "event_type": "payment_made",
                    "amount": 1,
                    "score_change": 5,
                    "event_date": datetime.now(timezone.utc),
                },
                {
                    "event_type": "payment_missed",
                    "amount": 1,
                    "score_change": -10,
                    "event_date": datetime.now(timezone.utc),
                },
                {
                    "event_type": "credit_inquiry",
                    "amount": 0,
                    "score_change": 0,
                    "event_date": datetime.now(timezone.utc),
                },
            ],
            "blockchain_data": {},
        }
        factor = credit_service._calculate_payment_history_factor(data)
        assert factor.normalized_value == 0.5


class TestBulkScoring:
    def test_bulk_uses_job_manager_when_present(self, credit_service: Any) -> Any:
        credit_service.job_manager = MagicMock()
        credit_service.job_manager.submit_job.return_value = "job-1"
        result = credit_service.bulk_calculate_scores(["a", "b", "a"])
        assert result == {"job_id": "job-1", "user_count": 2, "status": "submitted"}

    def test_bulk_runs_inline_for_small_batches(self, db: Any, sample_user: Any) -> Any:
        service = CreditScoringService(db, ai_client=stub_client(None))
        result = service.bulk_calculate_scores([sample_user.id])
        assert result["status"] == "completed"
        assert 300 <= result["results"][sample_user.id] <= 850

    def test_bulk_rejects_large_batches_without_job_manager(
        self, credit_service: Any
    ) -> Any:
        result = credit_service.bulk_calculate_scores([str(i) for i in range(500)])
        assert result["status"] == "rejected"


class TestLiveAiService:
    @pytest.fixture(scope="class")
    def live_url(self) -> Any:
        pytest.importorskip("xgboost")
        pytest.importorskip("pandas")
        sys.path.insert(0, AI_DIR)
        try:
            from blockscore_ai.api import create_app as create_ai_app
        except Exception as exc:
            pytest.skip(f"ai_models server unavailable: {exc}")
        from werkzeug.serving import make_server

        httpd = make_server("127.0.0.1", 0, create_ai_app(), threaded=True)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        yield f"http://127.0.0.1:{httpd.server_port}"
        httpd.shutdown()
        thread.join(timeout=5)
        sys.path.remove(AI_DIR)
        for name in [m for m in sys.modules if m.startswith("blockscore_ai")]:
            sys.modules.pop(name, None)

    def test_end_to_end_scoring_over_http(
        self, db: Any, sample_user: Any, live_url: str
    ) -> Any:
        add_events(db, sample_user.id, GOOD)
        service = CreditScoringService(
            db, ai_client=AIModelClient(live_url, timeout=10, retries=0)
        )
        assert service.is_ai_service_available() is True
        result = service.calculate_credit_score(
            sample_user.id, force_recalculation=True
        )
        assert result["scoring"]["source"] == "ai_model"
        assert result["scoring"]["model_name"]
        assert 300 <= result["score"] <= 850

    def test_good_history_outscores_bad_history_over_http(
        self, db: Any, live_url: str
    ) -> Any:
        from models.user import User, UserStatus

        scores = {}
        for label, specs in (("good", GOOD), ("bad", BAD)):
            user = User(
                id=str(uuid.uuid4()),
                email=f"{label}-{uuid.uuid4().hex[:6]}@example.com",
                password_hash="x",
                status=UserStatus.ACTIVE,
                is_active=True,
                email_verified=True,
            )
            db.session.add(user)
            db.session.commit()
            add_events(db, user.id, specs)
            service = CreditScoringService(
                db, ai_client=AIModelClient(live_url, timeout=10, retries=0)
            )
            scores[label] = service.calculate_credit_score(
                user.id, force_recalculation=True
            )["score"]
        assert scores["good"] > scores["bad"]

    def test_unreachable_service_falls_back_cleanly(
        self, db: Any, sample_user: Any
    ) -> Any:
        add_events(db, sample_user.id, GOOD)
        service = CreditScoringService(
            db, ai_client=AIModelClient("http://127.0.0.1:9", timeout=1, retries=0)
        )
        assert service.is_ai_service_available() is False
        result = service.calculate_credit_score(
            sample_user.id, force_recalculation=True
        )
        assert result["scoring"]["source"] == "rule_based"


class TestScoreEndpointWithLiveAi:
    @pytest.fixture()
    def live_url(self) -> Any:
        pytest.importorskip("xgboost")
        sys.path.insert(0, AI_DIR)
        try:
            from blockscore_ai.api import create_app as create_ai_app
        except Exception as exc:
            pytest.skip(f"ai_models server unavailable: {exc}")
        from werkzeug.serving import make_server

        httpd = make_server("127.0.0.1", 0, create_ai_app(), threaded=True)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        yield f"http://127.0.0.1:{httpd.server_port}"
        httpd.shutdown()
        thread.join(timeout=5)
        sys.path.remove(AI_DIR)
        for name in [m for m in sys.modules if m.startswith("blockscore_ai")]:
            sys.modules.pop(name, None)

    def test_calculate_score_endpoint_returns_ai_metadata(
        self, app: Any, client: Any, db: Any, sample_user: Any, live_url: str
    ) -> Any:
        add_events(db, sample_user.id, GOOD)
        login = client.post(
            "/api/auth/login",
            json={"email": sample_user.email, "password": "TestPassword123!"},
        )
        assert login.status_code == 200
        token = login.get_json()["tokens"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        wallet = "0x1234567890123456789012345678901234567890"

        credit_service = app.extensions["credit_service"]
        original = credit_service.ai_client
        credit_service.ai_client = AIModelClient(live_url, timeout=10, retries=0)
        try:
            response = client.post(
                "/api/credit/calculate-score",
                json={"walletAddress": wallet, "force_recalculation": True},
                headers=headers,
            )
            health = client.get("/api/health")
        finally:
            credit_service.ai_client = original
        assert response.status_code == 200
        data = response.get_json()["data"]
        assert data["scoring"]["source"] == "ai_model"
        assert data["scoring_source"] == "ai_model"
        assert 300 <= data["score"] <= 850
        assert data["confidence"] > 0
        assert "insights" in data
        assert health.get_json()["services"]["ai_model"] in ("up", "down")
