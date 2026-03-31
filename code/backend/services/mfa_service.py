"""
Multi-Factor Authentication (MFA) Service for Financial Applications
Implements TOTP, SMS, and backup codes for enhanced security
"""

import base64
import hashlib
import hmac
import io
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import pyotp
import qrcode
import requests
from flask import current_app
from models.audit import AuditEventType, AuditSeverity
from models.user import User, UserProfile
from services.audit_service import AuditService
from sqlalchemy.orm import Session


class MFAMethod:
    """MFA method enumeration"""

    TOTP = "totp"
    SMS = "sms"
    EMAIL = "email"
    BACKUP_CODES = "backup_codes"
    HARDWARE_TOKEN = "hardware_token"


class MFAService:
    """Multi-Factor Authentication service for enhanced security"""

    def __init__(self, db_session: Session) -> None:
        self.db = db_session
        self.audit_service = AuditService(db_session)
        self.totp_issuer = "BlockScore"
        self.totp_window = 1
        self.backup_codes_count = 10
        self.sms_code_length = 6
        self.sms_code_expiry = 300
        self.max_failed_attempts = 3
        self.lockout_duration = 900
        self.sms_provider_url = os.environ.get("SMS_PROVIDER_URL")
        self.sms_api_key = os.environ.get("SMS_API_KEY")
        self.email_service_url = os.environ.get("EMAIL_SERVICE_URL")
        self.email_api_key = os.environ.get("EMAIL_API_KEY")

    def setup_totp(self, user_id: int) -> Dict[str, Any]:
        """Set up TOTP (Time-based One-Time Password) for user"""
        try:
            user = User.query.get(user_id)
            if not user:
                raise ValueError("User not found")
            secret = pyotp.random_base32()
            totp = pyotp.TOTP(secret)
            provisioning_uri = totp.provisioning_uri(
                name=user.email, issuer_name=self.totp_issuer
            )
            qr_code_data = self._generate_qr_code(provisioning_uri)
            if not user.profile:
                user.profile = UserProfile(user_id=user_id)
                self.db.add(user.profile)
            user.profile.totp_secret = self._encrypt_secret(secret)
            user.profile.mfa_enabled = False
            user.profile.mfa_methods = user.profile.mfa_methods or []
            self.db.commit()
            self.audit_service.log_event(
                event_type=AuditEventType.MFA_SETUP,
                event_description="TOTP setup initiated",
                user_id=user_id,
                event_data={"mfa_method": MFAMethod.TOTP, "setup_stage": "initiated"},
            )
            return {
                "success": True,
                "secret": secret,
                "qr_code": qr_code_data,
                "provisioning_uri": provisioning_uri,
                "backup_codes": None,
            }
        except Exception as e:
            current_app.logger.error(f"TOTP setup error for user {user_id}: {e}")
            raise

    def verify_totp_setup(self, user_id: int, verification_code: str) -> Dict[str, Any]:
        """Verify TOTP setup and enable MFA"""
        try:
            user = User.query.get(user_id)
            if not user or not user.profile or (not user.profile.totp_secret):
                raise ValueError("TOTP not set up for user")
            secret = self._decrypt_secret(user.profile.totp_secret)
            totp = pyotp.TOTP(secret)
            if not totp.verify(verification_code, valid_window=self.totp_window):
                self.audit_service.log_event(
                    event_type=AuditEventType.MFA_VERIFICATION,
                    event_description="TOTP setup verification failed",
                    severity=AuditSeverity.MEDIUM,
                    user_id=user_id,
                    event_data={
                        "mfa_method": MFAMethod.TOTP,
                        "verification_result": "failed",
                    },
                )
                return {"success": False, "error": "Invalid verification code"}
            user.profile.mfa_enabled = True
            if MFAMethod.TOTP not in user.profile.mfa_methods:
                user.profile.mfa_methods.append(MFAMethod.TOTP)
            backup_codes = self._generate_backup_codes(user_id)
            self.db.commit()
            self.audit_service.log_event(
                event_type=AuditEventType.MFA_SETUP,
                event_description="TOTP setup completed successfully",
                user_id=user_id,
                event_data={"mfa_method": MFAMethod.TOTP, "setup_stage": "completed"},
            )
            return {
                "success": True,
                "mfa_enabled": True,
                "backup_codes": backup_codes,
                "message": "TOTP authentication enabled successfully",
            }
        except Exception as e:
            current_app.logger.error(f"TOTP verification error for user {user_id}: {e}")
            raise

    def setup_sms_mfa(self, user_id: int, phone_number: str) -> Dict[str, Any]:
        """Set up SMS-based MFA"""
        try:
            user = User.query.get(user_id)
            if not user:
                raise ValueError("User not found")
            if not self._validate_phone_number(phone_number):
                return {"success": False, "error": "Invalid phone number format"}
            verification_code = self._generate_sms_code()
            if not user.profile:
                user.profile = UserProfile(user_id=user_id)
                self.db.add(user.profile)
            user.profile.phone_number = self._encrypt_secret(phone_number)
            user.profile.sms_verification_code = self._encrypt_secret(verification_code)
            user.profile.sms_code_expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=self.sms_code_expiry
            )
            self.db.commit()
            sms_sent = self._send_sms(
                phone_number,
                f"Your BlockScore verification code is: {verification_code}",
            )
            if not sms_sent:
                return {
                    "success": False,
                    "error": "Failed to send SMS verification code",
                }
            self.audit_service.log_event(
                event_type=AuditEventType.MFA_SETUP,
                event_description="SMS MFA setup initiated",
                user_id=user_id,
                event_data={
                    "mfa_method": MFAMethod.SMS,
                    "phone_number_masked": self._mask_phone_number(phone_number),
                },
            )
            return {
                "success": True,
                "message": "Verification code sent to your phone",
                "phone_number_masked": self._mask_phone_number(phone_number),
            }
        except Exception as e:
            current_app.logger.error(f"SMS MFA setup error for user {user_id}: {e}")
            raise

    def verify_sms_setup(self, user_id: int, verification_code: str) -> Dict[str, Any]:
        """Verify SMS setup and enable SMS MFA"""
        try:
            user = User.query.get(user_id)
            if not user or not user.profile:
                raise ValueError("User or profile not found")
            if (
                not user.profile.sms_verification_code
                or not user.profile.sms_code_expires_at
            ):
                return {"success": False, "error": "No pending SMS verification"}
            if datetime.now(timezone.utc) > user.profile.sms_code_expires_at:
                return {"success": False, "error": "Verification code expired"}
            stored_code = self._decrypt_secret(user.profile.sms_verification_code)
            if verification_code != stored_code:
                self.audit_service.log_event(
                    event_type=AuditEventType.MFA_VERIFICATION,
                    event_description="SMS setup verification failed",
                    severity=AuditSeverity.MEDIUM,
                    user_id=user_id,
                    event_data={
                        "mfa_method": MFAMethod.SMS,
                        "verification_result": "failed",
                    },
                )
                return {"success": False, "error": "Invalid verification code"}
            user.profile.mfa_enabled = True
            if MFAMethod.SMS not in (user.profile.mfa_methods or []):
                user.profile.mfa_methods = (user.profile.mfa_methods or []) + [
                    MFAMethod.SMS
                ]
            user.profile.sms_verification_code = None
            user.profile.sms_code_expires_at = None
            self.db.commit()
            self.audit_service.log_event(
                event_type=AuditEventType.MFA_SETUP,
                event_description="SMS MFA setup completed successfully",
                user_id=user_id,
                event_data={"mfa_method": MFAMethod.SMS, "setup_stage": "completed"},
            )
            return {
                "success": True,
                "mfa_enabled": True,
                "message": "SMS authentication enabled successfully",
            }
        except Exception as e:
            current_app.logger.error(f"SMS verification error for user {user_id}: {e}")
            raise

    def verify_mfa(
        self, user_id: int, method: str, code: str, backup_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """Verify MFA code during authentication"""
        try:
            user = User.query.get(user_id)
            if not user or not user.profile:
                raise ValueError("User or profile not found")
            if not user.profile.mfa_enabled:
                return {"success": False, "error": "MFA not enabled for user"}
            if self._is_mfa_locked(user_id):
                return {
                    "success": False,
                    "error": "Account temporarily locked due to failed MFA attempts",
                }
            verification_result = False
            if backup_code:
                verification_result = self._verify_backup_code(user_id, backup_code)
                method = MFAMethod.BACKUP_CODES
            elif method == MFAMethod.TOTP:
                verification_result = self._verify_totp_code(user_id, code)
            elif method == MFAMethod.SMS:
                verification_result = self._verify_sms_code(user_id, code)
            else:
                return {"success": False, "error": "Unsupported MFA method"}
            if verification_result:
                self._reset_mfa_failed_attempts(user_id)
                self.audit_service.log_event(
                    event_type=AuditEventType.MFA_VERIFICATION,
                    event_description=f"MFA verification successful using {method}",
                    user_id=user_id,
                    event_data={"mfa_method": method, "verification_result": "success"},
                )
                return {
                    "success": True,
                    "method_used": method,
                    "message": "MFA verification successful",
                }
            else:
                self._increment_mfa_failed_attempts(user_id)
                self.audit_service.log_event(
                    event_type=AuditEventType.MFA_VERIFICATION,
                    event_description=f"MFA verification failed using {method}",
                    severity=AuditSeverity.MEDIUM,
                    user_id=user_id,
                    event_data={"mfa_method": method, "verification_result": "failed"},
                )
                return {"success": False, "error": "Invalid MFA code"}
        except Exception as e:
            current_app.logger.error(f"MFA verification error for user {user_id}: {e}")
            raise

    def send_sms_code(self, user_id: int) -> Dict[str, Any]:
        """Send SMS verification code for authentication"""
        try:
            user = User.query.get(user_id)
            if not user or not user.profile:
                raise ValueError("User or profile not found")
            if MFAMethod.SMS not in (user.profile.mfa_methods or []):
                return {"success": False, "error": "SMS MFA not enabled for user"}
            if self._is_sms_rate_limited(user_id):
                return {
                    "success": False,
                    "error": "SMS rate limit exceeded. Please try again later.",
                }
            verification_code = self._generate_sms_code()
            phone_number = self._decrypt_secret(user.profile.phone_number)
            user.profile.sms_verification_code = self._encrypt_secret(verification_code)
            user.profile.sms_code_expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=self.sms_code_expiry
            )
            self.db.commit()
            sms_sent = self._send_sms(
                phone_number, f"Your BlockScore login code is: {verification_code}"
            )
            if not sms_sent:
                return {"success": False, "error": "Failed to send SMS code"}
            self._update_sms_rate_limit(user_id)
            return {
                "success": True,
                "message": "SMS code sent successfully",
                "expires_in": self.sms_code_expiry,
            }
        except Exception as e:
            current_app.logger.error(f"SMS code sending error for user {user_id}: {e}")
            raise

    def disable_mfa(self, user_id: int, method: Optional[str] = None) -> Dict[str, Any]:
        """Disable MFA for user (specific method or all)"""
        try:
            user = User.query.get(user_id)
            if not user or not user.profile:
                raise ValueError("User or profile not found")
            if method:
                if user.profile.mfa_methods and method in user.profile.mfa_methods:
                    user.profile.mfa_methods.remove(method)
                    if method == MFAMethod.TOTP:
                        user.profile.totp_secret = None
                    elif method == MFAMethod.SMS:
                        user.profile.phone_number = None
                        user.profile.sms_verification_code = None
                        user.profile.sms_code_expires_at = None
                    if not user.profile.mfa_methods:
                        user.profile.mfa_enabled = False
                        user.profile.backup_codes = None
            else:
                user.profile.mfa_enabled = False
                user.profile.mfa_methods = []
                user.profile.totp_secret = None
                user.profile.phone_number = None
                user.profile.sms_verification_code = None
                user.profile.sms_code_expires_at = None
                user.profile.backup_codes = None
            self.db.commit()
            self.audit_service.log_event(
                event_type=AuditEventType.MFA_DISABLED,
                event_description=f"MFA disabled: {method or 'all methods'}",
                severity=AuditSeverity.MEDIUM,
                user_id=user_id,
                event_data={
                    "disabled_method": method or "all",
                    "remaining_methods": user.profile.mfa_methods or [],
                },
            )
            return {
                "success": True,
                "message": f"MFA {method or 'completely'} disabled successfully",
                "mfa_enabled": user.profile.mfa_enabled,
                "active_methods": user.profile.mfa_methods or [],
            }
        except Exception as e:
            current_app.logger.error(f"MFA disable error for user {user_id}: {e}")
            raise

    def get_mfa_status(self, user_id: int) -> Dict[str, Any]:
        """Get MFA status and available methods for user"""
        try:
            user = User.query.get(user_id)
            if not user or not user.profile:
                return {
                    "mfa_enabled": False,
                    "available_methods": [],
                    "backup_codes_remaining": 0,
                }
            backup_codes_remaining = 0
            if user.profile.backup_codes:
                backup_codes = self._decrypt_secret(user.profile.backup_codes)
                backup_codes_list = backup_codes.split(",") if backup_codes else []
                backup_codes_remaining = len(
                    [code for code in backup_codes_list if code.strip()]
                )
            return {
                "mfa_enabled": user.profile.mfa_enabled or False,
                "available_methods": user.profile.mfa_methods or [],
                "backup_codes_remaining": backup_codes_remaining,
                "phone_number_masked": (
                    self._mask_phone_number(
                        self._decrypt_secret(user.profile.phone_number)
                    )
                    if user.profile.phone_number
                    else None
                ),
            }
        except Exception as e:
            current_app.logger.error(f"MFA status error for user {user_id}: {e}")
            return {
                "mfa_enabled": False,
                "available_methods": [],
                "backup_codes_remaining": 0,
            }

    def regenerate_backup_codes(self, user_id: int) -> Dict[str, Any]:
        """Regenerate backup codes for user"""
        try:
            user = User.query.get(user_id)
            if not user or not user.profile or (not user.profile.mfa_enabled):
                raise ValueError("MFA not enabled for user")
            backup_codes = self._generate_backup_codes(user_id)
            self.audit_service.log_event(
                event_type=AuditEventType.MFA_BACKUP_CODES_REGENERATED,
                event_description="Backup codes regenerated",
                user_id=user_id,
                event_data={"codes_count": len(backup_codes)},
            )
            return {
                "success": True,
                "backup_codes": backup_codes,
                "message": "New backup codes generated successfully",
            }
        except Exception as e:
            current_app.logger.error(
                f"Backup codes regeneration error for user {user_id}: {e}"
            )
            raise

    def _generate_qr_code(self, data: str) -> str:
        """Generate QR code as base64 encoded image"""
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return base64.b64encode(buffer.getvalue()).decode()

    def _encrypt_secret(self, secret: str) -> str:
        """Encrypt sensitive data"""
        key = os.environ.get("MFA_ENCRYPTION_KEY", "default_key_change_in_production")
        return (
            base64.b64encode(
                hmac.new(key.encode(), secret.encode(), hashlib.sha256).digest()
            ).decode()
            + ":"
            + base64.b64encode(secret.encode()).decode()
        )

    def _decrypt_secret(self, encrypted_secret: str) -> str:
        """Decrypt sensitive data"""
        try:
            parts = encrypted_secret.split(":")
            if len(parts) != 2:
                raise ValueError("Invalid encrypted data format")
            return base64.b64decode(parts[1]).decode()
        except Exception:
            raise ValueError("Failed to decrypt secret")

    def _generate_backup_codes(self, user_id: int) -> List[str]:
        """Generate backup codes for user"""
        codes = []
        for _ in range(self.backup_codes_count):
            code = "".join([str(secrets.randbelow(10)) for _ in range(8)])
            codes.append(f"{code[:4]}-{code[4:]}")
        user = User.query.get(user_id)
        user.profile.backup_codes = self._encrypt_secret(",".join(codes))
        self.db.commit()
        return codes

    def _generate_sms_code(self) -> str:
        """Generate SMS verification code"""
        return "".join(
            [str(secrets.randbelow(10)) for _ in range(self.sms_code_length)]
        )

    def _validate_phone_number(self, phone_number: str) -> bool:
        """Validate phone number format"""
        import re

        pattern = "^\\+?1?[2-9]\\d{2}[2-9]\\d{2}\\d{4}$"
        return bool(re.match(pattern, phone_number.replace("-", "").replace(" ", "")))

    def _mask_phone_number(self, phone_number: str) -> str:
        """Mask phone number for display"""
        if not phone_number or len(phone_number) < 4:
            return "****"
        return f"****{phone_number[-4:]}"

    def _send_sms(self, phone_number: str, message: str) -> bool:
        """Send SMS message"""
        try:
            if not self.sms_provider_url or not self.sms_api_key:
                current_app.logger.warning("SMS service not configured")
                return False
            headers = {
                "Authorization": f"Bearer {self.sms_api_key}",
                "Content-Type": "application/json",
            }
            payload = {"to": phone_number, "message": message}
            response = requests.post(
                self.sms_provider_url, json=payload, headers=headers, timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            current_app.logger.error(f"SMS sending error: {e}")
            return False

    def _verify_totp_code(self, user_id: int, code: str) -> bool:
        """Verify TOTP code"""
        try:
            user = User.query.get(user_id)
            if not user.profile.totp_secret:
                return False
            secret = self._decrypt_secret(user.profile.totp_secret)
            totp = pyotp.TOTP(secret)
            return totp.verify(code, valid_window=self.totp_window)
        except Exception as e:
            current_app.logger.error(f"TOTP verification error: {e}")
            return False

    def _verify_sms_code(self, user_id: int, code: str) -> bool:
        """Verify SMS code"""
        try:
            user = User.query.get(user_id)
            if (
                not user.profile.sms_verification_code
                or not user.profile.sms_code_expires_at
            ):
                return False
            if datetime.now(timezone.utc) > user.profile.sms_code_expires_at:
                return False
            stored_code = self._decrypt_secret(user.profile.sms_verification_code)
            return code == stored_code
        except Exception as e:
            current_app.logger.error(f"SMS verification error: {e}")
            return False

    def _verify_backup_code(self, user_id: int, code: str) -> bool:
        """Verify and consume backup code"""
        try:
            user = User.query.get(user_id)
            if not user.profile.backup_codes:
                return False
            backup_codes = self._decrypt_secret(user.profile.backup_codes)
            codes_list = backup_codes.split(",")
            if code in codes_list:
                codes_list.remove(code)
                user.profile.backup_codes = self._encrypt_secret(",".join(codes_list))
                self.db.commit()
                return True
            return False
        except Exception as e:
            current_app.logger.error(f"Backup code verification error: {e}")
            return False

    def _is_mfa_locked(self, user_id: int) -> bool:
        """Check if user is locked due to failed MFA attempts"""
        try:
            user = User.query.get(user_id)
            if not user or not user.profile:
                return False
            if (
                hasattr(user.profile, "mfa_lockout_until")
                and user.profile.mfa_lockout_until
            ):
                if datetime.now(timezone.utc) < user.profile.mfa_lockout_until:
                    return True
                user.profile.mfa_lockout_until = None
                user.profile.mfa_failed_attempts = 0
                self.db.commit()
            return False
        except Exception:
            return False

    def _increment_mfa_failed_attempts(self, user_id: int) -> Any:
        """Increment failed MFA attempts counter and lock if threshold exceeded"""
        try:
            user = User.query.get(user_id)
            if not user or not user.profile:
                return
            if not hasattr(user.profile, "mfa_failed_attempts"):
                user.profile.mfa_failed_attempts = 0
            user.profile.mfa_failed_attempts = (
                user.profile.mfa_failed_attempts or 0
            ) + 1
            if user.profile.mfa_failed_attempts >= self.max_failed_attempts:
                user.profile.mfa_lockout_until = datetime.now(timezone.utc) + timedelta(
                    seconds=self.lockout_duration
                )
                user.profile.mfa_failed_attempts = 0
            self.db.commit()
        except Exception as e:
            current_app.logger.error(
                f"Failed to increment MFA attempts for user {user_id}: {e}"
            )
        """Increment failed MFA attempts counter"""

    def _reset_mfa_failed_attempts(self, user_id: int) -> Any:
        """Reset failed MFA attempts counter after successful verification"""
        try:
            user = User.query.get(user_id)
            if not user or not user.profile:
                return
            user.profile.mfa_failed_attempts = 0
            user.profile.mfa_lockout_until = None
            self.db.commit()
        except Exception as e:
            current_app.logger.error(
                f"Failed to reset MFA attempts for user {user_id}: {e}"
            )
        """Reset failed MFA attempts counter"""

    def _is_sms_rate_limited(self, user_id: int) -> bool:
        """Check if SMS sending is rate limited for user"""
        try:
            user = User.query.get(user_id)
            if not user or not user.profile:
                return False
            if (
                hasattr(user.profile, "last_sms_sent_at")
                and user.profile.last_sms_sent_at
            ):
                time_since_last_sms = (
                    datetime.now(timezone.utc) - user.profile.last_sms_sent_at
                ).total_seconds()
                if time_since_last_sms < 60:
                    return True
            if hasattr(user.profile, "sms_sent_count_today"):
                today_start = datetime.now(timezone.utc).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                if (
                    hasattr(user.profile, "sms_count_reset_at")
                    and user.profile.sms_count_reset_at
                ):
                    if user.profile.sms_count_reset_at < today_start:
                        return False
                if (user.profile.sms_sent_count_today or 0) >= 10:
                    return True
            return False
        except Exception:
            return False

    def _update_sms_rate_limit(self, user_id: int) -> Any:
        """Update SMS rate limiting counter"""
        try:
            user = User.query.get(user_id)
            if not user or not user.profile:
                return
            today_start = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            if (
                not hasattr(user.profile, "sms_count_reset_at")
                or not user.profile.sms_count_reset_at
                or user.profile.sms_count_reset_at < today_start
            ):
                user.profile.sms_sent_count_today = 1
                user.profile.sms_count_reset_at = datetime.now(timezone.utc)
            else:
                user.profile.sms_sent_count_today = (
                    user.profile.sms_sent_count_today or 0
                ) + 1
            user.profile.last_sms_sent_at = datetime.now(timezone.utc)
            self.db.commit()
        except Exception as e:
            current_app.logger.error(
                f"Failed to update SMS rate limit for user {user_id}: {e}"
            )
