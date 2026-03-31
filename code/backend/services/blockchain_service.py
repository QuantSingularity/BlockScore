"""
Blockchain Service for BlockScore Backend
Smart contract integration and blockchain transaction management
"""

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List

from extensions import db
from models.blockchain import (
    BlockchainTransaction,
    ContractStatus,
    ContractType,
    SmartContract,
    TransactionStatus,
    TransactionType,
)
from web3 import Web3
from web3.exceptions import TransactionNotFound


class BlockchainService:
    """Comprehensive blockchain service for smart contract integration"""

    def __init__(self, config: Any) -> None:
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.web3 = None
        self.is_connected_flag = False
        self._initialize_web3()
        self.contract_addresses = {
            ContractType.CREDIT_SCORE: config.get("CREDIT_SCORE_CONTRACT_ADDRESS"),
            ContractType.LOAN_AGREEMENT: config.get("LOAN_AGREEMENT_CONTRACT_ADDRESS"),
            ContractType.IDENTITY_REGISTRY: config.get(
                "IDENTITY_REGISTRY_CONTRACT_ADDRESS"
            ),
            ContractType.PAYMENT_PROCESSOR: config.get(
                "PAYMENT_PROCESSOR_CONTRACT_ADDRESS"
            ),
        }
        self.default_gas_limit = 200000
        self.default_gas_price = Web3.to_wei(20, "gwei")
        self.confirmation_blocks = 12
        self.transaction_timeout = 300
        self.network_id = config.get("BLOCKCHAIN_NETWORK_ID", 1)
        self.network_name = config.get("BLOCKCHAIN_NETWORK_NAME", "ethereum")
        self.contract_abis = self._load_contract_abis()

    def is_connected(self) -> bool:
        """Check if blockchain connection is active"""
        if not self.web3:
            return False
        try:
            self.web3.eth.block_number
            self.is_connected_flag = True
            return True
        except Exception as e:
            self.logger.warning(f"Blockchain connection check failed: {e}")
            self.is_connected_flag = False
            return False

    def submit_credit_score_update(
        self, user_id: str, credit_score_id: str, score: int, wallet_address: str
    ) -> Dict[str, Any]:
        """Submit credit score update to blockchain"""
        try:
            if not self.is_connected():
                raise Exception("Blockchain not connected")
            contract_address = self.contract_addresses.get(ContractType.CREDIT_SCORE)
            if not contract_address:
                raise Exception("Credit score contract not configured")
            contract = self._get_contract_instance(ContractType.CREDIT_SCORE)
            if not contract:
                raise Exception("Failed to get contract instance")
            function_data = {
                "user_address": wallet_address,
                "score": score,
                "timestamp": int(datetime.now(timezone.utc).timestamp()),
                "score_id": credit_score_id,
            }
            transaction = contract.functions.updateCreditScore(
                wallet_address, score, function_data["timestamp"], credit_score_id
            ).build_transaction(
                {
                    "from": self.config.get("BLOCKCHAIN_FROM_ADDRESS"),
                    "gas": self.default_gas_limit,
                    "gasPrice": self.default_gas_price,
                    "nonce": self.web3.eth.get_transaction_count(
                        self.config.get("BLOCKCHAIN_FROM_ADDRESS")
                    ),
                }
            )
            signed_txn = self.web3.eth.account.sign_transaction(
                transaction, private_key=self.config.get("BLOCKCHAIN_PRIVATE_KEY")
            )
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.raw_transaction)
            tx_hash_hex = tx_hash.hex()
            blockchain_tx = self._create_blockchain_transaction(
                transaction_hash=tx_hash_hex,
                transaction_type=TransactionType.CREDIT_SCORE_UPDATE,
                from_address=self.config.get("BLOCKCHAIN_FROM_ADDRESS"),
                to_address=contract_address,
                contract_address=contract_address,
                function_name="updateCreditScore",
                input_data=function_data,
                user_id=user_id,
                related_entity_type="credit_score",
                related_entity_id=credit_score_id,
                gas_limit=self.default_gas_limit,
                gas_price=self.default_gas_price,
            )
            return {
                "transaction_id": blockchain_tx.id,
                "transaction_hash": tx_hash_hex,
                "status": "submitted",
                "estimated_confirmation_time": self.confirmation_blocks * 15,
            }
        except Exception as e:
            self.logger.error(f"Credit score update submission failed: {e}")
            raise e

    def submit_loan_agreement(
        self,
        loan_id: str,
        borrower_address: str,
        loan_amount: Decimal,
        interest_rate: float,
        term_months: int,
    ) -> Dict[str, Any]:
        """Submit loan agreement to blockchain"""
        try:
            if not self.is_connected():
                raise Exception("Blockchain not connected")
            contract = self._get_contract_instance(ContractType.LOAN_AGREEMENT)
            if not contract:
                raise Exception("Loan agreement contract not available")
            loan_amount_wei = int(loan_amount * 10**18)
            function_data = {
                "loan_id": loan_id,
                "borrower": borrower_address,
                "amount": str(loan_amount),
                "interest_rate": interest_rate,
                "term_months": term_months,
                "created_at": int(datetime.now(timezone.utc).timestamp()),
            }
            transaction = contract.functions.createLoanAgreement(
                loan_id,
                borrower_address,
                loan_amount_wei,
                int(interest_rate * 100),
                term_months,
            ).build_transaction(
                {
                    "from": self.config.get("BLOCKCHAIN_FROM_ADDRESS"),
                    "gas": self.default_gas_limit,
                    "gasPrice": self.default_gas_price,
                    "nonce": self.web3.eth.get_transaction_count(
                        self.config.get("BLOCKCHAIN_FROM_ADDRESS")
                    ),
                }
            )
            signed_txn = self.web3.eth.account.sign_transaction(
                transaction, private_key=self.config.get("BLOCKCHAIN_PRIVATE_KEY")
            )
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.raw_transaction)
            tx_hash_hex = tx_hash.hex()
            blockchain_tx = self._create_blockchain_transaction(
                transaction_hash=tx_hash_hex,
                transaction_type=TransactionType.LOAN_APPLICATION,
                from_address=self.config.get("BLOCKCHAIN_FROM_ADDRESS"),
                to_address=self.contract_addresses.get(ContractType.LOAN_AGREEMENT),
                contract_address=self.contract_addresses.get(
                    ContractType.LOAN_AGREEMENT
                ),
                function_name="createLoanAgreement",
                input_data=function_data,
                related_entity_type="loan",
                related_entity_id=loan_id,
                gas_limit=self.default_gas_limit,
                gas_price=self.default_gas_price,
                value=0,
            )
            return {
                "transaction_id": blockchain_tx.id,
                "transaction_hash": tx_hash_hex,
                "status": "submitted",
            }
        except Exception as e:
            self.logger.error(f"Loan agreement submission failed: {e}")
            raise e

    def record_payment(
        self, loan_id: str, payment_amount: Decimal, borrower_address: str
    ) -> Dict[str, Any]:
        """Record loan payment on blockchain"""
        try:
            if not self.is_connected():
                raise Exception("Blockchain not connected")
            contract = self._get_contract_instance(ContractType.PAYMENT_PROCESSOR)
            if not contract:
                raise Exception("Payment processor contract not available")
            payment_amount_wei = int(payment_amount * 10**18)
            function_data = {
                "loan_id": loan_id,
                "borrower": borrower_address,
                "amount": str(payment_amount),
                "payment_date": int(datetime.now(timezone.utc).timestamp()),
            }
            transaction = contract.functions.recordPayment(
                loan_id, borrower_address, payment_amount_wei
            ).build_transaction(
                {
                    "from": self.config.get("BLOCKCHAIN_FROM_ADDRESS"),
                    "gas": self.default_gas_limit,
                    "gasPrice": self.default_gas_price,
                    "nonce": self.web3.eth.get_transaction_count(
                        self.config.get("BLOCKCHAIN_FROM_ADDRESS")
                    ),
                }
            )
            signed_txn = self.web3.eth.account.sign_transaction(
                transaction, private_key=self.config.get("BLOCKCHAIN_PRIVATE_KEY")
            )
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.raw_transaction)
            tx_hash_hex = tx_hash.hex()
            blockchain_tx = self._create_blockchain_transaction(
                transaction_hash=tx_hash_hex,
                transaction_type=TransactionType.PAYMENT_RECORD,
                from_address=self.config.get("BLOCKCHAIN_FROM_ADDRESS"),
                to_address=self.contract_addresses.get(ContractType.PAYMENT_PROCESSOR),
                contract_address=self.contract_addresses.get(
                    ContractType.PAYMENT_PROCESSOR
                ),
                function_name="recordPayment",
                input_data=function_data,
                related_entity_type="loan",
                related_entity_id=loan_id,
                gas_limit=self.default_gas_limit,
                gas_price=self.default_gas_price,
                value=0,
            )
            return {
                "transaction_id": blockchain_tx.id,
                "transaction_hash": tx_hash_hex,
                "status": "submitted",
            }
        except Exception as e:
            self.logger.error(f"Payment recording failed: {e}")
            raise e

    def get_transaction_status(self, transaction_hash: str) -> Dict[str, Any]:
        """Get blockchain transaction status"""
        try:
            if not self.is_connected():
                return {"status": "unknown", "error": "Blockchain not connected"}
            try:
                receipt = self.web3.eth.get_transaction_receipt(transaction_hash)
                transaction = self.web3.eth.get_transaction(transaction_hash)
                current_block = self.web3.eth.block_number
                confirmations = (
                    current_block - receipt.blockNumber if receipt.blockNumber else 0
                )
                if receipt.status == 1:
                    status = (
                        "confirmed"
                        if confirmations >= self.confirmation_blocks
                        else "pending"
                    )
                else:
                    status = "failed"
                return {
                    "status": status,
                    "block_number": receipt.blockNumber,
                    "block_hash": (
                        receipt.blockHash.hex() if receipt.blockHash else None
                    ),
                    "transaction_index": receipt.transactionIndex,
                    "gas_used": receipt.gasUsed,
                    "gas_price": transaction.gasPrice,
                    "confirmations": confirmations,
                    "required_confirmations": self.confirmation_blocks,
                }
            except TransactionNotFound:
                return {"status": "not_found", "error": "Transaction not found"}
            except Exception as e:
                return {"status": "error", "error": str(e)}
        except Exception as e:
            self.logger.error(f"Transaction status check failed: {e}")
            return {"status": "error", "error": str(e)}

    def update_transaction_status(self, transaction_id: str) -> bool:
        """Update blockchain transaction status in database"""
        try:
            blockchain_tx = db.session.get(BlockchainTransaction, transaction_id)
            if not blockchain_tx:
                return False
            status_info = self.get_transaction_status(blockchain_tx.transaction_hash)
            if status_info["status"] == "confirmed":
                blockchain_tx.status = TransactionStatus.CONFIRMED
                blockchain_tx.block_number = status_info.get("block_number")
                blockchain_tx.block_hash = status_info.get("block_hash")
                blockchain_tx.transaction_index = status_info.get("transaction_index")
                blockchain_tx.gas_used = status_info.get("gas_used")
                blockchain_tx.confirmation_count = status_info.get("confirmations", 0)
                blockchain_tx.confirmed_at = datetime.now(timezone.utc)
            elif status_info["status"] == "failed":
                blockchain_tx.status = TransactionStatus.FAILED
                blockchain_tx.error_message = status_info.get(
                    "error", "Transaction failed"
                )
            elif status_info["status"] == "pending":
                blockchain_tx.confirmation_count = status_info.get("confirmations", 0)
            if status_info.get("gas_used") and status_info.get("gas_price"):
                fee_wei = status_info["gas_used"] * status_info["gas_price"]
                blockchain_tx.transaction_fee = Decimal(fee_wei) / Decimal(10**18)
            self.db.session.commit()
            return True
        except Exception as e:
            self.db.session.rollback()
            self.logger.error(f"Transaction status update failed: {e}")
            return False

    def get_wallet_transaction_history(
        self, wallet_address: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get transaction history for wallet address"""
        try:
            transactions = (
                BlockchainTransaction.query.filter(
                    (BlockchainTransaction.from_address == wallet_address)
                    | (BlockchainTransaction.to_address == wallet_address)
                )
                .order_by(BlockchainTransaction.submitted_at.desc())
                .limit(limit)
                .all()
            )
            if not transactions and self.is_connected():
                transactions = self._fetch_wallet_history_from_blockchain(
                    wallet_address, limit
                )
            return [tx.to_dict() for tx in transactions]
        except Exception as e:
            self.logger.error(f"Wallet history retrieval failed: {e}")
            return []

    def deploy_smart_contract(
        self,
        contract_type: ContractType,
        contract_name: str,
        bytecode: str,
        abi: List[Dict],
        constructor_args: List = None,
    ) -> Dict[str, Any]:
        """Deploy smart contract to blockchain"""
        try:
            if not self.is_connected():
                raise Exception("Blockchain not connected")
            contract = self.web3.eth.contract(abi=abi, bytecode=bytecode)
            constructor_args = constructor_args or []
            transaction = contract.constructor(*constructor_args).build_transaction(
                {
                    "from": self.config.get("BLOCKCHAIN_FROM_ADDRESS"),
                    "gas": self.default_gas_limit * 3,
                    "gasPrice": self.default_gas_price,
                    "nonce": self.web3.eth.get_transaction_count(
                        self.config.get("BLOCKCHAIN_FROM_ADDRESS")
                    ),
                }
            )
            signed_txn = self.web3.eth.account.sign_transaction(
                transaction, private_key=self.config.get("BLOCKCHAIN_PRIVATE_KEY")
            )
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.raw_transaction)
            tx_hash_hex = tx_hash.hex()
            receipt = self.web3.eth.wait_for_transaction_receipt(
                tx_hash, timeout=self.transaction_timeout
            )
            if receipt.status != 1:
                raise Exception("Contract deployment failed")
            contract_address = receipt.contractAddress
            smart_contract = SmartContract(
                id=str(uuid.uuid4()),
                contract_address=contract_address,
                contract_name=contract_name,
                contract_type=contract_type,
                contract_version="1.0.0",
                status=ContractStatus.DEPLOYED,
                deployment_transaction_hash=tx_hash_hex,
                deployment_block_number=receipt.blockNumber,
                deployer_address=self.config.get("BLOCKCHAIN_FROM_ADDRESS"),
                network_id=self.network_id,
                network_name=self.network_name,
                deployed_at=datetime.now(timezone.utc),
            )
            smart_contract.set_abi(abi)
            smart_contract.set_constructor_args(constructor_args)
            self.db.session.add(smart_contract)
            self.db.session.commit()
            return {
                "contract_id": smart_contract.id,
                "contract_address": contract_address,
                "transaction_hash": tx_hash_hex,
                "status": "deployed",
            }
        except Exception as e:
            self.db.session.rollback()
            self.logger.error(f"Contract deployment failed: {e}")
            raise e

    def get_contract_info(self, contract_address: str) -> Dict[str, Any]:
        """Get smart contract information"""
        try:
            contract = SmartContract.query.filter_by(
                contract_address=contract_address
            ).first()
            if contract:
                return contract.to_dict()
            if self.is_connected():
                try:
                    code = self.web3.eth.get_code(contract_address)
                    if code != b"":
                        return {
                            "contract_address": contract_address,
                            "has_code": True,
                            "network_id": self.network_id,
                            "network_name": self.network_name,
                        }
                except Exception:
                    pass
            return {"error": "Contract not found"}
        except Exception as e:
            self.logger.error(f"Contract info retrieval failed: {e}")
            return {"error": str(e)}

    def estimate_gas(
        self, contract_address: str, function_name: str, function_args: List = None
    ) -> Dict[str, Any]:
        """Estimate gas for contract function call"""
        try:
            if not self.is_connected():
                return {"error": "Blockchain not connected"}
            contract_record = SmartContract.query.filter_by(
                contract_address=contract_address
            ).first()
            if not contract_record:
                return {"error": "Contract not found"}
            contract = self.web3.eth.contract(
                address=contract_address, abi=contract_record.get_abi()
            )
            function = getattr(contract.functions, function_name)
            if not function:
                return {"error": "Function not found"}
            function_args = function_args or []
            gas_estimate = function(*function_args).estimate_gas(
                {"from": self.config.get("BLOCKCHAIN_FROM_ADDRESS")}
            )
            gas_price = self.web3.eth.gas_price
            estimated_cost_wei = gas_estimate * gas_price
            estimated_cost_eth = estimated_cost_wei / 10**18
            return {
                "gas_estimate": gas_estimate,
                "gas_price": gas_price,
                "estimated_cost_wei": estimated_cost_wei,
                "estimated_cost_eth": estimated_cost_eth,
            }
        except Exception as e:
            self.logger.error(f"Gas estimation failed: {e}")
            return {"error": str(e)}

    def _initialize_web3(self) -> Any:
        """Initialize Web3 connection"""
        try:
            provider_url = self.config.get("BLOCKCHAIN_PROVIDER_URL")
            if not provider_url:
                self.logger.warning("Blockchain provider URL not configured")
                return
            if provider_url.startswith("http"):
                self.web3 = Web3(Web3.HTTPProvider(provider_url))
            elif provider_url.startswith("ws"):
                self.web3 = Web3(Web3.WebsocketProvider(provider_url))
            else:
                self.logger.error(f"Unsupported provider URL: {provider_url}")
                return
            if self.web3.is_connected():
                self.is_connected_flag = True
                self.logger.info("Blockchain connection established")
            else:
                self.logger.warning("Blockchain connection failed")
        except Exception as e:
            self.logger.error(f"Web3 initialization failed: {e}")
            self.web3 = None

    def _load_contract_abis(self) -> Dict[ContractType, List[Dict]]:
        """Load contract ABIs from configuration or files"""
        abis = {}
        for contract_type in ContractType:
            abi_key = f"{contract_type.value.upper()}_CONTRACT_ABI"
            abi_data = self.config.get(abi_key)
            if abi_data:
                try:
                    if isinstance(abi_data, str):
                        abis[contract_type] = json.loads(abi_data)
                    else:
                        abis[contract_type] = abi_data
                except json.JSONDecodeError:
                    self.logger.error(f"Invalid ABI format for {contract_type}")
            else:
                try:
                    abi_file = f"../blockchain/build/contracts/{contract_type.value.title()}.json"
                    with open(abi_file, "r") as f:
                        contract_json = json.load(f)
                        abis[contract_type] = contract_json.get("abi", [])
                except FileNotFoundError:
                    self.logger.warning(f"ABI file not found for {contract_type}")
                except Exception as e:
                    self.logger.error(f"Error loading ABI for {contract_type}: {e}")
        return abis

    def _get_contract_instance(self, contract_type: ContractType) -> Any:
        """Get contract instance for given type"""
        try:
            contract_address = self.contract_addresses.get(contract_type)
            contract_abi = self.contract_abis.get(contract_type)
            if not contract_address or not contract_abi:
                return None
            return self.web3.eth.contract(address=contract_address, abi=contract_abi)
        except Exception as e:
            self.logger.error(
                f"Failed to get contract instance for {contract_type}: {e}"
            )
            return None

    def _create_blockchain_transaction(
        self,
        transaction_hash: str,
        transaction_type: TransactionType,
        from_address: str,
        to_address: str = None,
        contract_address: str = None,
        function_name: str = None,
        input_data: Dict[str, Any] = None,
        user_id: str = None,
        related_entity_type: str = None,
        related_entity_id: str = None,
        gas_limit: int = None,
        gas_price: int = None,
        value: int = 0,
    ) -> BlockchainTransaction:
        """Create blockchain transaction record in database"""
        try:
            blockchain_tx = BlockchainTransaction(
                id=str(uuid.uuid4()),
                transaction_hash=transaction_hash,
                transaction_type=transaction_type,
                status=TransactionStatus.PENDING,
                from_address=from_address,
                to_address=to_address,
                contract_address=contract_address,
                function_name=function_name,
                gas_limit=gas_limit,
                gas_price=gas_price,
                value=Decimal(value) / Decimal(10**18) if value else None,
                network_id=self.network_id,
                network_name=self.network_name,
                user_id=user_id,
                related_entity_type=related_entity_type,
                related_entity_id=related_entity_id,
                confirmation_count=0,
                required_confirmations=self.confirmation_blocks,
                submitted_at=datetime.now(timezone.utc),
            )
            if input_data:
                blockchain_tx.set_input_data(input_data)
            self.db.session.add(blockchain_tx)
            self.db.session.commit()
            return blockchain_tx
        except Exception as e:
            self.db.session.rollback()
            raise e

    def _fetch_wallet_history_from_blockchain(
        self, wallet_address: str, limit: int = 100
    ) -> List[BlockchainTransaction]:
        """Fetch wallet transaction history from blockchain (simplified implementation)"""
        try:
            return []
        except Exception as e:
            self.logger.error(f"Blockchain history fetch failed: {e}")
            return []

    def get_network_info(self) -> Dict[str, Any]:
        """Get blockchain network information"""
        try:
            if not self.is_connected():
                return {"connected": False, "error": "Not connected"}
            latest_block = self.web3.eth.block_number
            gas_price = self.web3.eth.gas_price
            return {
                "connected": True,
                "network_id": self.network_id,
                "network_name": self.network_name,
                "latest_block": latest_block,
                "gas_price": gas_price,
                "gas_price_gwei": gas_price / 10**9,
            }
        except Exception as e:
            self.logger.error(f"Network info retrieval failed: {e}")
            return {"connected": False, "error": str(e)}

    def monitor_pending_transactions(self) -> Dict[str, Any]:
        """Monitor and update pending transactions"""
        try:
            pending_txs = (
                BlockchainTransaction.query.filter_by(status=TransactionStatus.PENDING)
                .filter(
                    BlockchainTransaction.submitted_at
                    > datetime.now(timezone.utc) - timedelta(hours=24)
                )
                .all()
            )
            updated_count = 0
            failed_count = 0
            for tx in pending_txs:
                try:
                    if self.update_transaction_status(tx.id):
                        updated_count += 1
                except Exception as e:
                    self.logger.error(f"Failed to update transaction {tx.id}: {e}")
                    failed_count += 1
            return {
                "total_pending": len(pending_txs),
                "updated": updated_count,
                "failed": failed_count,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            self.logger.error(f"Transaction monitoring failed: {e}")
            return {"error": str(e)}

    def get_blockchain_metrics(self) -> Dict[str, Any]:
        """Get blockchain service metrics"""
        try:
            total_txs = BlockchainTransaction.query.count()
            confirmed_txs = BlockchainTransaction.query.filter_by(
                status=TransactionStatus.CONFIRMED
            ).count()
            failed_txs = BlockchainTransaction.query.filter_by(
                status=TransactionStatus.FAILED
            ).count()
            pending_txs = BlockchainTransaction.query.filter_by(
                status=TransactionStatus.PENDING
            ).count()
            recent_cutoff = datetime.now(timezone.utc) - timedelta(days=30)
            recent_txs = BlockchainTransaction.query.filter(
                BlockchainTransaction.submitted_at > recent_cutoff
            ).count()
            total_contracts = SmartContract.query.count()
            active_contracts = SmartContract.query.filter_by(
                status=ContractStatus.ACTIVE
            ).count()
            return {
                "connection_status": self.is_connected(),
                "network_info": self.get_network_info(),
                "transaction_stats": {
                    "total": total_txs,
                    "confirmed": confirmed_txs,
                    "failed": failed_txs,
                    "pending": pending_txs,
                    "recent_30d": recent_txs,
                    "success_rate": (
                        confirmed_txs / total_txs * 100 if total_txs > 0 else 0
                    ),
                },
                "contract_stats": {
                    "total": total_contracts,
                    "active": active_contracts,
                },
                "service_health": {
                    "connected": self.is_connected(),
                    "last_check": datetime.now(timezone.utc).isoformat(),
                },
            }
        except Exception as e:
            self.logger.error(f"Metrics collection failed: {e}")
            return {"error": str(e)}
