import { ThemeProvider } from "@mui/material";
import { render, screen } from "@testing-library/react";
import CreditScoreGauge from "../../components/dashboard/CreditScoreGauge";
import theme from "../../theme";

const renderWithTheme = (component) => {
  return render(<ThemeProvider theme={theme}>{component}</ThemeProvider>);
};

describe("CreditScoreGauge Component", () => {
  test("renders credit score correctly", () => {
    renderWithTheme(<CreditScoreGauge score={750} />);
    expect(screen.getByText("750")).toBeInTheDocument();
    expect(screen.getByText("out of 850")).toBeInTheDocument();
  });

  test("displays correct color for excellent score", () => {
    renderWithTheme(<CreditScoreGauge score={800} />);
    const scoreElement = screen.getByText("800");
    expect(scoreElement).toHaveStyle({ color: "#4caf50" }); // Green for excellent
  });

  test("displays correct color for poor score", () => {
    renderWithTheme(<CreditScoreGauge score={550} />);
    const scoreElement = screen.getByText("550");
    expect(scoreElement).toHaveStyle({ color: "#f44336" }); // Red for poor
  });
});
