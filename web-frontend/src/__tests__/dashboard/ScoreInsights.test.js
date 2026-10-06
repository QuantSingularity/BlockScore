import { render, screen } from "@testing-library/react";
import ScoreInsights from "../../components/dashboard/ScoreInsights";
describe("ScoreInsights", () => {
  it("renders nothing without scoring metadata", () => {
    const { container } = render(<ScoreInsights creditData={null} />);
    expect(container).toBeEmptyDOMElement();
    const { container: legacy } = render(
      <ScoreInsights creditData={{ score: 650 }} />,
    );
    expect(legacy).toBeEmptyDOMElement();
  });
  it("shows model source, confidence and insights for AI scores", () => {
    render(
      <ScoreInsights
        creditData={{
          scoring_source: "ai_model",
          confidence: 0.85,
          model_name: "blockscore-xgboost",
          model_version: "2.0.0",
          insights: {
            positive: [
              {
                factor: "Excellent payment history",
                description: "Consistently repaying obligations",
              },
            ],
            negative: [{ factor: "High outstanding debt", description: "" }],
          },
        }}
      />,
    );
    expect(screen.getByText("AI model")).toBeInTheDocument();
    expect(screen.getByText("Confidence 85%")).toBeInTheDocument();
    expect(screen.getByText("blockscore-xgboost v2.0.0")).toBeInTheDocument();
    expect(screen.getByText("Excellent payment history")).toBeInTheDocument();
    expect(screen.getByText("High outstanding debt")).toBeInTheDocument();
    expect(screen.getByText("Helping your score")).toBeInTheDocument();
    expect(screen.getByText("Hurting your score")).toBeInTheDocument();
  });
  it("explains the rule-based fallback", () => {
    render(
      <ScoreInsights
        creditData={{ scoring_source: "rule_based", confidence: 0.7 }}
      />,
    );
    expect(screen.getByText("Rule-based engine")).toBeInTheDocument();
    expect(
      screen.getByText(/built-in multi-factor rules/i),
    ).toBeInTheDocument();
    expect(screen.queryByText("Helping your score")).not.toBeInTheDocument();
  });
  it("clamps out-of-range confidence", () => {
    render(
      <ScoreInsights
        creditData={{ scoring_source: "ai_model", confidence: 4 }}
      />,
    );
    expect(screen.getByText("Confidence 100%")).toBeInTheDocument();
  });
});
