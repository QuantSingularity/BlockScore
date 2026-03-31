"""
Risk Analytics Module for Financial Institutions
Comprehensive risk assessment, portfolio analysis, and regulatory reporting
"""

import logging
import warnings
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import scipy.stats as stats
from scipy.stats import norm

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RiskType(Enum):
    """Risk type enumeration"""

    CREDIT = "credit"
    MARKET = "market"
    OPERATIONAL = "operational"
    LIQUIDITY = "liquidity"
    CONCENTRATION = "concentration"
    REGULATORY = "regulatory"


class RiskLevel(Enum):
    """Risk level enumeration"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskMetrics:
    """Risk metrics container"""

    var_95: float
    var_99: float
    expected_shortfall_95: float
    expected_shortfall_99: float
    maximum_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    volatility: float
    skewness: float
    kurtosis: float
    beta: float = None
    alpha: float = None


@dataclass
class PortfolioRisk:
    """Portfolio risk assessment"""

    total_exposure: float
    diversification_ratio: float
    concentration_risk: float
    sector_concentration: Dict[str, float]
    geographic_concentration: Dict[str, float]
    correlation_risk: float
    liquidity_risk: float
    credit_risk: float


class RiskAnalytics:
    """
    Comprehensive risk analytics for financial institutions
    """

    def __init__(self) -> None:
        self.risk_models = {}
        self.portfolio_data = None
        self.market_data = None
        self.credit_data = None
        self.risk_factors = {}
        self.stress_scenarios = {}
        self.confidence_levels = [0.95, 0.99, 0.999]
        self.time_horizons = [1, 5, 10, 22, 252]
        self.lookback_periods = [252, 504, 1260]
        self.basel_parameters = {
            "risk_weight_corporate": 1.0,
            "risk_weight_retail": 0.75,
            "risk_weight_sovereign": 0.0,
            "capital_conservation_buffer": 0.025,
            "countercyclical_buffer": 0.0,
            "systemic_buffer": 0.0,
        }

    def load_portfolio_data(self, portfolio_df: pd.DataFrame) -> None:
        """Load portfolio data for risk analysis"""
        self.portfolio_data = portfolio_df.copy()
        logger.info(f"Loaded portfolio data with {len(portfolio_df)} positions")
        required_cols = [
            "asset_id",
            "position_size",
            "market_value",
            "asset_class",
            "sector",
        ]
        missing_cols = [col for col in required_cols if col not in portfolio_df.columns]
        if missing_cols:
            logger.warning(f"Missing required columns: {missing_cols}")

    def load_market_data(self, market_df: pd.DataFrame) -> None:
        """Load market data for risk calculations"""
        self.market_data = market_df.copy()
        logger.info(f"Loaded market data with {len(market_df)} observations")
        if "returns" not in market_df.columns and "price" in market_df.columns:
            self.market_data["returns"] = market_df["price"].pct_change()

    def load_credit_data(self, credit_df: pd.DataFrame) -> None:
        """Load credit data for credit risk analysis"""
        self.credit_data = credit_df.copy()
        logger.info(f"Loaded credit data with {len(credit_df)} borrowers")

    def calculate_var(
        self,
        returns: pd.Series,
        confidence_level: float = 0.95,
        method: str = "historical",
    ) -> float:
        """
        Calculate Value at Risk (VaR) using different methods
        """
        if method == "historical":
            return self._historical_var(returns, confidence_level)
        elif method == "parametric":
            return self._parametric_var(returns, confidence_level)
        elif method == "monte_carlo":
            return self._monte_carlo_var(returns, confidence_level)
        else:
            raise ValueError(f"Unknown VaR method: {method}")

    def _historical_var(self, returns: pd.Series, confidence_level: float) -> float:
        """Calculate historical VaR"""
        return np.percentile(returns.dropna(), (1 - confidence_level) * 100)

    def _parametric_var(self, returns: pd.Series, confidence_level: float) -> float:
        """Calculate parametric VaR assuming normal distribution"""
        mean_return = returns.mean()
        std_return = returns.std()
        z_score = norm.ppf(1 - confidence_level)
        return mean_return + z_score * std_return

    def _monte_carlo_var(
        self, returns: pd.Series, confidence_level: float, n_simulations: int = 10000
    ) -> float:
        """Calculate Monte Carlo VaR"""
        mean_return = returns.mean()
        std_return = returns.std()
        simulated_returns = np.random.normal(mean_return, std_return, n_simulations)
        return np.percentile(simulated_returns, (1 - confidence_level) * 100)

    def calculate_expected_shortfall(
        self, returns: pd.Series, confidence_level: float = 0.95
    ) -> float:
        """Calculate Expected Shortfall (Conditional VaR)"""
        var = self._historical_var(returns, confidence_level)
        return returns[returns <= var].mean()

    def calculate_portfolio_risk_metrics(
        self, returns: pd.DataFrame, benchmark_returns: pd.Series = None
    ) -> RiskMetrics:
        """Calculate comprehensive risk metrics for portfolio"""
        if "portfolio" not in returns.columns:
            portfolio_returns = returns.mean(axis=1)
        else:
            portfolio_returns = returns["portfolio"]
        var_95 = self.calculate_var(portfolio_returns, 0.95)
        var_99 = self.calculate_var(portfolio_returns, 0.99)
        es_95 = self.calculate_expected_shortfall(portfolio_returns, 0.95)
        es_99 = self.calculate_expected_shortfall(portfolio_returns, 0.99)
        cumulative_returns = (1 + portfolio_returns).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = drawdown.min()
        volatility = portfolio_returns.std() * np.sqrt(252)
        mean_return = portfolio_returns.mean() * 252
        risk_free_rate = 0.02
        sharpe_ratio = (mean_return - risk_free_rate) / volatility
        downside_returns = portfolio_returns[portfolio_returns < 0]
        downside_deviation = downside_returns.std() * np.sqrt(252)
        sortino_ratio = (
            (mean_return - risk_free_rate) / downside_deviation
            if downside_deviation > 0
            else np.inf
        )
        calmar_ratio = mean_return / abs(max_drawdown) if max_drawdown != 0 else np.inf
        skewness = portfolio_returns.skew()
        kurtosis = portfolio_returns.kurtosis()
        beta, alpha = (None, None)
        if benchmark_returns is not None:
            covariance = np.cov(portfolio_returns.dropna(), benchmark_returns.dropna())[
                0, 1
            ]
            benchmark_variance = benchmark_returns.var()
            beta = covariance / benchmark_variance
            alpha = mean_return - beta * (benchmark_returns.mean() * 252)
        return RiskMetrics(
            var_95=var_95,
            var_99=var_99,
            expected_shortfall_95=es_95,
            expected_shortfall_99=es_99,
            maximum_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            volatility=volatility,
            skewness=skewness,
            kurtosis=kurtosis,
            beta=beta,
            alpha=alpha,
        )

    def analyze_concentration_risk(self, portfolio_df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze concentration risk in portfolio"""
        total_value = portfolio_df["market_value"].sum()
        position_weights = portfolio_df["market_value"] / total_value
        hhi = (position_weights**2).sum()
        top_10_concentration = position_weights.nlargest(10).sum()
        sector_concentration = (
            portfolio_df.groupby("sector")["market_value"].sum() / total_value
        )
        sector_hhi = (sector_concentration**2).sum()
        geographic_concentration = {}
        if "country" in portfolio_df.columns:
            geographic_concentration = (
                portfolio_df.groupby("country")["market_value"].sum() / total_value
            )
            geo_hhi = (geographic_concentration**2).sum()
        else:
            geo_hhi = None
        asset_class_concentration = (
            portfolio_df.groupby("asset_class")["market_value"].sum() / total_value
        )
        asset_class_hhi = (asset_class_concentration**2).sum()
        return {
            "position_hhi": hhi,
            "sector_hhi": sector_hhi,
            "asset_class_hhi": asset_class_hhi,
            "geographic_hhi": geo_hhi,
            "top_10_concentration": top_10_concentration,
            "largest_position": position_weights.max(),
            "sector_concentration": sector_concentration.to_dict(),
            "asset_class_concentration": asset_class_concentration.to_dict(),
            "geographic_concentration": (
                geographic_concentration.to_dict() if geographic_concentration else {}
            ),
        }

    def calculate_credit_risk_metrics(self, credit_df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate credit risk metrics"""
        if "default_flag" in credit_df.columns:
            overall_pd = credit_df["default_flag"].mean()
        elif "credit_score" in credit_df.columns:
            overall_pd = self._estimate_pd_from_score(credit_df["credit_score"])
        else:
            overall_pd = 0.02
        if "recovery_rate" in credit_df.columns:
            lgd = 1 - credit_df["recovery_rate"].mean()
        else:
            lgd = 0.45
        if "exposure" in credit_df.columns:
            total_exposure = credit_df["exposure"].sum()
            avg_exposure = credit_df["exposure"].mean()
        else:
            total_exposure = (
                credit_df["loan_amount"].sum()
                if "loan_amount" in credit_df.columns
                else 0
            )
            avg_exposure = (
                credit_df["loan_amount"].mean()
                if "loan_amount" in credit_df.columns
                else 0
            )
        expected_loss = overall_pd * lgd * total_exposure
        credit_var_99 = self._calculate_credit_var(
            overall_pd, lgd, total_exposure, 0.99
        )
        credit_metrics = {
            "total_exposure": total_exposure,
            "average_exposure": avg_exposure,
            "probability_of_default": overall_pd,
            "loss_given_default": lgd,
            "expected_loss": expected_loss,
            "expected_loss_rate": (
                expected_loss / total_exposure if total_exposure > 0 else 0
            ),
            "credit_var_99": credit_var_99,
            "unexpected_loss": credit_var_99 - expected_loss,
        }
        if "rating" in credit_df.columns:
            rating_distribution = (
                credit_df["rating"].value_counts(normalize=True).to_dict()
            )
            credit_metrics["rating_distribution"] = rating_distribution
        if "sector" in credit_df.columns:
            sector_exposure = credit_df.groupby("sector")[
                "exposure" if "exposure" in credit_df.columns else "loan_amount"
            ].sum()
            sector_exposure_pct = sector_exposure / sector_exposure.sum()
            credit_metrics["sector_exposure"] = sector_exposure_pct.to_dict()
        return credit_metrics

    def _estimate_pd_from_score(self, credit_scores: pd.Series) -> float:
        """Estimate PD from credit scores using logistic transformation"""
        min_score, max_score = (credit_scores.min(), credit_scores.max())
        normalized_scores = (credit_scores - min_score) / (max_score - min_score)
        pd_estimates = 1 / (1 + np.exp(10 * (normalized_scores - 0.5)))
        return pd_estimates.mean()

    def _calculate_credit_var(
        self, pd: float, lgd: float, exposure: float, confidence_level: float
    ) -> float:
        """Calculate Credit VaR using single-factor model"""
        correlation = 0.12 * (1 - np.exp(-50 * pd)) / (1 - np.exp(-50)) + 0.24 * (
            1 - (1 - np.exp(-50 * pd)) / (1 - np.exp(-50))
        )
        z_alpha = norm.ppf(confidence_level)
        conditional_pd = norm.cdf(
            (norm.ppf(pd) + np.sqrt(correlation) * z_alpha) / np.sqrt(1 - correlation)
        )
        credit_var = conditional_pd * lgd * exposure
        return credit_var

    def perform_stress_testing(
        self, scenarios: Dict[str, Dict[str, float]]
    ) -> Dict[str, Any]:
        """Perform stress testing on portfolio"""
        stress_results = {}
        for scenario_name, scenario_params in scenarios.items():
            logger.info(f"Running stress test: {scenario_name}")
            scenario_result = {
                "scenario_name": scenario_name,
                "parameters": scenario_params,
                "results": {},
            }
            if "market_shock" in scenario_params:
                market_shock = scenario_params["market_shock"]
                stressed_portfolio_value = self._apply_market_stress(market_shock)
                scenario_result["results"][
                    "portfolio_value_change"
                ] = stressed_portfolio_value
            if "pd_multiplier" in scenario_params:
                pd_multiplier = scenario_params["pd_multiplier"]
                stressed_credit_loss = self._apply_credit_stress(pd_multiplier)
                scenario_result["results"]["credit_loss_change"] = stressed_credit_loss
            if "interest_rate_shock" in scenario_params:
                ir_shock = scenario_params["interest_rate_shock"]
                duration_impact = self._apply_interest_rate_stress(ir_shock)
                scenario_result["results"]["duration_impact"] = duration_impact
            stress_results[scenario_name] = scenario_result
        return stress_results

    def _apply_market_stress(self, market_shock: float) -> float:
        """Apply market stress scenario"""
        if self.portfolio_data is None:
            return 0.0
        current_value = self.portfolio_data["market_value"].sum()
        stressed_value = current_value * (1 + market_shock)
        return stressed_value - current_value

    def _apply_credit_stress(self, pd_multiplier: float) -> float:
        """Apply credit stress scenario"""
        if self.credit_data is None:
            return 0.0
        base_pd = 0.02
        stressed_pd = base_pd * pd_multiplier
        lgd = 0.45
        total_exposure = (
            self.credit_data["loan_amount"].sum()
            if "loan_amount" in self.credit_data.columns
            else 0
        )
        base_el = base_pd * lgd * total_exposure
        stressed_el = stressed_pd * lgd * total_exposure
        return stressed_el - base_el

    def _apply_interest_rate_stress(self, ir_shock: float) -> float:
        """Apply interest rate stress scenario"""
        if self.portfolio_data is None:
            return 0.0
        avg_duration = 5.0
        fixed_income_value = (
            self.portfolio_data[self.portfolio_data["asset_class"] == "Fixed Income"][
                "market_value"
            ].sum()
            if "asset_class" in self.portfolio_data.columns
            else 0
        )
        duration_impact = -avg_duration * ir_shock * fixed_income_value
        return duration_impact

    def calculate_regulatory_capital(self, credit_df: pd.DataFrame) -> Dict[str, float]:
        """Calculate regulatory capital requirements (Basel III)"""
        rwa_corporate = 0
        rwa_retail = 0
        rwa_sovereign = 0
        if "exposure_type" in credit_df.columns and "exposure" in credit_df.columns:
            corporate_exposure = credit_df[credit_df["exposure_type"] == "corporate"][
                "exposure"
            ].sum()
            retail_exposure = credit_df[credit_df["exposure_type"] == "retail"][
                "exposure"
            ].sum()
            sovereign_exposure = credit_df[credit_df["exposure_type"] == "sovereign"][
                "exposure"
            ].sum()
            rwa_corporate = (
                corporate_exposure * self.basel_parameters["risk_weight_corporate"]
            )
            rwa_retail = retail_exposure * self.basel_parameters["risk_weight_retail"]
            rwa_sovereign = (
                sovereign_exposure * self.basel_parameters["risk_weight_sovereign"]
            )
        total_rwa = rwa_corporate + rwa_retail + rwa_sovereign
        minimum_capital_ratio = 0.08
        minimum_capital = total_rwa * minimum_capital_ratio
        conservation_buffer = (
            total_rwa * self.basel_parameters["capital_conservation_buffer"]
        )
        countercyclical_buffer = (
            total_rwa * self.basel_parameters["countercyclical_buffer"]
        )
        systemic_buffer = total_rwa * self.basel_parameters["systemic_buffer"]
        total_capital_requirement = (
            minimum_capital
            + conservation_buffer
            + countercyclical_buffer
            + systemic_buffer
        )
        return {
            "total_rwa": total_rwa,
            "rwa_corporate": rwa_corporate,
            "rwa_retail": rwa_retail,
            "rwa_sovereign": rwa_sovereign,
            "minimum_capital": minimum_capital,
            "conservation_buffer": conservation_buffer,
            "countercyclical_buffer": countercyclical_buffer,
            "systemic_buffer": systemic_buffer,
            "total_capital_requirement": total_capital_requirement,
            "capital_ratio_required": (
                total_capital_requirement / total_rwa if total_rwa > 0 else 0
            ),
        }

    def detect_risk_anomalies(self, returns_df: pd.DataFrame) -> Dict[str, Any]:
        """Detect anomalies in risk patterns"""
        anomalies = {}
        for column in returns_df.select_dtypes(include=[np.number]).columns:
            series = returns_df[column].dropna()
            z_scores = np.abs(stats.zscore(series))
            z_anomalies = series[z_scores > 3].index.tolist()
            Q1 = series.quantile(0.25)
            Q3 = series.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            iqr_anomalies = series[
                (series < lower_bound) | (series > upper_bound)
            ].index.tolist()
            anomalies[column] = {
                "z_score_anomalies": z_anomalies,
                "iqr_anomalies": iqr_anomalies,
                "anomaly_count": len(set(z_anomalies + iqr_anomalies)),
            }
        try:
            from sklearn.ensemble import IsolationForest

            numeric_data = returns_df.select_dtypes(include=[np.number]).fillna(0)
            if len(numeric_data.columns) > 1:
                iso_forest = IsolationForest(contamination=0.1, random_state=42)
                anomaly_labels = iso_forest.fit_predict(numeric_data)
                anomaly_indices = numeric_data.index[anomaly_labels == -1].tolist()
                anomalies["multivariate"] = {
                    "anomaly_indices": anomaly_indices,
                    "anomaly_count": len(anomaly_indices),
                    "anomaly_scores": iso_forest.decision_function(
                        numeric_data
                    ).tolist(),
                }
        except ImportError:
            logger.warning(
                "Scikit-learn not available for multivariate anomaly detection"
            )
        return anomalies

    def generate_risk_dashboard_data(self) -> Dict[str, Any]:
        """Generate data for risk dashboard"""
        dashboard_data = {
            "timestamp": datetime.now().isoformat(),
            "summary_metrics": {},
            "risk_breakdown": {},
            "alerts": [],
            "trends": {},
        }
        if self.portfolio_data is not None:
            total_value = self.portfolio_data["market_value"].sum()
            position_count = len(self.portfolio_data)
            dashboard_data["summary_metrics"] = {
                "total_portfolio_value": total_value,
                "position_count": position_count,
                "average_position_size": (
                    total_value / position_count if position_count > 0 else 0
                ),
            }
            concentration_metrics = self.analyze_concentration_risk(self.portfolio_data)
            dashboard_data["risk_breakdown"]["concentration"] = concentration_metrics
        if self.credit_data is not None:
            credit_metrics = self.calculate_credit_risk_metrics(self.credit_data)
            dashboard_data["risk_breakdown"]["credit"] = credit_metrics
            regulatory_capital = self.calculate_regulatory_capital(self.credit_data)
            dashboard_data["risk_breakdown"]["regulatory"] = regulatory_capital
        if self.market_data is not None:
            market_metrics = self.calculate_portfolio_risk_metrics(
                self.market_data[["returns"]]
                if "returns" in self.market_data.columns
                else pd.DataFrame()
            )
            dashboard_data["risk_breakdown"]["market"] = {
                "var_95": market_metrics.var_95,
                "var_99": market_metrics.var_99,
                "expected_shortfall_95": market_metrics.expected_shortfall_95,
                "volatility": market_metrics.volatility,
                "sharpe_ratio": market_metrics.sharpe_ratio,
            }
        dashboard_data["alerts"] = self._generate_risk_alerts()
        return dashboard_data

    def _generate_risk_alerts(self) -> List[Dict[str, Any]]:
        """Generate risk alerts based on thresholds"""
        alerts = []
        if self.portfolio_data is not None:
            concentration = self.analyze_concentration_risk(self.portfolio_data)
            if concentration["top_10_concentration"] > 0.5:
                alerts.append(
                    {
                        "type": "concentration",
                        "severity": "high",
                        "message": f"Top 10 positions represent {concentration['top_10_concentration']:.1%} of portfolio",
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            if concentration["largest_position"] > 0.1:
                alerts.append(
                    {
                        "type": "concentration",
                        "severity": "medium",
                        "message": f"Largest position represents {concentration['largest_position']:.1%} of portfolio",
                        "timestamp": datetime.now().isoformat(),
                    }
                )
        if self.credit_data is not None:
            credit_metrics = self.calculate_credit_risk_metrics(self.credit_data)
            if credit_metrics["expected_loss_rate"] > 0.05:
                alerts.append(
                    {
                        "type": "credit",
                        "severity": "high",
                        "message": f"Expected loss rate is {credit_metrics['expected_loss_rate']:.2%}",
                        "timestamp": datetime.now().isoformat(),
                    }
                )
        return alerts

    def export_risk_report(self, output_path: str) -> Any:
        """Export comprehensive risk report"""
        report_data = {
            "report_date": datetime.now().isoformat(),
            "executive_summary": {},
            "detailed_analysis": {},
            "regulatory_compliance": {},
            "recommendations": [],
        }
        if self.portfolio_data is not None:
            report_data["detailed_analysis"]["concentration"] = (
                self.analyze_concentration_risk(self.portfolio_data)
            )
        if self.credit_data is not None:
            report_data["detailed_analysis"]["credit"] = (
                self.calculate_credit_risk_metrics(self.credit_data)
            )
            report_data["regulatory_compliance"]["basel_iii"] = (
                self.calculate_regulatory_capital(self.credit_data)
            )
        if self.market_data is not None:
            market_metrics = self.calculate_portfolio_risk_metrics(
                self.market_data[["returns"]]
                if "returns" in self.market_data.columns
                else pd.DataFrame()
            )
            report_data["detailed_analysis"]["market"] = {
                "var_95": market_metrics.var_95,
                "var_99": market_metrics.var_99,
                "expected_shortfall_95": market_metrics.expected_shortfall_95,
                "expected_shortfall_99": market_metrics.expected_shortfall_99,
                "maximum_drawdown": market_metrics.maximum_drawdown,
                "sharpe_ratio": market_metrics.sharpe_ratio,
                "volatility": market_metrics.volatility,
            }
        report_data["recommendations"] = self._generate_recommendations()
        import json

        with open(output_path, "w") as f:
            json.dump(report_data, f, indent=2, default=str)
        logger.info(f"Risk report exported to {output_path}")

    def _generate_recommendations(self) -> List[str]:
        """Generate risk management recommendations"""
        recommendations = []
        if self.portfolio_data is not None:
            concentration = self.analyze_concentration_risk(self.portfolio_data)
            if concentration["top_10_concentration"] > 0.4:
                recommendations.append(
                    "Consider diversifying portfolio to reduce concentration risk"
                )
            if concentration["sector_hhi"] > 0.25:
                recommendations.append(
                    "Reduce sector concentration to improve diversification"
                )
        if self.credit_data is not None:
            credit_metrics = self.calculate_credit_risk_metrics(self.credit_data)
            if credit_metrics["expected_loss_rate"] > 0.03:
                recommendations.append(
                    "Review credit underwriting standards to reduce expected losses"
                )
        return recommendations


def main() -> Any:
    """Example usage of RiskAnalytics"""
    risk_analyzer = RiskAnalytics()
    np.random.seed(42)
    portfolio_data = pd.DataFrame(
        {
            "asset_id": [f"ASSET_{i:03d}" for i in range(100)],
            "position_size": np.random.uniform(1000, 100000, 100),
            "market_value": np.random.uniform(50000, 5000000, 100),
            "asset_class": np.random.choice(
                ["Equity", "Fixed Income", "Alternatives"], 100
            ),
            "sector": np.random.choice(
                ["Technology", "Healthcare", "Finance", "Energy", "Consumer"], 100
            ),
            "country": np.random.choice(["US", "EU", "Asia", "Other"], 100),
        }
    )
    dates = pd.date_range("2020-01-01", "2023-12-31", freq="D")
    market_data = pd.DataFrame(
        {"date": dates, "returns": np.random.normal(0.0005, 0.02, len(dates))}
    )
    credit_data = pd.DataFrame(
        {
            "borrower_id": [f"BORROWER_{i:04d}" for i in range(1000)],
            "loan_amount": np.random.uniform(10000, 1000000, 1000),
            "credit_score": np.random.normal(650, 100, 1000),
            "exposure_type": np.random.choice(
                ["corporate", "retail", "sovereign"], 1000, p=[0.6, 0.35, 0.05]
            ),
            "sector": np.random.choice(
                ["Technology", "Healthcare", "Finance", "Energy", "Consumer"], 1000
            ),
            "rating": np.random.choice(
                ["AAA", "AA", "A", "BBB", "BB", "B", "CCC"],
                1000,
                p=[0.05, 0.1, 0.2, 0.3, 0.2, 0.1, 0.05],
            ),
        }
    )
    risk_analyzer.load_portfolio_data(portfolio_data)
    risk_analyzer.load_market_data(market_data)
    risk_analyzer.load_credit_data(credit_data)
    logger.info("Performing comprehensive risk analysis...")
    market_metrics = risk_analyzer.calculate_portfolio_risk_metrics(
        market_data[["returns"]]
    )
    logger.info(f"Portfolio VaR (95%): {market_metrics.var_95:.4f}")
    logger.info(f"Portfolio Sharpe Ratio: {market_metrics.sharpe_ratio:.2f}")
    concentration_metrics = risk_analyzer.analyze_concentration_risk(portfolio_data)
    logger.info(f"Portfolio HHI: {concentration_metrics['position_hhi']:.4f}")
    logger.info(
        f"Top 10 concentration: {concentration_metrics['top_10_concentration']:.2%}"
    )
    credit_metrics = risk_analyzer.calculate_credit_risk_metrics(credit_data)
    logger.info(f"Expected Loss Rate: {credit_metrics['expected_loss_rate']:.2%}")
    logger.info(f"Credit VaR (99%): {credit_metrics['credit_var_99']:,.0f}")
    regulatory_capital = risk_analyzer.calculate_regulatory_capital(credit_data)
    logger.info(f"Total RWA: {regulatory_capital['total_rwa']:,.0f}")
    logger.info(
        f"Capital Requirement: {regulatory_capital['total_capital_requirement']:,.0f}"
    )
    stress_scenarios = {
        "market_crash": {"market_shock": -0.3, "pd_multiplier": 2.0},
        "interest_rate_shock": {"interest_rate_shock": 0.02, "pd_multiplier": 1.5},
        "credit_crisis": {"pd_multiplier": 3.0, "market_shock": -0.2},
    }
    risk_analyzer.perform_stress_testing(stress_scenarios)
    logger.info("Stress testing completed")
    dashboard_data = risk_analyzer.generate_risk_dashboard_data()
    logger.info(f"Generated dashboard with {len(dashboard_data['alerts'])} alerts")
    risk_analyzer.export_risk_report("risk_report.json")
    logger.info("Risk analysis completed successfully!")


if __name__ == "__main__":
    main()
