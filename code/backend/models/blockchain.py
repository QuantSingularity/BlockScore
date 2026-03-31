"""
Blockchain integration models for BlockScore Backend
"""

import enum
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from flask_sqlalchemy import SQLAlchemy
from marshmallow import Schema, fields, validate

db = SQLAlchemy()


class TransactionStatus(enum.Enum):
    """Blockchain transaction status enumeration"""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TransactionType(enum.Enum):
    """Blockchain transaction type enumeration"""

    CREDIT_SCORE_UPDATE = "credit_score_update"
    LOAN_APPLICATION = "loan_application"
    LOAN_APPROVAL = "loan_approval"
    LOAN_DISBURSEMENT = "loan_disbursement"
    PAYMENT_RECORD = "payment_record"
    IDENTITY_VERIFICATION = "identity_verification"
    SMART_CONTRACT_DEPLOYMENT = "smart_contract_deployment"
    SMART_CONTRACT_INTERACTION = "smart_contract_interaction"


class ContractType(enum.Enum):
    """Smart contract type enumeration"""

    CREDIT_SCORE = "credit_score"
    LOAN_AGREEMENT = "loan_agreement"
    IDENTITY_REGISTRY = "identity_registry"
    PAYMENT_PROCESSOR = "payment_processor"
    GOVERNANCE = "governance"


class ContractStatus(enum.Enum):
    """Smart contract status enumeration"""

    DEPLOYED = "deployed"
    ACTIVE = "active"
    PAUSED = "paused"
    DEPRECATED = "deprecated"
    DESTROYED = "destroyed"


class BlockchainTransaction(db.Model):
    """Blockchain transaction tracking"""

    __tablename__ = "blockchain_transactions"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    transaction_hash = db.Column(db.String(66), unique=True, nullable=False, index=True)
    block_number = db.Column(db.BigInteger, nullable=True, index=True)
    block_hash = db.Column(db.String(66), nullable=True)
    transaction_index = db.Column(db.Integer, nullable=True)
    transaction_type = db.Column(db.Enum(TransactionType), nullable=False)
    status = db.Column(db.Enum(TransactionStatus), default=TransactionStatus.PENDING)
    from_address = db.Column(db.String(42), nullable=False, index=True)
    to_address = db.Column(db.String(42), nullable=True, index=True)
    contract_address = db.Column(db.String(42), nullable=True, index=True)
    function_name = db.Column(db.String(100), nullable=True)
    input_data = db.Column(db.Text, nullable=True)
    output_data = db.Column(db.Text, nullable=True)
    gas_limit = db.Column(db.BigInteger, nullable=True)
    gas_used = db.Column(db.BigInteger, nullable=True)
    gas_price = db.Column(db.BigInteger, nullable=True)
    transaction_fee = db.Column(db.Decimal(20, 8), nullable=True)
    value = db.Column(db.Decimal(20, 8), nullable=True)
    token_transfers = db.Column(db.Text, nullable=True)
    network_id = db.Column(db.Integer, nullable=False, default=1)
    network_name = db.Column(db.String(50), nullable=False, default="ethereum")
    user_id = db.Column(db.String(36), nullable=True, index=True)
    related_entity_type = db.Column(db.String(50), nullable=True)
    related_entity_id = db.Column(db.String(36), nullable=True, index=True)
    nonce = db.Column(db.BigInteger, nullable=True)
    confirmation_count = db.Column(db.Integer, default=0)
    required_confirmations = db.Column(db.Integer, default=12)
    error_message = db.Column(db.Text, nullable=True)
    revert_reason = db.Column(db.Text, nullable=True)
    submitted_at = db.Column(
        db.DateTime(timezone=True), default=datetime.now(timezone.utc)
    )
    confirmed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True), default=datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )

    def get_input_data(self) -> Dict[str, Any]:
        """Get parsed input data"""
        if self.input_data:
            try:
                return json.loads(self.input_data)
            except json.JSONDecodeError:
                return {}
        return {}

    def set_input_data(self, data: Any) -> None:
        """Set input data as JSON"""
        self.input_data = json.dumps(data) if data else None

    def get_output_data(self) -> Dict[str, Any]:
        """Get parsed output data"""
        if self.output_data:
            try:
                return json.loads(self.output_data)
            except json.JSONDecodeError:
                return {}
        return {}

    def set_output_data(self, data: Any) -> None:
        """Set output data as JSON"""
        self.output_data = json.dumps(data) if data else None

    def get_token_transfers(self) -> List[Any]:
        """Get parsed token transfers"""
        if self.token_transfers:
            try:
                return json.loads(self.token_transfers)
            except json.JSONDecodeError:
                return []
        return []

    def set_token_transfers(self, transfers: Any) -> None:
        """Set token transfers as JSON"""
        self.token_transfers = json.dumps(transfers) if transfers else None

    def is_confirmed(self) -> bool:
        """Check if transaction is confirmed"""
        return (
            self.status == TransactionStatus.CONFIRMED
            and self.confirmation_count >= self.required_confirmations
        )

    def calculate_transaction_fee_usd(self, eth_price_usd: Any = None) -> float:
        """Calculate transaction fee in USD"""
        if self.transaction_fee and eth_price_usd:
            return float(self.transaction_fee) * eth_price_usd
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "transaction_hash": self.transaction_hash,
            "block_number": self.block_number,
            "block_hash": self.block_hash,
            "transaction_index": self.transaction_index,
            "transaction_type": self.transaction_type.value,
            "status": self.status.value,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "contract_address": self.contract_address,
            "function_name": self.function_name,
            "input_data": self.get_input_data(),
            "output_data": self.get_output_data(),
            "gas_limit": self.gas_limit,
            "gas_used": self.gas_used,
            "gas_price": self.gas_price,
            "transaction_fee": (
                float(self.transaction_fee) if self.transaction_fee else None
            ),
            "value": float(self.value) if self.value else None,
            "token_transfers": self.get_token_transfers(),
            "network_id": self.network_id,
            "network_name": self.network_name,
            "user_id": self.user_id,
            "related_entity_type": self.related_entity_type,
            "related_entity_id": self.related_entity_id,
            "nonce": self.nonce,
            "confirmation_count": self.confirmation_count,
            "required_confirmations": self.required_confirmations,
            "is_confirmed": self.is_confirmed(),
            "error_message": self.error_message,
            "revert_reason": self.revert_reason,
            "submitted_at": self.submitted_at.isoformat(),
            "confirmed_at": (
                self.confirmed_at.isoformat() if self.confirmed_at else None
            ),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class SmartContract(db.Model):
    """Smart contract registry and management"""

    __tablename__ = "smart_contracts"
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    contract_address = db.Column(db.String(42), unique=True, nullable=False, index=True)
    contract_name = db.Column(db.String(100), nullable=False)
    contract_type = db.Column(db.Enum(ContractType), nullable=False)
    contract_version = db.Column(db.String(20), nullable=False, default="1.0.0")
    status = db.Column(db.Enum(ContractStatus), default=ContractStatus.DEPLOYED)
    is_verified = db.Column(db.Boolean, default=False)
    is_proxy = db.Column(db.Boolean, default=False)
    implementation_address = db.Column(db.String(42), nullable=True)
    bytecode = db.Column(db.Text, nullable=True)
    source_code = db.Column(db.Text, nullable=True)
    abi = db.Column(db.Text, nullable=False)
    constructor_args = db.Column(db.Text, nullable=True)
    deployment_transaction_hash = db.Column(db.String(66), nullable=False, index=True)
    deployment_block_number = db.Column(db.BigInteger, nullable=True)
    deployer_address = db.Column(db.String(42), nullable=False)
    network_id = db.Column(db.Integer, nullable=False, default=1)
    network_name = db.Column(db.String(50), nullable=False, default="ethereum")
    description = db.Column(db.Text, nullable=True)
    documentation_url = db.Column(db.String(255), nullable=True)
    source_code_url = db.Column(db.String(255), nullable=True)
    security_audit_status = db.Column(db.String(50), nullable=True)
    audit_reports = db.Column(db.Text, nullable=True)
    known_vulnerabilities = db.Column(db.Text, nullable=True)
    total_transactions = db.Column(db.BigInteger, default=0)
    last_interaction = db.Column(db.DateTime(timezone=True), nullable=True)
    deployed_at = db.Column(db.DateTime(timezone=True), nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True), default=datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )

    def get_abi(self) -> List[Any]:
        """Get parsed ABI"""
        if self.abi:
            try:
                return json.loads(self.abi)
            except json.JSONDecodeError:
                return []
        return []

    def set_abi(self, abi: Any) -> None:
        """Set ABI as JSON"""
        self.abi = json.dumps(abi) if abi else None

    def get_constructor_args(self) -> List[Any]:
        """Get parsed constructor arguments"""
        if self.constructor_args:
            try:
                return json.loads(self.constructor_args)
            except json.JSONDecodeError:
                return []
        return []

    def set_constructor_args(self, args: Any) -> None:
        """Set constructor arguments as JSON"""
        self.constructor_args = json.dumps(args) if args else None

    def get_audit_reports(self) -> List[Any]:
        """Get parsed audit reports"""
        if self.audit_reports:
            try:
                return json.loads(self.audit_reports)
            except json.JSONDecodeError:
                return []
        return []

    def set_audit_reports(self, reports: Any) -> None:
        """Set audit reports as JSON"""
        self.audit_reports = json.dumps(reports) if reports else None

    def get_known_vulnerabilities(self) -> List[Any]:
        """Get parsed known vulnerabilities"""
        if self.known_vulnerabilities:
            try:
                return json.loads(self.known_vulnerabilities)
            except json.JSONDecodeError:
                return []
        return []

    def set_known_vulnerabilities(self, vulnerabilities: Any) -> None:
        """Set known vulnerabilities as JSON"""
        self.known_vulnerabilities = (
            json.dumps(vulnerabilities) if vulnerabilities else None
        )

    def is_active(self) -> bool:
        """Check if contract is active"""
        return self.status == ContractStatus.ACTIVE

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "contract_address": self.contract_address,
            "contract_name": self.contract_name,
            "contract_type": self.contract_type.value,
            "contract_version": self.contract_version,
            "status": self.status.value,
            "is_verified": self.is_verified,
            "is_proxy": self.is_proxy,
            "implementation_address": self.implementation_address,
            "abi": self.get_abi(),
            "constructor_args": self.get_constructor_args(),
            "deployment_transaction_hash": self.deployment_transaction_hash,
            "deployment_block_number": self.deployment_block_number,
            "deployer_address": self.deployer_address,
            "network_id": self.network_id,
            "network_name": self.network_name,
            "description": self.description,
            "documentation_url": self.documentation_url,
            "source_code_url": self.source_code_url,
            "security_audit_status": self.security_audit_status,
            "audit_reports": self.get_audit_reports(),
            "known_vulnerabilities": self.get_known_vulnerabilities(),
            "total_transactions": self.total_transactions,
            "last_interaction": (
                self.last_interaction.isoformat() if self.last_interaction else None
            ),
            "is_active": self.is_active(),
            "deployed_at": self.deployed_at.isoformat(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class BlockchainTransactionSchema(Schema):
    """Schema for blockchain transaction serialization"""

    id = fields.Str(dump_only=True)
    transaction_hash = fields.Str(dump_only=True)
    block_number = fields.Int(dump_only=True)
    block_hash = fields.Str(dump_only=True)
    transaction_index = fields.Int(dump_only=True)
    transaction_type = fields.Str(dump_only=True)
    status = fields.Str(dump_only=True)
    from_address = fields.Str(dump_only=True)
    to_address = fields.Str(dump_only=True)
    contract_address = fields.Str(dump_only=True)
    function_name = fields.Str(dump_only=True)
    input_data = fields.Dict(dump_only=True)
    output_data = fields.Dict(dump_only=True)
    gas_limit = fields.Int(dump_only=True)
    gas_used = fields.Int(dump_only=True)
    gas_price = fields.Int(dump_only=True)
    transaction_fee = fields.Decimal(places=8, dump_only=True)
    value = fields.Decimal(places=8, dump_only=True)
    token_transfers = fields.List(fields.Dict(), dump_only=True)
    network_id = fields.Int(dump_only=True)
    network_name = fields.Str(dump_only=True)
    confirmation_count = fields.Int(dump_only=True)
    required_confirmations = fields.Int(dump_only=True)
    is_confirmed = fields.Bool(dump_only=True)
    error_message = fields.Str(dump_only=True)
    submitted_at = fields.DateTime(dump_only=True)
    confirmed_at = fields.DateTime(dump_only=True)
    created_at = fields.DateTime(dump_only=True)


class SmartContractSchema(Schema):
    """Schema for smart contract serialization"""

    id = fields.Str(dump_only=True)
    contract_address = fields.Str(dump_only=True)
    contract_name = fields.Str(dump_only=True)
    contract_type = fields.Str(dump_only=True)
    contract_version = fields.Str(dump_only=True)
    status = fields.Str(dump_only=True)
    is_verified = fields.Bool(dump_only=True)
    is_proxy = fields.Bool(dump_only=True)
    implementation_address = fields.Str(dump_only=True)
    abi = fields.List(fields.Dict(), dump_only=True)
    deployment_transaction_hash = fields.Str(dump_only=True)
    deployment_block_number = fields.Int(dump_only=True)
    deployer_address = fields.Str(dump_only=True)
    network_id = fields.Int(dump_only=True)
    network_name = fields.Str(dump_only=True)
    description = fields.Str(dump_only=True)
    documentation_url = fields.Str(dump_only=True)
    security_audit_status = fields.Str(dump_only=True)
    audit_reports = fields.List(fields.Dict(), dump_only=True)
    total_transactions = fields.Int(dump_only=True)
    last_interaction = fields.DateTime(dump_only=True)
    is_active = fields.Bool(dump_only=True)
    deployed_at = fields.DateTime(dump_only=True)
    created_at = fields.DateTime(dump_only=True)


class TransactionSubmissionSchema(Schema):
    """Schema for transaction submission"""

    transaction_type = fields.Str(
        required=True, validate=validate.OneOf([e.value for e in TransactionType])
    )
    to_address = fields.Str(validate=validate.Length(equal=42), allow_none=True)
    contract_address = fields.Str(validate=validate.Length(equal=42), allow_none=True)
    function_name = fields.Str(allow_none=True)
    function_params = fields.Dict(missing={})
    value = fields.Decimal(places=8, missing=0)
    gas_limit = fields.Int(validate=validate.Range(min=21000), allow_none=True)
    gas_price = fields.Int(validate=validate.Range(min=1), allow_none=True)


class ContractDeploymentSchema(Schema):
    """Schema for smart contract deployment"""

    contract_name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    contract_type = fields.Str(
        required=True, validate=validate.OneOf([e.value for e in ContractType])
    )
    contract_version = fields.Str(missing="1.0.0")
    bytecode = fields.Str(required=True)
    abi = fields.List(fields.Dict(), required=True)
    constructor_args = fields.List(fields.Raw(), missing=[])
    description = fields.Str(allow_none=True)
    documentation_url = fields.Str(allow_none=True)
    source_code_url = fields.Str(allow_none=True)
