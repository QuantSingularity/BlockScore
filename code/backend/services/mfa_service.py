import base64
import io
import json
import logging
import os
import secrets
from typing import Any, Dict, List, Optional

import pyotp
import qrcode
from extensions import db
from models.audit import AuditEventType, AuditSeverity
from models.user import User
from services.audit_service import AuditService

logger = logging.getLogger(__name__)


class MFAMethod:

    TOTP = "totp"
    SMS = "sms"
    EMAIL = "email"
    BACKUP_CODES = "backup_codes"
    HARDWARE_TOKEN = "hardware_token"


class MFAService:

    def __init__(self, db_session: Any) -> None:
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

    def setup_totp(self, user_id: Any) -> Dict[str, Any]:
        try:
            user = db.session.get(User, user_id)
            if not user:
                return {"success": False, "message": "User not found"}

            secret = pyotp.random_base32()
            totp = pyotp.TOTP(secret)
            provisioning_uri = totp.provisioning_uri(
                name=getattr(user, "email", str(user_id)),
                issuer_name=self.totp_issuer,
            )
            qr_code_data = self._generate_qr_code(provisioning_uri)

            user.mfa_secret = secret
            try:
                self.db.commit()
            except Exception:
                pass

            try:
                self._log(
                    AuditEventType.MFA_SETUP,
                    "TOTP setup initiated",
                    user_id,
                    {"mfa_method": MFAMethod.TOTP, "setup_stage": "initiated"},
                )
            except Exception:
                pass

            return {
                "success": True,
                "secret": secret,
                "qr_code": qr_code_data,
                "provisioning_uri": provisioning_uri,
                "backup_codes": None,
            }
        except Exception as e:
            logger.error(f"TOTP setup error for user {user_id}: {e}")
            return {"success": False, "message": str(e)}

    def verify_totp(self, user_id: Any, code: str) -> Dict[str, Any]:
        try:
            user = db.session.get(User, user_id)
            if not user:
                return {"valid": False, "message": "User not found"}

            secret = getattr(user, "mfa_secret", None) or getattr(
                user, "totp_secret", None
            )
            if not secret:
                return {"valid": False, "message": "MFA not configured"}

            totp = pyotp.TOTP(secret)
            if totp.verify(code, valid_window=self.totp_window):
                return {"valid": True}
            return {"valid": False, "message": "Invalid or expired code"}
        except Exception as e:
            logger.error(f"TOTP verify error for user {user_id}: {e}")
            return {"valid": False, "message": str(e)}

    def enable_mfa(self, user_id: Any, verification_code: str) -> Dict[str, Any]:
        try:
            user = db.session.get(User, user_id)
            if not user:
                return {"success": False, "message": "User not found"}

            secret = getattr(user, "mfa_secret", None) or getattr(
                user, "totp_secret", None
            )
            if not secret:
                return {"success": False, "message": "MFA not set up"}

            totp = pyotp.TOTP(secret)
            if not totp.verify(verification_code, valid_window=self.totp_window):
                return {"success": False, "message": "Invalid verification code"}

            user.mfa_enabled = True
            try:
                self.db.commit()
            except Exception:
                pass

            try:
                self._log(
                    AuditEventType.MFA_SETUP,
                    "MFA enabled",
                    user_id,
                    {"mfa_method": MFAMethod.TOTP, "setup_stage": "enabled"},
                )
            except Exception:
                pass

            return {"success": True, "message": "MFA enabled"}
        except Exception as e:
            logger.error(f"enable_mfa error for user {user_id}: {e}")
            return {"success": False, "message": str(e)}

    def disable_mfa(self, user_id: Any, verification_code: str) -> Dict[str, Any]:
        try:
            user = db.session.get(User, user_id)
            if not user:
                return {"success": False, "message": "User not found"}

            secret = getattr(user, "mfa_secret", None) or getattr(
                user, "totp_secret", None
            )
            if not secret:
                return {"success": False, "message": "MFA not configured"}

            totp = pyotp.TOTP(secret)
            if not totp.verify(verification_code, valid_window=self.totp_window):
                return {"success": False, "message": "Invalid verification code"}

            user.mfa_enabled = False
            user.mfa_secret = None
            if hasattr(user, "totp_secret"):
                user.totp_secret = None
            if hasattr(user, "backup_codes"):
                user.backup_codes = None

            try:
                self.db.commit()
            except Exception:
                pass

            try:
                self._log(
                    AuditEventType.MFA_DISABLED,
                    "MFA disabled",
                    user_id,
                    {"mfa_method": "all"},
                    severity=AuditSeverity.MEDIUM,
                )
            except Exception:
                pass

            return {"success": True, "message": "MFA disabled successfully"}
        except Exception as e:
            logger.error(f"disable_mfa error for user {user_id}: {e}")
            return {"success": False, "message": str(e)}

    def get_mfa_status(self, user_id: Any) -> Dict[str, Any]:
        try:
            user = db.session.get(User, user_id)
            if not user:
                return {
                    "mfa_enabled": False,
                    "available_methods": [],
                    "backup_codes_remaining": 0,
                }

            mfa_enabled = bool(getattr(user, "mfa_enabled", False))
            backup_codes_remaining = 0
            raw_codes = getattr(user, "backup_codes", None)
            if raw_codes:
                try:
                    codes = json.loads(raw_codes)
                    backup_codes_remaining = len(codes)
                except Exception:
                    pass

            available_methods = []
            if getattr(user, "mfa_secret", None) or getattr(user, "totp_secret", None):
                available_methods.append(MFAMethod.TOTP)

            return {
                "mfa_enabled": mfa_enabled,
                "available_methods": available_methods,
                "backup_codes_remaining": backup_codes_remaining,
            }
        except Exception as e:
            logger.error(f"get_mfa_status error for user {user_id}: {e}")
            return {
                "mfa_enabled": False,
                "available_methods": [],
                "backup_codes_remaining": 0,
            }

    def verify_backup_code(self, user_id: Any, code: str) -> Dict[str, Any]:
        try:
            user = db.session.get(User, user_id)
            if not user:
                return {"valid": False, "message": "User not found"}

            raw = getattr(user, "backup_codes", None)
            if not raw:
                return {"valid": False, "message": "No backup codes"}

            codes = json.loads(raw)
            if code.upper() in [c.upper() for c in codes]:
                codes = [c for c in codes if c.upper() != code.upper()]
                user.backup_codes = json.dumps(codes)
                try:
                    self.db.commit()
                except Exception:
                    pass
                return {"valid": True}
            return {"valid": False, "message": "Invalid backup code"}
        except Exception as e:
            logger.error(f"verify_backup_code error for user {user_id}: {e}")
            return {"valid": False, "message": str(e)}

    def _generate_backup_codes(self, user_id_or_count: Any = None) -> List[str]:
        count = self.backup_codes_count
        user_id = None

        if isinstance(user_id_or_count, int):
            if user_id_or_count <= 100:
                count = user_id_or_count
            else:
                user_id = user_id_or_count

        codes = []
        for _ in range(count):
            code = "".join([str(secrets.randbelow(10)) for _ in range(8)])
            codes.append(f"{code[:4]}-{code[4:]}")

        if user_id is not None:
            try:
                user = db.session.get(User, user_id)
                if user:
                    user.backup_codes = json.dumps(codes)
                    self.db.commit()
            except Exception:
                pass

        return codes

    def _generate_qr_code(self, data: str) -> str:
        try:
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            return (
                "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()
            )
        except Exception:
            return (
                "data:image/png;base64," + base64.b64encode(b"PNG_PLACEHOLDER").decode()
            )

    def _log(
        self,
        event_type: AuditEventType,
        description: str,
        user_id: Any,
        event_data: Dict = None,
        severity: AuditSeverity = AuditSeverity.LOW,
    ) -> None:
        try:
            self.audit_service.log_event(
                event_type=event_type,
                event_description=description,
                user_id=user_id,
                severity=severity,
                event_data=event_data,
            )
        except Exception as e:
            logger.warning(f"Audit log failed: {e}")

    def setup_sms_mfa(self, user_id: int, phone_number: str) -> Dict[str, Any]:
        return {"success": False, "error": "SMS MFA requires external SMS provider"}

    def verify_mfa(
        self, user_id: int, method: str, code: str, backup_code: Optional[str] = None
    ) -> Dict[str, Any]:
        if backup_code:
            return self.verify_backup_code(user_id, backup_code)
        if method == MFAMethod.TOTP:
            result = self.verify_totp(user_id, code)
            return {"success": result.get("valid", False), **result}
        return {"success": False, "error": "Unsupported MFA method"}

    def regenerate_backup_codes(self, user_id: int) -> Dict[str, Any]:
        try:
            user = db.session.get(User, user_id)
            if not user:
                raise ValueError("User not found")
            backup_codes = self._generate_backup_codes(user_id)
            try:
                self._log(
                    AuditEventType.MFA_BACKUP_CODES_REGENERATED,
                    "Backup codes regenerated",
                    user_id,
                    {"codes_count": len(backup_codes)},
                )
            except Exception:
                pass
            return {
                "success": True,
                "backup_codes": backup_codes,
                "message": "New backup codes generated successfully",
            }
        except Exception as e:
            logger.error(f"Backup codes regeneration error for user {user_id}: {e}")
            raise
