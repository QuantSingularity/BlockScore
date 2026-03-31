"""
Credit scoring models for BlockScore Backend
"""

import enum
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from extensions import db
from marshmallow import Schema, fields, validate


class CreditScoreStatus(enum.Enum):
    """Credit score status enumeration"""

    CALCULATING = "calculating"
    ACTIVE = "active"
    EXPIRED = "expired"
    DISPUTED = "disputed"
    FROZEN = "frozen"


class CreditFactorType(enum.Enum):
    """Credit factor type enumeration"""

    PAYMENT_HISTORY = "payment_history"
    CREDIT_UTILIZATION = "credit_utilization"
    LENGTH_OF_HISTORY = "length_of_history"
    CREDIT_MIX = "credit_mix"
    NEW_CREDIT = "new_credit"
    INCOME_STABILITY = "income_stability"
    DEBT_TO_INCOME = "debt_to_income"
    BLOCKCHAIN_ACTIVITY = "blockchain_activity"


class CreditEventType(enum.Enum):
    """Credit event type enumeration"""

    LOAN_APPLICATION = "loan_application"
    LOAN_APPROVAL = "loan_approval"
    LOAN_DISBURSEMENT = "loan_disbursement"
    PAYMENT_MADE = "payment_made"
    PAYMENT_MISSED = "payment_missed"
    PAYMENT_LATE = "payment_late"
    LOAN_CLOSED = "loan_closed"
    CREDIT_INQUIRY = "credit_inquiry"
    SCORE_RECALCULATION = "score_recalculation"


class CreditScore(db.Model):
    """Credit score model with versioning and audit trail"""

    __tablename__ = "credit_scores"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(
        db.String(36), db.ForeignKey("users.id"), nullable=False, index=True
    )
    score = db.Column(db.Integer, nullable=False)
    score_version = db.Column(db.String(10), nullable=False, default="1.0")
    status = db.Column(
        db.Enum(CreditScoreStatus), default=CreditScoreStatus.CALCULATING
    )
    payment_history_score = db.Column(db.Integer, nullable=True)
    credit_utilization_score = db.Column(db.Integer, nullable=True)
    length_of_history_score = db.Column(db.Integer, nullable=True)
    credit_mix_score = db.Column(db.Integer, nullable=True)
    new_credit_score = db.Column(db.Integer, nullable=True)
    income_stability_score = db.Column(db.Integer, nullable=True)
    debt_to_income_score = db.Column(db.Integer, nullable=True)
    blockchain_activity_score = db.Column(db.Integer, nullable=True)
    model_name = db.Column(db.String(100), nullable=False, default="BlockScore_v1.0")
    model_confidence = db.Column(db.Float, nullable=True)
    calculation_method = db.Column(db.Text, nullable=True)
    calculated_at = db.Column(
        db.DateTime(timezone=True), default=datetime.now(timezone.utc)
    )
    expires_at = db.Column(db.DateTime(timezone=True), nullable=True)
    valid_until = db.Column(db.DateTime(timezone=True), nullable=True)
    blockchain_hash = db.Column(db.String(66), nullable=True, index=True)
    blockchain_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(
        db.DateTime(timezone=True), default=datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )
    factors = db.relationship(
        "CreditFactor", backref="credit_score", cascade="all, delete-orphan"
    )
    history = db.relationship(
        "CreditHistory", backref="credit_score", cascade="all, delete-orphan"
    )

    def is_valid(self) -> bool:
        """Check if credit score is still valid"""
        if self.valid_until:
            return datetime.now(timezone.utc) < self.valid_until
        return True

    def is_expired(self) -> bool:
        """Check if credit score is expired"""
        if self.expires_at:
            return datetime.now(timezone.utc) > self.expires_at
        return False

    def get_score_breakdown(self) -> Dict[str, Any]:
        """Get detailed score breakdown"""
        return {
            "total_score": self.score,
            "payment_history": self.payment_history_score,
            "credit_utilization": self.credit_utilization_score,
            "length_of_history": self.length_of_history_score,
            "credit_mix": self.credit_mix_score,
            "new_credit": self.new_credit_score,
            "income_stability": self.income_stability_score,
            "debt_to_income": self.debt_to_income_score,
            "blockchain_activity": self.blockchain_activity_score,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "score": self.score,
            "score_version": self.score_version,
            "status": self.status.value,
            "score_breakdown": self.get_score_breakdown(),
            "model_name": self.model_name,
            "model_confidence": self.model_confidence,
            "calculated_at": self.calculated_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "blockchain_hash": self.blockchain_hash,
            "blockchain_verified": self.blockchain_verified,
            "is_valid": self.is_valid(),
            "is_expired": self.is_expired(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class CreditFactor(db.Model):
    """Individual credit factors that contribute to the overall score"""

    __tablename__ = "credit_factors"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    credit_score_id = db.Column(
        db.String(36), db.ForeignKey("credit_scores.id"), nullable=False
    )
    factor_type = db.Column(db.Enum(CreditFactorType), nullable=False)
    factor_name = db.Column(db.String(100), nullable=False)
    factor_description = db.Column(db.Text, nullable=True)
    raw_value = db.Column(db.Float, nullable=True)
    normalized_value = db.Column(db.Float, nullable=True)
    weight = db.Column(db.Float, nullable=False, default=1.0)
    contribution = db.Column(db.Float, nullable=True)
    data_source = db.Column(db.String(100), nullable=True)
    confidence_level = db.Column(db.Float, nullable=True)
    calculation_details = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True), default=datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "credit_score_id": self.credit_score_id,
            "factor_type": self.factor_type.value,
            "factor_name": self.factor_name,
            "factor_description": self.factor_description,
            "raw_value": self.raw_value,
            "normalized_value": self.normalized_value,
            "weight": self.weight,
            "contribution": self.contribution,
            "data_source": self.data_source,
            "confidence_level": self.confidence_level,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class CreditHistory(db.Model):
    """Credit history events and timeline"""

    __tablename__ = "credit_history"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(
        db.String(36), db.ForeignKey("users.id"), nullable=False, index=True
    )
    credit_score_id = db.Column(
        db.String(36), db.ForeignKey("credit_scores.id"), nullable=True
    )
    event_type = db.Column(db.Enum(CreditEventType), nullable=False)
    event_title = db.Column(db.String(255), nullable=False)
    event_description = db.Column(db.Text, nullable=True)
    event_data = db.Column(db.Text, nullable=True)
    amount = db.Column(db.Decimal(15, 2), nullable=True)
    currency = db.Column(db.String(3), nullable=True, default="USD")
    score_before = db.Column(db.Integer, nullable=True)
    score_after = db.Column(db.Integer, nullable=True)
    score_change = db.Column(db.Integer, nullable=True)
    loan_id = db.Column(db.String(36), nullable=True)
    transaction_id = db.Column(db.String(255), nullable=True)
    blockchain_hash = db.Column(db.String(66), nullable=True)
    event_date = db.Column(db.DateTime(timezone=True), nullable=False)
    reported_date = db.Column(
        db.DateTime(timezone=True), default=datetime.now(timezone.utc)
    )
    created_at = db.Column(
        db.DateTime(timezone=True), default=datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )

    def get_event_data(self) -> Dict[str, Any]:
        """Get parsed event data"""
        if self.event_data:
            try:
                return json.loads(self.event_data)
            except json.JSONDecodeError:
                return {}
        return {}

    def set_event_data(self, data: Any) -> None:
        """Set event data as JSON"""
        self.event_data = json.dumps(data) if data else None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "credit_score_id": self.credit_score_id,
            "event_type": self.event_type.value,
            "event_title": self.event_title,
            "event_description": self.event_description,
            "event_data": self.get_event_data(),
            "amount": float(self.amount) if self.amount else None,
            "currency": self.currency,
            "score_before": self.score_before,
            "score_after": self.score_after,
            "score_change": self.score_change,
            "loan_id": self.loan_id,
            "transaction_id": self.transaction_id,
            "blockchain_hash": self.blockchain_hash,
            "event_date": self.event_date.isoformat(),
            "reported_date": self.reported_date.isoformat(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class CreditScoreSchema(Schema):
    """Schema for credit score serialization"""

    id = fields.Str(dump_only=True)
    user_id = fields.Str(dump_only=True)
    score = fields.Int(validate=validate.Range(min=300, max=850))
    score_version = fields.Str(dump_only=True)
    status = fields.Str(dump_only=True)
    score_breakdown = fields.Dict(dump_only=True)
    model_name = fields.Str(dump_only=True)
    model_confidence = fields.Float(dump_only=True)
    calculated_at = fields.DateTime(dump_only=True)
    expires_at = fields.DateTime(dump_only=True)
    valid_until = fields.DateTime(dump_only=True)
    blockchain_hash = fields.Str(dump_only=True)
    blockchain_verified = fields.Bool(dump_only=True)
    is_valid = fields.Bool(dump_only=True)
    is_expired = fields.Bool(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class CreditFactorSchema(Schema):
    """Schema for credit factor serialization"""

    id = fields.Str(dump_only=True)
    credit_score_id = fields.Str(dump_only=True)
    factor_type = fields.Str(dump_only=True)
    factor_name = fields.Str(dump_only=True)
    factor_description = fields.Str(dump_only=True)
    raw_value = fields.Float(dump_only=True)
    normalized_value = fields.Float(
        validate=validate.Range(min=0, max=1), dump_only=True
    )
    weight = fields.Float(validate=validate.Range(min=0), dump_only=True)
    contribution = fields.Float(dump_only=True)
    data_source = fields.Str(dump_only=True)
    confidence_level = fields.Float(
        validate=validate.Range(min=0, max=1), dump_only=True
    )
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class CreditHistorySchema(Schema):
    """Schema for credit history serialization"""

    id = fields.Str(dump_only=True)
    user_id = fields.Str(dump_only=True)
    credit_score_id = fields.Str(dump_only=True)
    event_type = fields.Str(dump_only=True)
    event_title = fields.Str(dump_only=True)
    event_description = fields.Str(dump_only=True)
    event_data = fields.Dict(dump_only=True)
    amount = fields.Decimal(places=2, dump_only=True)
    currency = fields.Str(dump_only=True)
    score_before = fields.Int(dump_only=True)
    score_after = fields.Int(dump_only=True)
    score_change = fields.Int(dump_only=True)
    loan_id = fields.Str(dump_only=True)
    transaction_id = fields.Str(dump_only=True)
    blockchain_hash = fields.Str(dump_only=True)
    event_date = fields.DateTime(dump_only=True)
    reported_date = fields.DateTime(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class CreditScoreCalculationRequest(Schema):
    """Schema for credit score calculation request"""

    user_id = fields.Str(required=True)
    force_recalculation = fields.Bool(load_default=False)
    include_factors = fields.Bool(load_default=True)
    model_version = fields.Str(load_default="1.0")
