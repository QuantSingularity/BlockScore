const { expect } = require("chai");
const { ethers } = require("hardhat");
const ONE_TOKEN = 10n ** 18n;
describe("GovernanceToken", function () {
  let token;
  let admin;
  let treasury;
  let alice;
  let bob;
  beforeEach(async function () {
    [admin, treasury, alice, bob] = await ethers.getSigners();
    const GovernanceToken = await ethers.getContractFactory("GovernanceToken");
    token = await GovernanceToken.deploy(treasury.address);
    await token.waitForDeployment();
  });
  it("mints the initial supply and allocates the treasury reserve and community pool", async function () {
    const initialSupply = 100000000n * ONE_TOKEN;
    const treasuryReserve = (initialSupply * 30n) / 100n;
    const communityRewards = (initialSupply * 20n) / 100n;
    expect(await token.totalSupply()).to.equal(initialSupply);
    expect(await token.balanceOf(treasury.address)).to.equal(treasuryReserve);
    expect(await token.balanceOf(await token.getAddress())).to.equal(
      communityRewards,
    );
    expect(await token.balanceOf(admin.address)).to.equal(
      initialSupply - treasuryReserve - communityRewards,
    );
  });
  it("allows MINTER_ROLE to mint up to the max supply", async function () {
    const MINTER_ROLE = await token.MINTER_ROLE();
    expect(await token.hasRole(MINTER_ROLE, admin.address)).to.equal(true);
    await token.mint(alice.address, 1000n * ONE_TOKEN);
    expect(await token.balanceOf(alice.address)).to.equal(1000n * ONE_TOKEN);
  });
  it("rejects minting beyond MAX_SUPPLY", async function () {
    const maxSupply = await token.MAX_SUPPLY();
    const totalSupply = await token.totalSupply();
    const remaining = maxSupply - totalSupply;
    await expect(token.mint(alice.address, remaining + 1n)).to.be.revertedWith(
      "Exceeds max supply",
    );
  });
  it("rejects minting from a non-minter account", async function () {
    await expect(token.connect(alice).mint(alice.address, 1n)).to.be.reverted;
  });
  describe("Vesting", function () {
    it("linearly releases tokens over the vesting period", async function () {
      const total = 1000000n * ONE_TOKEN;
      await token.mint(admin.address, total);
      await token.approve(await token.getAddress(), total);
      const latestBlock = await ethers.provider.getBlock("latest");
      const startTime = latestBlock.timestamp;
      const cliff = 0;
      const duration = 1000;
      await token.createVestingSchedule(
        alice.address,
        total,
        startTime,
        cliff,
        duration,
        true,
      );
      await ethers.provider.send("evm_increaseTime", [500]);
      await ethers.provider.send("evm_mine");
      const vestedBeforeRelease = await token.getVestedAmount(alice.address);
      expect(vestedBeforeRelease).to.be.gt(0);
      expect(vestedBeforeRelease).to.be.lt(total);
      const tx = await token.connect(alice).releaseVestedTokens();
      const receipt = await tx.wait();
      const releaseBlock = await ethers.provider.getBlock(receipt.blockNumber);
      const expectedVested =
        (total * BigInt(releaseBlock.timestamp - startTime)) / BigInt(duration);
      expect(await token.balanceOf(alice.address)).to.equal(expectedVested);
    });
    it("prevents a second vesting schedule for the same beneficiary", async function () {
      const total = 1000n * ONE_TOKEN;
      await token.mint(admin.address, total * 2n);
      const latestBlock = await ethers.provider.getBlock("latest");
      await token.createVestingSchedule(
        alice.address,
        total,
        latestBlock.timestamp,
        0,
        1000,
        true,
      );
      await expect(
        token.createVestingSchedule(
          alice.address,
          total,
          latestBlock.timestamp,
          0,
          1000,
          true,
        ),
      ).to.be.revertedWith("Beneficiary already has vesting schedule");
    });
  });
  describe("Staking", function () {
    it("stakes tokens, accrues rewards over time, and unstakes after the lock period", async function () {
      const stakeAmount = 10000n * ONE_TOKEN;
      await token.transfer(alice.address, stakeAmount);
      const lockPeriod = 30 * 24 * 60 * 60;
      await token.connect(alice).stakeTokens(stakeAmount, lockPeriod);
      const [amount] = await token.stakes(alice.address);
      expect(amount).to.equal(stakeAmount);
      expect(await token.totalStaked()).to.equal(stakeAmount);
      await ethers.provider.send("evm_increaseTime", [lockPeriod + 1]);
      await ethers.provider.send("evm_mine");
      const rewards = await token.getStakingRewards(alice.address);
      expect(rewards).to.be.gt(0);
      await token.connect(alice).unstakeTokens(stakeAmount);
      expect(await token.balanceOf(alice.address)).to.be.gt(stakeAmount);
    });
    it("rejects staking below the minimum lock period", async function () {
      const stakeAmount = 1000n * ONE_TOKEN;
      await token.transfer(alice.address, stakeAmount);
      await expect(
        token.connect(alice).stakeTokens(stakeAmount, 1),
      ).to.be.revertedWith("Lock period too short");
    });
    it("rejects unstaking before the lock period ends", async function () {
      const stakeAmount = 1000n * ONE_TOKEN;
      await token.transfer(alice.address, stakeAmount);
      await token.connect(alice).stakeTokens(stakeAmount, 30 * 24 * 60 * 60);
      await expect(
        token.connect(alice).unstakeTokens(stakeAmount),
      ).to.be.revertedWith("Tokens still locked");
    });
  });
  describe("Pausing", function () {
    it("blocks transfers while paused", async function () {
      await token.transfer(alice.address, 100n * ONE_TOKEN);
      await token.pause();
      await expect(
        token.connect(alice).transfer(bob.address, 1n * ONE_TOKEN),
      ).to.be.revertedWith("Pausable: paused");
      await token.unpause();
      await token.connect(alice).transfer(bob.address, 1n * ONE_TOKEN);
      expect(await token.balanceOf(bob.address)).to.equal(1n * ONE_TOKEN);
    });
  });
  describe("Governance parameters", function () {
    it("lets the admin update governance parameters", async function () {
      await token.updateGovernanceParameters(
        2000000n * ONE_TOKEN,
        2 * 24 * 60 * 60,
        14 * 24 * 60 * 60,
        500,
      );
      expect(await token.proposalThreshold()).to.equal(2000000n * ONE_TOKEN);
      expect(await token.quorumPercentage()).to.equal(500);
    });
  });
  describe("Voting power", function () {
    it("includes both delegated votes and staked balance", async function () {
      const amount = 5000n * ONE_TOKEN;
      await token.transfer(alice.address, amount);
      await token.connect(alice).delegate(alice.address);
      const stakeAmount = 1000n * ONE_TOKEN;
      await token.connect(alice).stakeTokens(stakeAmount, 30 * 24 * 60 * 60);
      const votingPower = await token.getVotingPower(alice.address);
      expect(votingPower).to.equal(amount);
    });
  });
});
