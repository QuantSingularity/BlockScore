const { expect } = require("chai");
const { ethers } = require("hardhat");
describe("LoanContract", function () {
  let creditScore;
  let loanContract;
  let owner;
  let borrower;
  let other;
  beforeEach(async function () {
    [owner, borrower, other] = await ethers.getSigners();
    const CreditScore = await ethers.getContractFactory("CreditScore");
    creditScore = await CreditScore.deploy();
    await creditScore.waitForDeployment();
    const LoanContract = await ethers.getContractFactory("LoanContract");
    loanContract = await LoanContract.deploy(await creditScore.getAddress());
    await loanContract.waitForDeployment();
    await creditScore.authorizeProvider(await loanContract.getAddress());
  });
  it("should create a loan request", async function () {
    await loanContract.connect(borrower).createLoan(5000, 500, 30);
    const loan = await loanContract.getLoanDetails(0);
    expect(loan.borrower).to.equal(borrower.address);
    expect(loan.amount).to.equal(5000);
    expect(loan.interestRate).to.equal(500);
    expect(loan.approved).to.equal(false);
    expect(loan.repaid).to.equal(false);
  });
  it("should reject loans with zero amount or duration", async function () {
    await expect(
      loanContract.connect(borrower).createLoan(0, 500, 30),
    ).to.be.revertedWith("Loan amount must be greater than zero");
    await expect(
      loanContract.connect(borrower).createLoan(5000, 500, 0),
    ).to.be.revertedWith("Loan duration must be greater than zero");
  });
  it("should allow the owner to approve a loan and record a positive credit event", async function () {
    await loanContract.connect(borrower).createLoan(5000, 500, 30);
    await loanContract.approveLoan(0);
    const loan = await loanContract.getLoanDetails(0);
    expect(loan.approved).to.equal(true);
    const history = await creditScore.getCreditHistory(borrower.address);
    expect(history.length).to.equal(1);
    expect(history[0].recordType).to.equal("loan");
    expect(history[0].scoreImpact).to.equal(2);
  });
  it("should not allow non-owners to approve loans", async function () {
    await loanContract.connect(borrower).createLoan(5000, 500, 30);
    await expect(
      loanContract.connect(borrower).approveLoan(0),
    ).to.be.revertedWith("Only owner can call this function");
  });
  it("should not allow approving the same loan twice", async function () {
    await loanContract.connect(borrower).createLoan(5000, 500, 30);
    await loanContract.approveLoan(0);
    await expect(loanContract.approveLoan(0)).to.be.revertedWith(
      "Loan already approved",
    );
  });
  it("should allow the borrower to repay an approved loan on time", async function () {
    await loanContract.connect(borrower).createLoan(5000, 500, 30);
    await loanContract.approveLoan(0);
    await loanContract.connect(borrower).repayLoan(0);
    const loan = await loanContract.getLoanDetails(0);
    expect(loan.repaid).to.equal(true);
    expect(loan.repaymentTimestamp).to.be.gt(0);
    const history = await creditScore.getCreditHistory(borrower.address);
    expect(history.length).to.equal(2);
    expect(history[1].recordType).to.equal("repayment");
    expect(history[1].scoreImpact).to.equal(5);
  });
  it("should not allow repaying a loan that was never approved", async function () {
    await loanContract.connect(borrower).createLoan(5000, 500, 30);
    await expect(
      loanContract.connect(borrower).repayLoan(0),
    ).to.be.revertedWith("Loan not approved");
  });
  it("should not allow an unrelated account to repay someone else's loan", async function () {
    await loanContract.connect(borrower).createLoan(5000, 500, 30);
    await loanContract.approveLoan(0);
    await expect(loanContract.connect(other).repayLoan(0)).to.be.revertedWith(
      "Only borrower or owner can repay",
    );
  });
  it("should list all loans for a borrower", async function () {
    await loanContract.connect(borrower).createLoan(1000, 100, 10);
    await loanContract.connect(borrower).createLoan(2000, 200, 20);
    const loanIds = await loanContract.getBorrowerLoans(borrower.address);
    expect(loanIds.length).to.equal(2);
  });
  it("should read a borrower's credit score through the loan contract", async function () {
    await loanContract.connect(borrower).createLoan(5000, 500, 30);
    await loanContract.approveLoan(0);
    const [score] = await loanContract.getBorrowerCreditScore(borrower.address);
    expect(score).to.be.gt(0);
  });
});
