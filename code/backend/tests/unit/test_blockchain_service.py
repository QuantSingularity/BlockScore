from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from models.blockchain import BlockchainTransaction


@pytest.fixture
def mock_contract():
    contract = MagicMock()
    built_tx = {
        "from": "0x1234567890123456789012345678901234567890",
        "gas": 200000,
        "gasPrice": 20000000000,
        "nonce": 0,
        "data": "0x",
    }
    contract.functions.addCreditRecord.return_value.build_transaction.return_value = (
        built_tx
    )
    contract.functions.makePayment.return_value.build_transaction.return_value = (
        built_tx
    )
    return contract


def _mock_signed_and_sent(blockchain_service, tx_hash="0x" + "ab" * 32):
    blockchain_service.web3.eth.get_transaction_count.return_value = 0
    blockchain_service.web3.eth.account.sign_transaction.return_value = MagicMock(
        raw_transaction=b"\x00"
    )
    blockchain_service.web3.eth.send_raw_transaction.return_value = MagicMock(
        hex=lambda: tx_hash
    )
    blockchain_service.web3.keccak.return_value = b"\x00" * 32
    return tx_hash


class TestSubmitCreditScoreUpdate:
    def test_calls_add_credit_record_with_correct_arguments(
        self, blockchain_service, mock_contract
    ):
        blockchain_service._get_contract_instance = MagicMock(
            return_value=mock_contract
        )
        tx_hash = _mock_signed_and_sent(blockchain_service)

        result = blockchain_service.submit_credit_score_update(
            user_id="user-1",
            credit_score_id="score-1",
            score=720,
            wallet_address="0xBorrower000000000000000000000000000001",
            previous_score=700,
        )

        assert result["status"] == "submitted"
        assert result["transaction_hash"] == tx_hash

        args, kwargs = mock_contract.functions.addCreditRecord.call_args
        user, amount, record_type, score_impact, data_hash, flags, signature = args
        assert user == "0xBorrower000000000000000000000000000001"
        assert record_type == "score_recalculation"
        assert score_impact == 20
        assert signature == b""

        stored = BlockchainTransaction.query.filter_by(transaction_hash=tx_hash).first()
        assert stored is not None
        assert stored.function_name == "addCreditRecord"

    def test_clamps_score_impact_to_contract_bounds(
        self, blockchain_service, mock_contract
    ):
        blockchain_service._get_contract_instance = MagicMock(
            return_value=mock_contract
        )
        _mock_signed_and_sent(blockchain_service, tx_hash="0x" + "cd" * 32)

        blockchain_service.submit_credit_score_update(
            user_id="user-2",
            credit_score_id="score-2",
            score=850,
            wallet_address="0xBorrower000000000000000000000000000002",
            previous_score=300,
        )

        args, _ = mock_contract.functions.addCreditRecord.call_args
        score_impact = args[3]
        assert score_impact == 50

    def test_no_previous_score_logs_neutral_event(
        self, blockchain_service, mock_contract
    ):
        blockchain_service._get_contract_instance = MagicMock(
            return_value=mock_contract
        )
        _mock_signed_and_sent(blockchain_service, tx_hash="0x" + "ef" * 32)

        blockchain_service.submit_credit_score_update(
            user_id="user-3",
            credit_score_id="score-3",
            score=650,
            wallet_address="0xBorrower000000000000000000000000000003",
            previous_score=None,
        )

        args, _ = mock_contract.functions.addCreditRecord.call_args
        assert args[3] == 0


class TestRecordPayment:
    def test_calls_make_payment_not_a_nonexistent_function(
        self, blockchain_service, mock_contract
    ):
        blockchain_service._get_contract_instance = MagicMock(
            return_value=mock_contract
        )
        tx_hash = _mock_signed_and_sent(blockchain_service, tx_hash="0x" + "12" * 32)

        result = blockchain_service.record_payment(
            loan_id="1",
            payment_amount=Decimal("250.00"),
            borrower_address="0xBorrower000000000000000000000000000004",
            payment_method="bank_transfer",
        )

        assert result["status"] == "submitted"
        args, _ = mock_contract.functions.makePayment.call_args
        loan_id, amount_wei, method = args
        assert loan_id == 1
        assert amount_wei == int(Decimal("250.00") * 10**18)
        assert method == "bank_transfer"

        stored = BlockchainTransaction.query.filter_by(transaction_hash=tx_hash).first()
        assert stored is not None
        assert stored.function_name == "makePayment"


class TestSubmitLoanAgreement:
    def test_records_borrower_submitted_transaction_without_relaying(
        self, blockchain_service
    ):
        blockchain_service.update_transaction_status = MagicMock()

        result = blockchain_service.submit_loan_agreement(
            loan_id="loan-1",
            borrower_address="0xBorrower000000000000000000000000000005",
            transaction_hash="0x" + "34" * 32,
            loan_amount=Decimal("5000"),
            interest_rate=5.5,
            term_months=12,
        )

        assert result["status"] == "tracking"
        stored = BlockchainTransaction.query.filter_by(
            transaction_hash="0x" + "34" * 32
        ).first()
        assert stored is not None
        assert stored.function_name == "submitLoanApplication"
        assert stored.from_address == "0xBorrower000000000000000000000000000005"
