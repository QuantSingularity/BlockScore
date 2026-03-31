"""
Unit tests for Authentication Service
"""

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import Mock, patch

from models.audit import AuditLog
from models.user import User, UserSession


class TestAuthenticationService:
    """Test cases for AuthenticationService"""

    def test_register_user_success(
        self, auth_service: Any, db: Any, sample_user_data: Any
    ) -> Any:
        """Test successful user registration"""
        result = auth_service.register_user(sample_user_data)
        assert result["success"] is True
        assert "user_id" in result
        assert "message" in result
        user = User.query.filter_by(email=sample_user_data["email"]).first()
        assert user is not None
        assert user.email == sample_user_data["email"]
        assert user.profile is not None
        assert user.profile.first_name == sample_user_data["first_name"]

    def test_register_user_duplicate_email(
        self, auth_service: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test registration with duplicate email"""
        user_data = {
            "email": sample_user.email,
            "password": "NewPassword123!",
            "first_name": "Jane",
            "last_name": "Smith",
        }
        result = auth_service.register_user(user_data)
        assert result["success"] is False
        assert "already exists" in result["message"].lower()

    def test_register_user_invalid_email(self, auth_service: Any, db: Any) -> Any:
        """Test registration with invalid email"""
        user_data = {
            "email": "invalid-email",
            "password": "Password123!",
            "first_name": "John",
            "last_name": "Doe",
        }
        result = auth_service.register_user(user_data)
        assert result["success"] is False
        assert "invalid" in result["message"].lower()

    def test_register_user_weak_password(self, auth_service: Any, db: Any) -> Any:
        """Test registration with weak password"""
        user_data = {
            "email": "test@example.com",
            "password": "123",
            "first_name": "John",
            "last_name": "Doe",
        }
        result = auth_service.register_user(user_data)
        assert result["success"] is False
        assert "password" in result["message"].lower()

    def test_authenticate_user_success(
        self, auth_service: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test successful user authentication"""
        with patch.object(auth_service, "_verify_password", return_value=True):
            result = auth_service.authenticate_user(
                sample_user.email, "correct_password"
            )
        assert result["success"] is True
        assert result["user_id"] == sample_user.id
        assert "access_token" in result
        assert "refresh_token" in result

    def test_authenticate_user_invalid_email(self, auth_service: Any, db: Any) -> Any:
        """Test authentication with invalid email"""
        result = auth_service.authenticate_user("nonexistent@example.com", "password")
        assert result["success"] is False
        assert "invalid" in result["message"].lower()

    def test_authenticate_user_wrong_password(
        self, auth_service: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test authentication with wrong password"""
        with patch.object(auth_service, "_verify_password", return_value=False):
            result = auth_service.authenticate_user(sample_user.email, "wrong_password")
        assert result["success"] is False
        assert "invalid" in result["message"].lower()

    def test_authenticate_user_inactive_account(
        self, auth_service: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test authentication with inactive account"""
        sample_user.is_active = False
        db.session.commit()
        with patch.object(auth_service, "_verify_password", return_value=True):
            result = auth_service.authenticate_user(
                sample_user.email, "correct_password"
            )
        assert result["success"] is False
        assert "inactive" in result["message"].lower()

    def test_authenticate_user_unverified_email(
        self, auth_service: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test authentication with unverified email"""
        sample_user.email_verified = False
        db.session.commit()
        with patch.object(auth_service, "_verify_password", return_value=True):
            result = auth_service.authenticate_user(
                sample_user.email, "correct_password"
            )
        assert result["success"] is False
        assert "verify" in result["message"].lower()

    def test_validate_token_success(
        self, auth_service: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test successful token validation"""
        token = auth_service._generate_access_token(sample_user.id)
        result = auth_service.validate_token(token)
        assert result["valid"] is True
        assert result["user_id"] == sample_user.id

    def test_validate_token_expired(
        self, auth_service: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test validation of expired token"""
        with patch("services.auth_service.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime.now(timezone.utc) - timedelta(
                hours=2
            )
            mock_datetime.timezone = timezone
            token = auth_service._generate_access_token(sample_user.id)
        result = auth_service.validate_token(token)
        assert result["valid"] is False
        assert "expired" in result["message"].lower()

    def test_validate_token_invalid(self, auth_service: Any, db: Any) -> Any:
        """Test validation of invalid token"""
        result = auth_service.validate_token("invalid_token")
        assert result["valid"] is False
        assert "invalid" in result["message"].lower()

    def test_refresh_token_success(
        self, auth_service: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test successful token refresh"""
        session = UserSession(
            user_id=sample_user.id,
            session_token="test_refresh_token",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db.session.add(session)
        db.session.commit()
        result = auth_service.refresh_token("test_refresh_token")
        assert result["success"] is True
        assert "access_token" in result
        assert "refresh_token" in result

    def test_refresh_token_invalid(self, auth_service: Any, db: Any) -> Any:
        """Test refresh with invalid token"""
        result = auth_service.refresh_token("invalid_refresh_token")
        assert result["success"] is False
        assert "invalid" in result["message"].lower()

    def test_refresh_token_expired(
        self, auth_service: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test refresh with expired token"""
        session = UserSession(
            user_id=sample_user.id,
            session_token="expired_refresh_token",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        db.session.add(session)
        db.session.commit()
        result = auth_service.refresh_token("expired_refresh_token")
        assert result["success"] is False
        assert "expired" in result["message"].lower()

    def test_logout_user_success(
        self, auth_service: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test successful user logout"""
        session = UserSession(
            user_id=sample_user.id,
            session_token="test_session_token",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db.session.add(session)
        db.session.commit()
        result = auth_service.logout_user(sample_user.id, "test_session_token")
        assert result["success"] is True
        updated_session = UserSession.query.filter_by(
            session_token="test_session_token"
        ).first()
        assert updated_session.is_active is False

    def test_logout_user_invalid_session(
        self, auth_service: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test logout with invalid session"""
        result = auth_service.logout_user(sample_user.id, "invalid_session_token")
        assert result["success"] is False
        assert "invalid" in result["message"].lower()

    def test_change_password_success(
        self, auth_service: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test successful password change"""
        with patch.object(auth_service, "_verify_password", return_value=True):
            with patch.object(
                auth_service, "_hash_password", return_value="new_hashed_password"
            ):
                result = auth_service.change_password(
                    sample_user.id, "old_password", "NewPassword123!"
                )
        assert result["success"] is True
        updated_user = User.query.get(sample_user.id)
        assert updated_user.password_hash == "new_hashed_password"

    def test_change_password_wrong_current(
        self, auth_service: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test password change with wrong current password"""
        with patch.object(auth_service, "_verify_password", return_value=False):
            result = auth_service.change_password(
                sample_user.id, "wrong_password", "NewPassword123!"
            )
        assert result["success"] is False
        assert "current password" in result["message"].lower()

    def test_change_password_weak_new_password(
        self, auth_service: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test password change with weak new password"""
        with patch.object(auth_service, "_verify_password", return_value=True):
            result = auth_service.change_password(sample_user.id, "old_password", "123")
        assert result["success"] is False
        assert "password" in result["message"].lower()

    def test_reset_password_request_success(
        self, auth_service: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test successful password reset request"""
        result = auth_service.request_password_reset(sample_user.email)
        assert result["success"] is True
        assert "reset_token" in result
        updated_user = User.query.get(sample_user.id)
        assert updated_user.password_reset_token is not None
        assert updated_user.password_reset_expires is not None

    def test_reset_password_request_invalid_email(
        self, auth_service: Any, db: Any
    ) -> Any:
        """Test password reset request with invalid email"""
        result = auth_service.request_password_reset("nonexistent@example.com")
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_reset_password_success(
        self, auth_service: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test successful password reset"""
        reset_token = "test_reset_token"
        sample_user.password_reset_token = reset_token
        sample_user.password_reset_expires = datetime.now(timezone.utc) + timedelta(
            hours=1
        )
        db.session.commit()
        with patch.object(
            auth_service, "_hash_password", return_value="new_hashed_password"
        ):
            result = auth_service.reset_password(reset_token, "NewPassword123!")
        assert result["success"] is True
        updated_user = User.query.get(sample_user.id)
        assert updated_user.password_hash == "new_hashed_password"
        assert updated_user.password_reset_token is None
        assert updated_user.password_reset_expires is None

    def test_reset_password_invalid_token(self, auth_service: Any, db: Any) -> Any:
        """Test password reset with invalid token"""
        result = auth_service.reset_password("invalid_token", "NewPassword123!")
        assert result["success"] is False
        assert "invalid" in result["message"].lower()

    def test_reset_password_expired_token(
        self, auth_service: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test password reset with expired token"""
        reset_token = "expired_reset_token"
        sample_user.password_reset_token = reset_token
        sample_user.password_reset_expires = datetime.now(timezone.utc) - timedelta(
            hours=1
        )
        db.session.commit()
        result = auth_service.reset_password(reset_token, "NewPassword123!")
        assert result["success"] is False
        assert "expired" in result["message"].lower()

    def test_enable_mfa_success(
        self, auth_service: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test successful MFA enablement"""
        result = auth_service.enable_mfa(sample_user.id)
        assert result["success"] is True
        assert "secret" in result
        assert "qr_code" in result
        updated_user = User.query.get(sample_user.id)
        assert updated_user.mfa_secret is not None

    def test_verify_mfa_success(
        self, auth_service: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test successful MFA verification"""
        sample_user.mfa_secret = "test_mfa_secret"
        sample_user.mfa_enabled = True
        db.session.commit()
        with patch("pyotp.TOTP") as mock_totp:
            mock_totp_instance = Mock()
            mock_totp_instance.verify.return_value = True
            mock_totp.return_value = mock_totp_instance
            result = auth_service.verify_mfa_token(sample_user.id, "123456")
        assert result["valid"] is True

    def test_verify_mfa_invalid_token(
        self, auth_service: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test MFA verification with invalid token"""
        sample_user.mfa_secret = "test_mfa_secret"
        sample_user.mfa_enabled = True
        db.session.commit()
        with patch("pyotp.TOTP") as mock_totp:
            mock_totp_instance = Mock()
            mock_totp_instance.verify.return_value = False
            mock_totp.return_value = mock_totp_instance
            result = auth_service.verify_mfa_token(sample_user.id, "000000")
        assert result["valid"] is False

    def test_disable_mfa_success(
        self, auth_service: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test successful MFA disablement"""
        sample_user.mfa_secret = "test_mfa_secret"
        sample_user.mfa_enabled = True
        db.session.commit()
        with patch.object(
            auth_service, "verify_mfa_token", return_value={"valid": True}
        ):
            result = auth_service.disable_mfa(sample_user.id, "123456")
        assert result["success"] is True
        updated_user = User.query.get(sample_user.id)
        assert updated_user.mfa_enabled is False
        assert updated_user.mfa_secret is None

    def test_get_user_sessions(
        self, auth_service: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test getting user sessions"""
        session1 = UserSession(
            user_id=sample_user.id,
            session_token="token1",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            ip_address="192.168.1.1",
            user_agent="Browser 1",
        )
        session2 = UserSession(
            user_id=sample_user.id,
            session_token="token2",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            ip_address="192.168.1.2",
            user_agent="Browser 2",
        )
        db.session.add_all([session1, session2])
        db.session.commit()
        sessions = auth_service.get_user_sessions(sample_user.id)
        assert len(sessions) == 2
        assert all(("session_token" not in session for session in sessions))
        assert all(("ip_address" in session for session in sessions))

    def test_revoke_session_success(
        self, auth_service: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test successful session revocation"""
        session = UserSession(
            user_id=sample_user.id,
            session_token="test_token",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db.session.add(session)
        db.session.commit()
        result = auth_service.revoke_session(sample_user.id, session.id)
        assert result["success"] is True
        updated_session = UserSession.query.get(session.id)
        assert updated_session.is_active is False

    def test_audit_logging(self, auth_service: Any, db: Any, sample_user: Any) -> Any:
        """Test that authentication events are logged"""
        with patch.object(auth_service, "_verify_password", return_value=True):
            auth_service.authenticate_user(sample_user.email, "correct_password")
        audit_logs = AuditLog.query.filter_by(user_id=sample_user.id).all()
        assert len(audit_logs) > 0
        login_log = next(
            (log for log in audit_logs if log.event_type == "user_login"), None
        )
        assert login_log is not None

    def test_password_validation(self, auth_service: Any) -> Any:
        """Test password validation rules"""
        assert auth_service._validate_password("StrongPass123!")["valid"] is True
        assert auth_service._validate_password("AnotherGood1@")["valid"] is True
        assert auth_service._validate_password("weak")["valid"] is False
        assert auth_service._validate_password("NoNumbers!")["valid"] is False
        assert auth_service._validate_password("nonumbers123")["valid"] is False
        assert auth_service._validate_password("NoSpecialChars123")["valid"] is False
        assert auth_service._validate_password("short1!")["valid"] is False

    def test_email_validation(self, auth_service: Any) -> Any:
        """Test email validation"""
        assert auth_service._validate_email("test@example.com") is True
        assert auth_service._validate_email("user.name+tag@domain.co.uk") is True
        assert auth_service._validate_email("invalid-email") is False
        assert auth_service._validate_email("@domain.com") is False
        assert auth_service._validate_email("user@") is False
        assert auth_service._validate_email("user@domain") is False

    def test_rate_limiting(self, auth_service: Any, db: Any, sample_user: Any) -> Any:
        """Test authentication rate limiting"""
        with patch.object(auth_service, "_verify_password", return_value=False):
            for _ in range(6):
                auth_service.authenticate_user(sample_user.email, "wrong_password")
        with patch.object(auth_service, "_verify_password", return_value=True):
            result = auth_service.authenticate_user(
                sample_user.email, "correct_password"
            )
        assert result["success"] is False
        assert "rate limit" in result["message"].lower()

    def test_security_headers(
        self, auth_service: Any, db: Any, sample_user: Any
    ) -> Any:
        """Test security-related functionality"""
        with patch.object(auth_service, "_verify_password", return_value=True):
            auth_service.change_password(sample_user.id, "old_pass", "NewPass123!")
        updated_user = User.query.get(sample_user.id)
        assert updated_user.password_changed_at is not None
        assert updated_user.updated_at > sample_user.updated_at
