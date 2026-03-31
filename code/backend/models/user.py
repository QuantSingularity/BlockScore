"""
User models for BlockScore Backend
"""

import enum
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from extensions import bcrypt, db
from marshmallow import Schema, ValidationError, fields, validate, validates_schema


class UserStatus(enum.Enum):
    """User account status enumeration"""

    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"
    BANNED = "banned"


class KYCStatus(enum.Enum):
    """KYC verification status enumeration"""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class User(db.Model):
    """User model for authentication and basic information"""

    __tablename__ = "users"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    status = db.Column(db.Enum(UserStatus), default=UserStatus.PENDING, nullable=False)
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime(timezone=True), nullable=True)
    last_login = db.Column(db.DateTime(timezone=True), nullable=True)
    password_changed_at = db.Column(
        db.DateTime(timezone=True), default=datetime.now(timezone.utc)
    )
    mfa_enabled = db.Column(db.Boolean, default=False)
    mfa_secret = db.Column(db.String(32), nullable=True)
    backup_codes = db.Column(db.Text, nullable=True)
    # MFA-related fields
    totp_secret = db.Column(db.String(255), nullable=True)
    sms_verification_code = db.Column(db.String(255), nullable=True)
    mfa_methods = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True), default=datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )
    profile = db.relationship(
        "UserProfile", backref="user", uselist=False, cascade="all, delete-orphan"
    )
    sessions = db.relationship(
        "UserSession", backref="user", cascade="all, delete-orphan"
    )

    def set_password(self, password: Any) -> None:
        """Set password hash"""
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
        self.password_changed_at = datetime.now(timezone.utc)

    def check_password(self, password: Any) -> bool:
        """Check password against hash"""
        return bcrypt.check_password_hash(self.password_hash, password)

    def is_locked(self) -> bool:
        """Check if account is locked"""
        if self.locked_until:
            return datetime.now(timezone.utc) < self.locked_until
        return False

    def lock_account(self, duration_minutes: Any = 30) -> None:
        """Lock account for specified duration"""
        self.locked_until = datetime.now(timezone.utc) + timedelta(
            minutes=duration_minutes
        )
        self.failed_login_attempts += 1

    def unlock_account(self) -> None:
        """Unlock account and reset failed attempts"""
        self.locked_until = None
        self.failed_login_attempts = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "email": self.email,
            "status": self.status.value,
            "mfa_enabled": self.mfa_enabled,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class UserProfile(db.Model):
    """Extended user profile information"""

    __tablename__ = "user_profiles"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)
    street_address = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(100), nullable=True)
    postal_code = db.Column(db.String(20), nullable=True)
    country = db.Column(db.String(100), nullable=True)
    kyc_status = db.Column(db.Enum(KYCStatus), default=KYCStatus.NOT_STARTED)
    kyc_completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    kyc_documents = db.Column(db.Text, nullable=True)
    annual_income = db.Column(db.Decimal(15, 2), nullable=True)
    employment_status = db.Column(db.String(50), nullable=True)
    employer_name = db.Column(db.String(255), nullable=True)
    wallet_address = db.Column(db.String(42), nullable=True, index=True)
    wallet_verified = db.Column(db.Boolean, default=False)
    data_sharing_consent = db.Column(db.Boolean, default=False)
    marketing_consent = db.Column(db.Boolean, default=False)
    # MFA-related fields
    totp_secret = db.Column(db.String(255), nullable=True)
    sms_verification_code = db.Column(db.String(255), nullable=True)
    mfa_methods = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True), default=datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )

    def get_full_name(self) -> str:
        """Get full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name or "Unknown"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.get_full_name(),
            "date_of_birth": (
                self.date_of_birth.isoformat() if self.date_of_birth else None
            ),
            "phone_number": self.phone_number,
            "address": {
                "street_address": self.street_address,
                "city": self.city,
                "state": self.state,
                "postal_code": self.postal_code,
                "country": self.country,
            },
            "kyc_status": self.kyc_status.value,
            "kyc_completed_at": (
                self.kyc_completed_at.isoformat() if self.kyc_completed_at else None
            ),
            "annual_income": float(self.annual_income) if self.annual_income else None,
            "employment_status": self.employment_status,
            "employer_name": self.employer_name,
            "wallet_address": self.wallet_address,
            "wallet_verified": self.wallet_verified,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class UserSession(db.Model):
    """User session tracking for security"""

    __tablename__ = "user_sessions"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    session_token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    refresh_token = db.Column(db.String(255), unique=True, nullable=True, index=True)
    device_fingerprint = db.Column(db.String(255), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    location = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    last_activity = db.Column(
        db.DateTime(timezone=True), default=datetime.now(timezone.utc)
    )
    created_at = db.Column(
        db.DateTime(timezone=True), default=datetime.now(timezone.utc)
    )

    def is_expired(self) -> bool:
        """Check if session is expired"""
        return datetime.now(timezone.utc) > self.expires_at

    def revoke(self) -> None:
        """Revoke session"""
        self.is_active = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "device_fingerprint": self.device_fingerprint,
            "ip_address": self.ip_address,
            "location": self.location,
            "is_active": self.is_active,
            "expires_at": self.expires_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "created_at": self.created_at.isoformat(),
        }


class UserRegistrationSchema(Schema):
    """Schema for user registration"""

    email = fields.Email(required=True, validate=validate.Length(max=255))
    password = fields.Str(required=True, validate=validate.Length(min=8, max=128))
    confirm_password = fields.Str(required=True)

    @validates_schema
    def validate_passwords_match(self, data: Any, **kwargs) -> Any:
        if data.get("password") != data.get("confirm_password"):
            raise ValidationError(
                "Passwords do not match", field_name="confirm_password"
            )


class UserLoginSchema(Schema):
    """Schema for user login"""

    email = fields.Email(required=True)
    password = fields.Str(required=True)
    remember_me = fields.Bool(load_default=False)
    mfa_code = fields.Str(validate=validate.Length(equal=6), allow_none=True)


class UserProfileSchema(Schema):
    """Schema for user profile"""

    first_name = fields.Str(validate=validate.Length(max=100), allow_none=True)
    last_name = fields.Str(validate=validate.Length(max=100), allow_none=True)
    date_of_birth = fields.Date(allow_none=True)
    phone_number = fields.Str(validate=validate.Length(max=20), allow_none=True)
    street_address = fields.Str(validate=validate.Length(max=255), allow_none=True)
    city = fields.Str(validate=validate.Length(max=100), allow_none=True)
    state = fields.Str(validate=validate.Length(max=100), allow_none=True)
    postal_code = fields.Str(validate=validate.Length(max=20), allow_none=True)
    country = fields.Str(validate=validate.Length(max=100), allow_none=True)
    annual_income = fields.Decimal(places=2, allow_none=True)
    employment_status = fields.Str(validate=validate.Length(max=50), allow_none=True)
    employer_name = fields.Str(validate=validate.Length(max=255), allow_none=True)
    wallet_address = fields.Str(validate=validate.Length(equal=42), allow_none=True)


class UserSchema(Schema):
    """Schema for user serialization"""

    id = fields.Str(dump_only=True)
    email = fields.Email(dump_only=True)
    status = fields.Str(dump_only=True)
    mfa_enabled = fields.Bool(dump_only=True)
    last_login = fields.DateTime(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    profile = fields.Nested(UserProfileSchema, dump_only=True)
