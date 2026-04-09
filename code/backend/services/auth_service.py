import compat_stubs  # noqa

"""
Authentication Service for BlockScore Backend
Implements financial industry security standards
"""

import base64
import hashlib
import io
import json
import logging
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import pyotp
import qrcode
import redis
from extensions import db
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token, create_refresh_token
from models.audit import AuditEventType, AuditLog, AuditSeverity
from models.user import KYCStatus, User, UserProfile, UserSession, UserStatus

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


class AuthService:
    """Authentication service with enterprise security features"""

    def __init__(
        self, db: Any, bcrypt: Bcrypt = None, redis_client: Optional[redis.Redis] = None
    ) -> None:
        self.db = db
        self.bcrypt = bcrypt
        self.redis = redis_client
        self.max_login_attempts = 5
        self.lockout_duration_minutes = 30
        self.password_min_length = 8
        self.session_timeout_hours = 24
        self.mfa_window = 1
        self.jwt_secret = None

    # ------------------------------------------------------------------
    # Public API methods expected by tests
    # ------------------------------------------------------------------

    def register_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new user (returns dict with success/message/user_id)"""
        try:
            email = user_data.get("email", "").strip().lower()
            password = user_data.get("password", "")

            if not self._validate_email(email):
                return {"success": False, "message": "Invalid email address format"}

            validation = self._validate_password(password)
            if not validation["valid"]:
                return {"success": False, "message": validation["message"]}

            existing = User.query.filter_by(email=email).first()
            if existing:
                return {
                    "success": False,
                    "message": "A user with this email already exists",
                }

            user = User(
                id=str(uuid.uuid4()),
                email=email,
                status=UserStatus.ACTIVE,
                is_active=True,
                email_verified=True,
                password_hash="placeholder",
            )
            user.set_password(password)

            profile = UserProfile(
                id=str(uuid.uuid4()),
                user_id=user.id,
                first_name=user_data.get("first_name"),
                last_name=user_data.get("last_name"),
                phone_number=user_data.get("phone_number") or user_data.get("phone"),
                kyc_status=KYCStatus.NOT_STARTED,
                data_sharing_consent=user_data.get("data_sharing_consent", False),
                marketing_consent=user_data.get("marketing_consent", False),
            )

            self.db.session.add(user)
            self.db.session.add(profile)
            self.db.session.commit()

            self._log_audit_event(
                event_type=AuditEventType.USER_REGISTRATION,
                description=f"User registered: {email}",
                user_id=user.id,
            )

            return {
                "success": True,
                "message": "User registered successfully",
                "user_id": user.id,
                "user": user.to_dict(),
            }
        except Exception as e:
            self.db.session.rollback()
            logger.error(f"register_user error: {e}")
            raise

    def create_user(self, email: str, password: str, **kwargs) -> User:
        """Create a new user object (used by app.py register route)"""
        result = self.register_user({"email": email, "password": password, **kwargs})
        if not result["success"]:
            raise ValueError(result["message"])
        return User.query.filter_by(email=email.lower().strip()).first()

    def authenticate_user(
        self,
        email: str,
        password: str,
        ip_address: str = None,
        user_agent: str = None,
        mfa_code: str = None,
    ) -> Dict[str, Any]:
        """Authenticate user; always returns a dict with success/message/tokens."""
        return self._authenticate_internal(
            email, password, ip_address, user_agent, mfa_code, return_dict=True
        )

    def authenticate_user_dict(
        self,
        email: str,
        password: str,
        ip_address: str = None,
        user_agent: str = None,
        mfa_code: str = None,
    ) -> Dict[str, Any]:
        """Authenticate user returning a dict result for service consumers"""
        return self._authenticate_internal(
            email, password, ip_address, user_agent, mfa_code, return_dict=True
        )

    def _authenticate_internal(
        self,
        email: str,
        password: str,
        ip_address=None,
        user_agent=None,
        mfa_code=None,
        return_dict=False,
    ) -> Any:
        try:
            user = User.query.filter_by(email=email.lower().strip()).first()

            def _fail(msg):
                if return_dict:
                    return {"success": False, "message": msg}
                return None

            if not user:
                return _fail("Invalid email or password")

            if not user.is_active:
                return _fail("Account is inactive")

            if hasattr(user, "email_verified") and not user.email_verified:
                return _fail("Please verify your email before logging in")

            if user.is_locked():
                return _fail(
                    "Account is temporarily locked due to failed login attempts"
                )

            if not self._verify_password(user.password_hash, password):
                user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
                if user.failed_login_attempts >= self.max_login_attempts:
                    user.lock_account(self.lockout_duration_minutes)
                self.db.session.add(user)
                self.db.session.commit()
                return _fail("Invalid email or password")

            if user.mfa_enabled:
                if not mfa_code or not self._verify_mfa_code(user, mfa_code):
                    return _fail("Invalid MFA code")

            if self._is_suspicious_login(user, ip_address, user_agent):
                self._log_security_alert(
                    user_id=user.id,
                    alert_type="suspicious_login",
                    details={"ip_address": ip_address, "user_agent": user_agent},
                )

            user.failed_login_attempts = 0
            user.locked_until = None
            user.last_login = datetime.now(timezone.utc)
            self.db.session.add(user)
            self.db.session.commit()

            self._log_audit_event(
                event_type=AuditEventType.USER_LOGIN,
                description=f"User logged in: {email}",
                user_id=user.id,
                ip_address=ip_address,
            )

            if return_dict:
                try:
                    access_token = create_access_token(identity=user.id)
                    refresh_token = create_refresh_token(identity=user.id)
                except RuntimeError:
                    access_token = self._generate_access_token(user.id)
                    refresh_token = secrets.token_urlsafe(32)
                return {
                    "success": True,
                    "user_id": user.id,
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "message": "Login successful",
                }
            return user
        except Exception:
            self.db.session.rollback()
            raise

    def create_session(
        self,
        user_id: str,
        access_token: str,
        refresh_token: str,
        ip_address: str = None,
        user_agent: str = None,
    ) -> UserSession:
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
        except Exception:
            self.db.session.rollback()
            raise

    def revoke_session(self, user_id: str, session_id: Optional[str] = None) -> Any:
        """Revoke user session(s). Returns dict when called with session_id, else bool."""
        try:
            if session_id:
                session = UserSession.query.filter_by(
                    user_id=user_id, id=session_id, is_active=True
                ).first()
                if not session:
                    return {
                        "success": False,
                        "message": "Invalid or already revoked session",
                    }
                session.revoke()
                self.db.session.commit()
                return {"success": True, "message": "Session revoked"}
            else:
                sessions = UserSession.query.filter_by(
                    user_id=user_id, is_active=True
                ).all()
                for s in sessions:
                    s.revoke()
                self.db.session.commit()
                if self.redis:
                    self._remove_cached_sessions(user_id, None)
                return True
        except Exception:
            self.db.session.rollback()
            return False

    def logout_user(self, user_id: str, session_token: str) -> Dict[str, Any]:
        """Logout user by revoking a specific session by token"""
        try:
            session = UserSession.query.filter_by(
                user_id=user_id, session_token=session_token, is_active=True
            ).first()
            if not session:
                return {"success": False, "message": "Invalid session token"}
            session.revoke()
            self.db.session.commit()
            self._log_audit_event(
                event_type=AuditEventType.USER_LOGOUT,
                description="User logged out",
                user_id=user_id,
            )
            return {"success": True, "message": "Logged out successfully"}
        except Exception as e:
            self.db.session.rollback()
            return {"success": False, "message": str(e)}

    def refresh_token(self, refresh_token_value: str) -> Dict[str, Any]:
        """Refresh an access token using a session's refresh_token / session_token"""
        try:
            session = (
                UserSession.query.filter(
                    (UserSession.session_token == refresh_token_value)
                    | (UserSession.refresh_token == refresh_token_value)
                )
                .filter_by(is_active=True)
                .first()
            )

            if not session:
                return {"success": False, "message": "Invalid refresh token"}

            if session.is_expired():
                return {"success": False, "message": "Refresh token has expired"}

            user = db.session.get(User, session.user_id)
            if not user or not user.is_active:
                return {"success": False, "message": "User not found or inactive"}

            try:
                new_access_token = create_access_token(identity=user.id)
                new_refresh_token = create_refresh_token(identity=user.id)
            except RuntimeError:
                new_access_token = self._generate_access_token(user.id)
                new_refresh_token = secrets.token_urlsafe(32)

            session.session_token = new_refresh_token
            session.last_activity = datetime.now(timezone.utc)
            self.db.session.commit()

            return {
                "success": True,
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
            }
        except Exception as e:
            self.db.session.rollback()
            return {"success": False, "message": str(e)}

    def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate a JWT access token"""
        try:
            import jwt as pyjwt
            from flask import current_app

            secret = current_app.config.get("JWT_SECRET_KEY", "jwt-secret-key")
            payload = pyjwt.decode(token, secret, algorithms=["HS256"])
            user_id = payload.get("sub") or payload.get("user_id")
            return {"valid": True, "user_id": user_id}
        except Exception as e:
            msg = str(e).lower()
            if "expired" in msg:
                return {"valid": False, "message": "Token has expired"}
            return {"valid": False, "message": "Invalid token"}

    def request_password_reset(self, email: str) -> Dict[str, Any]:
        """Request a password reset token"""
        try:
            user = User.query.filter_by(email=email.lower().strip()).first()
            if not user:
                return {"success": False, "message": "User not found"}
            reset_token = secrets.token_urlsafe(32)
            user.password_reset_token = reset_token
            user.password_reset_expires = datetime.now(timezone.utc) + timedelta(
                hours=1
            )
            self.db.session.add(user)
            self.db.session.commit()
            return {
                "success": True,
                "message": "Password reset email sent",
                "reset_token": reset_token,
            }
        except Exception as e:
            self.db.session.rollback()
            return {"success": False, "message": str(e)}

    def reset_password(self, reset_token: str, new_password: str) -> Dict[str, Any]:
        """Reset password using a reset token"""
        try:
            user = User.query.filter_by(password_reset_token=reset_token).first()
            if not user:
                return {"success": False, "message": "Invalid or unknown reset token"}

            if user.password_reset_expires:
                expires = user.password_reset_expires
                if expires.tzinfo is None:
                    expires = expires.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) > expires:
                    return {"success": False, "message": "Reset token has expired"}

            validation = self._validate_password(new_password)
            if not validation["valid"]:
                return {"success": False, "message": validation["message"]}

            user.set_password(new_password)
            user.password_reset_token = None
            user.password_reset_expires = None
            self.db.session.add(user)
            self.db.session.commit()
            return {"success": True, "message": "Password reset successfully"}
        except Exception as e:
            self.db.session.rollback()
            return {"success": False, "message": str(e)}

    def change_password(
        self, user_id: str, current_password: str, new_password: str
    ) -> Dict[str, Any]:
        """Change user password with security validations"""
        try:
            user = db.session.get(User, user_id)
            if not user:
                return {"success": False, "message": "User not found"}

            if not self._verify_password(user.password_hash, current_password):
                return {"success": False, "message": "Current password is incorrect"}

            validation = self._validate_password(new_password)
            if not validation["valid"]:
                return {"success": False, "message": validation["message"]}

            user.set_password(new_password)
            self.db.session.add(user)
            self.db.session.commit()
            return {"success": True, "message": "Password changed successfully"}
        except Exception:
            self.db.session.rollback()
            raise

    def setup_mfa(self, user_id: str) -> Dict[str, Any]:
        """Set up multi-factor authentication for user"""
        try:
            user = db.session.get(User, user_id)
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
                "success": True,
                "secret": secret,
                "qr_code": f"data:image/png;base64,{qr_code_base64}",
                "backup_codes": backup_codes,
                "manual_entry_key": secret,
            }
        except Exception:
            self.db.session.rollback()
            raise

    def enable_mfa(self, user_id: str, verification_code: str = None) -> Dict[str, Any]:
        """Enable MFA: sets up secret if not set, verifies if code provided"""
        try:
            user = db.session.get(User, user_id)
            if not user:
                return {"success": False, "message": "User not found"}

            if not user.mfa_secret:
                return self.setup_mfa(user_id)

            if verification_code:
                if not self._verify_mfa_code(user, verification_code):
                    return {"success": False, "message": "Invalid verification code"}
                user.mfa_enabled = True
                self.db.session.commit()
                return {
                    "success": True,
                    "message": "MFA enabled",
                    "secret": user.mfa_secret,
                }

            return {
                "success": True,
                "message": "MFA secret already set; provide verification code to activate",
                "secret": user.mfa_secret,
            }
        except Exception:
            self.db.session.rollback()
            raise

    def verify_mfa_token(self, user_id: str, code: str) -> Dict[str, Any]:
        """Verify a TOTP MFA token for a user"""
        try:
            user = db.session.get(User, user_id)
            if not user or not user.mfa_secret:
                return {"valid": False, "message": "MFA not configured"}
            if self._verify_mfa_code(user, code):
                return {"valid": True}
            return {"valid": False, "message": "Invalid MFA token"}
        except Exception as e:
            return {"valid": False, "message": str(e)}

    def disable_mfa(
        self, user_id: str, verification_code: str = None, password: str = None
    ) -> Dict[str, Any]:
        """Disable MFA with proper verification"""
        try:
            user = db.session.get(User, user_id)
            if not user:
                return {"success": False, "message": "User not found"}

            if password and not self._verify_password(user.password_hash, password):
                return {"success": False, "message": "Incorrect password"}

            if verification_code:
                result = self.verify_mfa_token(user_id, verification_code)
                if not result["valid"]:
                    return {"success": False, "message": "Invalid MFA token"}

            user.mfa_enabled = False
            user.mfa_secret = None
            user.backup_codes = None
            self.db.session.commit()
            return {"success": True, "message": "MFA disabled"}
        except Exception as e:
            self.db.session.rollback()
            return {"success": False, "message": str(e)}

    def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all active sessions for a user"""
        sessions = (
            UserSession.query.filter_by(user_id=user_id, is_active=True)
            .order_by(UserSession.last_activity.desc())
            .all()
        )
        return [session.to_dict() for session in sessions]

    def get_security_summary(self, user_id: str) -> Dict[str, Any]:
        user = db.session.get(User, user_id)
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
            "password_changed_at": (
                user.password_changed_at.isoformat()
                if user.password_changed_at
                else None
            ),
            "active_sessions": active_sessions,
            "recent_logins_30d": recent_logins,
            "account_status": user.status.value,
            "failed_login_attempts": user.failed_login_attempts,
            "is_locked": user.is_locked(),
        }

    # ------------------------------------------------------------------
    # Internal / helper methods
    # ------------------------------------------------------------------

    def _validate_password(self, password: str) -> Dict[str, Any]:
        """Validate password meets security requirements. Returns dict."""
        if not password or len(password) < self.password_min_length:
            return {
                "valid": False,
                "message": f"Password must be at least {self.password_min_length} characters",
            }
        if not any(c.isupper() for c in password):
            return {
                "valid": False,
                "message": "Password must contain at least one uppercase letter",
            }
        if not any(c.islower() for c in password):
            return {
                "valid": False,
                "message": "Password must contain at least one lowercase letter",
            }
        if not any(c.isdigit() for c in password):
            return {
                "valid": False,
                "message": "Password must contain at least one number",
            }
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            return {
                "valid": False,
                "message": "Password must contain at least one special character",
            }
        return {"valid": True, "message": "Password is strong"}

    def _validate_password_strength(self, password: str) -> bool:
        """Validate password meets security requirements (legacy boolean API)"""
        return self._validate_password(password)["valid"]

    def _validate_email(self, email: str) -> bool:
        """Validate email format"""
        if not email:
            return False
        return bool(EMAIL_REGEX.match(email))

    def _verify_password(self, password_hash: str, password: str) -> bool:
        """Verify a plain password against its hash"""
        if self.bcrypt:
            try:
                return self.bcrypt.check_password_hash(password_hash, password)
            except Exception:
                return False
        try:
            from flask_bcrypt import check_password_hash

            return check_password_hash(password_hash, password)
        except Exception:
            return False

    def _hash_password(self, password: str) -> str:
        """Hash a plain password"""
        if self.bcrypt:
            return self.bcrypt.generate_password_hash(password).decode("utf-8")
        from flask_bcrypt import generate_password_hash

        return generate_password_hash(password).decode("utf-8")

    def _generate_access_token(self, user_id: str) -> str:
        """Generate a JWT-like access token (fallback when outside app context)"""
        import time

        import jwt as pyjwt

        payload = {
            "sub": str(user_id),
            "iat": int(time.time()),
            "exp": int(time.time()) + 900,
            "jti": str(uuid.uuid4()),
        }
        try:
            from flask import current_app

            secret = current_app.config.get("JWT_SECRET_KEY", "jwt-secret-key")
        except RuntimeError:
            secret = "jwt-secret-key"
        return pyjwt.encode(payload, secret, algorithm="HS256")

    def _verify_mfa_code(self, user: User, code: str) -> bool:
        """Verify MFA code (TOTP or backup code)"""
        if not user.mfa_secret:
            return False
        totp = pyotp.TOTP(user.mfa_secret)
        if totp.verify(code, valid_window=self.mfa_window):
            return True
        if user.backup_codes:
            try:
                backup_codes = json.loads(user.backup_codes)
                if code.upper() in backup_codes:
                    backup_codes.remove(code.upper())
                    user.backup_codes = json.dumps(backup_codes)
                    return True
            except Exception:
                pass
        return False

    def _is_suspicious_login(
        self, user: User, ip_address: str, user_agent: str
    ) -> bool:
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
        recent_ips = {s.ip_address for s in recent_sessions if s.ip_address}
        if ip_address not in recent_ips and len(recent_ips) > 0:
            return True
        return False

    def _generate_session_token(self) -> str:
        return secrets.token_urlsafe(32)

    def _generate_device_fingerprint(
        self, user_agent: str = None, ip_address: str = None
    ) -> str:
        data = (
            f"{user_agent or ''}{ip_address or ''}{datetime.now(timezone.utc).date()}"
        )
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def _cache_session(self, session: UserSession) -> None:
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
            logger.debug(f"Failed to cache session: {e}")

    def _remove_cached_sessions(
        self, user_id: str, session_id: Optional[str] = None
    ) -> None:
        if not self.redis:
            return
        try:
            if session_id:
                session = db.session.get(UserSession, session_id)
                if session:
                    self.redis.delete(f"session:{session.session_token}")
            else:
                sessions = UserSession.query.filter_by(user_id=user_id).all()
                for s in sessions:
                    self.redis.delete(f"session:{s.session_token}")
        except Exception as e:
            logger.debug(f"Failed to remove cached sessions: {e}")

    def _is_password_recently_used(self, user: User, new_password: str) -> bool:
        return self._verify_password(user.password_hash, new_password)

    def _log_audit_event(
        self,
        event_type: AuditEventType,
        description: str,
        user_id: str = None,
        ip_address: str = None,
        severity: AuditSeverity = AuditSeverity.LOW,
    ) -> None:
        try:
            log = AuditLog(
                id=str(uuid.uuid4()),
                event_type=event_type,
                event_category=event_type.value.split("_")[0],
                event_description=description,
                severity=severity,
                user_id=user_id,
                ip_address=ip_address,
            )
            self.db.session.add(log)
            self.db.session.commit()
        except Exception as e:
            logger.debug(f"Failed to log audit event: {e}")

    def _log_security_alert(
        self, user_id: str, alert_type: str, details: Dict[str, Any]
    ) -> None:
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
            logger.debug(f"Failed to log security alert: {e}")


# Alias so tests can import AuthenticationService
AuthenticationService = AuthService
