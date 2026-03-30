/**
 * Credit Service
 * Handles credit score and credit history operations
 */

import { API_CONFIG } from "../config/api.config";
import httpClient from "./http.client";

export interface CreditScore {
  score: number;
  address: string;
  lastUpdated?: number;
}

export interface CreditRecord {
  amount: number;
  recordType: string;
  scoreImpact: number;
  timestamp: number;
  isRepaid: boolean;
  provider: string;
}

export interface CreditHistory {
  address: string;
  records: CreditRecord[];
}

/**
 * Get credit score for an address
 */
export const getCreditScore = async (address: string): Promise<CreditScore> => {
  try {
    const response = await httpClient.get(
      `${API_CONFIG.ENDPOINTS.CREDIT.SCORE}/${address}`,
    );

    if (response.data.success) {
      return response.data.data;
    }

    throw new Error("Failed to get credit score");
  } catch (error: any) {
    throw new Error(
      error.response?.data?.message ||
        "Failed to get credit score. Please try again.",
    );
  }
};

/**
 * Get credit history for an address
 */
export const getCreditHistory = async (
  address: string,
): Promise<CreditHistory> => {
  try {
    const response = await httpClient.get(
      `${API_CONFIG.ENDPOINTS.CREDIT.HISTORY}/${address}`,
    );

    if (response.data.success) {
      return response.data.data;
    }

    throw new Error("Failed to get credit history");
  } catch (error: any) {
    throw new Error(
      error.response?.data?.message ||
        "Failed to get credit history. Please try again.",
    );
  }
};

/**
 * Calculate credit score using AI
 */
export const calculateCreditScore = async (
  walletAddress: string,
): Promise<any> => {
  try {
    const response = await httpClient.post(
      API_CONFIG.ENDPOINTS.CREDIT.CALCULATE,
      { walletAddress },
    );

    if (response.data.success) {
      return response.data.data;
    }

    throw new Error("Failed to calculate credit score");
  } catch (error: any) {
    throw new Error(
      error.response?.data?.message ||
        "Failed to calculate credit score. Please try again.",
    );
  }
};

/**
 * Get score factors analysis
 */
export const getScoreFactors = async (address: string): Promise<any[]> => {
  try {
    // This would ideally be a separate endpoint, but for now we can derive it from history
    const history = await getCreditHistory(address);

    // Analyze history to create score factors
    const factors = [
      {
        name: "Payment History",
        impact: "High",
        status: calculatePaymentStatus(history.records),
        icon: "check-circle",
        color: "#50E3C2",
      },
      {
        name: "Credit Utilization",
        impact: "High",
        status: "Good",
        icon: "trending-up",
        color: "#50E3C2",
      },
      {
        name: "Length of Credit History",
        impact: "Medium",
        status: calculateHistoryLength(history.records),
        icon: "history",
        color: "#50E3C2",
      },
      {
        name: "Credit Mix",
        impact: "Low",
        status: "Fair",
        icon: "mix",
        color: "#F5A623",
      },
      {
        name: "New Credit",
        impact: "Low",
        status: "Good",
        icon: "fiber-new",
        color: "#50E3C2",
      },
    ];

    return factors;
  } catch (error) {
    console.error("Error getting score factors:", error);
    return [];
  }
};

/**
 * Helper: Calculate payment history status
 */
const calculatePaymentStatus = (records: CreditRecord[]): string => {
  if (records.length === 0) return "No Data";

  const repaidCount = records.filter((r) => r.isRepaid).length;
  const repaidPercentage = (repaidCount / records.length) * 100;

  if (repaidPercentage >= 90) return "Excellent";
  if (repaidPercentage >= 75) return "Good";
  if (repaidPercentage >= 50) return "Fair";
  return "Needs Improvement";
};

/**
 * Helper: Calculate credit history length status
 */
const calculateHistoryLength = (records: CreditRecord[]): string => {
  if (records.length === 0) return "No Data";

  const now = Date.now() / 1000;
  const oldestRecord = Math.min(...records.map((r) => r.timestamp));
  const ageInYears = (now - oldestRecord) / (365 * 24 * 60 * 60);

  if (ageInYears >= 5) return "Excellent";
  if (ageInYears >= 3) return "Good";
  if (ageInYears >= 1) return "Fair";
  return "Building";
};
