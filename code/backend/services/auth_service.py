"""
Authentication Service for BlockScore Backend
Implements financial industry security standards
"""

import base64
import hashlib
import io
import json
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import pyotp
import qrcode
import redis
from flask_bcrypt import Bcrypt
from models.audit import AuditEventType, AuditLog, AuditSeverity
from models.user import KYCStatus, User, UserProfile, UserSession, UserStatus

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service with enterprise security features"""

    def __init__(
        self, db: Any, bcrypt: Bcrypt, redis_client: Optional[redis.Redis] = None
    ) -> None:
        self.db = db
        self.bcrypt = bcrypt
        self.redis = redis_client
        self.max_login_attempts = 5
        self.lockout_duration_minutes = 30
        self.password_min_length = 8
        self.session_timeout_hours = 24
        self.mfa_window = 30

    def create_user(self, email: str, password: str, **kwargs) -> User:
        """Create a new user with security validations"""
        try:
            if not self._validate_password_strength(password):
                raise ValueError("Password does not meet security requirements")
            user = User(
                id=str(uuid.uuid4()),
                email=email.lower().strip(),
                status=UserStatus.PENDING,
            )
            user.set_password(password)
            profile = UserProfile(
                id=str(uuid.uuid4()),
                user_id=user.id,
                kyc_status=KYCStatus.NOT_STARTED,
                data_sharing_consent=kwargs.get("data_sharing_consent", False),
                marketing_consent=kwargs.get("marketing_consent", False),
            )
            self.db.session.add(user)
            self.db.session.add(profile)
            self.db.session.commit()
            return user
        except Exception as e:
            self.db.session.rollback()
            raise e

    def authenticate_user(
        self,
        email: str,
        password: str,
        ip_address: str = None,
        user_agent: str = None,
        mfa_code: str = None,
    ) -> Optional[User]:
        """Authenticate user with comprehensive security checks"""
        try:
            user = User.query.filter_by(email=email.lower().strip()).first()
            if not user:
                return None
            if user.is_locked():
                return None
            if not user.check_password(password):
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= self.max_login_attempts:
                    user.lock_account(self.lockout_duration_minutes)
                self.db.session.commit()
                return None
            if user.mfa_enabled:
                if not mfa_code or not self._verify_mfa_code(user, mfa_code):
                    return None
            if self._is_suspicious_login(user, ip_address, user_agent):
                self._log_security_alert(
                    user_id=user.id,
                    alert_type="suspicious_login",
                    details={
                        "ip_address": ip_address,
                        "user_agent": user_agent,
                        "reason": "Unusual login pattern detected",
                    },
                )
            user.failed_login_attempts = 0
            user.locked_until = None
            user.last_login = datetime.now(timezone.utc)
            self.db.session.commit()
            return user
        except Exception as e:
            self.db.session.rollback()
            raise e

    def create_session(
        self,
        user_id: str,
        access_token: str,
        refresh_token: str,
        ip_address: str = None,
        user_agent: str = None,
    ) -> UserSession:
        """Create a new user session with tracking"""
        try:
            session_token = self._generate_session_token()
            session = UserSession(
                id=str(uuid.uuid4()),
                user_id=user_id,
                session_token=session_token,
                refresh_token=refresh_token,
                ip_address=ip_address,
                user_agent=user_agent,
                device_fingerprint=self._generate_device_fingerprint(
                    user_agent, ip_address
                ),
                expires_at=datetime.now(timezone.utc)
                + timedelta(hours=self.session_timeout_hours),
                is_active=True,
            )
            self.db.session.add(session)
            self.db.session.commit()
            if self.redis:
                self._cache_session(session)
            return session
        except Exception as e:
            self.db.session.rollback()
            raise e

    def revoke_session(self, user_id: str, session_id: Optional[str] = None) -> bool:
        """Revoke user session(s)"""
        try:
            if session_id:
                session = UserSession.query.filter_by(
                    user_id=user_id, id=session_id, is_active=True
                ).first()
                if session:
                    session.revoke()
            else:
                sessions = UserSession.query.filter_by(
                    user_id=user_id, is_active=True
                ).all()
                for session in sessions:
                    session.revoke()
            self.db.session.commit()
            if self.redis:
                self._remove_cached_sessions(user_id, session_id)
            return True
        except Exception:
            self.db.session.rollback()
            return False

    def setup_mfa(self, user_id: str) -> Dict[str, Any]:
        """Set up multi-factor authentication for user"""
        try:
            user = User.query.get(user_id)
            if not user:
                raise ValueError("User not found")
            secret = pyotp.random_base32()
            user.mfa_secret = secret
            backup_codes = [secrets.token_hex(4).upper() for _ in range(10)]
            user.backup_codes = json.dumps(backup_codes)
            self.db.session.commit()
            totp = pyotp.TOTP(secret)
            provisioning_uri = totp.provisioning_uri(
                name=user.email, issuer_name="BlockScore"
            )
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(provisioning_uri)
            qr.make(fit=True)
            qr_image = qr.make_image(fill_color="black", back_color="white")
            qr_buffer = io.BytesIO()
            qr_image.save(qr_buffer, format="PNG")
            qr_code_base64 = base64.b64encode(qr_buffer.getvalue()).decode()
            return {
                "secret": secret,
                "qr_code": f"data:image/png;base64,{qr_code_base64}",
                "backup_codes": backup_codes,
                "manual_entry_key": secret,
            }
        except Exception as e:
            self.db.session.rollback()
            raise e

    def enable_mfa(self, user_id: str, verification_code: str) -> bool:
        """Enable MFA after verifying the setup"""
        try:
            user = User.query.get(user_id)
            if not user or not user.mfa_secret:
                return False
            if self._verify_mfa_code(user, verification_code):
                user.mfa_enabled = True
                self.db.session.commit()
                return True
            return False
        except Exception:
            self.db.session.rollback()
            return False

    def disable_mfa(
        self, user_id: str, password: str, verification_code: str = None
    ) -> bool:
        """Disable MFA with proper verification"""
        try:
            user = User.query.get(user_id)
            if not user:
                return False
            if not user.check_password(password):
                return False
            if user.mfa_enabled and verification_code:
                if not self._verify_mfa_code(user, verification_code):
                    return False
            user.mfa_enabled = False
            user.mfa_secret = None
            user.backup_codes = None
            self.db.session.commit()
            return True
        except Exception:
            self.db.session.rollback()
            return False

    def change_password(
        self, user_id: str, current_password: str, new_password: str
    ) -> bool:
        """Change user password with security validations"""
        try:
            user = User.query.get(user_id)
            if not user:
                return False
            if not user.check_password(current_password):
                return False
            if not self._validate_password_strength(new_password):
                raise ValueError("New password does not meet security requirements")
            if self._is_password_recently_used(user, new_password):
                raise ValueError("Cannot reuse a recent password")
            user.set_password(new_password)
            self.revoke_session(user_id)
            self.db.session.commit()
            return True
        except Exception as e:
            self.db.session.rollback()
            raise e

    def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all active sessions for a user"""
        sessions = (
            UserSession.query.filter_by(user_id=user_id, is_active=True)
            .order_by(UserSession.last_activity.desc())
            .all()
        )
        return [session.to_dict() for session in sessions]

    def _validate_password_strength(self, password: str) -> bool:
        """Validate password meets security requirements"""
        if len(password) < self.password_min_length:
            return False
        has_upper = any((c.isupper() for c in password))
        has_lower = any((c.islower() for c in password))
        has_digit = any((c.isdigit() for c in password))
        has_special = any((c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password))
        return has_upper and has_lower and has_digit and has_special

    def _verify_mfa_code(self, user: User, code: str) -> bool:
        """Verify MFA code (TOTP or backup code)"""
        if not user.mfa_secret:
            return False
        totp = pyotp.TOTP(user.mfa_secret)
        if totp.verify(code, valid_window=self.mfa_window):
            return True
        if user.backup_codes:
            backup_codes = json.loads(user.backup_codes)
            if code.upper() in backup_codes:
                backup_codes.remove(code.upper())
                user.backup_codes = json.dumps(backup_codes)
                return True
        return False

    def _is_suspicious_login(
        self, user: User, ip_address: str, user_agent: str
    ) -> bool:
        """Detect suspicious login patterns"""
        if not ip_address:
            return False
        recent_sessions = (
            UserSession.query.filter_by(user_id=user.id)
            .filter(
                UserSession.created_at > datetime.now(timezone.utc) - timedelta(days=30)
            )
            .order_by(UserSession.created_at.desc())
            .limit(10)
            .all()
        )
        if not recent_sessions:
            return False
        recent_ips = {
            session.ip_address for session in recent_sessions if session.ip_address
        }
        if ip_address not in recent_ips and len(recent_ips) > 0:
            return True
        recent_agents = {
            session.user_agent for session in recent_sessions if session.user_agent
        }
        if user_agent and user_agent not in recent_agents and (len(recent_agents) > 0):
            return True
        return False

    def _generate_session_token(self) -> str:
        """Generate secure session token"""
        return secrets.token_urlsafe(32)

    def _generate_device_fingerprint(
        self, user_agent: str = None, ip_address: str = None
    ) -> str:
        """Generate device fingerprint for session tracking"""
        fingerprint_data = (
            f"{user_agent or ''}{ip_address or ''}{datetime.now().date()}"
        )
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16]

    def _cache_session(self, session: UserSession) -> Any:
        """Cache session in Redis"""
        if not self.redis:
            return
        try:
            session_data = {
                "user_id": session.user_id,
                "expires_at": session.expires_at.isoformat(),
                "is_active": session.is_active,
            }
            self.redis.setex(
                f"session:{session.session_token}",
                int(timedelta(hours=self.session_timeout_hours).total_seconds()),
                json.dumps(session_data),
            )
        except Exception as e:
            logger.info(f"Failed to cache session: {e}")

    def _remove_cached_sessions(
        self, user_id: str, session_id: Optional[str] = None
    ) -> Any:
        """Remove cached sessions from Redis"""
        if not self.redis:
            return
        try:
            if session_id:
                session = UserSession.query.get(session_id)
                if session:
                    self.redis.delete(f"session:{session.session_token}")
            else:
                sessions = UserSession.query.filter_by(
                    user_id=user_id, is_active=True
                ).all()
                for session in sessions:
                    self.redis.delete(f"session:{session.session_token}")
        except Exception as e:
            logger.info(f"Failed to remove cached sessions: {e}")

    def _is_password_recently_used(self, user: User, new_password: str) -> bool:
        """Check if password was recently used (simplified implementation)"""
        return user.check_password(new_password)

    def _log_security_alert(
        self, user_id: str, alert_type: str, details: Dict[str, Any]
    ) -> Any:
        """Log security alerts"""
        try:
            audit_log = AuditLog(
                id=str(uuid.uuid4()),
                event_type=AuditEventType.SECURITY_ALERT,
                event_category="security",
                event_description=f"Security alert: {alert_type}",
                severity=AuditSeverity.HIGH,
                user_id=user_id,
                ip_address=details.get("ip_address"),
                user_agent=details.get("user_agent"),
                compliance_relevant=True,
            )
            audit_log.set_event_data(details)
            self.db.session.add(audit_log)
            self.db.session.commit()
        except Exception as e:
            logger.info(f"Failed to log security alert: {e}")

    def get_security_summary(self, user_id: str) -> Dict[str, Any]:
        """Get security summary for user"""
        user = User.query.get(user_id)
        if not user:
            return {}
        active_sessions = UserSession.query.filter_by(
            user_id=user_id, is_active=True
        ).count()
        recent_logins = (
            UserSession.query.filter_by(user_id=user_id)
            .filter(
                UserSession.created_at > datetime.now(timezone.utc) - timedelta(days=30)
            )
            .count()
        )
        return {
            "mfa_enabled": user.mfa_enabled,
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "password_changed_at": user.password_changed_at.isoformat(),
            "active_sessions": active_sessions,
            "recent_logins_30d": recent_logins,
            "account_status": user.status.value,
            "failed_login_attempts": user.failed_login_attempts,
            "is_locked": user.is_locked(),
        }
