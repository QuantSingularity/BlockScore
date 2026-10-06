import { API_CONFIG } from "../config/api.config";
import httpClient from "./http.client";
export interface ScoreBreakdown {
  total_score?: number;
  payment_history?: number;
  credit_utilization?: number;
  length_of_history?: number;
  credit_mix?: number;
  new_credit?: number;
  income_stability?: number;
  debt_to_income?: number;
  blockchain_activity?: number;
}
export interface CreditFactor {
  factor_type: string;
  factor_name: string;
  factor_description?: string;
  normalized_value: number;
  contribution: number;
  impact?: string;
}
export type ScoringSource = "ai_model" | "rule_based" | "unknown";
export interface ScoreInsight {
  factor: string;
  impact: string;
  description?: string;
}
export interface ScoreInsights {
  positive: ScoreInsight[];
  negative: ScoreInsight[];
}
export interface CreditScoreResult {
  credit_score_id: string;
  score: number;
  score_grade: string;
  model_version: string;
  model_name?: string;
  calculated_at: string;
  expires_at: string;
  is_valid: boolean;
  score_breakdown: ScoreBreakdown;
  confidence: number | null;
  scoring_source?: ScoringSource;
  insights?: ScoreInsights;
  factors?: CreditFactor[];
}
export interface ScoringSummary {
  source: ScoringSource;
  sourceLabel: string;
  confidencePercent: number | null;
  modelLabel: string | null;
  positive: ScoreInsight[];
  negative: ScoreInsight[];
}
export interface CreditHistoryEvent {
  id: string;
  event_type: string;
  event_title: string;
  event_description?: string;
  amount?: number | null;
  currency?: string;
  score_before?: number;
  score_after?: number;
  score_change?: number;
  transaction_id?: string;
  event_date: string;
}
export interface CreditHistoryResult {
  history: CreditHistoryEvent[];
  pagination: {
    page: number;
    per_page: number;
    total: number;
    pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}
export const getCreditScore = async (
  walletAddress?: string,
): Promise<CreditScoreResult> => {
  try {
    const response = await httpClient.post<{
      success: boolean;
      data: CreditScoreResult;
    }>(API_CONFIG.ENDPOINTS.CREDIT.CALCULATE, {
      walletAddress,
      force_recalculation: false,
    });
    return response.data.data;
  } catch (error: any) {
    throw new Error(
      error.response?.data?.message || "Failed to fetch credit score.",
    );
  }
};
export const calculateCreditScore = async (
  walletAddress?: string,
): Promise<CreditScoreResult> => {
  try {
    const response = await httpClient.post<{
      success: boolean;
      data: CreditScoreResult;
    }>(API_CONFIG.ENDPOINTS.CREDIT.CALCULATE, {
      walletAddress,
      force_recalculation: true,
    });
    return response.data.data;
  } catch (error: any) {
    throw new Error(
      error.response?.data?.message || "Failed to calculate credit score.",
    );
  }
};
export const getCreditHistory = async (
  page = 1,
  perPage = 20,
): Promise<CreditHistoryResult> => {
  try {
    const response = await httpClient.get<{
      success: boolean;
      data: CreditHistoryResult;
    }>(API_CONFIG.ENDPOINTS.CREDIT.HISTORY, {
      params: { page, per_page: perPage },
    });
    return response.data.data;
  } catch (error: any) {
    throw new Error(
      error.response?.data?.message || "Failed to fetch credit history.",
    );
  }
};
export const getScoreFactors = (
  result: CreditScoreResult | null,
): {
  name: string;
  value: number;
  description?: string;
}[] => {
  if (!result) {
    return [];
  }
  if (result.factors?.length) {
    return result.factors.map((factor) => ({
      name: factor.factor_name,
      value: Math.round(factor.contribution),
      description: factor.factor_description,
    }));
  }
  const breakdown = result.score_breakdown || {};
  const labels: Record<string, string> = {
    payment_history: "Payment History",
    credit_utilization: "Credit Utilization",
    length_of_history: "Length of History",
    credit_mix: "Credit Mix",
    new_credit: "New Credit",
    income_stability: "Income Stability",
    debt_to_income: "Debt to Income",
    blockchain_activity: "Blockchain Activity",
  };
  return Object.entries(labels)
    .filter(([key]) => breakdown[key as keyof ScoreBreakdown] !== undefined)
    .map(([key, name]) => ({
      name,
      value: Math.round(breakdown[key as keyof ScoreBreakdown] as number),
    }));
};
const SOURCE_LABELS: Record<ScoringSource, string> = {
  ai_model: "AI model",
  rule_based: "Rule-based engine",
  unknown: "Unknown",
};
export const getScoringSummary = (
  result: CreditScoreResult | null,
): ScoringSummary | null => {
  if (!result) {
    return null;
  }
  const source: ScoringSource = result.scoring_source ?? "unknown";
  const confidence =
    typeof result.confidence === "number" && Number.isFinite(result.confidence)
      ? Math.round(Math.min(1, Math.max(0, result.confidence)) * 100)
      : null;
  const modelLabel =
    source === "ai_model" && result.model_name
      ? `${result.model_name} v${result.model_version || "?"}`
      : null;
  return {
    source,
    sourceLabel: SOURCE_LABELS[source] ?? SOURCE_LABELS.unknown,
    confidencePercent: confidence,
    modelLabel,
    positive: result.insights?.positive ?? [],
    negative: result.insights?.negative ?? [],
  };
};
