import { ThemeProvider } from "@mui/material";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import App from "./App";
import { AuthProvider } from "./contexts/AuthContext";
import { CreditProvider } from "./contexts/CreditContext";
import { Web3Provider } from "./contexts/Web3Context";
import theme from "./theme";

// Mock contexts
jest.mock("./contexts/AuthContext", () => ({
  AuthProvider: ({ children }) => <div>{children}</div>,
  useAuth: () => ({
    user: { address: "0x123", name: "Test User" },
    isAuthenticated: true,
    loading: false,
  }),
}));

jest.mock("./contexts/Web3Context", () => ({
  Web3Provider: ({ children }) => <div>{children}</div>,
  useWeb3: () => ({
    web3: {},
    accounts: ["0x123"],
    networkId: 1,
    loading: false,
  }),
}));

jest.mock("./contexts/CreditContext", () => ({
  CreditProvider: ({ children }) => <div>{children}</div>,
  useCredit: () => ({
    creditData: { score: 720 },
    loading: false,
    error: null,
  }),
}));

const renderWithProviders = (ui, { route = "/" } = {}) => {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <ThemeProvider theme={theme}>
        <AuthProvider>
          <Web3Provider>
            <CreditProvider>{ui}</CreditProvider>
          </Web3Provider>
        </AuthProvider>
      </ThemeProvider>
    </MemoryRouter>,
  );
};

describe("App Component", () => {
  test("renders without crashing", () => {
    renderWithProviders(<App />);
  });

  test("shows loading screen initially", () => {
    renderWithProviders(<App />);
    // Loading screen should appear briefly
    expect(
      screen.getByText(/Loading BlockScore/i) ||
        screen.queryByRole("progressbar"),
    ).toBeTruthy();
  });

  test("renders landing page on root route", async () => {
    renderWithProviders(<App />, { route: "/" });
    await waitFor(
      () => {
        // Wait for loading to finish
        expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
      },
      { timeout: 2000 },
    );
  });

  test("renders not found page for invalid route", async () => {
    renderWithProviders(<App />, { route: "/invalid-route" });
    await waitFor(
      () => {
        expect(
          screen.queryByText(/404/i) || screen.queryByText(/not found/i),
        ).toBeTruthy();
      },
      { timeout: 2000 },
    );
  });
});
