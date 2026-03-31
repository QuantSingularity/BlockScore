"""
Database models package for BlockScore Backend
"""

from extensions import db, ma

from .audit import AuditLog, ComplianceRecord
from .blockchain import BlockchainTransaction, SmartContract
from .credit import CreditFactor, CreditHistory, CreditScore
from .loan import Loan, LoanApplication, LoanPayment
from .user import User, UserProfile, UserSession

__all__ = [
    "db",
    "ma",
    "User",
    "UserProfile",
    "UserSession",
    "CreditScore",
    "CreditHistory",
    "CreditFactor",
    "Loan",
    "LoanApplication",
    "LoanPayment",
    "AuditLog",
    "ComplianceRecord",
    "BlockchainTransaction",
    "SmartContract",
]
