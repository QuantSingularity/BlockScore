"""
Loan management models for BlockScore Backend
"""

import enum
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from extensions import db
from marshmallow import Schema, fields, validate


class LoanStatus(enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    DISBURSED = "disbursed"
    ACTIVE = "active"
    PAID_OFF = "paid_off"
    DEFAULTED = "defaulted"
    CANCELLED = "cancelled"


class LoanType(enum.Enum):
    PERSONAL = "personal"
    BUSINESS = "business"
    MORTGAGE = "mortgage"
    AUTO = "auto"
    STUDENT = "student"
    CREDIT_LINE = "credit_line"
    DEFI = "defi"


class PaymentStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentMethod(enum.Enum):
    BANK_TRANSFER = "bank_transfer"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    CRYPTOCURRENCY = "cryptocurrency"
    WIRE_TRANSFER = "wire_transfer"
    ACH = "ach"


class LoanApplication(db.Model):
    __tablename__ = "loan_applications"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(
        db.String(36), db.ForeignKey("users.id"), nullable=False, index=True
    )
    application_number = db.Column(
        db.String(20), unique=True, nullable=True, index=True
    )
    loan_type = db.Column(db.Enum(LoanType), nullable=False)
    requested_amount = db.Column(db.Numeric(15, 2), nullable=False)
    requested_term_months = db.Column(db.Integer, nullable=False)
    requested_rate = db.Column(db.Float, nullable=True)
    purpose = db.Column(db.String(255), nullable=True)
    employment_status = db.Column(db.String(50), nullable=True)
    annual_income = db.Column(db.Numeric(15, 2), nullable=True)
    monthly_expenses = db.Column(db.Numeric(15, 2), nullable=True)
    status = db.Column(db.Enum(LoanStatus), default=LoanStatus.DRAFT, nullable=False)
    status_reason = db.Column(db.Text, nullable=True)
    credit_score_at_application = db.Column(db.Integer, nullable=True)
    risk_assessment = db.Column(db.Text, nullable=True)
    approval_probability = db.Column(db.Float, nullable=True)
    approved_amount = db.Column(db.Numeric(15, 2), nullable=True)
    approved_term_months = db.Column(db.Integer, nullable=True)
    approved_rate = db.Column(db.Float, nullable=True)
    monthly_payment = db.Column(db.Numeric(10, 2), nullable=True)
    application_data = db.Column(db.Text, nullable=True)
    documents = db.Column(db.Text, nullable=True)
    reviewed_by = db.Column(db.String(36), nullable=True)
    reviewed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    decision_notes = db.Column(db.Text, nullable=True)
    blockchain_hash = db.Column(db.String(66), nullable=True, index=True)
    smart_contract_address = db.Column(db.String(42), nullable=True)
    submitted_at = db.Column(db.DateTime(timezone=True), nullable=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    loan = db.relationship("Loan", backref="application", uselist=False)

    @staticmethod
    def generate_application_number() -> str:
        import secrets

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        random_part = str(secrets.randbelow(9000) + 1000)
        return f"APP{timestamp}{random_part}"

    def get_application_data(self) -> Dict[str, Any]:
        if self.application_data:
            try:
                return json.loads(self.application_data)
            except json.JSONDecodeError:
                return {}
        return {}

    def set_application_data(self, data: Any) -> None:
        self.application_data = json.dumps(data) if data else None

    def get_risk_assessment(self) -> Dict[str, Any]:
        if self.risk_assessment:
            try:
                return json.loads(self.risk_assessment)
            except json.JSONDecodeError:
                return {}
        return {}

    def set_risk_assessment(self, data: Any) -> None:
        self.risk_assessment = json.dumps(data) if data else None

    def is_expired(self) -> bool:
        if self.expires_at:
            expires = self.expires_at
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) > expires
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "application_number": self.application_number,
            "loan_type": self.loan_type.value,
            "requested_amount": float(self.requested_amount),
            "requested_term_months": self.requested_term_months,
            "requested_rate": self.requested_rate,
            "purpose": self.purpose,
            "status": self.status.value,
            "status_reason": self.status_reason,
            "credit_score_at_application": self.credit_score_at_application,
            "risk_assessment": self.get_risk_assessment(),
            "approval_probability": self.approval_probability,
            "approved_amount": (
                float(self.approved_amount) if self.approved_amount else None
            ),
            "approved_term_months": self.approved_term_months,
            "approved_rate": self.approved_rate,
            "monthly_payment": (
                float(self.monthly_payment) if self.monthly_payment else None
            ),
            "application_data": self.get_application_data(),
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "decision_notes": self.decision_notes,
            "blockchain_hash": self.blockchain_hash,
            "smart_contract_address": self.smart_contract_address,
            "submitted_at": (
                self.submitted_at.isoformat() if self.submitted_at else None
            ),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_expired": self.is_expired(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class Loan(db.Model):
    __tablename__ = "loans"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(
        db.String(36), db.ForeignKey("users.id"), nullable=False, index=True
    )
    application_id = db.Column(
        db.String(36), db.ForeignKey("loan_applications.id"), nullable=False
    )
    loan_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    loan_type = db.Column(db.Enum(LoanType), nullable=False)
    principal_amount = db.Column(db.Numeric(15, 2), nullable=False)
    interest_rate = db.Column(db.Float, nullable=False)
    term_months = db.Column(db.Integer, nullable=False)
    monthly_payment = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.Enum(LoanStatus), default=LoanStatus.APPROVED, nullable=False)
    current_balance = db.Column(db.Numeric(15, 2), nullable=False)
    total_paid = db.Column(db.Numeric(15, 2), default=0, nullable=False)
    payments_made = db.Column(db.Integer, default=0, nullable=False)
    payments_remaining = db.Column(db.Integer, nullable=False)
    first_payment_date = db.Column(db.Date, nullable=False)
    last_payment_date = db.Column(db.Date, nullable=False)
    next_payment_date = db.Column(db.Date, nullable=True)
    next_payment_amount = db.Column(db.Numeric(10, 2), nullable=True)
    days_past_due = db.Column(db.Integer, default=0)
    late_fees = db.Column(db.Numeric(10, 2), default=0)
    total_late_payments = db.Column(db.Integer, default=0)
    smart_contract_address = db.Column(db.String(42), nullable=True, index=True)
    blockchain_verified = db.Column(db.Boolean, default=False)
    disbursed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    maturity_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    payments = db.relationship(
        "LoanPayment", backref="loan", cascade="all, delete-orphan"
    )

    @staticmethod
    def generate_loan_number() -> str:
        import secrets

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        random_part = str(secrets.randbelow(90000) + 10000)
        return f"LN{timestamp}{random_part}"

    def calculate_remaining_balance(self) -> float:
        total_payments = sum(
            float(payment.amount)
            for payment in self.payments
            if payment.status == PaymentStatus.COMPLETED
        )
        return float(self.principal_amount) - total_payments - float(self.late_fees)

    def is_current(self) -> bool:
        return self.days_past_due == 0

    def is_delinquent(self) -> bool:
        return self.days_past_due >= 30

    def is_in_default(self) -> bool:
        return self.days_past_due >= 90

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "application_id": self.application_id,
            "loan_number": self.loan_number,
            "loan_type": self.loan_type.value,
            "principal_amount": float(self.principal_amount),
            "interest_rate": self.interest_rate,
            "term_months": self.term_months,
            "monthly_payment": float(self.monthly_payment),
            "status": self.status.value,
            "current_balance": float(self.current_balance),
            "total_paid": float(self.total_paid),
            "payments_made": self.payments_made,
            "payments_remaining": self.payments_remaining,
            "first_payment_date": self.first_payment_date.isoformat(),
            "last_payment_date": self.last_payment_date.isoformat(),
            "next_payment_date": (
                self.next_payment_date.isoformat() if self.next_payment_date else None
            ),
            "next_payment_amount": (
                float(self.next_payment_amount) if self.next_payment_amount else None
            ),
            "days_past_due": self.days_past_due,
            "late_fees": float(self.late_fees),
            "total_late_payments": self.total_late_payments,
            "smart_contract_address": self.smart_contract_address,
            "blockchain_verified": self.blockchain_verified,
            "disbursed_at": (
                self.disbursed_at.isoformat() if self.disbursed_at else None
            ),
            "maturity_date": self.maturity_date.isoformat(),
            "is_current": self.is_current(),
            "is_delinquent": self.is_delinquent(),
            "is_in_default": self.is_in_default(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class LoanPayment(db.Model):
    __tablename__ = "loan_payments"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    loan_id = db.Column(
        db.String(36), db.ForeignKey("loans.id"), nullable=False, index=True
    )
    payment_number = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    principal_amount = db.Column(db.Numeric(10, 2), nullable=False)
    interest_amount = db.Column(db.Numeric(10, 2), nullable=False)
    late_fee = db.Column(db.Numeric(10, 2), default=0)
    status = db.Column(
        db.Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False
    )
    payment_method = db.Column(db.Enum(PaymentMethod), nullable=True)
    due_date = db.Column(db.Date, nullable=False)
    scheduled_date = db.Column(db.Date, nullable=True)
    processed_date = db.Column(db.DateTime(timezone=True), nullable=True)
    transaction_id = db.Column(db.String(255), nullable=True, index=True)
    processor_response = db.Column(db.Text, nullable=True)
    failure_reason = db.Column(db.Text, nullable=True)
    blockchain_hash = db.Column(db.String(66), nullable=True, index=True)
    blockchain_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def is_late(self) -> bool:
        if self.status == PaymentStatus.COMPLETED:
            return False
        return datetime.now(timezone.utc).date() > self.due_date

    def days_late(self) -> int:
        if not self.is_late():
            return 0
        return (datetime.now(timezone.utc).date() - self.due_date).days

    def get_processor_response(self) -> Dict[str, Any]:
        if self.processor_response:
            try:
                return json.loads(self.processor_response)
            except json.JSONDecodeError:
                return {}
        return {}

    def set_processor_response(self, data: Any) -> None:
        self.processor_response = json.dumps(data) if data else None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "loan_id": self.loan_id,
            "payment_number": self.payment_number,
            "amount": float(self.amount),
            "principal_amount": float(self.principal_amount),
            "interest_amount": float(self.interest_amount),
            "late_fee": float(self.late_fee),
            "status": self.status.value,
            "payment_method": (
                self.payment_method.value if self.payment_method else None
            ),
            "due_date": self.due_date.isoformat(),
            "scheduled_date": (
                self.scheduled_date.isoformat() if self.scheduled_date else None
            ),
            "processed_date": (
                self.processed_date.isoformat() if self.processed_date else None
            ),
            "transaction_id": self.transaction_id,
            "processor_response": self.get_processor_response(),
            "failure_reason": self.failure_reason,
            "blockchain_hash": self.blockchain_hash,
            "blockchain_verified": self.blockchain_verified,
            "is_late": self.is_late(),
            "days_late": self.days_late(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class LoanApplicationSchema(Schema):
    loan_type = fields.Str(
        required=True, validate=validate.OneOf([e.value for e in LoanType])
    )
    requested_amount = fields.Decimal(
        required=True, places=2, validate=validate.Range(min=100)
    )
    requested_term_months = fields.Int(
        required=True, validate=validate.Range(min=1, max=360)
    )
    requested_rate = fields.Float(
        validate=validate.Range(min=0, max=100), allow_none=True
    )
    application_data = fields.Dict(load_default={})


class LoanApplicationResponseSchema(Schema):
    id = fields.Str(dump_only=True)
    application_number = fields.Str(dump_only=True)
    status = fields.Str(dump_only=True)
    approval_probability = fields.Float(dump_only=True)
    approved_amount = fields.Decimal(places=2, dump_only=True)
    approved_rate = fields.Float(dump_only=True)
    monthly_payment = fields.Decimal(places=2, dump_only=True)
    created_at = fields.DateTime(dump_only=True)


class LoanSchema(Schema):
    id = fields.Str(dump_only=True)
    loan_number = fields.Str(dump_only=True)
    loan_type = fields.Str(dump_only=True)
    principal_amount = fields.Decimal(places=2, dump_only=True)
    interest_rate = fields.Float(dump_only=True)
    term_months = fields.Int(dump_only=True)
    monthly_payment = fields.Decimal(places=2, dump_only=True)
    status = fields.Str(dump_only=True)
    current_balance = fields.Decimal(places=2, dump_only=True)
    next_payment_date = fields.Date(dump_only=True)
    next_payment_amount = fields.Decimal(places=2, dump_only=True)
    days_past_due = fields.Int(dump_only=True)
    is_current = fields.Bool(dump_only=True)
    created_at = fields.DateTime(dump_only=True)


class LoanPaymentSchema(Schema):
    amount = fields.Decimal(required=True, places=2, validate=validate.Range(min=0.01))
    payment_method = fields.Str(
        required=True, validate=validate.OneOf([e.value for e in PaymentMethod])
    )
    scheduled_date = fields.Date(allow_none=True)


class LoanPaymentResponseSchema(Schema):
    id = fields.Str(dump_only=True)
    payment_number = fields.Int(dump_only=True)
    amount = fields.Decimal(places=2, dump_only=True)
    status = fields.Str(dump_only=True)
    due_date = fields.Date(dump_only=True)
    processed_date = fields.DateTime(dump_only=True)
    transaction_id = fields.Str(dump_only=True)
    is_late = fields.Bool(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
