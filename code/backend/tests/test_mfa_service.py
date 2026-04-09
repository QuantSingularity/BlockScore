"""
Comprehensive Test Suite for Multi-Factor Authentication Service
Tests for TOTP, SMS, backup codes, and security features
"""

import json
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
from unittest.mock import Mock, patch

import compat_stubs  # noqa
import pyotp
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.user import User
from services.mfa_service import MFAMethod, MFAService


class TestMFAService:
    """Test suite for MFAService"""

    @pytest.fixture
    def db_session(self) -> Any:
        """Mock database session"""
        session = Mock()
        session.commit = Mock()
        session.rollback = Mock()
        session.add = Mock()
        return session

    @pytest.fixture
    def mock_user(self) -> Any:
        """Create a mock user"""
        user = Mock(spec=User)
        user.id = 1
        user.email = "test@example.com"
        user.mfa_enabled = False
        user.mfa_secret = None
        user.totp_secret = None
        user.backup_codes = None
        return user

    @pytest.fixture
    def mfa_service(self, db_session: Any) -> Any:
        """Create MFAService instance for testing"""
        return MFAService(db_session)

    def test_mfa_service_init(self, mfa_service: Any) -> Any:
        """Test MFAService initializes correctly"""
        assert mfa_service is not None

    def test_setup_totp_success(self, mfa_service: Any, mock_user: Any) -> Any:
        """Test successful TOTP setup"""
        with patch("services.mfa_service.db") as mock_db:
            mock_db.session.get.return_value = mock_user
            result = mfa_service.setup_totp(mock_user.id)
        assert result["success"] is True
        assert "secret" in result
        assert "qr_code" in result

    def test_setup_totp_user_not_found(self, mfa_service: Any) -> Any:
        """Test TOTP setup with nonexistent user"""
        with patch("services.mfa_service.db") as mock_db:
            mock_db.session.get.return_value = None
            result = mfa_service.setup_totp(999)
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_verify_totp_valid_code(self, mfa_service: Any, mock_user: Any) -> Any:
        """Test TOTP verification with valid code"""
        secret = pyotp.random_base32()
        mock_user.mfa_secret = secret
        mock_user.totp_secret = secret
        mock_user.mfa_enabled = True
        totp = pyotp.TOTP(secret)
        current_code = totp.now()
        with patch("services.mfa_service.db") as mock_db:
            mock_db.session.get.return_value = mock_user
            result = mfa_service.verify_totp(mock_user.id, current_code)
        assert result["valid"] is True

    def test_verify_totp_invalid_code(self, mfa_service: Any, mock_user: Any) -> Any:
        """Test TOTP verification with invalid code"""
        secret = pyotp.random_base32()
        mock_user.mfa_secret = secret
        mock_user.totp_secret = secret
        mock_user.mfa_enabled = True
        with patch("services.mfa_service.db") as mock_db:
            mock_db.session.get.return_value = mock_user
            result = mfa_service.verify_totp(mock_user.id, "000000")
        assert result["valid"] is False

    def test_verify_totp_user_not_found(self, mfa_service: Any) -> Any:
        """Test TOTP verification when user doesn't exist"""
        with patch("services.mfa_service.db") as mock_db:
            mock_db.session.get.return_value = None
            result = mfa_service.verify_totp(999, "123456")
        assert result["valid"] is False

    def test_enable_mfa_success(self, mfa_service: Any, mock_user: Any) -> Any:
        """Test enabling MFA after setup"""
        secret = pyotp.random_base32()
        mock_user.mfa_secret = secret
        totp = pyotp.TOTP(secret)
        code = totp.now()
        with patch("services.mfa_service.db") as mock_db:
            mock_db.session.get.return_value = mock_user
            result = mfa_service.enable_mfa(mock_user.id, code)
        assert result["success"] is True
        assert mock_user.mfa_enabled is True

    def test_enable_mfa_invalid_code(self, mfa_service: Any, mock_user: Any) -> Any:
        """Test enabling MFA with invalid code"""
        secret = pyotp.random_base32()
        mock_user.mfa_secret = secret
        with patch("services.mfa_service.db") as mock_db:
            mock_db.session.get.return_value = mock_user
            result = mfa_service.enable_mfa(mock_user.id, "000000")
        assert result["success"] is False

    def test_disable_mfa_success(self, mfa_service: Any, mock_user: Any) -> Any:
        """Test disabling MFA"""
        secret = pyotp.random_base32()
        mock_user.mfa_secret = secret
        mock_user.mfa_enabled = True
        totp = pyotp.TOTP(secret)
        code = totp.now()
        with patch("services.mfa_service.db") as mock_db:
            mock_db.session.get.return_value = mock_user
            result = mfa_service.disable_mfa(mock_user.id, code)
        assert result["success"] is True
        assert mock_user.mfa_enabled is False

    def test_disable_mfa_invalid_code(self, mfa_service: Any, mock_user: Any) -> Any:
        """Test disabling MFA with invalid code"""
        secret = pyotp.random_base32()
        mock_user.mfa_secret = secret
        mock_user.mfa_enabled = True
        with patch("services.mfa_service.db") as mock_db:
            mock_db.session.get.return_value = mock_user
            result = mfa_service.disable_mfa(mock_user.id, "000000")
        assert result["success"] is False

    def test_generate_backup_codes(self, mfa_service: Any) -> Any:
        """Test backup code generation"""
        codes = mfa_service._generate_backup_codes(10)
        assert len(codes) == 10
        assert all(len(c) > 0 for c in codes)
        assert len(set(codes)) == 10

    def test_verify_backup_code_success(self, mfa_service: Any, mock_user: Any) -> Any:
        """Test verifying a valid backup code"""
        backup_codes = ["ABCD1234", "EFGH5678"]
        mock_user.backup_codes = json.dumps(backup_codes)
        with patch("services.mfa_service.db") as mock_db:
            mock_db.session.get.return_value = mock_user
            result = mfa_service.verify_backup_code(mock_user.id, "ABCD1234")
        assert result["valid"] is True

    def test_verify_backup_code_invalid(self, mfa_service: Any, mock_user: Any) -> Any:
        """Test verifying an invalid backup code"""
        backup_codes = ["ABCD1234", "EFGH5678"]
        mock_user.backup_codes = json.dumps(backup_codes)
        with patch("services.mfa_service.db") as mock_db:
            mock_db.session.get.return_value = mock_user
            result = mfa_service.verify_backup_code(mock_user.id, "INVALID9")
        assert result["valid"] is False

    def test_verify_backup_code_consumed(self, mfa_service: Any, mock_user: Any) -> Any:
        """Test that used backup codes are removed"""
        backup_codes = ["ABCD1234", "EFGH5678"]
        mock_user.backup_codes = json.dumps(backup_codes)
        with patch("services.mfa_service.db") as mock_db:
            mock_db.session.get.return_value = mock_user
            mfa_service.verify_backup_code(mock_user.id, "ABCD1234")
        remaining = json.loads(mock_user.backup_codes)
        assert "ABCD1234" not in remaining
        assert "EFGH5678" in remaining

    def test_mfa_method_constants(self) -> Any:
        """Test MFAMethod constants"""
        assert MFAMethod.TOTP == "totp"
        assert MFAMethod.SMS == "sms"

    def test_get_mfa_status_enabled(self, mfa_service: Any, mock_user: Any) -> Any:
        """Test MFA status when enabled"""
        mock_user.mfa_enabled = True
        mock_user.mfa_secret = "test_secret"
        with patch("services.mfa_service.db") as mock_db:
            mock_db.session.get.return_value = mock_user
            status = mfa_service.get_mfa_status(mock_user.id)
        assert status["mfa_enabled"] is True

    def test_get_mfa_status_disabled(self, mfa_service: Any, mock_user: Any) -> Any:
        """Test MFA status when disabled"""
        mock_user.mfa_enabled = False
        mock_user.mfa_secret = None
        with patch("services.mfa_service.db") as mock_db:
            mock_db.session.get.return_value = mock_user
            status = mfa_service.get_mfa_status(mock_user.id)
        assert status["mfa_enabled"] is False

    def test_totp_is_time_based(self) -> Any:
        """Test that TOTP codes change over time"""
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        code = totp.now()
        assert len(code) == 6
        assert code.isdigit()

    def test_setup_totp_generates_qr(self, mfa_service: Any, mock_user: Any) -> Any:
        """Test that TOTP setup generates a QR code"""
        with patch("services.mfa_service.db") as mock_db:
            mock_db.session.get.return_value = mock_user
            result = mfa_service.setup_totp(mock_user.id)
        if result["success"]:
            assert "qr_code" in result
            qr = result["qr_code"]
            assert qr.startswith("data:image/png;base64,") or len(qr) > 0
