const { expect } = require("chai");
const { ethers } = require("hardhat");
describe("CreditScore Contract", function () {
  let CreditScore;
  let creditScore;
  let owner;
  let provider1;
  let provider2;
  let user1;
  let user2;
  beforeEach(async function () {
    [owner, provider1, provider2, user1, user2] = await ethers.getSigners();
    CreditScore = await ethers.getContractFactory("CreditScore");
    creditScore = await CreditScore.deploy();
    await creditScore.waitForDeployment();
  });
  describe("Authorization", function () {
    it("should set the deployer as owner and authorized provider", async function () {
      expect(await creditScore.isAuthorizedProvider(owner.address)).to.equal(
        true,
      );
    });
    it("should allow owner to authorize new providers", async function () {
      await creditScore.authorizeProvider(provider1.address);
      expect(
        await creditScore.isAuthorizedProvider(provider1.address),
      ).to.equal(true);
    });
    it("should allow owner to revoke providers", async function () {
      await creditScore.authorizeProvider(provider1.address);
      expect(
        await creditScore.isAuthorizedProvider(provider1.address),
      ).to.equal(true);
      await creditScore.revokeProvider(provider1.address);
      expect(
        await creditScore.isAuthorizedProvider(provider1.address),
      ).to.equal(false);
    });
    it("should not allow non-owners to authorize providers", async function () {
      await expect(
        creditScore.connect(provider1).authorizeProvider(provider2.address),
      ).to.be.revertedWith("Only owner can call this function");
    });
    it("should not allow revoking the owner", async function () {
      await expect(
        creditScore.revokeProvider(owner.address),
      ).to.be.revertedWith("Cannot revoke owner's authorization");
    });
  });
  describe("Credit Records", function () {
    beforeEach(async function () {
      await creditScore.authorizeProvider(provider1.address);
    });
    it("should allow authorized providers to add credit records", async function () {
      await creditScore
        .connect(provider1)
        .addCreditRecord(user1.address, 1000, "loan", 5);
      const history = await creditScore.getCreditHistory(user1.address);
      expect(history.length).to.equal(1);
      expect(history[0].amount).to.equal(1000);
      expect(history[0].recordType).to.equal("loan");
      expect(history[0].scoreImpact).to.equal(5);
    });
    it("should not allow unauthorized providers to add credit records", async function () {
      await expect(
        creditScore
          .connect(provider2)
          .addCreditRecord(user1.address, 1000, "loan", 5),
      ).to.be.revertedWith("Only authorized providers can call this function");
    });
    it("should validate score impact range", async function () {
      await expect(
        creditScore
          .connect(provider1)
          .addCreditRecord(user1.address, 1000, "loan", 11),
      ).to.be.revertedWith("Score impact must be between -10 and 10");
      await expect(
        creditScore
          .connect(provider1)
          .addCreditRecord(user1.address, 1000, "loan", -11),
      ).to.be.revertedWith("Score impact must be between -10 and 10");
    });
    it("should allow marking records as repaid", async function () {
      await creditScore
        .connect(provider1)
        .addCreditRecord(user1.address, 1000, "loan", 5);
      await creditScore.connect(provider1).markRepaid(user1.address, 0);
      const history = await creditScore.getCreditHistory(user1.address);
      expect(history[0].repaid).to.equal(true);
      expect(history[0].repaymentTimestamp).to.be.gt(0);
    });
    it("should not allow marking non-existent records", async function () {
      await expect(
        creditScore.connect(provider1).markRepaid(user1.address, 0),
      ).to.be.revertedWith("Record index out of bounds");
    });
    it("should not allow marking already repaid records", async function () {
      await creditScore
        .connect(provider1)
        .addCreditRecord(user1.address, 1000, "loan", 5);
      await creditScore.connect(provider1).markRepaid(user1.address, 0);
      await expect(
        creditScore.connect(provider1).markRepaid(user1.address, 0),
      ).to.be.revertedWith("Record already marked as repaid");
    });
  });
  describe("Credit Scores", function () {
    beforeEach(async function () {
      await creditScore.authorizeProvider(provider1.address);
    });
    it("should initialize new users with a default score", async function () {
      await creditScore
        .connect(provider1)
        .addCreditRecord(user1.address, 1000, "loan", 5);
      const [score, lastUpdated] = await creditScore.getCreditScore(
        user1.address,
      );
      expect(score).to.be.gt(0);
      expect(lastUpdated).to.be.gt(0);
    });
    it("should update scores based on record impact", async function () {
      await creditScore
        .connect(provider1)
        .addCreditRecord(user1.address, 1000, "loan", 5);
      const [initialScore, initialTimestamp] = await creditScore.getCreditScore(
        user1.address,
      );
      await creditScore
        .connect(provider1)
        .addCreditRecord(user1.address, 2000, "loan", -3);
      const [updatedScore, updatedTimestamp] = await creditScore.getCreditScore(
        user1.address,
      );
      expect(updatedScore).to.be.lt(initialScore);
      expect(updatedTimestamp).to.be.gte(initialTimestamp);
    });
    it("should return zero for users with no credit profile", async function () {
      const [score, lastUpdated] = await creditScore.getCreditScore(
        user2.address,
      );
      expect(score).to.equal(0);
      expect(lastUpdated).to.equal(0);
    });
    it("should keep scores within valid range (300-850)", async function () {
      for (let i = 0; i < 20; i++) {
        await creditScore
          .connect(provider1)
          .addCreditRecord(user1.address, 1000, "loan", 10);
      }
      const [highScore] = await creditScore.getCreditScore(user1.address);
      expect(highScore).to.be.lte(850);
      for (let i = 0; i < 20; i++) {
        await creditScore
          .connect(provider1)
          .addCreditRecord(user2.address, 1000, "loan", -10);
      }
      const [lowScore] = await creditScore.getCreditScore(user2.address);
      expect(lowScore).to.be.gte(300);
    });
  });
});
