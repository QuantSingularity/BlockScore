/**
 * Auth Slice
 * Redux slice for authentication state management
 */

import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import * as authService from "../../services/auth.service";
import {
  getToken,
  getUser,
  getWalletAddress,
} from "../../services/storage.service";

export interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  user: {
    username: string;
    role: string;
    walletAddress?: string;
  } | null;
  token: string | null;
}

const initialState: AuthState = {
  isAuthenticated: false,
  isLoading: false,
  error: null,
  user: null,
  token: null,
};

/**
 * Async thunk for login
 */
export const loginUser = createAsyncThunk(
  "auth/login",
  async (
    credentials: { username: string; password: string },
    { rejectWithValue },
  ) => {
    try {
      const response = await authService.login(credentials);
      return response.data;
    } catch (error: any) {
      return rejectWithValue(error.message);
    }
  },
);

/**
 * Async thunk for registration
 */
export const registerUser = createAsyncThunk(
  "auth/register",
  async (
    userData: { username: string; password: string },
    { rejectWithValue },
  ) => {
    try {
      const response = await authService.register(userData);
      return response.data;
    } catch (error: any) {
      return rejectWithValue(error.message);
    }
  },
);

/**
 * Async thunk for logout
 */
export const logoutUser = createAsyncThunk("auth/logout", async () => {
  await authService.logout();
});

/**
 * Async thunk for checking stored auth
 */
export const checkStoredAuth = createAsyncThunk(
  "auth/checkStored",
  async () => {
    const [user, token, walletAddress] = await Promise.all([
      getUser(),
      getToken(),
      getWalletAddress(),
    ]);

    if (user && token) {
      return {
        user: { ...user, walletAddress: walletAddress || undefined },
        token,
      };
    }

    return null;
  },
);

/**
 * Async thunk for updating wallet address
 */
export const updateWallet = createAsyncThunk(
  "auth/updateWallet",
  async (walletAddress: string, { rejectWithValue }) => {
    try {
      await authService.updateWalletAddress(walletAddress);
      return walletAddress;
    } catch (error: any) {
      return rejectWithValue(error.message);
    }
  },
);

/**
 * Auth slice
 */
const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    // Login
    builder.addCase(loginUser.pending, (state) => {
      state.isLoading = true;
      state.error = null;
    });
    builder.addCase(loginUser.fulfilled, (state, action) => {
      state.isLoading = false;
      state.isAuthenticated = true;
      state.user = action.payload.user;
      state.token = action.payload.token;
      state.error = null;
    });
    builder.addCase(loginUser.rejected, (state, action) => {
      state.isLoading = false;
      state.error = action.payload as string;
    });

    // Register
    builder.addCase(registerUser.pending, (state) => {
      state.isLoading = true;
      state.error = null;
    });
    builder.addCase(registerUser.fulfilled, (state) => {
      state.isLoading = false;
      state.error = null;
    });
    builder.addCase(registerUser.rejected, (state, action) => {
      state.isLoading = false;
      state.error = action.payload as string;
    });

    // Logout
    builder.addCase(logoutUser.fulfilled, (state) => {
      state.isAuthenticated = false;
      state.user = null;
      state.token = null;
      state.error = null;
    });

    // Check stored auth
    builder.addCase(checkStoredAuth.fulfilled, (state, action) => {
      if (action.payload) {
        state.isAuthenticated = true;
        state.user = action.payload.user;
        state.token = action.payload.token;
      }
    });

    // Update wallet
    builder.addCase(updateWallet.fulfilled, (state, action) => {
      if (state.user) {
        state.user.walletAddress = action.payload;
      }
    });
    builder.addCase(updateWallet.rejected, (state, action) => {
      state.error = action.payload as string;
    });
  },
});

export const { clearError } = authSlice.actions;
export default authSlice.reducer;
