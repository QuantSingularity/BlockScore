/**
 * Loan Slice
 * Redux slice for loan management
 */

import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import type { Loan, LoanCalculation } from "../../services/loan.service";
import * as loanService from "../../services/loan.service";

export interface LoanState {
  loans: Loan[];
  currentLoan: Loan | null;
  calculation: LoanCalculation | null;
  isLoading: boolean;
  error: string | null;
}

const initialState: LoanState = {
  loans: [],
  currentLoan: null,
  calculation: null,
  isLoading: false,
  error: null,
};

/**
 * Async thunk for fetching loans by borrower
 */
export const fetchBorrowerLoans = createAsyncThunk(
  "loan/fetchBorrowerLoans",
  async (address: string, { rejectWithValue }) => {
    try {
      const loans = await loanService.getLoansByBorrower(address);
      return loans;
    } catch (error: any) {
      return rejectWithValue(error.message);
    }
  },
);

/**
 * Async thunk for fetching loan by ID
 */
export const fetchLoanById = createAsyncThunk(
  "loan/fetchById",
  async (loanId: number, { rejectWithValue }) => {
    try {
      const loan = await loanService.getLoanById(loanId);
      return loan;
    } catch (error: any) {
      return rejectWithValue(error.message);
    }
  },
);

/**
 * Async thunk for creating a loan
 */
export const createNewLoan = createAsyncThunk(
  "loan/create",
  async (
    loanData: {
      amount: number;
      interestRate: number;
      durationDays: number;
      privateKey: string;
    },
    { rejectWithValue },
  ) => {
    try {
      const result = await loanService.createLoan(
        loanData.amount,
        loanData.interestRate,
        loanData.durationDays,
        loanData.privateKey,
      );
      return result;
    } catch (error: any) {
      return rejectWithValue(error.message);
    }
  },
);

/**
 * Loan slice
 */
const loanSlice = createSlice({
  name: "loan",
  initialState,
  reducers: {
    clearLoanError: (state) => {
      state.error = null;
    },
    resetLoans: (state) => {
      state.loans = [];
      state.currentLoan = null;
      state.calculation = null;
      state.error = null;
    },
    setLoanCalculation: (state, action) => {
      state.calculation = action.payload;
    },
  },
  extraReducers: (builder) => {
    // Fetch borrower loans
    builder.addCase(fetchBorrowerLoans.pending, (state) => {
      state.isLoading = true;
      state.error = null;
    });
    builder.addCase(fetchBorrowerLoans.fulfilled, (state, action) => {
      state.isLoading = false;
      state.loans = action.payload;
      state.error = null;
    });
    builder.addCase(fetchBorrowerLoans.rejected, (state, action) => {
      state.isLoading = false;
      state.error = action.payload as string;
    });

    // Fetch loan by ID
    builder.addCase(fetchLoanById.pending, (state) => {
      state.isLoading = true;
      state.error = null;
    });
    builder.addCase(fetchLoanById.fulfilled, (state, action) => {
      state.isLoading = false;
      state.currentLoan = action.payload;
      state.error = null;
    });
    builder.addCase(fetchLoanById.rejected, (state, action) => {
      state.isLoading = false;
      state.error = action.payload as string;
    });

    // Create loan
    builder.addCase(createNewLoan.pending, (state) => {
      state.isLoading = true;
      state.error = null;
    });
    builder.addCase(createNewLoan.fulfilled, (state) => {
      state.isLoading = false;
      state.error = null;
    });
    builder.addCase(createNewLoan.rejected, (state, action) => {
      state.isLoading = false;
      state.error = action.payload as string;
    });
  },
});

export const { clearLoanError, resetLoans, setLoanCalculation } =
  loanSlice.actions;
export default loanSlice.reducer;
