import { createContext, useContext, useEffect, useState } from "react";

// Create context
const AuthContext = createContext();

// Provider component
export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is logged in
    const checkAuth = async () => {
      try {
        // For demo purposes, we'll simulate a logged-in user
        const demoUser = {
          address: "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
          name: "Demo User",
          balance: "2.5 ETH",
        };

        setUser(demoUser);
        setIsAuthenticated(true);
        setLoading(false);
      } catch (error) {
        console.error("Authentication error:", error);
        setUser(null);
        setIsAuthenticated(false);
        setLoading(false);
      }
    };

    checkAuth();
  }, []);

  // Login function
  const login = async (address) => {
    try {
      setLoading(true);
      // In a real app, we would verify the wallet signature here

      const user = {
        address,
        name: "Demo User",
        balance: "2.5 ETH",
      };

      setUser(user);
      setIsAuthenticated(true);
      return true;
    } catch (error) {
      console.error("Login error:", error);
      return false;
    } finally {
      setLoading(false);
    }
  };

  // Logout function
  const logout = () => {
    setUser(null);
    setIsAuthenticated(false);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated,
        loading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

// Custom hook to use the auth context
export const useAuth = () => useContext(AuthContext);
