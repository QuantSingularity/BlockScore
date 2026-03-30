/**
 * Credit Slice
 * Redux slice for credit score and history management
 */

import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import type { CreditHistory, CreditScore } from "../../services/credit.service";
import * as creditService from "../../services/credit.service";

export interface CreditState {
  score: CreditScore | null;
  history: CreditHistory | null;
  scoreFactors: any[];
  isLoading: boolean;
  error: string | null;
}

const initialState: CreditState = {
  score: null,
  history: null,
  scoreFactors: [],
  isLoading: false,
  error: null,
};

/**
 * Async thunk for fetching credit score
 */
export const fetchCreditScore = createAsyncThunk(
  "credit/fetchScore",
  async (address: string, { rejectWithValue }) => {
    try {
      const score = await creditService.getCreditScore(address);
      return score;
    } catch (error: any) {
      return rejectWithValue(error.message);
    }
  },
);

/**
 * Async thunk for fetching credit history
 */
export const fetchCreditHistory = createAsyncThunk(
  "credit/fetchHistory",
  async (address: string, { rejectWithValue }) => {
    try {
      const history = await creditService.getCreditHistory(address);
      return history;
    } catch (error: any) {
      return rejectWithValue(error.message);
    }
  },
);

/**
 * Async thunk for fetching score factors
 */
export const fetchScoreFactors = createAsyncThunk(
  "credit/fetchFactors",
  async (address: string, { rejectWithValue }) => {
    try {
      const factors = await creditService.getScoreFactors(address);
      return factors;
    } catch (error: any) {
      return rejectWithValue(error.message);
    }
  },
);

/**
 * Async thunk for calculating credit score
 */
export const calculateScore = createAsyncThunk(
  "credit/calculate",
  async (walletAddress: string, { rejectWithValue }) => {
    try {
      const result = await creditService.calculateCreditScore(walletAddress);
      return result;
    } catch (error: any) {
      return rejectWithValue(error.message);
    }
  },
);

/**
 * Credit slice
 */
const creditSlice = createSlice({
  name: "credit",
  initialState,
  reducers: {
    clearCreditError: (state) => {
      state.error = null;
    },
    resetCredit: (state) => {
      state.score = null;
      state.history = null;
      state.scoreFactors = [];
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    // Fetch credit score
    builder.addCase(fetchCreditScore.pending, (state) => {
      state.isLoading = true;
      state.error = null;
    });
    builder.addCase(fetchCreditScore.fulfilled, (state, action) => {
      state.isLoading = false;
      state.score = action.payload;
      state.error = null;
    });
    builder.addCase(fetchCreditScore.rejected, (state, action) => {
      state.isLoading = false;
      state.error = action.payload as string;
    });

    // Fetch credit history
    builder.addCase(fetchCreditHistory.pending, (state) => {
      state.isLoading = true;
      state.error = null;
    });
    builder.addCase(fetchCreditHistory.fulfilled, (state, action) => {
      state.isLoading = false;
      state.history = action.payload;
      state.error = null;
    });
    builder.addCase(fetchCreditHistory.rejected, (state, action) => {
      state.isLoading = false;
      state.error = action.payload as string;
    });

    // Fetch score factors
    builder.addCase(fetchScoreFactors.pending, (state) => {
      state.isLoading = true;
      state.error = null;
    });
    builder.addCase(fetchScoreFactors.fulfilled, (state, action) => {
      state.isLoading = false;
      state.scoreFactors = action.payload;
      state.error = null;
    });
    builder.addCase(fetchScoreFactors.rejected, (state, action) => {
      state.isLoading = false;
      state.error = action.payload as string;
    });

    // Calculate score
    builder.addCase(calculateScore.pending, (state) => {
      state.isLoading = true;
      state.error = null;
    });
    builder.addCase(calculateScore.fulfilled, (state, action) => {
      state.isLoading = false;
      if (action.payload.calculatedScore !== undefined) {
        state.score = {
          score: action.payload.calculatedScore,
          address: action.payload.address,
        };
      }
      state.error = null;
    });
    builder.addCase(calculateScore.rejected, (state, action) => {
      state.isLoading = false;
      state.error = action.payload as string;
    });
  },
});

export const { clearCreditError, resetCredit } = creditSlice.actions;
export default creditSlice.reducer;
