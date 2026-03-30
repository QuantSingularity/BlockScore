import { createContext, useContext, useEffect, useState } from "react";
import {
  calculateCreditScore,
  getCreditHistory,
  getCreditScore,
} from "../utils/api";
import { useAuth } from "./AuthContext";
import { useWeb3 } from "./Web3Context";

// Create context
const CreditContext = createContext();

// Provider component
export const CreditProvider = ({ children }) => {
  const { user } = useAuth();
  const { accounts } = useWeb3();

  const [creditData, setCreditData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchCreditScore = async (walletAddress) => {
    try {
      setLoading(true);
      setError(null);

      // Use provided wallet address or get from context
      const address = walletAddress || accounts[0] || user?.address;

      if (!address) {
        throw new Error("No wallet address available");
      }

      // Try to get credit score from blockchain first
      let data;
      try {
        data = await getCreditScore(address);
      } catch (_apiError) {
        // If blockchain call fails, try calculating with AI
        console.log("Blockchain call failed, trying AI calculation...");
        data = await calculateCreditScore(address);
      }

      // Get credit history
      let history = [];
      try {
        history = await getCreditHistory(address);
      } catch (historyError) {
        console.log("Could not fetch credit history:", historyError.message);
      }

      const creditInfo = {
        address: data.address || address,
        score: data.score || data.calculatedScore || 0,
        features: data.features || {
          total_loans: 0,
          total_amount: 0,
          repaid_ratio: 0,
          avg_loan_amount: 0,
        },
        history: history.length > 0 ? history : data.history || [],
      };

      setCreditData(creditInfo);
      return creditInfo;
    } catch (err) {
      console.error("Error fetching credit score:", err);
      setError("Failed to load credit score data. Using demo data.");

      // For demo purposes, set mock data if API fails
      const mockData = {
        address:
          walletAddress ||
          accounts[0] ||
          user?.address ||
          "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
        score: 720,
        features: {
          total_loans: 5,
          total_amount: 15000,
          repaid_ratio: 0.8,
          avg_loan_amount: 3000,
        },
        history: [
          { timestamp: Date.now() - 7776000000, amount: 1000, repaid: true },
          { timestamp: Date.now() - 5184000000, amount: 2000, repaid: true },
          { timestamp: Date.now() - 2592000000, amount: 3000, repaid: true },
          { timestamp: Date.now() - 1296000000, amount: 4000, repaid: true },
          { timestamp: Date.now() - 604800000, amount: 5000, repaid: false },
        ],
      };

      setCreditData(mockData);
      return mockData;
    } finally {
      setLoading(false);
    }
  };

  // Refresh credit data
  const refreshCreditData = async () => {
    const walletAddress = accounts[0] || user?.address;
    if (walletAddress) {
      return await fetchCreditScore(walletAddress);
    }
  };

  // Fetch credit score on component mount or when wallet/user changes
  useEffect(() => {
    const walletAddress = accounts[0] || user?.address;
    if (walletAddress) {
      fetchCreditScore(walletAddress);
    } else {
      setLoading(false);
    }
  }, [accounts, user, fetchCreditScore]);

  return (
    <CreditContext.Provider
      value={{
        creditData,
        loading,
        error,
        fetchCreditScore,
        refreshCreditData,
      }}
    >
      {children}
    </CreditContext.Provider>
  );
};

// Custom hook to use the credit context
export const useCredit = () => useContext(CreditContext);

export default CreditContext;
