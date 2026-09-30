// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Votes.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/security/Pausable.sol";

/**
 * @title GovernanceToken
 * @dev ERC20 governance token for BlockScore protocol with voting capabilities
 * Implements financial industry standards for tokenized governance
 */
contract GovernanceToken is
    ERC20,
    ERC20Permit,
    ERC20Votes,
    AccessControl,
    Pausable
{
    // Role definitions
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant BURNER_ROLE = keccak256("BURNER_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");
    bytes32 public constant TREASURY_ROLE = keccak256("TREASURY_ROLE");

    // Token economics
    uint256 public constant MAX_SUPPLY = 1_000_000_000 * 10 ** 18; // 1 billion tokens
    uint256 public constant INITIAL_SUPPLY = 100_000_000 * 10 ** 18; // 100 million tokens

    // Vesting and distribution
    struct VestingSchedule {
        uint256 totalAmount;
        uint256 releasedAmount;
        uint256 startTime;
        uint256 cliffDuration;
        uint256 vestingDuration;
        bool revocable;
        bool revoked;
    }

    mapping(address => VestingSchedule) public vestingSchedules;
    mapping(address => bool) public isVestingBeneficiary;

    // Staking for governance participation
    struct StakeInfo {
        uint256 amount;
        uint256 stakingTime;
        uint256 lockPeriod;
        uint256 rewardDebt;
    }

    mapping(address => StakeInfo) public stakes;
    uint256 public totalStaked;
    uint256 public stakingRewardRate = 500; // 5% APY in basis points
    uint256 public minStakingPeriod = 30 days;

    // Governance parameters
    uint256 public proposalThreshold = 1000000 * 10 ** 18; // 1M tokens to create proposal
    uint256 public votingDelay = 1 days;
    uint256 public votingPeriod = 7 days;
    uint256 public quorumPercentage = 400; // 4% of total supply

    // Treasury and rewards
    address public treasury;
    uint256 public treasuryReserve;
    uint256 public communityRewards;

    // Events
    event TokensVested(address indexed beneficiary, uint256 amount);
    event VestingRevoked(address indexed beneficiary, uint256 unvestedAmount);
    event TokensStaked(
        address indexed staker,
        uint256 amount,
        uint256 lockPeriod
    );
    event TokensUnstaked(
        address indexed staker,
        uint256 amount,
        uint256 reward
    );
    event RewardsDistributed(address indexed recipient, uint256 amount);
    event TreasuryFunded(uint256 amount);
    event GovernanceParametersUpdated(
        uint256 proposalThreshold,
        uint256 votingDelay,
        uint256 votingPeriod,
        uint256 quorumPercentage
    );

    /**
     * @dev Constructor
     */
    constructor(
        address _treasury
    )
        ERC20("BlockScore Governance Token", "BSGT")
        ERC20Permit("BlockScore Governance Token")
    {
        treasury = _treasury;

        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _grantRole(MINTER_ROLE, msg.sender);
        _grantRole(PAUSER_ROLE, msg.sender);
        _grantRole(TREASURY_ROLE, _treasury);

        // Mint initial supply
        _mint(msg.sender, INITIAL_SUPPLY);

        // Allocate initial distribution
        treasuryReserve = ((INITIAL_SUPPLY * 30) / 100); // 30% to treasury
        communityRewards = ((INITIAL_SUPPLY * 20) / 100); // 20% for community rewards

        _transfer(msg.sender, treasury, treasuryReserve);
        // The community rewards pool must actually be held in custody by
        // this contract, since staking rewards and distributeCommunityRewards()
        // both pay out of address(this)'s own balance. Previously
        // `communityRewards` was only ever updated as a bookkeeping number
        // with no corresponding tokens ever transferred to the contract,
        // which meant reward payouts would revert with "transfer amount
        // exceeds balance" as soon as they exceeded whatever had
        // incidentally been staked.
        _transfer(msg.sender, address(this), communityRewards);
    }

    /**
     * @dev Create vesting schedule for team/advisors
     */
    function createVestingSchedule(
        address beneficiary,
        uint256 totalAmount,
        uint256 startTime,
        uint256 cliffDuration,
        uint256 vestingDuration,
        bool revocable
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(beneficiary != address(0), "Invalid beneficiary");
        require(totalAmount > 0, "Amount must be positive");
        require(vestingDuration > 0, "Vesting duration must be positive");
        require(
            !isVestingBeneficiary[beneficiary],
            "Beneficiary already has vesting schedule"
        );

        // Ensure the funding admin actually has enough tokens to seed this
        // vesting schedule. (Previously this checked the contract's own
        // balance instead of the caller's, before the tokens were ever
        // transferred in - which made this requirement impossible to
        // satisfy on a fresh vesting schedule and broke the feature.)
        require(
            balanceOf(msg.sender) >= totalAmount,
            "Insufficient tokens for vesting"
        );

        vestingSchedules[beneficiary] = VestingSchedule({
            totalAmount: totalAmount,
            releasedAmount: 0,
            startTime: startTime,
            cliffDuration: cliffDuration,
            vestingDuration: vestingDuration,
            revocable: revocable,
            revoked: false
        });

        isVestingBeneficiary[beneficiary] = true;

        // Transfer tokens to contract for vesting
        _transfer(msg.sender, address(this), totalAmount);
    }

    /**
     * @dev Release vested tokens to beneficiary
     */
    function releaseVestedTokens() external {
        require(isVestingBeneficiary[msg.sender], "No vesting schedule found");

        VestingSchedule storage schedule = vestingSchedules[msg.sender];
        require(!schedule.revoked, "Vesting schedule revoked");

        uint256 vestedAmount = _calculateVestedAmount(msg.sender);
        uint256 releasableAmount = (vestedAmount - schedule.releasedAmount);

        require(releasableAmount > 0, "No tokens to release");

        schedule.releasedAmount = (schedule.releasedAmount + releasableAmount);
        _transfer(address(this), msg.sender, releasableAmount);

        emit TokensVested(msg.sender, releasableAmount);
    }

    /**
     * @dev Revoke vesting schedule (admin only)
     */
    function revokeVesting(
        address beneficiary
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(isVestingBeneficiary[beneficiary], "No vesting schedule found");

        VestingSchedule storage schedule = vestingSchedules[beneficiary];
        require(schedule.revocable, "Vesting schedule not revocable");
        require(!schedule.revoked, "Vesting already revoked");

        uint256 vestedAmount = _calculateVestedAmount(beneficiary);
        uint256 releasableAmount = (vestedAmount - schedule.releasedAmount);
        uint256 unvestedAmount = (schedule.totalAmount - vestedAmount);

        schedule.revoked = true;

        // Release any vested tokens
        if (releasableAmount > 0) {
            schedule.releasedAmount = (schedule.releasedAmount +
                releasableAmount);
            _transfer(address(this), beneficiary, releasableAmount);
        }

        // Return unvested tokens to admin
        if (unvestedAmount > 0) {
            _transfer(address(this), msg.sender, unvestedAmount);
        }

        emit VestingRevoked(beneficiary, unvestedAmount);
    }

    /**
     * @dev Stake tokens for governance participation
     */
    function stakeTokens(
        uint256 amount,
        uint256 lockPeriod
    ) external whenNotPaused {
        require(amount > 0, "Amount must be positive");
        require(lockPeriod >= minStakingPeriod, "Lock period too short");
        require(balanceOf(msg.sender) >= amount, "Insufficient balance");

        // If user already has stake, claim rewards first
        if (stakes[msg.sender].amount > 0) {
            _claimStakingRewards(msg.sender);
        }

        // Transfer tokens to contract
        _transfer(msg.sender, address(this), amount);

        // Update stake info
        stakes[msg.sender] = StakeInfo({
            amount: (stakes[msg.sender].amount + amount),
            stakingTime: block.timestamp,
            lockPeriod: lockPeriod,
            rewardDebt: 0
        });

        totalStaked = (totalStaked + amount);

        emit TokensStaked(msg.sender, amount, lockPeriod);
    }

    /**
     * @dev Unstake tokens after lock period
     */
    function unstakeTokens(uint256 amount) external {
        StakeInfo storage stake = stakes[msg.sender];
        require(stake.amount >= amount, "Insufficient staked amount");
        require(
            block.timestamp >= (stake.stakingTime + stake.lockPeriod),
            "Tokens still locked"
        );

        // Calculate and claim rewards
        uint256 rewards = _claimStakingRewards(msg.sender);

        // Update stake
        stake.amount = (stake.amount - amount);
        totalStaked = (totalStaked - amount);

        // Transfer tokens back to user
        _transfer(address(this), msg.sender, amount);

        emit TokensUnstaked(msg.sender, amount, rewards);
    }

    /**
     * @dev Claim staking rewards
     */
    function claimStakingRewards() external {
        uint256 rewards = _claimStakingRewards(msg.sender);
        require(rewards > 0, "No rewards to claim");
    }

    /**
     * @dev Mint new tokens (minter role only)
     */
    function mint(address to, uint256 amount) external onlyRole(MINTER_ROLE) {
        require((totalSupply() + amount) <= MAX_SUPPLY, "Exceeds max supply");
        _mint(to, amount);
    }

    /**
     * @dev Burn tokens (burner role only)
     */
    function burn(uint256 amount) external onlyRole(BURNER_ROLE) {
        _burn(msg.sender, amount);
    }

    /**
     * @dev Burn tokens from account (burner role only)
     */
    function burnFrom(
        address account,
        uint256 amount
    ) external onlyRole(BURNER_ROLE) {
        uint256 currentAllowance = allowance(account, msg.sender);
        require(currentAllowance >= amount, "Burn amount exceeds allowance");

        _approve(account, msg.sender, (currentAllowance - amount));
        _burn(account, amount);
    }

    /**
     * @dev Pause token transfers (pauser role only)
     */
    function pause() external onlyRole(PAUSER_ROLE) {
        _pause();
    }

    /**
     * @dev Unpause token transfers (pauser role only)
     */
    function unpause() external onlyRole(PAUSER_ROLE) {
        _unpause();
    }

    /**
     * @dev Update governance parameters (admin only)
     */
    function updateGovernanceParameters(
        uint256 _proposalThreshold,
        uint256 _votingDelay,
        uint256 _votingPeriod,
        uint256 _quorumPercentage
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        proposalThreshold = _proposalThreshold;
        votingDelay = _votingDelay;
        votingPeriod = _votingPeriod;
        quorumPercentage = _quorumPercentage;

        emit GovernanceParametersUpdated(
            _proposalThreshold,
            _votingDelay,
            _votingPeriod,
            _quorumPercentage
        );
    }

    /**
     * @dev Fund treasury with tokens (treasury role only)
     */
    function fundTreasury(uint256 amount) external onlyRole(TREASURY_ROLE) {
        require(balanceOf(msg.sender) >= amount, "Insufficient balance");
        _transfer(msg.sender, treasury, amount);
        treasuryReserve = (treasuryReserve + amount);

        emit TreasuryFunded(amount);
    }

    /**
     * @dev Distribute community rewards (admin only)
     */
    function distributeCommunityRewards(
        address[] calldata recipients,
        uint256[] calldata amounts
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(recipients.length == amounts.length, "Array length mismatch");

        uint256 totalAmount = 0;
        for (uint256 i = 0; i < amounts.length; i++) {
            totalAmount = (totalAmount + amounts[i]);
        }

        require(
            communityRewards >= totalAmount,
            "Insufficient community rewards"
        );

        for (uint256 i = 0; i < recipients.length; i++) {
            _transfer(address(this), recipients[i], amounts[i]);
            emit RewardsDistributed(recipients[i], amounts[i]);
        }

        communityRewards = (communityRewards - totalAmount);
    }

    /**
     * @dev Get vested amount for beneficiary
     */
    function getVestedAmount(
        address beneficiary
    ) external view returns (uint256) {
        return _calculateVestedAmount(beneficiary);
    }

    /**
     * @dev Get staking rewards for account
     */
    function getStakingRewards(
        address account
    ) external view returns (uint256) {
        return _calculateStakingRewards(account);
    }

    /**
     * @dev Get voting power (includes staked tokens)
     */
    function getVotingPower(address account) external view returns (uint256) {
        return (getVotes(account) + stakes[account].amount);
    }

    /**
     * @dev Internal function to calculate vested amount
     */
    function _calculateVestedAmount(
        address beneficiary
    ) internal view returns (uint256) {
        VestingSchedule storage schedule = vestingSchedules[beneficiary];

        if (
            schedule.revoked ||
            block.timestamp < (schedule.startTime + schedule.cliffDuration)
        ) {
            return 0;
        }

        if (
            block.timestamp >= (schedule.startTime + schedule.vestingDuration)
        ) {
            return schedule.totalAmount;
        }

        uint256 timeVested = (block.timestamp - schedule.startTime);
        return ((schedule.totalAmount * timeVested) / schedule.vestingDuration);
    }

    /**
     * @dev Internal function to calculate staking rewards
     */
    function _calculateStakingRewards(
        address account
    ) internal view returns (uint256) {
        StakeInfo storage stake = stakes[account];

        if (stake.amount == 0) {
            return 0;
        }

        uint256 stakingDuration = (block.timestamp - stake.stakingTime);
        uint256 annualReward = ((stake.amount * stakingRewardRate) / 10000);
        uint256 reward = ((annualReward * stakingDuration) / 365 days);

        return (reward - stake.rewardDebt);
    }

    /**
     * @dev Internal function to claim staking rewards
     */
    function _claimStakingRewards(address account) internal returns (uint256) {
        uint256 rewards = _calculateStakingRewards(account);

        if (rewards > 0) {
            stakes[account].rewardDebt = (stakes[account].rewardDebt + rewards);

            // Mint rewards from community pool
            if (communityRewards >= rewards) {
                _transfer(address(this), account, rewards);
                communityRewards = (communityRewards - rewards);
            } else {
                // If not enough in community pool, mint new tokens (up to max supply)
                if ((totalSupply() + rewards) <= MAX_SUPPLY) {
                    _mint(account, rewards);
                }
            }

            emit RewardsDistributed(account, rewards);
        }

        return rewards;
    }

    /**
     * @dev Override required by Solidity
     */
    function _beforeTokenTransfer(
        address from,
        address to,
        uint256 amount
    ) internal override whenNotPaused {
        super._beforeTokenTransfer(from, to, amount);
    }

    /**
     * @dev Override required by Solidity
     */
    function _afterTokenTransfer(
        address from,
        address to,
        uint256 amount
    ) internal override(ERC20, ERC20Votes) {
        super._afterTokenTransfer(from, to, amount);
    }

    /**
     * @dev Override required by Solidity
     */
    function _mint(
        address to,
        uint256 amount
    ) internal override(ERC20, ERC20Votes) {
        super._mint(to, amount);
    }

    /**
     * @dev Override required by Solidity
     */
    function _burn(
        address account,
        uint256 amount
    ) internal override(ERC20, ERC20Votes) {
        super._burn(account, amount);
    }
}
