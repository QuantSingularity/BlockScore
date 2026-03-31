"""
Security Middleware for Financial Services
Implements comprehensive security controls for financial applications
"""

import base64
import hashlib
import hmac
import json
import os
import re
import time
from functools import wraps
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from flask import current_app, g, jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from models.audit import AuditEventType, AuditSeverity
from services.audit_service import AuditService


class SecurityMiddleware:
    """Comprehensive security middleware for financial applications"""

    def __init__(self, app: Any = None, redis_client: Any = None) -> None:
        self.app = app
        self.redis_client = redis_client
        self.audit_service = None
        self.max_request_size = 10 * 1024 * 1024
        self.allowed_file_types = {".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"}
        self.blocked_ips = set()
        self.rate_limit_windows = {
            "login": {"requests": 5, "window": 300},
            "api": {"requests": 100, "window": 60},
            "upload": {"requests": 10, "window": 300},
        }
        self._init_encryption()
        if app:
            self.init_app(app)

    def init_app(self, app: Any) -> Any:
        """Initialize security middleware with Flask app"""
        self.app = app
        self.audit_service = AuditService(app.extensions.get("sqlalchemy").db)
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        app.errorhandler(413)(self.request_entity_too_large)
        app.errorhandler(429)(self.rate_limit_exceeded)

    def _init_encryption(self) -> Any:
        """Initialize encryption components"""
        key = os.environ.get("ENCRYPTION_KEY")
        if not key:
            key = Fernet.generate_key()
            os.environ["ENCRYPTION_KEY"] = key.decode()
        if isinstance(key, str):
            key = key.encode()
        self.cipher_suite = Fernet(key)

    def before_request(self) -> Any:
        """Security checks before processing request"""
        try:
            g.request_start_time = time.time()
            g.request_id = self._generate_request_id()
            if (
                request.content_length
                and request.content_length > self.max_request_size
            ):
                return self._security_error(
                    "Request too large",
                    "Request size exceeds maximum allowed limit",
                    413,
                )
            if self._is_ip_blocked(request.remote_addr):
                return self._security_error(
                    "Access denied", "Your IP address has been blocked", 403
                )
            if not self._check_rate_limit():
                return self._security_error(
                    "Rate limit exceeded", "Too many requests from your IP address", 429
                )
            if not self._validate_input():
                return self._security_error(
                    "Invalid input",
                    "Request contains invalid or potentially malicious content",
                    400,
                )
            if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
                if not self._validate_csrf():
                    return self._security_error(
                        "CSRF validation failed", "Invalid or missing CSRF token", 403
                    )
            self._log_security_event(
                "request_processed",
                {
                    "method": request.method,
                    "endpoint": request.endpoint,
                    "ip_address": request.remote_addr,
                    "user_agent": request.headers.get("User-Agent"),
                },
            )
        except Exception as e:
            current_app.logger.error(f"Security middleware error: {e}")
            return self._security_error(
                "Security check failed",
                "An error occurred during security validation",
                500,
            )

    def after_request(self, response: Any) -> Any:
        """Security headers and logging after request processing"""
        try:
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
            )
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Permissions-Policy"] = (
                "geolocation=(), microphone=(), camera=()"
            )
            response.headers.pop("Server", None)
            if hasattr(g, "request_start_time"):
                response_time = (time.time() - g.request_start_time) * 1000
                self._log_security_event(
                    "response_sent",
                    {
                        "status_code": response.status_code,
                        "response_time_ms": response_time,
                        "content_length": response.content_length,
                    },
                )
            return response
        except Exception as e:
            current_app.logger.error(f"After request security error: {e}")
            return response

    def _generate_request_id(self) -> str:
        """Generate unique request ID"""
        return hashlib.sha256(
            f"{time.time()}{request.remote_addr}{request.user_agent}".encode()
        ).hexdigest()[:16]

    def _is_ip_blocked(self, ip_address: str) -> bool:
        """Check if IP address is blocked"""
        try:
            if ip_address in self.blocked_ips:
                return True
            if self.redis_client:
                blocked_key = f"blocked_ip:{ip_address}"
                if self.redis_client.exists(blocked_key):
                    return True
            return False
        except Exception as e:
            current_app.logger.error(f"IP blocking check error: {e}")
            return False

    def _check_rate_limit(self) -> bool:
        """Check rate limiting for current request"""
        try:
            if not self.redis_client:
                return True
            ip_address = request.remote_addr
            endpoint = request.endpoint or "unknown"
            limit_type = "api"
            if "login" in endpoint:
                limit_type = "login"
            elif "upload" in endpoint:
                limit_type = "upload"
            config = self.rate_limit_windows[limit_type]
            key = f"rate_limit:{limit_type}:{ip_address}"
            current_count = self.redis_client.get(key)
            if current_count is None:
                self.redis_client.setex(key, config["window"], 1)
                return True
            current_count = int(current_count)
            if current_count >= config["requests"]:
                self._log_security_event(
                    "rate_limit_exceeded",
                    {
                        "ip_address": ip_address,
                        "limit_type": limit_type,
                        "current_count": current_count,
                        "limit": config["requests"],
                    },
                    severity=AuditSeverity.HIGH,
                )
                return False
            self.redis_client.incr(key)
            return True
        except Exception as e:
            current_app.logger.error(f"Rate limiting error: {e}")
            return True

    def _validate_input(self) -> bool:
        """Validate request input for security threats"""
        try:
            sql_patterns = [
                "(\\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\\b)",
                "(\\b(OR|AND)\\s+\\d+\\s*=\\s*\\d+)",
                "(--|#|/\\*|\\*/)",
                "(\\bxp_cmdshell\\b|\\bsp_executesql\\b)",
            ]
            xss_patterns = [
                "<script[^>]*>.*?</script>",
                "javascript:",
                "on\\w+\\s*=",
                "<iframe[^>]*>.*?</iframe>",
            ]
            path_patterns = [
                "\\.\\./",
                "\\.\\.\\\\",
                "/etc/passwd",
                "/proc/",
                "\\\\windows\\\\system32",
            ]
            data_to_check = []
            for key, value in request.args.items():
                data_to_check.append(f"{key}={value}")
            if request.form:
                for key, value in request.form.items():
                    data_to_check.append(f"{key}={value}")
            if request.is_json and request.json:
                data_to_check.append(json.dumps(request.json))
            for header, value in request.headers:
                if header.lower() in ["user-agent", "referer", "x-forwarded-for"]:
                    data_to_check.append(value)
            for data in data_to_check:
                if not isinstance(data, str):
                    continue
                data_lower = data.lower()
                for pattern in sql_patterns:
                    if re.search(pattern, data_lower, re.IGNORECASE):
                        self._log_security_event(
                            "sql_injection_attempt",
                            {
                                "pattern": pattern,
                                "data": data[:100],
                                "ip_address": request.remote_addr,
                            },
                            severity=AuditSeverity.CRITICAL,
                        )
                        return False
                for pattern in xss_patterns:
                    if re.search(pattern, data_lower, re.IGNORECASE):
                        self._log_security_event(
                            "xss_attempt",
                            {
                                "pattern": pattern,
                                "data": data[:100],
                                "ip_address": request.remote_addr,
                            },
                            severity=AuditSeverity.HIGH,
                        )
                        return False
                for pattern in path_patterns:
                    if re.search(pattern, data_lower, re.IGNORECASE):
                        self._log_security_event(
                            "path_traversal_attempt",
                            {
                                "pattern": pattern,
                                "data": data[:100],
                                "ip_address": request.remote_addr,
                            },
                            severity=AuditSeverity.HIGH,
                        )
                        return False
            return True
        except Exception as e:
            current_app.logger.error(f"Input validation error: {e}")
            return True

    def _validate_csrf(self) -> bool:
        """Validate CSRF token for state-changing operations"""
        try:
            if request.path.startswith("/api/") and "Authorization" in request.headers:
                return True
            csrf_token = request.headers.get("X-CSRF-Token") or request.form.get(
                "csrf_token"
            )
            if not csrf_token:
                return False
            if self.redis_client:
                session_id = request.cookies.get("session_id")
                if session_id:
                    stored_token = self.redis_client.get(f"csrf_token:{session_id}")
                    if stored_token and stored_token.decode() == csrf_token:
                        return True
            return False
        except Exception as e:
            current_app.logger.error(f"CSRF validation error: {e}")
            return True

    def _log_security_event(
        self,
        event_type: str,
        event_data: Dict[str, Any],
        severity: AuditSeverity = AuditSeverity.LOW,
    ) -> Any:
        """Log security event to audit service"""
        try:
            if self.audit_service:
                self.audit_service.log_event(
                    event_type=AuditEventType.SECURITY_EVENT,
                    event_description=f"Security event: {event_type}",
                    severity=severity,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get("User-Agent"),
                    user_id=self._get_current_user_id(),
                    event_data=event_data,
                )
        except Exception as e:
            current_app.logger.error(f"Security event logging error: {e}")

    def _get_current_user_id(self) -> Optional[int]:
        """Get current user ID if authenticated"""
        try:
            verify_jwt_in_request(optional=True)
            return get_jwt_identity()
        except:
            return None

    def _security_error(self, error: str, message: str, status_code: int) -> Any:
        """Return security error response"""
        return (
            jsonify(
                {
                    "success": False,
                    "error": error,
                    "message": message,
                    "request_id": getattr(g, "request_id", None),
                }
            ),
            status_code,
        )

    def request_entity_too_large(self, error: Any) -> Any:
        """Handle request too large error"""
        return self._security_error(
            "Request too large", "Request size exceeds maximum allowed limit", 413
        )

    def rate_limit_exceeded(self, error: Any) -> Any:
        """Handle rate limit exceeded error"""
        return self._security_error(
            "Rate limit exceeded", "Too many requests. Please try again later.", 429
        )

    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        try:
            if isinstance(data, str):
                data = data.encode()
            return self.cipher_suite.encrypt(data).decode()
        except Exception as e:
            current_app.logger.error(f"Encryption error: {e}")
            raise

    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        try:
            if isinstance(encrypted_data, str):
                encrypted_data = encrypted_data.encode()
            return self.cipher_suite.decrypt(encrypted_data).decode()
        except Exception as e:
            current_app.logger.error(f"Decryption error: {e}")
            raise

    def hash_password(self, password: str, salt: Optional[str] = None) -> tuple:
        """Hash password with salt"""
        if salt is None:
            salt = os.urandom(32)
        elif isinstance(salt, str):
            salt = salt.encode()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return (key.decode(), base64.urlsafe_b64encode(salt).decode())

    def verify_password(self, password: str, hashed_password: str, salt: str) -> bool:
        """Verify password against hash"""
        try:
            key, _ = self.hash_password(
                password, base64.urlsafe_b64decode(salt.encode())
            )
            return hmac.compare_digest(key, hashed_password)
        except Exception:
            return False

    def generate_csrf_token(self, session_id: str) -> str:
        """Generate CSRF token for session"""
        token = base64.urlsafe_b64encode(os.urandom(32)).decode()
        if self.redis_client:
            self.redis_client.setex(f"csrf_token:{session_id}", 3600, token)
        return token

    def block_ip(
        self, ip_address: str, duration: int = 3600, reason: str = "Security violation"
    ) -> Any:
        """Block IP address for specified duration"""
        try:
            if self.redis_client:
                self.redis_client.setex(f"blocked_ip:{ip_address}", duration, reason)
            self._log_security_event(
                "ip_blocked",
                {"ip_address": ip_address, "duration": duration, "reason": reason},
                severity=AuditSeverity.HIGH,
            )
        except Exception as e:
            current_app.logger.error(f"IP blocking error: {e}")


def require_api_key(f: Any) -> Any:
    """Decorator to require API key authentication"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "API key required",
                        "message": "API key is required for this endpoint",
                    }
                ),
                401,
            )
        if not _validate_api_key(api_key):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Invalid API key",
                        "message": "The provided API key is invalid",
                    }
                ),
                401,
            )
        return f(*args, **kwargs)

    return decorated_function


def require_mfa(f: Any) -> Any:
    """Decorator to require multi-factor authentication"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = get_jwt_identity()
        if not user_id:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Authentication required",
                        "message": "You must be logged in to access this resource",
                    }
                ),
                401,
            )
        mfa_verified = request.headers.get("X-MFA-Verified")
        if not mfa_verified or mfa_verified != "true":
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "MFA required",
                        "message": "Multi-factor authentication is required for this operation",
                    }
                ),
                403,
            )
        return f(*args, **kwargs)

    return decorated_function


def _validate_api_key(api_key: str) -> bool:
    """Validate API key (implement your validation logic)"""
    valid_keys = os.environ.get("VALID_API_KEYS", "").split(",")
    return api_key in valid_keys
