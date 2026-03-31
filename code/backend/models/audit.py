"""
Audit and compliance models for BlockScore Backend
"""

import enum
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from flask_sqlalchemy import SQLAlchemy
from marshmallow import Schema, fields, validate

db = SQLAlchemy()


class AuditEventType(enum.Enum):
    """Audit event type enumeration"""

    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_REGISTRATION = "user_registration"
    PASSWORD_CHANGE = "password_change"
    PROFILE_UPDATE = "profile_update"
    CREDIT_SCORE_CALCULATION = "credit_score_calculation"
    LOAN_APPLICATION = "loan_application"
    LOAN_APPROVAL = "loan_approval"
    LOAN_DISBURSEMENT = "loan_disbursement"
    PAYMENT_PROCESSED = "payment_processed"
    DATA_ACCESS = "data_access"
    DATA_EXPORT = "data_export"
    ADMIN_ACTION = "admin_action"
    SECURITY_ALERT = "security_alert"
    COMPLIANCE_CHECK = "compliance_check"
    BLOCKCHAIN_TRANSACTION = "blockchain_transaction"


class AuditSeverity(enum.Enum):
    """Audit severity enumeration"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComplianceType(enum.Enum):
    """Compliance type enumeration"""

    KYC = "kyc"
    AML = "aml"
    GDPR = "gdpr"
    SOX = "sox"
    PCI_DSS = "pci_dss"
    CCPA = "ccpa"
    FAIR_CREDIT = "fair_credit"
    EQUAL_CREDIT = "equal_credit"


class ComplianceStatus(enum.Enum):
    """Compliance status enumeration"""

    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PENDING_REVIEW = "pending_review"
    REQUIRES_ACTION = "requires_action"
    EXEMPTED = "exempted"


class AuditLog(db.Model):
    """Comprehensive audit log for all system activities"""

    __tablename__ = "audit_logs"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type = db.Column(db.Enum(AuditEventType), nullable=False, index=True)
    event_category = db.Column(db.String(50), nullable=False, index=True)
    event_description = db.Column(db.Text, nullable=False)
    severity = db.Column(
        db.Enum(AuditSeverity), default=AuditSeverity.LOW, nullable=False
    )
    user_id = db.Column(db.String(36), nullable=True, index=True)
    session_id = db.Column(db.String(36), nullable=True, index=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    request_method = db.Column(db.String(10), nullable=True)
    request_url = db.Column(db.Text, nullable=True)
    request_headers = db.Column(db.Text, nullable=True)
    request_body = db.Column(db.Text, nullable=True)
    response_status = db.Column(db.Integer, nullable=True)
    response_time_ms = db.Column(db.Integer, nullable=True)
    event_data = db.Column(db.Text, nullable=True)
    before_state = db.Column(db.Text, nullable=True)
    after_state = db.Column(db.Text, nullable=True)
    resource_type = db.Column(db.String(50), nullable=True)
    resource_id = db.Column(db.String(36), nullable=True, index=True)
    compliance_relevant = db.Column(db.Boolean, default=False)
    risk_score = db.Column(db.Float, nullable=True)
    blockchain_hash = db.Column(db.String(66), nullable=True, index=True)
    blockchain_verified = db.Column(db.Boolean, default=False)
    event_timestamp = db.Column(
        db.DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    created_at = db.Column(
        db.DateTime(timezone=True), default=datetime.now(timezone.utc)
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

    def get_before_state(self) -> Dict[str, Any]:
        """Get parsed before state"""
        if self.before_state:
            try:
                return json.loads(self.before_state)
            except json.JSONDecodeError:
                return {}
        return {}

    def set_before_state(self, data: Any) -> None:
        """Set before state as JSON"""
        self.before_state = json.dumps(data) if data else None

    def get_after_state(self) -> Dict[str, Any]:
        """Get parsed after state"""
        if self.after_state:
            try:
                return json.loads(self.after_state)
            except json.JSONDecodeError:
                return {}
        return {}

    def set_after_state(self, data: Any) -> None:
        """Set after state as JSON"""
        self.after_state = json.dumps(data) if data else None

    def get_request_headers(self) -> Dict[str, Any]:
        """Get parsed request headers"""
        if self.request_headers:
            try:
                return json.loads(self.request_headers)
            except json.JSONDecodeError:
                return {}
        return {}

    def set_request_headers(self, headers: Any) -> None:
        """Set request headers as JSON (excluding sensitive headers)"""
        if headers:
            safe_headers = {
                k: v
                for k, v in headers.items()
                if k.lower() not in ["authorization", "cookie", "x-api-key"]
            }
            self.request_headers = json.dumps(safe_headers)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "event_category": self.event_category,
            "event_description": self.event_description,
            "severity": self.severity.value,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "ip_address": self.ip_address,
            "request_method": self.request_method,
            "request_url": self.request_url,
            "response_status": self.response_status,
            "response_time_ms": self.response_time_ms,
            "event_data": self.get_event_data(),
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "compliance_relevant": self.compliance_relevant,
            "risk_score": self.risk_score,
            "blockchain_hash": self.blockchain_hash,
            "blockchain_verified": self.blockchain_verified,
            "event_timestamp": self.event_timestamp.isoformat(),
            "created_at": self.created_at.isoformat(),
        }


class ComplianceRecord(db.Model):
    """Compliance tracking and reporting"""

    __tablename__ = "compliance_records"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    compliance_type = db.Column(db.Enum(ComplianceType), nullable=False, index=True)
    regulation_name = db.Column(db.String(100), nullable=False)
    requirement_description = db.Column(db.Text, nullable=False)
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.String(36), nullable=False, index=True)
    status = db.Column(db.Enum(ComplianceStatus), nullable=False)
    compliance_score = db.Column(db.Float, nullable=True)
    assessment_data = db.Column(db.Text, nullable=True)
    violations = db.Column(db.Text, nullable=True)
    remediation_actions = db.Column(db.Text, nullable=True)
    assessed_by = db.Column(db.String(36), nullable=True)
    assessment_method = db.Column(db.String(50), nullable=True)
    valid_from = db.Column(
        db.DateTime(timezone=True), default=datetime.now(timezone.utc)
    )
    valid_until = db.Column(db.DateTime(timezone=True), nullable=True)
    next_review_date = db.Column(db.DateTime(timezone=True), nullable=True)
    supporting_documents = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    assessed_at = db.Column(
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

    def get_assessment_data(self) -> Dict[str, Any]:
        """Get parsed assessment data"""
        if self.assessment_data:
            try:
                return json.loads(self.assessment_data)
            except json.JSONDecodeError:
                return {}
        return {}

    def set_assessment_data(self, data: Any) -> None:
        """Set assessment data as JSON"""
        self.assessment_data = json.dumps(data) if data else None

    def get_violations(self) -> List[Any]:
        """Get parsed violations"""
        if self.violations:
            try:
                return json.loads(self.violations)
            except json.JSONDecodeError:
                return []
        return []

    def set_violations(self, violations: Any) -> None:
        """Set violations as JSON"""
        self.violations = json.dumps(violations) if violations else None

    def get_remediation_actions(self) -> List[Any]:
        """Get parsed remediation actions"""
        if self.remediation_actions:
            try:
                return json.loads(self.remediation_actions)
            except json.JSONDecodeError:
                return []
        return []

    def set_remediation_actions(self, actions: Any) -> None:
        """Set remediation actions as JSON"""
        self.remediation_actions = json.dumps(actions) if actions else None

    def is_valid(self) -> bool:
        """Check if compliance record is still valid"""
        now = datetime.now(timezone.utc)
        if self.valid_until:
            return now < self.valid_until
        return True

    def needs_review(self) -> bool:
        """Check if compliance record needs review"""
        if self.next_review_date:
            return datetime.now(timezone.utc) >= self.next_review_date
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "compliance_type": self.compliance_type.value,
            "regulation_name": self.regulation_name,
            "requirement_description": self.requirement_description,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "status": self.status.value,
            "compliance_score": self.compliance_score,
            "assessment_data": self.get_assessment_data(),
            "violations": self.get_violations(),
            "remediation_actions": self.get_remediation_actions(),
            "assessed_by": self.assessed_by,
            "assessment_method": self.assessment_method,
            "valid_from": self.valid_from.isoformat(),
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "next_review_date": (
                self.next_review_date.isoformat() if self.next_review_date else None
            ),
            "notes": self.notes,
            "is_valid": self.is_valid(),
            "needs_review": self.needs_review(),
            "assessed_at": self.assessed_at.isoformat(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class AuditLogSchema(Schema):
    """Schema for audit log serialization"""

    id = fields.Str(dump_only=True)
    event_type = fields.Str(dump_only=True)
    event_category = fields.Str(dump_only=True)
    event_description = fields.Str(dump_only=True)
    severity = fields.Str(dump_only=True)
    user_id = fields.Str(dump_only=True)
    ip_address = fields.Str(dump_only=True)
    request_method = fields.Str(dump_only=True)
    request_url = fields.Str(dump_only=True)
    response_status = fields.Int(dump_only=True)
    response_time_ms = fields.Int(dump_only=True)
    event_data = fields.Dict(dump_only=True)
    resource_type = fields.Str(dump_only=True)
    resource_id = fields.Str(dump_only=True)
    compliance_relevant = fields.Bool(dump_only=True)
    risk_score = fields.Float(dump_only=True)
    blockchain_hash = fields.Str(dump_only=True)
    blockchain_verified = fields.Bool(dump_only=True)
    event_timestamp = fields.DateTime(dump_only=True)
    created_at = fields.DateTime(dump_only=True)


class ComplianceRecordSchema(Schema):
    """Schema for compliance record serialization"""

    id = fields.Str(dump_only=True)
    compliance_type = fields.Str(dump_only=True)
    regulation_name = fields.Str(dump_only=True)
    requirement_description = fields.Str(dump_only=True)
    entity_type = fields.Str(dump_only=True)
    entity_id = fields.Str(dump_only=True)
    status = fields.Str(dump_only=True)
    compliance_score = fields.Float(dump_only=True)
    assessment_data = fields.Dict(dump_only=True)
    violations = fields.List(fields.Dict(), dump_only=True)
    remediation_actions = fields.List(fields.Dict(), dump_only=True)
    assessed_by = fields.Str(dump_only=True)
    assessment_method = fields.Str(dump_only=True)
    valid_from = fields.DateTime(dump_only=True)
    valid_until = fields.DateTime(dump_only=True)
    next_review_date = fields.DateTime(dump_only=True)
    notes = fields.Str(dump_only=True)
    is_valid = fields.Bool(dump_only=True)
    needs_review = fields.Bool(dump_only=True)
    assessed_at = fields.DateTime(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class AuditLogQuerySchema(Schema):
    """Schema for audit log query parameters"""

    event_type = fields.Str(
        validate=validate.OneOf([e.value for e in AuditEventType]), allow_none=True
    )
    severity = fields.Str(
        validate=validate.OneOf([e.value for e in AuditSeverity]), allow_none=True
    )
    user_id = fields.Str(allow_none=True)
    start_date = fields.DateTime(allow_none=True)
    end_date = fields.DateTime(allow_none=True)
    page = fields.Int(validate=validate.Range(min=1), missing=1)
    per_page = fields.Int(validate=validate.Range(min=1, max=100), missing=20)


class ComplianceReportSchema(Schema):
    """Schema for compliance reporting"""

    compliance_type = fields.Str(
        validate=validate.OneOf([e.value for e in ComplianceType]), allow_none=True
    )
    status = fields.Str(
        validate=validate.OneOf([e.value for e in ComplianceStatus]), allow_none=True
    )
    entity_type = fields.Str(allow_none=True)
    start_date = fields.DateTime(allow_none=True)
    end_date = fields.DateTime(allow_none=True)
    include_violations = fields.Bool(missing=True)
    include_remediation = fields.Bool(missing=True)
