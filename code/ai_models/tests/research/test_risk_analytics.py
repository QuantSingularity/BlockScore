import numpy as np
import pandas as pd
import pytest
from blockscore_ai.research.risk_analytics import RiskAnalytics


@pytest.fixture()
def analyzer():
    rng = np.random.default_rng(0)
    instance = RiskAnalytics()
    instance.load_portfolio_data(
        pd.DataFrame(
            {
                "asset_id": [f"A{i}" for i in range(30)],
                "position_size": rng.uniform(1, 10, 30),
                "market_value": rng.uniform(100, 1000, 30),
                "asset_class": rng.choice(["Equity", "Fixed Income"], 30),
                "sector": rng.choice(["Tech", "Energy", "Health"], 30),
                "country": rng.choice(["US", "EU"], 30),
            }
        )
    )
    instance.load_credit_data(
        pd.DataFrame(
            {
                "loan_amount": rng.uniform(1000, 5000, 200),
                "credit_score": rng.normal(650, 80, 200),
                "exposure_type": rng.choice(["corporate", "retail", "sovereign"], 200),
                "sector": rng.choice(["Tech", "Energy"], 200),
            }
        )
    )
    return instance


def test_concentration_includes_geography(analyzer):
    result = analyzer.analyze_concentration_risk(analyzer.portfolio_data)
    assert result["geographic_hhi"] is not None
    assert set(result["geographic_concentration"]) == {"US", "EU"}
    assert 0 < result["position_hhi"] <= 1


def test_concentration_rejects_empty_value():
    frame = pd.DataFrame({"market_value": [0.0], "sector": ["x"], "asset_class": ["y"]})
    with pytest.raises(ValueError):
        RiskAnalytics().analyze_concentration_risk(frame)


def test_credit_metrics_use_loan_amount(analyzer):
    metrics = analyzer.calculate_credit_risk_metrics(analyzer.credit_data)
    assert metrics["total_exposure"] == pytest.approx(
        analyzer.credit_data["loan_amount"].sum()
    )
    assert 0 < metrics["probability_of_default"] < 1
    assert metrics["credit_var_99"] >= metrics["expected_loss"]


def test_pd_estimate_uses_absolute_score_scale():
    analyzer = RiskAnalytics()
    low = analyzer._estimate_pd_from_score(pd.Series([400.0, 410.0]))
    high = analyzer._estimate_pd_from_score(pd.Series([800.0, 810.0]))
    constant = analyzer._estimate_pd_from_score(pd.Series([650.0, 650.0]))
    assert low > high
    assert np.isfinite(constant)


def test_regulatory_capital_is_nonzero(analyzer):
    capital = analyzer.calculate_regulatory_capital(analyzer.credit_data)
    assert capital["total_rwa"] > 0
    assert capital["total_capital_requirement"] > capital["minimum_capital"]


def test_stress_testing_scales_with_multiplier(analyzer):
    results = analyzer.perform_stress_testing(
        {"mild": {"pd_multiplier": 1.5}, "severe": {"pd_multiplier": 3.0}}
    )
    assert (
        results["severe"]["results"]["credit_loss_change"]
        > results["mild"]["results"]["credit_loss_change"]
        > 0
    )


def test_var_methods_agree_in_sign():
    returns = pd.Series(np.random.default_rng(1).normal(0.0005, 0.02, 2000))
    analyzer = RiskAnalytics()
    for method in ("historical", "parametric", "monte_carlo"):
        assert analyzer.calculate_var(returns, 0.95, method) < 0
    with pytest.raises(ValueError):
        analyzer.calculate_var(returns, 0.95, "unknown")


def test_beta_alignment_handles_mismatched_lengths():
    rng = np.random.default_rng(2)
    portfolio = pd.DataFrame({"portfolio": rng.normal(0, 0.01, 300)})
    benchmark = pd.Series(rng.normal(0, 0.01, 250))
    metrics = RiskAnalytics().calculate_portfolio_risk_metrics(portfolio, benchmark)
    assert metrics.beta is not None


def test_report_export(analyzer, tmp_path):
    path = tmp_path / "report.json"
    analyzer.export_risk_report(str(path))
    assert path.exists()
