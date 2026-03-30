/**
 * HTTP Client
 * Axios instance with interceptors for authentication and error handling
 */

import axios, {
  type AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
  type AxiosResponse,
} from "axios";
import { API_CONFIG } from "../config/api.config";
import { clearToken, getToken } from "./storage.service";

/**
 * Create axios instance with default configuration
 */
const httpClient: AxiosInstance = axios.create({
  baseURL: API_CONFIG.BASE_URL,
  timeout: API_CONFIG.TIMEOUT,
  headers: {
    "Content-Type": "application/json",
  },
});

/**
 * Request interceptor to add auth token
 */
httpClient.interceptors.request.use(
  async (config: AxiosRequestConfig) => {
    try {
      const token = await getToken();
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch (error) {
      console.error("Error getting token:", error);
    }
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  },
);

/**
 * Response interceptor for error handling
 */
httpClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError) => {
    if (error.response) {
      // Handle specific HTTP error codes
      switch (error.response.status) {
        case 401:
          // Unauthorized - clear token and redirect to login
          await clearToken();
          // You can dispatch a Redux action here to update auth state
          break;
        case 403:
          // Forbidden
          console.error("Access forbidden");
          break;
        case 404:
          // Not found
          console.error("Resource not found");
          break;
        case 500:
          // Server error
          console.error("Server error");
          break;
        default:
          console.error("HTTP error:", error.response.status);
      }
    } else if (error.request) {
      // Network error
      console.error("Network error:", error.message);
    } else {
      // Other errors
      console.error("Error:", error.message);
    }
    return Promise.reject(error);
  },
);

export default httpClient;
