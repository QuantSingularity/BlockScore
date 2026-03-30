/**
 * Loan Service
 * Handles loan operations and calculations
 */

import { API_CONFIG } from "../config/api.config";
import httpClient from "./http.client";

export interface Loan {
  loanId: number;
  borrower: string;
  amount: number;
  interestRate: number;
  durationDays: number;
  startTime: number;
  isApproved: boolean;
  isRepaid: boolean;
}

export interface LoanCalculation {
  loanAmount: number;
  interestRate: number;
  loanTerm: number; // in months
  monthlyPayment: number;
  totalPayment: number;
  totalInterest: number;
}

/**
 * Get loan details by ID
 */
export const getLoanById = async (loanId: number): Promise<Loan> => {
  try {
    const response = await httpClient.get(
      `${API_CONFIG.ENDPOINTS.LOANS.GET_BY_ID}/${loanId}`,
    );

    if (response.data.success) {
      return response.data.data;
    }

    throw new Error("Failed to get loan details");
  } catch (error: any) {
    throw new Error(
      error.response?.data?.message ||
        "Failed to get loan details. Please try again.",
    );
  }
};

/**
 * Get all loans for a borrower
 */
export const getLoansByBorrower = async (address: string): Promise<Loan[]> => {
  try {
    const response = await httpClient.get(
      `${API_CONFIG.ENDPOINTS.LOANS.GET_BY_BORROWER}/${address}`,
    );

    if (response.data.success) {
      return response.data.data.loans || [];
    }

    throw new Error("Failed to get borrower loans");
  } catch (error: any) {
    // If no loans found, return empty array instead of error
    if (error.response?.status === 404) {
      return [];
    }
    throw new Error(
      error.response?.data?.message ||
        "Failed to get borrower loans. Please try again.",
    );
  }
};

/**
 * Create a new loan
 */
export const createLoan = async (
  amount: number,
  interestRate: number,
  durationDays: number,
  privateKey: string,
): Promise<any> => {
  try {
    const response = await httpClient.post(API_CONFIG.ENDPOINTS.LOANS.CREATE, {
      amount,
      interestRate,
      durationDays,
      privateKey,
    });

    if (response.data.success) {
      return response.data.data;
    }

    throw new Error("Failed to create loan");
  } catch (error: any) {
    throw new Error(
      error.response?.data?.message ||
        "Failed to create loan. Please try again.",
    );
  }
};

/**
 * Calculate loan payment details
 */
export const calculateLoan = (
  loanAmount: number,
  interestRate: number,
  loanTerm: number,
): LoanCalculation => {
  const principal = loanAmount;
  const monthlyRate = interestRate / 100 / 12;
  const numberOfPayments = loanTerm;

  if (principal <= 0 || monthlyRate <= 0 || numberOfPayments <= 0) {
    return {
      loanAmount,
      interestRate,
      loanTerm,
      monthlyPayment: 0,
      totalPayment: 0,
      totalInterest: 0,
    };
  }

  const monthlyPayment =
    (principal * monthlyRate * (1 + monthlyRate) ** numberOfPayments) /
    ((1 + monthlyRate) ** numberOfPayments - 1);

  const totalPayment = monthlyPayment * numberOfPayments;
  const totalInterest = totalPayment - principal;

  return {
    loanAmount,
    interestRate,
    loanTerm,
    monthlyPayment: Number.isNaN(monthlyPayment) ? 0 : monthlyPayment,
    totalPayment: Number.isNaN(totalPayment) ? 0 : totalPayment,
    totalInterest: Number.isNaN(totalInterest) ? 0 : totalInterest,
  };
};

/**
 * Format number with commas
 */
export const formatNumber = (num: number): string => {
  return num.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
};

/**
 * Get loan status text
 */
export const getLoanStatus = (loan: Loan): string => {
  if (loan.isRepaid) return "Repaid";
  if (!loan.isApproved) return "Pending";
  return "Active";
};

/**
 * Get loan status color
 */
export const getLoanStatusColor = (loan: Loan): string => {
  if (loan.isRepaid) return "#50E3C2"; // success
  if (!loan.isApproved) return "#F5A623"; // warning
  return "#4A90E2"; // info
};
