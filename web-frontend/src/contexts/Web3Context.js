import { createContext, useContext, useEffect, useState } from "react";
import Web3 from "web3";

// Create context
const Web3Context = createContext();

// Provider component
export const Web3Provider = ({ children }) => {
  const [web3, setWeb3] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [networkId, setNetworkId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const initWeb3 = async () => {
      try {
        // Modern dapp browsers
        if (window.ethereum) {
          const web3Instance = new Web3(window.ethereum);
          setWeb3(web3Instance);

          try {
            // Request account access if needed
            await window.ethereum.request({ method: "eth_requestAccounts" });

            // Get accounts
            const accs = await web3Instance.eth.getAccounts();
            setAccounts(accs);

            // Get network ID
            const netId = await web3Instance.eth.net.getId();
            setNetworkId(netId);

            // Listen for account changes
            window.ethereum.on("accountsChanged", (newAccounts) => {
              setAccounts(newAccounts);
            });

            // Listen for chain changes
            window.ethereum.on("chainChanged", () => {
              window.location.reload();
            });
          } catch (_error) {
            // User denied account access
            console.error("User denied account access");
            setError("Please connect your wallet to use this application");
          }
        }
        // Legacy dapp browsers
        else if (window.web3) {
          const web3Instance = new Web3(window.web3.currentProvider);
          setWeb3(web3Instance);

          // Get accounts
          const accs = await web3Instance.eth.getAccounts();
          setAccounts(accs);

          // Get network ID
          const netId = await web3Instance.eth.net.getId();
          setNetworkId(netId);
        }
        // Fallback - use local provider
        else {
          // For demo purposes, we'll use a mock provider
          const web3Instance = new Web3("http://localhost:8545");
          setWeb3(web3Instance);
          setError(
            "No Ethereum browser extension detected. Using read-only mode.",
          );
        }
      } catch (error) {
        console.error("Error initializing web3:", error);
        setError("Failed to connect to blockchain network");
      } finally {
        setLoading(false);
      }
    };

    initWeb3();
  }, []);

  // Connect to contract
  const connectToContract = (contractABI, contractAddress) => {
    if (!web3) return null;
    return new web3.eth.Contract(contractABI, contractAddress);
  };

  return (
    <Web3Context.Provider
      value={{
        web3,
        accounts,
        networkId,
        loading,
        error,
        connectToContract,
      }}
    >
      {children}
    </Web3Context.Provider>
  );
};

// Custom hook to use the web3 context
export const useWeb3 = () => useContext(Web3Context);
