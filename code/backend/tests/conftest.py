import os
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Any

from app import create_app
from extensions import db as _db
from models.audit import AuditEventType, AuditLog, AuditSeverity
from models.credit import CreditScore, CreditScoreStatus
from models.loan import LoanApplication, LoanStatus, LoanType
from models.user import KYCStatus, User, UserProfile, UserStatus
from services.auth_service import AuthenticationService
from services.blockchain_service import BlockchainService
from services.compliance_service import ComplianceService
from services.credit_service import CreditScoringService
from utils.cache import CacheManager
from utils.monitoring import PerformanceMonitor

try:
    _has_redis = True
except ImportError:
    _has_redis = False


@pytest.fixture(scope="session")
def app() -> Any:
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.environ["FLASK_ENV"] = "testing"
    os.environ["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    os.environ["JWT_SECRET_KEY"] = "test-jwt-secret"
    os.environ["SECRET_KEY"] = "test-secret-key"

    _app = create_app("testing")
    _app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{db_path}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY="test-secret-key",
        JWT_SECRET_KEY="test-jwt-secret",
        REDIS_URL="redis://localhost:6379/15",
        WTF_CSRF_ENABLED=False,
        BCRYPT_LOG_ROUNDS=4,
        RATELIMIT_ENABLED=False,
    )

    with _app.app_context():
        _db.create_all()
        yield _app
        _db.session.remove()
        _db.drop_all()

    os.close(db_fd)
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture(scope="session", autouse=True)
def _push_app_context() -> Any:
    import tempfile

    _app = create_app("testing")
    db_fd, db_path = tempfile.mkstemp(suffix="_ctx.db")
    _app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{db_path}",
        SECRET_KEY="ctx-secret",
        JWT_SECRET_KEY="ctx-jwt-secret",
        RATELIMIT_ENABLED=False,
    )
    ctx = _app.app_context()
    ctx.push()
    _db.create_all()
    yield
    ctx.pop()
    import os as _os

    try:
        _os.close(db_fd)
        _os.unlink(db_path)
    except Exception:
        pass


@pytest.fixture(scope="function")
def db(app: Any) -> Any:
    _db.create_all()
    yield _db
    _db.session.remove()
    for table in reversed(_db.metadata.sorted_tables):
        try:
            _db.session.execute(table.delete())
        except Exception:
            _db.session.rollback()
    _db.session.commit()


@pytest.fixture(scope="function")
def client(app: Any) -> Any:
    return app.test_client()


@pytest.fixture(scope="function")
def runner(app: Any) -> Any:
    return app.test_cli_runner()


@pytest.fixture
def mock_redis() -> Any:
    mock_client = Mock()
    mock_client.ping.return_value = True
    mock_client.get.return_value = None
    mock_client.set.return_value = True
    mock_client.setex.return_value = True
    mock_client.delete.return_value = 1
    mock_client.exists.return_value = False
    mock_client.expire.return_value = True
    mock_client.ttl.return_value = 3600
    mock_client.keys.return_value = []
    mock_client.mget.return_value = []
    mock_client.incr.return_value = 1
    mock_client.decr.return_value = 0
    return mock_client


@pytest.fixture
def cache_manager(mock_redis: Any) -> Any:
    return CacheManager(redis_client=mock_redis)


@pytest.fixture
def performance_monitor() -> Any:
    return PerformanceMonitor(retention_hours=1)


@pytest.fixture
def sample_user_data() -> Any:
    return {
        "email": "test@example.com",
        "password": "TestPassword123!",
        "first_name": "John",
        "last_name": "Doe",
        "date_of_birth": "1990-01-01",
        "phone_number": "+1234567890",
        "address_line1": "123 Test Street",
        "city": "Test City",
        "state": "TS",
        "postal_code": "12345",
        "country": "US",
    }


@pytest.fixture
def sample_user(db: Any, sample_user_data: Any) -> Any:
    from flask_bcrypt import generate_password_hash

    email = sample_user_data.get("email", "test@example.com")
    user = User(
        id=str(uuid.uuid4()),
        email=email,
        password_hash=generate_password_hash("TestPassword123!").decode("utf-8"),
        status=UserStatus.ACTIVE,
        is_active=True,
        email_verified=True,
    )
    db.session.add(user)
    db.session.flush()

    dob_raw = sample_user_data.get("date_of_birth")
    dob = datetime.strptime(dob_raw, "%Y-%m-%d").date() if dob_raw else None

    profile = UserProfile(
        id=str(uuid.uuid4()),
        user_id=user.id,
        first_name=sample_user_data.get("first_name", "John"),
        last_name=sample_user_data.get("last_name", "Doe"),
        date_of_birth=dob,
        phone_number=sample_user_data.get("phone_number")
        or sample_user_data.get("phone"),
        address_line1=sample_user_data.get("address_line1", ""),
        street_address=sample_user_data.get("address_line1", ""),
        city=sample_user_data.get("city", ""),
        state=sample_user_data.get("state", ""),
        postal_code=sample_user_data.get("postal_code", ""),
        country=sample_user_data.get("country", "US"),
        kyc_status=KYCStatus.APPROVED,
    )
    db.session.add(profile)
    db.session.commit()
    return user


@pytest.fixture
def sample_credit_score(db: Any, sample_user: Any) -> Any:
    credit_score = CreditScore(
        user_id=sample_user.id,
        score=750,
        score_version="v2.0",
        status=CreditScoreStatus.ACTIVE,
        calculated_at=datetime.now(timezone.utc),
    )
    credit_score.set_factors_positive(["payment_history", "credit_utilization"])
    credit_score.set_factors_negative(["credit_age"])
    db.session.add(credit_score)
    db.session.commit()
    return credit_score


@pytest.fixture
def sample_loan_application(db: Any, sample_user: Any) -> Any:
    loan_app = LoanApplication(
        user_id=sample_user.id,
        application_number=LoanApplication.generate_application_number(),
        loan_type=LoanType.PERSONAL,
        requested_amount=10000.0,
        requested_term_months=36,
        requested_rate=12.5,
        purpose="debt_consolidation",
        employment_status="employed",
        annual_income=75000.0,
        monthly_expenses=3000.0,
        status=LoanStatus.SUBMITTED,
    )
    db.session.add(loan_app)
    db.session.commit()
    return loan_app


@pytest.fixture
def auth_service(db: Any, app: Any) -> Any:
    from extensions import bcrypt

    return AuthenticationService(db, bcrypt)


@pytest.fixture
def credit_service(db: Any, mock_redis: Any, app: Any) -> Any:
    from unittest.mock import Mock

    svc = CreditScoringService(db)
    mock_cache = Mock()
    mock_cache.get.return_value = None
    mock_cache.set.return_value = True
    svc.cache = mock_cache
    return svc


@pytest.fixture
def compliance_service(db: Any) -> Any:
    return ComplianceService(db)


@pytest.fixture
def mock_blockchain_config() -> Any:
    return {
        "BLOCKCHAIN_PROVIDER_URL": "http://localhost:8545",
        "BLOCKCHAIN_FROM_ADDRESS": "0x1234567890123456789012345678901234567890",
        "BLOCKCHAIN_PRIVATE_KEY": "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "CREDIT_SCORE_CONTRACT_ADDRESS": "0x1111111111111111111111111111111111111111",
        "LOAN_AGREEMENT_CONTRACT_ADDRESS": "0x2222222222222222222222222222222222222222",
        "IDENTITY_REGISTRY_CONTRACT_ADDRESS": "0x3333333333333333333333333333333333333333",
        "PAYMENT_PROCESSOR_CONTRACT_ADDRESS": "0x4444444444444444444444444444444444444444",
    }


@pytest.fixture
def blockchain_service(mock_blockchain_config: Any) -> Any:
    service = BlockchainService(mock_blockchain_config)
    service.web3 = Mock()
    service.is_connected_flag = True
    return service


def create_test_audit_log(
    db: Any, user_id: Any, event_type: Any = None, severity: Any = None
) -> Any:
    event_type = event_type or AuditEventType.USER_LOGIN
    severity = severity or AuditSeverity.LOW
    if isinstance(event_type, str):
        try:
            event_type = AuditEventType(event_type)
        except ValueError:
            event_type = AuditEventType.USER_LOGIN
    if isinstance(severity, str):
        try:
            severity = AuditSeverity(severity)
        except ValueError:
            severity = AuditSeverity.LOW

    audit_log = AuditLog(
        user_id=str(user_id),
        event_type=event_type,
        event_category=event_type.value.split("_")[0],
        event_description=f"Test {event_type.value} event",
        severity=severity,
        ip_address="127.0.0.1",
        user_agent="Test Agent",
    )
    db.session.add(audit_log)
    db.session.commit()
    return audit_log


def pytest_configure(config: Any) -> Any:
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line(
        "markers", "external: mark test as requiring external services"
    )
