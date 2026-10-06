const { expect } = require("chai");
const { ethers } = require("hardhat");
async function buildDomain(contract) {
  const network = await ethers.provider.getNetwork();
  return {
    name: "CreditScoreV2",
    version: "1",
    chainId: network.chainId,
    verifyingContract: await contract.getAddress(),
  };
}
const CREDIT_RECORD_TYPES = {
  CreditRecord: [
    { name: "user", type: "address" },
    { name: "amount", type: "uint256" },
    { name: "recordType", type: "string" },
    { name: "scoreImpact", type: "int16" },
    { name: "dataHash", type: "bytes32" },
    { name: "nonce", type: "uint256" },
  ],
};
const REPAYMENT_TYPES = {
  RepaymentRecord: [
    { name: "user", type: "address" },
    { name: "recordIndex", type: "uint256" },
    { name: "nonce", type: "uint256" },
  ],
};
describe("CreditScoreV2", function () {
  let creditScoreV2;
  let admin;
  let provider1;
  let complianceOfficer;
  let user1;
  let user2;
  let CREDIT_PROVIDER_ROLE;
  let COMPLIANCE_OFFICER_ROLE;
  let EMERGENCY_ROLE;
  beforeEach(async function () {
    [admin, provider1, complianceOfficer, user1, user2] =
      await ethers.getSigners();
    const CreditScoreV2 = await ethers.getContractFactory("CreditScoreV2");
    creditScoreV2 = await CreditScoreV2.deploy();
    await creditScoreV2.waitForDeployment();
    CREDIT_PROVIDER_ROLE = await creditScoreV2.CREDIT_PROVIDER_ROLE();
    COMPLIANCE_OFFICER_ROLE = await creditScoreV2.COMPLIANCE_OFFICER_ROLE();
    EMERGENCY_ROLE = await creditScoreV2.EMERGENCY_ROLE();
    await creditScoreV2.grantRole(CREDIT_PROVIDER_ROLE, provider1.address);
  });
  describe("Role-gated record submission (no signature)", function () {
    it("allows a CREDIT_PROVIDER_ROLE holder to add a record without a signature", async function () {
      await creditScoreV2
        .connect(provider1)
        .addCreditRecord(
          user1.address,
          1000,
          "loan",
          5,
          ethers.ZeroHash,
          "{}",
          "0x",
        );
      const history = await creditScoreV2
        .connect(user1)
        .getCreditHistory(user1.address);
      expect(history.length).to.equal(1);
      expect(history[0].amount).to.equal(1000);
      expect(history[0].scoreImpact).to.equal(5);
    });
    it("rejects callers without CREDIT_PROVIDER_ROLE", async function () {
      await expect(
        creditScoreV2
          .connect(user2)
          .addCreditRecord(
            user1.address,
            1000,
            "loan",
            5,
            ethers.ZeroHash,
            "{}",
            "0x",
          ),
      ).to.be.reverted;
    });
    it("enforces the score impact bounds", async function () {
      await expect(
        creditScoreV2
          .connect(provider1)
          .addCreditRecord(
            user1.address,
            1000,
            "loan",
            51,
            ethers.ZeroHash,
            "{}",
            "0x",
          ),
      ).to.be.revertedWithCustomError(creditScoreV2, "InvalidScoreRange");
    });
  });
  describe("EIP-712 signed record submission", function () {
    it("accepts a valid self-signed record from the provider", async function () {
      const domain = await buildDomain(creditScoreV2);
      const value = {
        user: user1.address,
        amount: 2500n,
        recordType: "loan",
        scoreImpact: 7,
        dataHash: ethers.ZeroHash,
        nonce: 0n,
      };
      const signature = await provider1.signTypedData(
        domain,
        CREDIT_RECORD_TYPES,
        value,
      );
      await creditScoreV2
        .connect(provider1)
        .addCreditRecord(
          value.user,
          value.amount,
          value.recordType,
          value.scoreImpact,
          value.dataHash,
          "{}",
          signature,
        );
      const history = await creditScoreV2
        .connect(user1)
        .getCreditHistory(user1.address);
      expect(history.length).to.equal(1);
    });
    it("rejects a record signed by someone other than msg.sender", async function () {
      const domain = await buildDomain(creditScoreV2);
      const value = {
        user: user1.address,
        amount: 2500n,
        recordType: "loan",
        scoreImpact: 7,
        dataHash: ethers.ZeroHash,
        nonce: 0n,
      };
      const signature = await user2.signTypedData(
        domain,
        CREDIT_RECORD_TYPES,
        value,
      );
      await expect(
        creditScoreV2
          .connect(provider1)
          .addCreditRecord(
            value.user,
            value.amount,
            value.recordType,
            value.scoreImpact,
            value.dataHash,
            "{}",
            signature,
          ),
      ).to.be.revertedWithCustomError(creditScoreV2, "InvalidSignature");
    });
  });
  describe("Repayment", function () {
    beforeEach(async function () {
      await creditScoreV2
        .connect(provider1)
        .addCreditRecord(
          user1.address,
          1000,
          "loan",
          5,
          ethers.ZeroHash,
          "{}",
          "0x",
        );
    });
    it("marks a record repaid without a signature and applies a repayment bonus", async function () {
      await creditScoreV2.connect(provider1).markRepaid(user1.address, 0, "0x");
      const history = await creditScoreV2
        .connect(user1)
        .getCreditHistory(user1.address);
      expect(history[0].repaid).to.equal(true);
      expect(history[0].repaymentTimestamp).to.be.gt(0);
    });
    it("only allows the original provider to mark a record repaid", async function () {
      await creditScoreV2.grantRole(CREDIT_PROVIDER_ROLE, user2.address);
      await expect(
        creditScoreV2.connect(user2).markRepaid(user1.address, 0, "0x"),
      ).to.be.revertedWith("Only original provider can mark repaid");
    });
  });
  describe("Compliance controls", function () {
    it("freezes and unfreezes a profile", async function () {
      await creditScoreV2
        .connect(provider1)
        .addCreditRecord(
          user1.address,
          1000,
          "loan",
          5,
          ethers.ZeroHash,
          "{}",
          "0x",
        );
      await creditScoreV2.freezeProfile(user1.address, "AML review");
      await expect(
        creditScoreV2
          .connect(provider1)
          .addCreditRecord(
            user1.address,
            1000,
            "loan",
            5,
            ethers.ZeroHash,
            "{}",
            "0x",
          ),
      ).to.be.revertedWithCustomError(creditScoreV2, "ProfileFrozen");
      await creditScoreV2.unfreezeProfile(user1.address);
      await creditScoreV2
        .connect(provider1)
        .addCreditRecord(
          user1.address,
          1000,
          "loan",
          5,
          ethers.ZeroHash,
          "{}",
          "0x",
        );
      const history = await creditScoreV2
        .connect(user1)
        .getCreditHistory(user1.address);
      expect(history.length).to.equal(2);
    });
    it("flags loan defaults for compliance review", async function () {
      await creditScoreV2
        .connect(provider1)
        .addCreditRecord(
          user1.address,
          1000,
          "loan_default",
          -25,
          ethers.ZeroHash,
          "{}",
          "0x",
        );
      const violations = await creditScoreV2
        .connect(admin)
        .getComplianceViolations(user1.address);
      expect(violations).to.include("LOAN_DEFAULT_RECORDED");
    });
  });
  describe("Emergency controls", function () {
    it("allows EMERGENCY_ROLE to pause and unpause", async function () {
      await creditScoreV2.connect(admin).emergencyPause();
      expect(await creditScoreV2.emergencyMode()).to.equal(true);
      await expect(
        creditScoreV2
          .connect(provider1)
          .addCreditRecord(
            user1.address,
            1000,
            "loan",
            5,
            ethers.ZeroHash,
            "{}",
            "0x",
          ),
      ).to.be.reverted;
      await creditScoreV2.connect(admin).emergencyUnpause();
      expect(await creditScoreV2.emergencyMode()).to.equal(false);
      await creditScoreV2
        .connect(provider1)
        .addCreditRecord(
          user1.address,
          1000,
          "loan",
          5,
          ethers.ZeroHash,
          "{}",
          "0x",
        );
    });
  });
  describe("Disputes", function () {
    it("lets a user dispute a record and a compliance officer resolve it", async function () {
      await creditScoreV2
        .connect(provider1)
        .addCreditRecord(
          user1.address,
          1000,
          "loan",
          5,
          ethers.ZeroHash,
          "{}",
          "0x",
        );
      await creditScoreV2.connect(user1).disputeRecord(0, "Not my loan");
      await expect(
        creditScoreV2.connect(admin).resolveDispute(1, true, "Confirmed error"),
      )
        .to.emit(creditScoreV2, "DisputeResolved")
        .withArgs(1, admin.address, true, "Confirmed error");
    });
  });
});
