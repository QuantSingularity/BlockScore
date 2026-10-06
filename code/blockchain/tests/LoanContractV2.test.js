const { expect } = require("chai");
const { ethers } = require("hardhat");
async function creditScoreDomain(contract) {
  const network = await ethers.provider.getNetwork();
  return {
    name: "CreditScoreV2",
    version: "1",
    chainId: network.chainId,
    verifyingContract: await contract.getAddress(),
  };
}
async function loanDomain(contract) {
  const network = await ethers.provider.getNetwork();
  return {
    name: "LoanContractV2",
    version: "1",
    chainId: network.chainId,
    verifyingContract: await contract.getAddress(),
  };
}
const LOAN_APPLICATION_TYPES = {
  LoanApplication: [
    { name: "applicant", type: "address" },
    { name: "amount", type: "uint256" },
    { name: "term", type: "uint256" },
    { name: "income", type: "uint256" },
    { name: "nonce", type: "uint256" },
  ],
};
const ONE_TOKEN = 10n ** 18n;
describe("LoanContractV2", function () {
  let creditScoreV2;
  let loanContractV2;
  let lendingToken;
  let admin;
  let loanOfficer;
  let underwriter;
  let borrower;
  let treasury;
  const LOAN_AMOUNT = 10000n * ONE_TOKEN;
  beforeEach(async function () {
    [admin, loanOfficer, underwriter, borrower, treasury] =
      await ethers.getSigners();
    const CreditScoreV2 = await ethers.getContractFactory("CreditScoreV2");
    creditScoreV2 = await CreditScoreV2.deploy();
    await creditScoreV2.waitForDeployment();
    const MockERC20 = await ethers.getContractFactory("MockERC20");
    lendingToken = await MockERC20.deploy("Lending Token", "LEND");
    await lendingToken.waitForDeployment();
    const LoanContractV2 = await ethers.getContractFactory("LoanContractV2");
    loanContractV2 = await LoanContractV2.deploy(
      await creditScoreV2.getAddress(),
      await lendingToken.getAddress(),
      treasury.address,
    );
    await loanContractV2.waitForDeployment();
    const CREDIT_PROVIDER_ROLE = await creditScoreV2.CREDIT_PROVIDER_ROLE();
    await creditScoreV2.grantRole(
      CREDIT_PROVIDER_ROLE,
      await loanContractV2.getAddress(),
    );
    await creditScoreV2.grantRole(CREDIT_PROVIDER_ROLE, admin.address);
    const LOAN_OFFICER_ROLE = await loanContractV2.LOAN_OFFICER_ROLE();
    const UNDERWRITER_ROLE = await loanContractV2.UNDERWRITER_ROLE();
    await loanContractV2.grantRole(LOAN_OFFICER_ROLE, loanOfficer.address);
    await loanContractV2.grantRole(UNDERWRITER_ROLE, underwriter.address);
    await creditScoreV2
      .connect(admin)
      .addCreditRecord(
        borrower.address,
        0,
        "initial",
        0,
        ethers.ZeroHash,
        "{}",
        "0x",
      );
    const reserve = (LOAN_AMOUNT * 1000n) / 10000n;
    await lendingToken.mint(
      await loanContractV2.getAddress(),
      LOAN_AMOUNT + reserve,
    );
  });
  async function submitApplication({
    amount = LOAN_AMOUNT,
    term = 180,
    income = 100000n * ONE_TOKEN,
    dti = 2000,
  } = {}) {
    const domain = await loanDomain(loanContractV2);
    const value = {
      applicant: borrower.address,
      amount,
      term,
      income,
      nonce: 0n,
    };
    const signature = await borrower.signTypedData(
      domain,
      LOAN_APPLICATION_TYPES,
      value,
    );
    const tx = await loanContractV2
      .connect(borrower)
      .submitLoanApplication(
        amount,
        term,
        "home improvement",
        income,
        dti,
        "employed",
        ethers.ZeroHash,
        signature,
      );
    await tx.wait();
    return 1n;
  }
  it("walks a loan through application, underwriting, funding, and full repayment", async function () {
    const applicationId = await submitApplication();
    await loanContractV2
      .connect(admin)
      .completeComplianceCheck(
        applicationId,
        true,
        true,
        true,
        true,
        true,
        "all clear",
      );
    const underwriteTx = await loanContractV2
      .connect(underwriter)
      .underwriteLoan(
        applicationId,
        LOAN_AMOUNT,
        500,
        180,
        100,
        false,
        0,
        "low risk",
      );
    const underwriteReceipt = await underwriteTx.wait();
    const loanId = 1n;
    let loan = await loanContractV2.connect(borrower).getLoanDetails(loanId);
    expect(loan.status).to.equal(2n);
    await loanContractV2.connect(loanOfficer).fundLoan(loanId);
    loan = await loanContractV2.connect(borrower).getLoanDetails(loanId);
    expect(loan.status).to.equal(3n);
    const originationFee = (LOAN_AMOUNT * 100n) / 10000n;
    const expectedNet = LOAN_AMOUNT - originationFee;
    expect(await lendingToken.balanceOf(borrower.address)).to.equal(
      expectedNet,
    );
    expect(await lendingToken.balanceOf(treasury.address)).to.equal(
      originationFee,
    );
    await lendingToken.mint(borrower.address, LOAN_AMOUNT);
    await lendingToken
      .connect(borrower)
      .approve(await loanContractV2.getAddress(), LOAN_AMOUNT * 2n);
    await loanContractV2
      .connect(borrower)
      .makePayment(loanId, LOAN_AMOUNT, "bank_transfer");
    loan = await loanContractV2.connect(borrower).getLoanDetails(loanId);
    expect(loan.status).to.equal(4n);
    expect(loan.amountRepaid).to.equal(LOAN_AMOUNT);
    const history = await creditScoreV2
      .connect(borrower)
      .getCreditHistory(borrower.address);
    const lastRecord = history[history.length - 1];
    expect(lastRecord.recordType).to.equal("loan_repaid");
    expect(lastRecord.scoreImpact).to.equal(10);
  });
  it("rejects applications below the minimum credit score", async function () {
    const [, , , , , freshApplicant] = await ethers.getSigners();
    const domain = await loanDomain(loanContractV2);
    const value = {
      applicant: freshApplicant.address,
      amount: LOAN_AMOUNT,
      term: 180,
      income: 100000n * ONE_TOKEN,
      nonce: 0n,
    };
    const signature = await freshApplicant.signTypedData(
      domain,
      LOAN_APPLICATION_TYPES,
      value,
    );
    await expect(
      loanContractV2
        .connect(freshApplicant)
        .submitLoanApplication(
          LOAN_AMOUNT,
          180,
          "purpose",
          value.income,
          2000,
          "employed",
          ethers.ZeroHash,
          signature,
        ),
    ).to.be.revertedWithCustomError(loanContractV2, "InsufficientCreditScore");
  });
  it("rejects loan amounts outside the configured bounds", async function () {
    const domain = await loanDomain(loanContractV2);
    const value = {
      applicant: borrower.address,
      amount: 1n,
      term: 180,
      income: 100000n * ONE_TOKEN,
      nonce: 0n,
    };
    const signature = await borrower.signTypedData(
      domain,
      LOAN_APPLICATION_TYPES,
      value,
    );
    await expect(
      loanContractV2
        .connect(borrower)
        .submitLoanApplication(
          1n,
          180,
          "purpose",
          value.income,
          2000,
          "employed",
          ethers.ZeroHash,
          signature,
        ),
    ).to.be.revertedWithCustomError(loanContractV2, "LoanAmountOutOfRange");
  });
  it("requires collateral to be deposited before funding a collateralized loan", async function () {
    const applicationId = await submitApplication();
    await loanContractV2
      .connect(admin)
      .completeComplianceCheck(
        applicationId,
        true,
        true,
        true,
        true,
        true,
        "ok",
      );
    await loanContractV2
      .connect(underwriter)
      .underwriteLoan(
        applicationId,
        LOAN_AMOUNT,
        500,
        180,
        100,
        true,
        LOAN_AMOUNT / 2n,
        "medium risk",
      );
    const loanId = 1n;
    await expect(
      loanContractV2.connect(loanOfficer).fundLoan(loanId),
    ).to.be.revertedWith("Collateral not deposited");
    const MockERC20 = await ethers.getContractFactory("MockERC20");
    const collateralToken = await MockERC20.deploy("Collateral", "COLL");
    await collateralToken.waitForDeployment();
    await collateralToken.mint(borrower.address, LOAN_AMOUNT);
    await collateralToken
      .connect(borrower)
      .approve(await loanContractV2.getAddress(), LOAN_AMOUNT);
    await loanContractV2
      .connect(borrower)
      .depositCollateral(
        loanId,
        LOAN_AMOUNT / 2n,
        await collateralToken.getAddress(),
      );
    await loanContractV2.connect(loanOfficer).fundLoan(loanId);
    const loan = await loanContractV2.connect(borrower).getLoanDetails(loanId);
    expect(loan.status).to.equal(3n);
  });
  it("reports aggregate contract statistics", async function () {
    const applicationId = await submitApplication();
    await loanContractV2
      .connect(admin)
      .completeComplianceCheck(
        applicationId,
        true,
        true,
        true,
        true,
        true,
        "ok",
      );
    await loanContractV2
      .connect(underwriter)
      .underwriteLoan(applicationId, LOAN_AMOUNT, 500, 180, 100, false, 0, "");
    await loanContractV2.connect(loanOfficer).fundLoan(1n);
    const stats = await loanContractV2.getContractStats();
    expect(stats.totalLoans).to.equal(1n);
    expect(stats.totalApplications).to.equal(1n);
    expect(stats._totalLent).to.equal(LOAN_AMOUNT);
    expect(stats.activeLoans).to.equal(1n);
  });
});
