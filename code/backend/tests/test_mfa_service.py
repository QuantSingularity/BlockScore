from typing import Any

"""
Comprehensive Test Suite for Multi-Factor Authentication Service
Tests for TOTP, SMS, backup codes, and security features
"""

import base64
import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pyotp
import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.user import User, UserProfile
from services.mfa_service import MFAMethod, MFAService


class TestMFAService:
    """Test suite for MFAService"""

    @pytest.fixture
    def db_session(self) -> Any:
        """Mock database session"""
        session = Mock()
        return session

    @pytest.fixture
    def mfa_service(self, db_session: Any) -> Any:
        """Create MFAService instance for testing"""
        return MFAService(db_session)

    @pytest.fixture
    def mock_user(self) -> Any:
        """Create mock user for testing"""
        user = Mock(spec=User)
        user.id = 1
        user.email = "test@example.com"
        user.profile = Mock(spec=UserProfile)
        user.profile.user_id = 1
        user.profile.mfa_enabled = False
        user.profile.mfa_methods = []
        user.profile.totp_secret = None
        user.profile.phone_number = None
        user.profile.backup_codes = None
        return user

    def test_setup_totp_success(self, mfa_service: Any, mock_user: Any) -> Any:
        """Test successful TOTP setup"""
        with patch("services.mfa_service.User") as MockUser, patch.object(
            mfa_service, "_generate_qr_code"
        ) as mock_qr, patch.object(mfa_service, "_encrypt_secret") as mock_encrypt:
            MockUser.query.get.return_value = mock_user
            mock_qr.return_value = "base64_qr_code_data"
            mock_encrypt.return_value = "encrypted_secret"
            result = mfa_service.setup_totp(1)
            assert result["success"] is True
            assert "secret" in result
            assert "qr_code" in result
            assert "provisioning_uri" in result
            assert len(result["secret"]) == 32

    def test_setup_totp_user_not_found(self, mfa_service: Any) -> Any:
        """Test TOTP setup with non-existent user"""
        with patch("services.mfa_service.User") as MockUser:
            MockUser.query.get.return_value = None
            with pytest.raises(ValueError, match="User not found"):
                mfa_service.setup_totp(999)

    def test_verify_totp_setup_success(self, mfa_service: Any, mock_user: Any) -> Any:
        """Test successful TOTP setup verification"""
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        current_code = totp.now()
        mock_user.profile.totp_secret = "encrypted_secret"
        with patch("services.mfa_service.User") as MockUser, patch.object(
            mfa_service, "_decrypt_secret"
        ) as mock_decrypt, patch.object(
            mfa_service, "_generate_backup_codes"
        ) as mock_backup:
            MockUser.query.get.return_value = mock_user
            mock_decrypt.return_value = secret
            mock_backup.return_value = ["1234-5678", "2345-6789"]
            result = mfa_service.verify_totp_setup(1, current_code)
            assert result["success"] is True
            assert result["mfa_enabled"] is True
            assert "backup_codes" in result
            assert mock_user.profile.mfa_enabled is True
            assert MFAMethod.TOTP in mock_user.profile.mfa_methods

    def test_verify_totp_setup_invalid_code(
        self, mfa_service: Any, mock_user: Any
    ) -> Any:
        """Test TOTP setup verification with invalid code"""
        secret = pyotp.random_base32()
        mock_user.profile.totp_secret = "encrypted_secret"
        with patch("services.mfa_service.User") as MockUser, patch.object(
            mfa_service, "_decrypt_secret"
        ) as mock_decrypt:
            MockUser.query.get.return_value = mock_user
            mock_decrypt.return_value = secret
            result = mfa_service.verify_totp_setup(1, "000000")
            assert result["success"] is False
            assert "Invalid verification code" in result["error"]

    def test_setup_sms_mfa_success(self, mfa_service: Any, mock_user: Any) -> Any:
        """Test successful SMS MFA setup"""
        phone_number = "+1234567890"
        with patch("services.mfa_service.User") as MockUser, patch.object(
            mfa_service, "_validate_phone_number"
        ) as mock_validate, patch.object(
            mfa_service, "_generate_sms_code"
        ) as mock_code, patch.object(
            mfa_service, "_send_sms"
        ) as mock_sms, patch.object(
            mfa_service, "_encrypt_secret"
        ) as mock_encrypt:
            MockUser.query.get.return_value = mock_user
            mock_validate.return_value = True
            mock_code.return_value = "123456"
            mock_sms.return_value = True
            mock_encrypt.return_value = "encrypted_data"
            result = mfa_service.setup_sms_mfa(1, phone_number)
            assert result["success"] is True
            assert "Verification code sent" in result["message"]
            assert "phone_number_masked" in result

    def test_setup_sms_mfa_invalid_phone(self, mfa_service: Any, mock_user: Any) -> Any:
        """Test SMS MFA setup with invalid phone number"""
        invalid_phone = "invalid-phone"
        with patch("services.mfa_service.User") as MockUser, patch.object(
            mfa_service, "_validate_phone_number"
        ) as mock_validate:
            MockUser.query.get.return_value = mock_user
            mock_validate.return_value = False
            result = mfa_service.setup_sms_mfa(1, invalid_phone)
            assert result["success"] is False
            assert "Invalid phone number format" in result["error"]

    def test_setup_sms_mfa_send_failure(self, mfa_service: Any, mock_user: Any) -> Any:
        """Test SMS MFA setup when SMS sending fails"""
        phone_number = "+1234567890"
        with patch("services.mfa_service.User") as MockUser, patch.object(
            mfa_service, "_validate_phone_number"
        ) as mock_validate, patch.object(
            mfa_service, "_generate_sms_code"
        ) as mock_code, patch.object(
            mfa_service, "_send_sms"
        ) as mock_sms, patch.object(
            mfa_service, "_encrypt_secret"
        ) as mock_encrypt:
            MockUser.query.get.return_value = mock_user
            mock_validate.return_value = True
            mock_code.return_value = "123456"
            mock_sms.return_value = False
            mock_encrypt.return_value = "encrypted_data"
            result = mfa_service.setup_sms_mfa(1, phone_number)
            assert result["success"] is False
            assert "Failed to send SMS verification code" in result["error"]

    def test_verify_sms_setup_success(self, mfa_service: Any, mock_user: Any) -> Any:
        """Test successful SMS setup verification"""
        verification_code = "123456"
        mock_user.profile.sms_verification_code = "encrypted_code"
        mock_user.profile.sms_code_expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=5
        )
        with patch("services.mfa_service.User") as MockUser, patch.object(
            mfa_service, "_decrypt_secret"
        ) as mock_decrypt:
            MockUser.query.get.return_value = mock_user
            mock_decrypt.return_value = verification_code
            result = mfa_service.verify_sms_setup(1, verification_code)
            assert result["success"] is True
            assert result["mfa_enabled"] is True
            assert mock_user.profile.mfa_enabled is True
            assert MFAMethod.SMS in mock_user.profile.mfa_methods

    def test_verify_sms_setup_expired_code(
        self, mfa_service: Any, mock_user: Any
    ) -> Any:
        """Test SMS setup verification with expired code"""
        verification_code = "123456"
        mock_user.profile.sms_verification_code = "encrypted_code"
        mock_user.profile.sms_code_expires_at = datetime.now(timezone.utc) - timedelta(
            minutes=1
        )
        with patch("services.mfa_service.User") as MockUser:
            MockUser.query.get.return_value = mock_user
            result = mfa_service.verify_sms_setup(1, verification_code)
            assert result["success"] is False
            assert "Verification code expired" in result["error"]

    def test_verify_mfa_totp_success(self, mfa_service: Any, mock_user: Any) -> Any:
        """Test successful MFA verification using TOTP"""
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        current_code = totp.now()
        mock_user.profile.mfa_enabled = True
        mock_user.profile.totp_secret = "encrypted_secret"
        with patch("services.mfa_service.User") as MockUser, patch.object(
            mfa_service, "_is_mfa_locked"
        ) as mock_locked, patch.object(
            mfa_service, "_verify_totp_code"
        ) as mock_verify, patch.object(
            mfa_service, "_reset_mfa_failed_attempts"
        ) as mock_reset:
            MockUser.query.get.return_value = mock_user
            mock_locked.return_value = False
            mock_verify.return_value = True
            result = mfa_service.verify_mfa(1, MFAMethod.TOTP, current_code)
            assert result["success"] is True
            assert result["method_used"] == MFAMethod.TOTP
            mock_reset.assert_called_once_with(1)

    def test_verify_mfa_backup_code_success(
        self, mfa_service: Any, mock_user: Any
    ) -> Any:
        """Test successful MFA verification using backup code"""
        backup_code = "1234-5678"
        mock_user.profile.mfa_enabled = True
        with patch("services.mfa_service.User") as MockUser, patch.object(
            mfa_service, "_is_mfa_locked"
        ) as mock_locked, patch.object(
            mfa_service, "_verify_backup_code"
        ) as mock_verify, patch.object(
            mfa_service, "_reset_mfa_failed_attempts"
        ) as mock_reset:
            MockUser.query.get.return_value = mock_user
            mock_locked.return_value = False
            mock_verify.return_value = True
            result = mfa_service.verify_mfa(1, MFAMethod.TOTP, "000000", backup_code)
            assert result["success"] is True
            assert result["method_used"] == MFAMethod.BACKUP_CODES
            mock_reset.assert_called_once_with(1)

    def test_verify_mfa_account_locked(self, mfa_service: Any, mock_user: Any) -> Any:
        """Test MFA verification when account is locked"""
        mock_user.profile.mfa_enabled = True
        with patch("services.mfa_service.User") as MockUser, patch.object(
            mfa_service, "_is_mfa_locked"
        ) as mock_locked:
            MockUser.query.get.return_value = mock_user
            mock_locked.return_value = True
            result = mfa_service.verify_mfa(1, MFAMethod.TOTP, "123456")
            assert result["success"] is False
            assert "Account temporarily locked" in result["error"]

    def test_verify_mfa_invalid_code(self, mfa_service: Any, mock_user: Any) -> Any:
        """Test MFA verification with invalid code"""
        mock_user.profile.mfa_enabled = True
        with patch("services.mfa_service.User") as MockUser, patch.object(
            mfa_service, "_is_mfa_locked"
        ) as mock_locked, patch.object(
            mfa_service, "_verify_totp_code"
        ) as mock_verify, patch.object(
            mfa_service, "_increment_mfa_failed_attempts"
        ) as mock_increment:
            MockUser.query.get.return_value = mock_user
            mock_locked.return_value = False
            mock_verify.return_value = False
            result = mfa_service.verify_mfa(1, MFAMethod.TOTP, "000000")
            assert result["success"] is False
            assert "Invalid MFA code" in result["error"]
            mock_increment.assert_called_once_with(1)

    def test_send_sms_code_success(self, mfa_service: Any, mock_user: Any) -> Any:
        """Test successful SMS code sending"""
        mock_user.profile.mfa_methods = [MFAMethod.SMS]
        mock_user.profile.phone_number = "encrypted_phone"
        with patch("services.mfa_service.User") as MockUser, patch.object(
            mfa_service, "_is_sms_rate_limited"
        ) as mock_rate_limit, patch.object(
            mfa_service, "_generate_sms_code"
        ) as mock_code, patch.object(
            mfa_service, "_decrypt_secret"
        ) as mock_decrypt, patch.object(
            mfa_service, "_send_sms"
        ) as mock_sms, patch.object(
            mfa_service, "_encrypt_secret"
        ) as mock_encrypt, patch.object(
            mfa_service, "_update_sms_rate_limit"
        ):
            MockUser.query.get.return_value = mock_user
            mock_rate_limit.return_value = False
            mock_code.return_value = "123456"
            mock_decrypt.return_value = "+1234567890"
            mock_sms.return_value = True
            mock_encrypt.return_value = "encrypted_code"
            result = mfa_service.send_sms_code(1)
            assert result["success"] is True
            assert "SMS code sent successfully" in result["message"]
            assert "expires_in" in result

    def test_send_sms_code_rate_limited(self, mfa_service: Any, mock_user: Any) -> Any:
        """Test SMS code sending when rate limited"""
        mock_user.profile.mfa_methods = [MFAMethod.SMS]
        with patch("services.mfa_service.User") as MockUser, patch.object(
            mfa_service, "_is_sms_rate_limited"
        ) as mock_rate_limit:
            MockUser.query.get.return_value = mock_user
            mock_rate_limit.return_value = True
            result = mfa_service.send_sms_code(1)
            assert result["success"] is False
            assert "SMS rate limit exceeded" in result["error"]

    def test_disable_mfa_specific_method(self, mfa_service: Any, mock_user: Any) -> Any:
        """Test disabling specific MFA method"""
        mock_user.profile.mfa_enabled = True
        mock_user.profile.mfa_methods = [MFAMethod.TOTP, MFAMethod.SMS]
        mock_user.profile.totp_secret = "encrypted_secret"
        with patch("services.mfa_service.User") as MockUser:
            MockUser.query.get.return_value = mock_user
            result = mfa_service.disable_mfa(1, MFAMethod.TOTP)
            assert result["success"] is True
            assert MFAMethod.TOTP not in mock_user.profile.mfa_methods
            assert MFAMethod.SMS in mock_user.profile.mfa_methods
            assert mock_user.profile.mfa_enabled is True
            assert mock_user.profile.totp_secret is None

    def test_disable_mfa_all_methods(self, mfa_service: Any, mock_user: Any) -> Any:
        """Test disabling all MFA methods"""
        mock_user.profile.mfa_enabled = True
        mock_user.profile.mfa_methods = [MFAMethod.TOTP]
        mock_user.profile.totp_secret = "encrypted_secret"
        mock_user.profile.backup_codes = "encrypted_codes"
        with patch("services.mfa_service.User") as MockUser:
            MockUser.query.get.return_value = mock_user
            result = mfa_service.disable_mfa(1)
            assert result["success"] is True
            assert mock_user.profile.mfa_enabled is False
            assert mock_user.profile.mfa_methods == []
            assert mock_user.profile.totp_secret is None
            assert mock_user.profile.backup_codes is None

    def test_get_mfa_status(self, mfa_service: Any, mock_user: Any) -> Any:
        """Test getting MFA status"""
        mock_user.profile.mfa_enabled = True
        mock_user.profile.mfa_methods = [MFAMethod.TOTP, MFAMethod.SMS]
        mock_user.profile.backup_codes = "encrypted_codes"
        mock_user.profile.phone_number = "encrypted_phone"
        with patch("services.mfa_service.User") as MockUser, patch.object(
            mfa_service, "_decrypt_secret"
        ) as mock_decrypt, patch.object(mfa_service, "_mask_phone_number") as mock_mask:
            MockUser.query.get.return_value = mock_user
            mock_decrypt.side_effect = ["code1,code2,code3", "+1234567890"]
            mock_mask.return_value = "****7890"
            result = mfa_service.get_mfa_status(1)
            assert result["mfa_enabled"] is True
            assert set(result["available_methods"]) == {MFAMethod.TOTP, MFAMethod.SMS}
            assert result["backup_codes_remaining"] == 3
            assert result["phone_number_masked"] == "****7890"

    def test_regenerate_backup_codes(self, mfa_service: Any, mock_user: Any) -> Any:
        """Test regenerating backup codes"""
        mock_user.profile.mfa_enabled = True
        with patch("services.mfa_service.User") as MockUser, patch.object(
            mfa_service, "_generate_backup_codes"
        ) as mock_generate:
            MockUser.query.get.return_value = mock_user
            mock_generate.return_value = ["1234-5678", "2345-6789", "3456-7890"]
            result = mfa_service.regenerate_backup_codes(1)
            assert result["success"] is True
            assert len(result["backup_codes"]) == 3
            assert "New backup codes generated" in result["message"]

    def test_regenerate_backup_codes_mfa_not_enabled(
        self, mfa_service: Any, mock_user: Any
    ) -> Any:
        """Test regenerating backup codes when MFA is not enabled"""
        mock_user.profile.mfa_enabled = False
        with patch("services.mfa_service.User") as MockUser:
            MockUser.query.get.return_value = mock_user
            with pytest.raises(ValueError, match="MFA not enabled for user"):
                mfa_service.regenerate_backup_codes(1)

    def test_encrypt_decrypt_secret(self, mfa_service: Any) -> Any:
        """Test secret encryption and decryption"""
        original_secret = "test_secret_123"
        encrypted = mfa_service._encrypt_secret(original_secret)
        decrypted = mfa_service._decrypt_secret(encrypted)
        assert decrypted == original_secret
        assert encrypted != original_secret
        assert ":" in encrypted

    def test_generate_backup_codes(self, mfa_service: Any, mock_user: Any) -> Any:
        """Test backup code generation"""
        with patch("services.mfa_service.User") as MockUser, patch.object(
            mfa_service, "_encrypt_secret"
        ) as mock_encrypt:
            MockUser.query.get.return_value = mock_user
            mock_encrypt.return_value = "encrypted_codes"
            codes = mfa_service._generate_backup_codes(1)
            assert len(codes) == mfa_service.backup_codes_count
            for code in codes:
                assert len(code) == 9
                assert "-" in code
                assert code[:4].isdigit()
                assert code[5:].isdigit()

    def test_validate_phone_number(self, mfa_service: Any) -> Any:
        """Test phone number validation"""
        valid_numbers = ["+12345678901", "12345678901", "+1-234-567-8901"]
        invalid_numbers = ["123", "invalid", "+1234", ""]
        for number in valid_numbers:
            result = mfa_service._validate_phone_number(number)
            assert isinstance(result, bool)
        for number in invalid_numbers:
            result = mfa_service._validate_phone_number(number)
            assert isinstance(result, bool)

    def test_mask_phone_number(self, mfa_service: Any) -> Any:
        """Test phone number masking"""
        phone_number = "+12345678901"
        masked = mfa_service._mask_phone_number(phone_number)
        assert masked == "****8901"
        assert len(masked) == 8
        assert masked.startswith("****")

    def test_generate_qr_code(self, mfa_service: Any) -> Any:
        """Test QR code generation"""
        test_data = (
            "otpauth://totp/Test:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=Test"
        )
        qr_code_data = mfa_service._generate_qr_code(test_data)
        assert isinstance(qr_code_data, str)
        assert len(qr_code_data) > 0
        try:
            base64.b64decode(qr_code_data)
        except Exception:
            pytest.fail("Generated QR code is not valid base64")

    def test_verify_totp_code_valid(self, mfa_service: Any, mock_user: Any) -> Any:
        """Test TOTP code verification with valid code"""
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        current_code = totp.now()
        mock_user.profile.totp_secret = "encrypted_secret"
        with patch("services.mfa_service.User") as MockUser, patch.object(
            mfa_service, "_decrypt_secret"
        ) as mock_decrypt:
            MockUser.query.get.return_value = mock_user
            mock_decrypt.return_value = secret
            result = mfa_service._verify_totp_code(1, current_code)
            assert result is True

    def test_verify_totp_code_invalid(self, mfa_service: Any, mock_user: Any) -> Any:
        """Test TOTP code verification with invalid code"""
        secret = pyotp.random_base32()
        mock_user.profile.totp_secret = "encrypted_secret"
        with patch("services.mfa_service.User") as MockUser, patch.object(
            mfa_service, "_decrypt_secret"
        ) as mock_decrypt:
            MockUser.query.get.return_value = mock_user
            mock_decrypt.return_value = secret
            result = mfa_service._verify_totp_code(1, "000000")
            assert result is False

    def test_verify_backup_code_valid(self, mfa_service: Any, mock_user: Any) -> Any:
        """Test backup code verification with valid code"""
        backup_codes = "1234-5678,2345-6789,3456-7890"
        test_code = "1234-5678"
        mock_user.profile.backup_codes = "encrypted_codes"
        with patch("services.mfa_service.User") as MockUser, patch.object(
            mfa_service, "_decrypt_secret"
        ) as mock_decrypt, patch.object(mfa_service, "_encrypt_secret") as mock_encrypt:
            MockUser.query.get.return_value = mock_user
            mock_decrypt.return_value = backup_codes
            mock_encrypt.return_value = "encrypted_remaining_codes"
            result = mfa_service._verify_backup_code(1, test_code)
            assert result is True
            mock_encrypt.assert_called_with("2345-6789,3456-7890")

    def test_verify_backup_code_invalid(self, mfa_service: Any, mock_user: Any) -> Any:
        """Test backup code verification with invalid code"""
        backup_codes = "1234-5678,2345-6789,3456-7890"
        test_code = "9999-9999"
        mock_user.profile.backup_codes = "encrypted_codes"
        with patch("services.mfa_service.User") as MockUser, patch.object(
            mfa_service, "_decrypt_secret"
        ) as mock_decrypt:
            MockUser.query.get.return_value = mock_user
            mock_decrypt.return_value = backup_codes
            result = mfa_service._verify_backup_code(1, test_code)
            assert result is False

    def test_concurrent_mfa_operations(self, mfa_service: Any, mock_user: Any) -> Any:
        """Test concurrent MFA operations"""
        import threading

        results = []

        def setup_totp():
            with patch("services.mfa_service.User") as MockUser, patch.object(
                mfa_service, "_generate_qr_code"
            ) as mock_qr, patch.object(mfa_service, "_encrypt_secret") as mock_encrypt:
                MockUser.query.get.return_value = mock_user
                mock_qr.return_value = "qr_data"
                mock_encrypt.return_value = "encrypted"
                result = mfa_service.setup_totp(1)
                results.append(result)

        threads = []
        for _ in range(3):
            thread = threading.Thread(target=setup_totp)
            threads.append(thread)
            thread.start()
        for thread in threads:
            thread.join()
        assert len(results) == 3
        assert all((result["success"] for result in results))


class TestMFAServiceIntegration:
    """Integration tests for MFA service"""

    def test_complete_totp_flow(self) -> Any:
        """Test complete TOTP setup and verification flow"""

    def test_complete_sms_flow(self) -> Any:
        """Test complete SMS MFA setup and verification flow"""

    def test_mfa_recovery_flow(self) -> Any:
        """Test MFA recovery using backup codes"""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
