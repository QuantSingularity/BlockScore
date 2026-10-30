# BlockScore Smart Contracts Documentation

## Overview

BlockScore uses Solidity smart contracts for immutable credit record storage and automated loan management on Ethereum/Polygon blockchains. Contracts are built and tested with Hardhat (`code/blockchain`), not Truffle.

There are two generations of the core contracts:

- **CreditScore.sol / LoanContract.sol** ("v1") - simple, owner/authorized-provider access control, no on-chain signatures.
- **CreditScoreV2.sol / LoanContractV2.sol** ("v2", primary) - role-based access control (OpenZeppelin `AccessControl`), EIP-712 signed submissions, compliance/dispute/freeze workflows, and a full underwriting -> funding -> repayment loan lifecycle. New integrations should target v2.

## Contracts

### 1. CreditScore.sol (v1)

Main contract for managing credit records and scores.

**Location**: `code/blockchain/contracts/CreditScore.sol`

**Key Functions**:

| Function            | Parameters                                                          | Description                            | Access               |
| ------------------- | ------------------------------------------------------------------- | -------------------------------------- | -------------------- |
| `addCreditRecord`   | `address user, uint256 amount, string recordType, int8 scoreImpact` | Add new credit record (impact -10..10) | Authorized providers |
| `markRepaid`        | `address user, uint256 recordIndex`                                 | Mark a record as repaid                | Authorized providers |
| `getCreditScore`    | `address user`                                                      | Returns `(score, lastUpdated)`         | Public               |
| `getCreditHistory`  | `address user`                                                      | Returns all credit records             | Public               |
| `authorizeProvider` | `address provider`                                                  | Authorize a credit provider            | Owner only           |
| `revokeProvider`    | `address provider`                                                  | Revoke a credit provider               | Owner only           |

**Example Usage** (Hardhat + ethers v6):

```javascript
const { ethers } = require("hardhat");

const CreditScore = await ethers.getContractFactory("CreditScore");
const creditScore = await CreditScore.deploy();
await creditScore.waitForDeployment();

// Add credit record
await creditScore.addCreditRecord(
  "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
  1000, // amount
  "loan", // record type
  5, // score impact
);

// Read the credit score
const [score, lastUpdated] = await creditScore.getCreditScore(
  "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
);
console.log(score.toString());
```

### 2. CreditScoreV2.sol (primary)

Role-gated credit registry with EIP-712 signed submissions, compliance flagging, disputes, and profile freeze/unfreeze.

**Location**: `code/blockchain/contracts/CreditScoreV2.sol`

**Key Functions**:

| Function                              | Parameters                                                                                                                      | Description                                                                                                                              | Access                      |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | --------------------------- |
| `addCreditRecord`                     | `address user, uint256 amount, string recordType, int16 scoreImpact, bytes32 dataHash, string complianceFlags, bytes signature` | Add a credit record (impact -50..50). `signature` is an optional EIP-712 self-attestation - pass `"0x"` to rely on role-based auth alone | `CREDIT_PROVIDER_ROLE`      |
| `markRepaid`                          | `address user, uint256 recordIndex, bytes signature`                                                                            | Mark a record repaid; applies a timing-based repayment bonus                                                                             | Original recording provider |
| `freezeProfile` / `unfreezeProfile`   | `address user, string reason` / `address user`                                                                                  | Block/unblock further records for a user pending review                                                                                  | `COMPLIANCE_OFFICER_ROLE`   |
| `disputeRecord`                       | `uint256 recordIndex, string reason`                                                                                            | User disputes one of their own records                                                                                                   | Public (the record's user)  |
| `resolveDispute`                      | `uint256 disputeId, bool upheld, string resolution`                                                                             | Resolve a dispute                                                                                                                        | `COMPLIANCE_OFFICER_ROLE`   |
| `emergencyPause` / `emergencyUnpause` | -                                                                                                                               | Halt/resume all state-changing calls                                                                                                     | `EMERGENCY_ROLE`            |

A contract integration (e.g. `LoanContractV2`) that already holds `CREDIT_PROVIDER_ROLE` can call `addCreditRecord`/`markRepaid` with an empty `signature` (`"0x"`), since it can never produce an ECDSA signature itself - role membership is the authentication. An EOA provider may optionally self-sign instead.

### 3. LoanContract.sol (v1)

Simple loan lifecycle: request, owner approval, repayment.

**Location**: `code/blockchain/contracts/LoanContract.sol`

**Key Functions**:

| Function           | Parameters                                                   | Description                                    |
| ------------------ | ------------------------------------------------------------ | ---------------------------------------------- |
| `createLoan`       | `uint256 amount, uint256 interestRate, uint256 durationDays` | Create a loan request (msg.sender is borrower) |
| `approveLoan`      | `uint256 loanId`                                             | Approve a loan (owner only)                    |
| `repayLoan`        | `uint256 loanId`                                             | Repay an approved loan                         |
| `getLoanDetails`   | `uint256 loanId`                                             | Get loan information                           |
| `getBorrowerLoans` | `address borrower`                                           | List a borrower's loan IDs                     |

### 4. LoanContractV2.sol (primary)

Full underwriting -> funding -> repayment/default loan lifecycle, with ERC20 lending and (optional) collateral tokens. Reports credit events back to `CreditScoreV2`.

**Location**: `code/blockchain/contracts/LoanContractV2.sol`

**Key Functions**:

| Function                              | Parameters (abridged)                                                                                                          | Description                                                                                                                                                                                                 | Access                    |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------- |
| `submitLoanApplication`               | `amount, termDays, purpose, annualIncome, debtToIncomeRatio, employmentStatus, documentsHash, signature`                       | Applicant submits a loan request. `signature` is a mandatory EIP-712 signature from the applicant themselves (`msg.sender`) - this call cannot be relayed by a third party such as a backend service wallet | Public (applicant)        |
| `completeComplianceCheck`             | `applicationId, kycPassed, amlPassed, sanctionsPassed, incomeVerified, identityVerified, notes`                                | Marks compliance checks complete for an application                                                                                                                                                         | `COMPLIANCE_OFFICER_ROLE` |
| `underwriteLoan`                      | `applicationId, approvedAmount, interestRate, termDays, originationFeeRate, requiresCollateral, collateralRequired, riskNotes` | Approves a loan application                                                                                                                                                                                 | `UNDERWRITER_ROLE`        |
| `depositCollateral`                   | `loanId, amount, tokenAddress`                                                                                                 | Borrower deposits required collateral before funding                                                                                                                                                        | Borrower                  |
| `fundLoan`                            | `loanId`                                                                                                                       | Disburses funds to the borrower (net of origination fee)                                                                                                                                                    | `LOAN_OFFICER_ROLE`       |
| `makePayment`                         | `loanId, paymentAmount, paymentMethod`                                                                                         | Applies a payment (interest first, then principal); not restricted to the borrower - anyone funding the payment may call it                                                                                 | Public                    |
| `getLoanDetails` / `getContractStats` | `loanId` / -                                                                                                                   | Read loan / aggregate statistics                                                                                                                                                                            | Public                    |

### 5. GovernanceToken.sol

ERC20 governance token (`ERC20Votes` + `ERC20Permit`) with linear vesting schedules and a staking module (time-locked stake with accruing rewards, paid from a dedicated community rewards pool funded at deployment).

**Location**: `code/blockchain/contracts/GovernanceToken.sol`

**Key Functions**:

| Function                        | Description                                                                                                                    | Access               |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ | -------------------- |
| `mint`                          | Mint new tokens up to `MAX_SUPPLY`                                                                                             | `MINTER_ROLE`        |
| `createVestingSchedule`         | Create a linear (optionally cliffed) vesting schedule for a beneficiary, funded from the caller's balance                      | `DEFAULT_ADMIN_ROLE` |
| `releaseVestedTokens`           | Beneficiary claims currently-vested tokens                                                                                     | Public (beneficiary) |
| `stakeTokens` / `unstakeTokens` | Lock tokens for a chosen period (>= 30 days) to accrue rewards; rewards paid from the contract's own community-rewards balance | Public               |
| `getVotingPower`                | Delegated voting power plus currently staked balance                                                                           | Public               |
| `updateGovernanceParameters`    | Update proposal threshold, voting delay/period, quorum                                                                         | `DEFAULT_ADMIN_ROLE` |

## Compiling and Testing

```bash
cd code/blockchain
npm install
npm run compile   # compiles fully offline via the local solc npm package
npm test          # 53 tests across all five contracts
```

## Deployment

`scripts/deploy.js` deploys all five contracts and wires up every cross-contract role they need (e.g. granting `LoanContractV2` `CREDIT_PROVIDER_ROLE` on `CreditScoreV2`) - deploying the contracts individually without this script will leave them unable to talk to each other.

### Local Development

```bash
cd code/blockchain
npx hardhat node               # in one terminal
npm run deploy:local           # in another (or: npx hardhat run scripts/deploy.js --network development)
```

On the `hardhat`/`localhost`/`development` networks, if `LENDING_TOKEN_ADDRESS` isn't set, `scripts/deploy.js` also deploys a disposable mock ERC20 to use as `LoanContractV2`'s lending token, and grants the deployer the operational roles (`LOAN_OFFICER_ROLE`, `UNDERWRITER_ROLE`, `LIQUIDATOR_ROLE`, `CREDIT_PROVIDER_ROLE`) needed to exercise the full loan lifecycle from one account.

### A Real Network (e.g. Polygon Amoy)

Add a matching entry to `code/blockchain/hardhat.config.js`'s `networks` block (RPC URL + account private key, typically read from environment variables), then:

```bash
cd code/blockchain
LENDING_TOKEN_ADDRESS=0x... TREASURY_ADDRESS=0x... \
  npx hardhat run scripts/deploy.js --network "<network-name>"
```

`scripts/deploy.js` writes `deployments/<network>/addresses.json` and `deployments/<network>/constructor-args.json` (the latter needed to verify source via `npx hardhat verify --network <network> <address> <constructor-args...>`, bundled as `@nomicfoundation/hardhat-verify` in `@nomicfoundation/hardhat-toolbox`).

The repo-root `scripts/smart_contract_deploy.sh` wraps this same flow with security scanning (solhint/slither), gas-optimization checks, and deployment record-keeping under `.blockscore_config/`:

```bash
./scripts/smart_contract_deploy.sh -n development
./scripts/smart_contract_deploy.sh -n test -v   # also verify on a block explorer
```

## Contract Addresses

Contract addresses aren't checked into the repo - each deployment produces its own (see `deployments/<network>/addresses.json` above). The backend reads them from environment variables: `CREDIT_SCORE_CONTRACT_ADDRESS`, `LOAN_AGREEMENT_CONTRACT_ADDRESS`, `GOVERNANCE_CONTRACT_ADDRESS` (see `code/backend/.env.example`).

See [Configuration Guide](CONFIGURATION.md) for setting these.
