/**
 * Authentication Service
 * Handles user authentication, registration, and wallet management
 */

import { API_CONFIG } from "../config/api.config";
import httpClient from "./http.client";
import {
  clearAll,
  saveToken,
  saveUser,
  saveWalletAddress,
} from "./storage.service";

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  success: boolean;
  data: {
    token: string;
    user: {
      username: string;
      role: string;
      walletAddress?: string;
    };
  };
}

export interface RegisterResponse {
  success: boolean;
  data: {
    username: string;
    role: string;
  };
}

/**
 * Login user
 */
export const login = async (
  credentials: LoginRequest,
): Promise<LoginResponse> => {
  try {
    const response = await httpClient.post<LoginResponse>(
      API_CONFIG.ENDPOINTS.AUTH.LOGIN,
      credentials,
    );

    if (response.data.success && response.data.data) {
      // Save token and user data
      await saveToken(response.data.data.token);
      await saveUser(response.data.data.user);
      if (response.data.data.user.walletAddress) {
        await saveWalletAddress(response.data.data.user.walletAddress);
      }
    }

    return response.data;
  } catch (error: any) {
    throw new Error(
      error.response?.data?.message || "Failed to login. Please try again.",
    );
  }
};

/**
 * Register new user
 */
export const register = async (
  userData: RegisterRequest,
): Promise<RegisterResponse> => {
  try {
    const response = await httpClient.post<RegisterResponse>(
      API_CONFIG.ENDPOINTS.AUTH.REGISTER,
      userData,
    );

    return response.data;
  } catch (error: any) {
    throw new Error(
      error.response?.data?.message || "Failed to register. Please try again.",
    );
  }
};

/**
 * Update wallet address
 */
export const updateWalletAddress = async (
  walletAddress: string,
): Promise<any> => {
  try {
    const response = await httpClient.post(API_CONFIG.ENDPOINTS.AUTH.WALLET, {
      walletAddress,
    });

    if (response.data.success) {
      await saveWalletAddress(walletAddress);
    }

    return response.data;
  } catch (error: any) {
    throw new Error(
      error.response?.data?.message ||
        "Failed to update wallet address. Please try again.",
    );
  }
};

/**
 * Logout user
 */
export const logout = async (): Promise<void> => {
  try {
    await clearAll();
  } catch (error) {
    console.error("Error during logout:", error);
    throw error;
  }
};
