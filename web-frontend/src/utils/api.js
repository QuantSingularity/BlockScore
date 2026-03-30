// API service for making backend requests
import axios from "axios";

// Get API URL from environment or use default
const getApiUrl = () => {
  if (process.env.REACT_APP_API_URL) {
    return process.env.REACT_APP_API_URL;
  }
  // Fallback to proxy in development, absolute URL in production
  return process.env.NODE_ENV === "production"
    ? "/api"
    : "http://localhost:5000/api";
};

// Create axios instance with default config
const api = axios.create({
  baseURL: getApiUrl(),
  timeout: parseInt(process.env.REACT_APP_API_TIMEOUT, 10) || 10000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor for adding auth tokens
api.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem("authToken");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  },
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // Server responded with error
      console.error("API Error:", error.response.status, error.response.data);
    } else if (error.request) {
      // Request made but no response
      console.error("Network Error:", error.message);
    } else {
      // Something else happened
      console.error("Error:", error.message);
    }
    return Promise.reject(error);
  },
);

// Credit score API calls
export const getCreditScore = async (walletAddress) => {
  try {
    const response = await api.get(`/credit/score/${walletAddress}`);
    return response.data.data || response.data;
  } catch (error) {
    console.error("Error fetching credit score:", error);
    throw error;
  }
};

// Get credit history
export const getCreditHistory = async (walletAddress) => {
  try {
    const response = await api.get(`/credit/history/${walletAddress}`);
    return response.data.data || response.data;
  } catch (error) {
    console.error("Error fetching credit history:", error);
    throw error;
  }
};

// Calculate credit score using AI model
export const calculateCreditScore = async (walletAddress) => {
  try {
    const response = await api.post("/credit/calculate-score", {
      walletAddress,
    });
    return response.data.data || response.data;
  } catch (error) {
    console.error("Error calculating credit score:", error);
    throw error;
  }
};

// Loan calculation API calls
export const calculateLoan = async (walletAddress, amount, rate, term = 36) => {
  try {
    const response = await api.post("/loans/calculate", {
      walletAddress,
      amount,
      rate,
      term,
    });
    return response.data.data || response.data;
  } catch (error) {
    console.error("Error calculating loan:", error);
    throw error;
  }
};

// Apply for loan
export const applyForLoan = async (walletAddress, amount, term) => {
  try {
    const response = await api.post("/loans/apply", {
      walletAddress,
      amount,
      term,
    });
    return response.data.data || response.data;
  } catch (error) {
    console.error("Error applying for loan:", error);
    throw error;
  }
};

// Health check
export const checkApiHealth = async () => {
  try {
    const response = await api.get("/health");
    return response.data;
  } catch (error) {
    console.error("API health check failed:", error);
    throw error;
  }
};

// Authentication API calls
export const login = async (walletAddress, signature) => {
  try {
    const response = await api.post("/auth/login", {
      walletAddress,
      signature,
    });
    if (response.data.token) {
      localStorage.setItem("authToken", response.data.token);
    }
    return response.data;
  } catch (error) {
    console.error("Login error:", error);
    throw error;
  }
};

export const logout = () => {
  localStorage.removeItem("authToken");
};

export default api;
