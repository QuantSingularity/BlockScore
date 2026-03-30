import { CssBaseline, ThemeProvider } from "@mui/material";
import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { AuthProvider } from "./contexts/AuthContext";
import { CreditProvider } from "./contexts/CreditContext";
import { Web3Provider } from "./contexts/Web3Context";
import theme from "./theme";
import "./index.css";

const container = document.getElementById("root");
const root = createRoot(container);

root.render(
  <React.StrictMode>
    <BrowserRouter>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <AuthProvider>
          <Web3Provider>
            <CreditProvider>
              <App />
            </CreditProvider>
          </Web3Provider>
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
