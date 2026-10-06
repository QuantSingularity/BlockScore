import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from blockscore_ai.config import ARTIFACTS_DIR
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.inspection import permutation_importance
from sklearn.linear_model import ElasticNet
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.preprocessing import RobustScaler

try:
    import shap
except ImportError:
    shap = None

logger = logging.getLogger(__name__)

PROTECTED_ATTRIBUTES = ["gender", "race"]
APPROVAL_THRESHOLD = 670
DISPARATE_IMPACT_FLOOR = 0.8
WINSOR_LOWER = 0.01
WINSOR_UPPER = 0.99
WINSOR_MIN_UNIQUE = 20


@dataclass
class ModelConfig:
    model_type: str = "ensemble"
    target_variable: str = "credit_score"
    test_size: float = 0.2
    validation_size: float = 0.2
    random_state: int = 42
    cv_folds: int = 3
    xgb_params: Optional[Dict[str, Any]] = None
    rf_params: Optional[Dict[str, Any]] = None
    gb_params: Optional[Dict[str, Any]] = None
    feature_selection: bool = True
    feature_selection_k: int = 20
    polynomial_features: bool = False
    interaction_features: bool = True
    fairness_constraints: bool = True
    explainability_required: bool = True
    model_monitoring: bool = True
    protected_attributes: List[str] = field(
        default_factory=lambda: list(PROTECTED_ATTRIBUTES)
    )

    def __post_init__(self) -> None:
        if self.xgb_params is None:
            self.xgb_params = {
                "n_estimators": 200,
                "learning_rate": 0.1,
                "max_depth": 6,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "reg_alpha": 0.1,
                "reg_lambda": 1.0,
                "random_state": self.random_state,
                "n_jobs": 1,
            }
        if self.rf_params is None:
            self.rf_params = {
                "n_estimators": 200,
                "max_depth": 10,
                "min_samples_split": 5,
                "min_samples_leaf": 2,
                "random_state": self.random_state,
                "n_jobs": 1,
            }
        if self.gb_params is None:
            self.gb_params = {
                "n_estimators": 200,
                "learning_rate": 0.1,
                "max_depth": 6,
                "subsample": 0.8,
                "random_state": self.random_state,
            }


class AdvancedCreditScoringModel:
    def __init__(self, config: ModelConfig) -> None:
        self.config = config
        self.models: Dict[str, Any] = {}
        self.ensemble_model: Any = None
        self.feature_names: List[str] = []
        self.scaler: Any = None
        self.feature_selector: Any = None
        self.category_maps: Dict[str, Dict[str, int]] = {}
        self.outlier_bounds: Dict[str, Tuple[float, float]] = {}
        self.feature_importance: Dict[str, Dict[str, float]] = {}
        self.model_metrics: Dict[str, Dict[str, float]] = {}
        self.fairness_metrics: Dict[str, Any] = {}
        self.explainer: Any = None
        self.training_data_stats: Dict[str, Any] = {}
        self.audit_frame: Optional[pd.DataFrame] = None

    def load_and_preprocess_data(
        self, data_path: Optional[str] = None, data: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        if data is not None:
            df = data.copy()
        elif data_path:
            df = pd.read_csv(data_path)
        else:
            df = self._generate_comprehensive_synthetic_data()
        logger.info("Loaded data with shape: %s", df.shape)
        self._perform_data_quality_checks(df)
        df = self._engineer_features(df)
        df = self._handle_missing_values(df)
        df = self._handle_outliers(df)
        self._store_training_statistics(df)
        return df

    def _generate_comprehensive_synthetic_data(
        self, n_samples: int = 10000
    ) -> pd.DataFrame:
        rng = np.random.default_rng(self.config.random_state)
        age = np.clip(rng.normal(40, 12, n_samples), 18, 80)
        income = rng.lognormal(10.5, 0.8, n_samples)
        employment_length = np.clip(rng.exponential(5, n_samples), 0, 40)
        credit_history_length = np.clip(rng.exponential(8, n_samples), 0, age - 18)
        payment_history_score = rng.beta(8, 2, n_samples)
        late_payments_12m = rng.poisson(0.5, n_samples)
        total_credit_limit = income * rng.uniform(0.1, 2.0, n_samples)
        credit_utilization = rng.beta(2, 5, n_samples)
        current_balance = total_credit_limit * credit_utilization
        total_debt = current_balance + rng.exponential(income * 0.1, n_samples)
        debt_to_income = total_debt / income
        num_open_accounts = rng.poisson(3, n_samples)
        num_closed_accounts = rng.poisson(5, n_samples)
        hard_inquiries_6m = rng.poisson(0.3, n_samples)
        hard_inquiries_12m = hard_inquiries_6m + rng.poisson(0.5, n_samples)
        homeownership = rng.choice(
            ["own", "rent", "mortgage"], n_samples, p=[0.3, 0.4, 0.3]
        )
        state = rng.choice(
            ["CA", "NY", "TX", "FL", "IL", "PA", "OH", "GA", "NC", "MI"], n_samples
        )
        gender = rng.choice(["M", "F"], n_samples, p=[0.52, 0.48])
        race = rng.choice(
            ["White", "Black", "Hispanic", "Asian", "Other"],
            n_samples,
            p=[0.6, 0.13, 0.18, 0.06, 0.03],
        )
        quality = (
            0.35 * payment_history_score
            + 0.25 * np.clip(1 - credit_utilization, 0, 1)
            + 0.12 * np.clip(np.log1p(credit_history_length) / np.log1p(30), 0, 1)
            + 0.08
            * np.clip(
                np.log1p(num_open_accounts + num_closed_accounts) / np.log1p(20), 0, 1
            )
            + 0.08 * np.clip(1 - hard_inquiries_12m / 5, 0, 1)
            + 0.07 * np.clip(1 - debt_to_income / 3, 0, 1)
            + 0.05 * np.clip(np.log1p(income) / np.log1p(500000), 0, 1)
            - 0.04 * np.minimum(late_payments_12m, 5)
        )
        credit_score = np.clip(
            300 + 550 * np.clip(quality, 0, 1) + rng.normal(0, 20, n_samples), 300, 850
        ).astype(int)
        return pd.DataFrame(
            {
                "age": age,
                "gender": gender,
                "race": race,
                "state": state,
                "homeownership": homeownership,
                "annual_income": income,
                "employment_length": employment_length,
                "credit_history_length": credit_history_length,
                "payment_history_score": payment_history_score,
                "late_payments_12m": late_payments_12m,
                "total_credit_limit": total_credit_limit,
                "current_balance": current_balance,
                "credit_utilization": credit_utilization,
                "total_debt": total_debt,
                "debt_to_income": debt_to_income,
                "num_open_accounts": num_open_accounts,
                "num_closed_accounts": num_closed_accounts,
                "total_accounts": num_open_accounts + num_closed_accounts,
                "hard_inquiries_6m": hard_inquiries_6m,
                "hard_inquiries_12m": hard_inquiries_12m,
                "credit_score": credit_score,
            }
        )

    def _perform_data_quality_checks(self, df: pd.DataFrame) -> None:
        missing_pct = df.isnull().sum() / max(len(df), 1) * 100
        if missing_pct.max() > 50:
            logger.warning(
                "High missing values detected: %s",
                missing_pct[missing_pct > 50].to_dict(),
            )
        duplicates = int(df.duplicated().sum())
        if duplicates > 0:
            logger.warning("Found %s duplicate rows", duplicates)
        target = self.config.target_variable
        if target in df.columns:
            logger.info(
                "Target variable statistics: %s", df[target].describe().to_dict()
            )

    def _engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["income_to_debt_ratio"] = df["annual_income"] / (df["total_debt"] + 1)
        df["available_credit"] = df["total_credit_limit"] - df["current_balance"]
        df["available_credit_ratio"] = df["available_credit"] / (
            df["total_credit_limit"] + 1
        )
        df["age_group"] = pd.cut(
            df["age"],
            bins=[0, 25, 35, 45, 55, 200],
            labels=["young", "young_adult", "middle_age", "mature", "senior"],
        ).astype(str)
        df["avg_account_age"] = df["credit_history_length"] / (df["total_accounts"] + 1)
        df["credit_experience"] = df["credit_history_length"] * df["total_accounts"]
        df["high_utilization"] = (df["credit_utilization"] > 0.8).astype(int)
        df["recent_inquiries"] = (df["hard_inquiries_6m"] > 2).astype(int)
        df["high_debt_to_income"] = (df["debt_to_income"] > 0.4).astype(int)
        if self.config.interaction_features:
            df["income_age_interaction"] = df["annual_income"] * df["age"]
            df["utilization_history_interaction"] = (
                df["credit_utilization"] * df["credit_history_length"]
            )
            df["payment_income_interaction"] = df["payment_history_score"] * np.log1p(
                df["annual_income"]
            )
        if self.config.polynomial_features:
            df["income_squared"] = df["annual_income"] ** 2
            df["age_squared"] = df["age"] ** 2
            df["utilization_squared"] = df["credit_utilization"] ** 2
        df["employment_stability"] = (df["employment_length"] > 2).astype(int)
        df["credit_maturity"] = (df["credit_history_length"] > 5).astype(int)
        return df

    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        for col in df.select_dtypes(include=[np.number]).columns:
            if df[col].isnull().any():
                fill = (
                    df[col].median()
                    if col in ("annual_income", "total_debt")
                    else df[col].mean()
                )
                df[col] = df[col].fillna(fill)
        for col in df.select_dtypes(include=["object", "category"]).columns:
            if df[col].isnull().any():
                df[col] = df[col].fillna(df[col].mode().iloc[0])
        return df

    def _handle_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        self.outlier_bounds = {}
        for col in df.select_dtypes(include=[np.number]).columns:
            if (
                col == self.config.target_variable
                or df[col].nunique() <= WINSOR_MIN_UNIQUE
            ):
                continue
            lower = float(df[col].quantile(WINSOR_LOWER))
            upper = float(df[col].quantile(WINSOR_UPPER))
            self.outlier_bounds[col] = (lower, upper)
            df[col] = df[col].clip(lower, upper)
        return df

    def _apply_outlier_bounds(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        for col, (lower, upper) in self.outlier_bounds.items():
            if col in df.columns:
                df[col] = df[col].clip(lower, upper)
        return df

    def _store_training_statistics(self, df: pd.DataFrame) -> None:
        numeric = df.select_dtypes(include=[np.number])
        self.training_data_stats = {
            "mean": numeric.mean().to_dict(),
            "std": numeric.std().to_dict(),
            "min": numeric.min().to_dict(),
            "max": numeric.max().to_dict(),
            "quantiles": {
                "25%": numeric.quantile(0.25).to_dict(),
                "50%": numeric.quantile(0.5).to_dict(),
                "75%": numeric.quantile(0.75).to_dict(),
            },
        }

    def _encode_categoricals(self, X: pd.DataFrame, fit: bool) -> pd.DataFrame:
        X = X.copy()
        for col in X.select_dtypes(include=["object", "category"]).columns:
            if fit:
                values = sorted(X[col].astype(str).unique())
                self.category_maps[col] = {
                    value: index for index, value in enumerate(values)
                }
            mapping = self.category_maps.get(col, {})
            X[col] = X[col].astype(str).map(mapping).fillna(-1).astype(int)
        return X

    def prepare_features_and_target(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.Series]:
        target = self.config.target_variable
        protected = [
            col for col in self.config.protected_attributes if col in df.columns
        ]
        self.audit_frame = (
            df[protected].copy() if protected else pd.DataFrame(index=df.index)
        )
        y = df[target]
        X = df.drop(columns=[target] + protected)
        X = self._encode_categoricals(X, fit=True)
        self.feature_names = X.columns.tolist()
        return X, y

    def _select(self, X_scaled: np.ndarray) -> np.ndarray:
        if self.feature_selector is not None:
            return self.feature_selector.transform(X_scaled)
        return X_scaled

    def _selected_feature_names(self) -> List[str]:
        if self.feature_selector is not None:
            return list(
                np.array(self.feature_names)[self.feature_selector.get_support()]
            )
        return list(self.feature_names)

    def train_models(
        self, X: pd.DataFrame, y: pd.Series
    ) -> Tuple[np.ndarray, pd.Series]:
        holdout = self.config.test_size + self.config.validation_size
        strata = pd.qcut(y, q=5, duplicates="drop")
        X_train, X_temp, y_train, y_temp = train_test_split(
            X,
            y,
            test_size=holdout,
            random_state=self.config.random_state,
            stratify=strata,
        )
        X_val, X_test, y_val, y_test = train_test_split(
            X_temp,
            y_temp,
            test_size=self.config.test_size / holdout,
            random_state=self.config.random_state,
            stratify=pd.qcut(y_temp, q=5, duplicates="drop"),
        )
        self.scaler = RobustScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)
        X_test_scaled = self.scaler.transform(X_test)
        if self.config.feature_selection:
            k = min(self.config.feature_selection_k, X_train_scaled.shape[1])
            self.feature_selector = SelectKBest(score_func=f_regression, k=k)
            X_train_sel = self.feature_selector.fit_transform(X_train_scaled, y_train)
        else:
            self.feature_selector = None
            X_train_sel = X_train_scaled
        X_val_sel = self._select(X_val_scaled)
        X_test_sel = self._select(X_test_scaled)
        self._train_xgboost(X_train_sel, y_train)
        self._train_random_forest(X_train_sel, y_train)
        self._train_gradient_boosting(X_train_sel, y_train)
        self._create_ensemble(X_val_sel, y_val)
        self._evaluate_models(X_test_sel, y_test)
        self._analyze_feature_importance(X_val_sel, y_val)
        if self.config.fairness_constraints:
            self._analyze_fairness(X_test_sel, y_test)
        if self.config.explainability_required:
            self._setup_explainability(X_train_sel)
        return X_test_sel, y_test

    def _train_xgboost(self, X_train: np.ndarray, y_train: pd.Series) -> None:
        param_grid = {
            "n_estimators": [100, 200],
            "learning_rate": [0.05, 0.1],
            "max_depth": [4, 6],
        }
        search = GridSearchCV(
            xgb.XGBRegressor(**self.config.xgb_params),
            param_grid,
            cv=self.config.cv_folds,
            scoring="neg_mean_squared_error",
            n_jobs=1,
        )
        search.fit(X_train, y_train)
        self.models["xgboost"] = search.best_estimator_
        logger.info("Best XGBoost parameters: %s", search.best_params_)

    def _train_random_forest(self, X_train: np.ndarray, y_train: pd.Series) -> None:
        model = RandomForestRegressor(**self.config.rf_params)
        model.fit(X_train, y_train)
        self.models["random_forest"] = model

    def _train_gradient_boosting(self, X_train: np.ndarray, y_train: pd.Series) -> None:
        model = GradientBoostingRegressor(**self.config.gb_params)
        model.fit(X_train, y_train)
        self.models["gradient_boosting"] = model

    def _base_predictions(self, X_selected: np.ndarray) -> np.ndarray:
        return np.column_stack(
            [model.predict(X_selected) for model in self.models.values()]
        )

    def _create_ensemble(self, X_val: np.ndarray, y_val: pd.Series) -> None:
        meta_learner = ElasticNet(
            alpha=0.01,
            l1_ratio=0.5,
            positive=True,
            random_state=self.config.random_state,
        )
        meta_learner.fit(self._base_predictions(X_val), y_val)
        self.ensemble_model = meta_learner
        logger.info(
            "Ensemble weights: %s",
            dict(zip(self.models.keys(), meta_learner.coef_.round(4))),
        )

    @staticmethod
    def _regression_metrics(y_true: Any, y_pred: Any) -> Dict[str, float]:
        mse = float(mean_squared_error(y_true, y_pred))
        return {
            "mse": mse,
            "rmse": float(np.sqrt(mse)),
            "mae": float(mean_absolute_error(y_true, y_pred)),
            "r2": float(r2_score(y_true, y_pred)),
        }

    def _evaluate_models(self, X_test: np.ndarray, y_test: pd.Series) -> None:
        for name, model in self.models.items():
            self.model_metrics[name] = self._regression_metrics(
                y_test, model.predict(X_test)
            )
        if self.ensemble_model is not None:
            predictions = self.ensemble_model.predict(self._base_predictions(X_test))
            self.model_metrics["ensemble"] = self._regression_metrics(
                y_test, predictions
            )
        for name, metrics in self.model_metrics.items():
            logger.info("%s: %s", name, {k: round(v, 3) for k, v in metrics.items()})

    def _analyze_feature_importance(self, X_val: np.ndarray, y_val: pd.Series) -> None:
        names = self._selected_feature_names()
        for key in ("xgboost", "random_forest"):
            if key in self.models:
                importances = self.models[key].feature_importances_
                self.feature_importance[key] = {
                    n: float(v) for n, v in zip(names, importances)
                }
        if "xgboost" in self.models:
            result = permutation_importance(
                self.models["xgboost"],
                X_val,
                y_val,
                n_repeats=5,
                random_state=self.config.random_state,
            )
            self.feature_importance["permutation"] = {
                n: float(v) for n, v in zip(names, result.importances_mean)
            }

    def _analyze_fairness(self, X_test: np.ndarray, y_test: pd.Series) -> None:
        if self.audit_frame is None or self.audit_frame.empty:
            return
        predictions = self.predict_selected(X_test)
        audit = self.audit_frame.loc[y_test.index]
        for attribute in audit.columns:
            groups: Dict[str, Dict[str, float]] = {}
            for value in audit[attribute].unique():
                mask = (audit[attribute] == value).to_numpy()
                if not mask.any():
                    continue
                group_predictions = predictions[mask]
                groups[str(value)] = {
                    "count": int(mask.sum()),
                    "mean_actual_score": float(y_test.to_numpy()[mask].mean()),
                    "mean_predicted_score": float(group_predictions.mean()),
                    "approval_rate": float(
                        (group_predictions >= APPROVAL_THRESHOLD).mean()
                    ),
                }
            rates = [g["approval_rate"] for g in groups.values() if g["count"] > 0]
            ratio = min(rates) / max(rates) if rates and max(rates) > 0 else 1.0
            self.fairness_metrics[attribute] = {
                "groups": groups,
                "disparate_impact_ratio": float(ratio),
                "passes_four_fifths_rule": bool(ratio >= DISPARATE_IMPACT_FLOOR),
            }
            logger.info(
                "Fairness for %s: disparate impact ratio %.3f", attribute, ratio
            )

    def _setup_explainability(self, X_train: np.ndarray) -> None:
        if shap is None or "xgboost" not in self.models:
            self.explainer = None
            logger.info("SHAP not available, explainability disabled")
            return
        self.explainer = shap.TreeExplainer(self.models["xgboost"])
        sample = X_train[: min(100, len(X_train))]
        self.explainer.shap_values(sample)

    def _prepare_inference(self, X: pd.DataFrame) -> np.ndarray:
        frame = self._engineer_features(X)
        frame = self._apply_outlier_bounds(frame)
        frame = self._encode_categoricals(frame, fit=False)
        missing = [name for name in self.feature_names if name not in frame.columns]
        if missing:
            raise ValueError(f"Missing required features: {missing}")
        frame = frame[self.feature_names]
        return self._select(self.scaler.transform(frame))

    def predict_selected(self, X_selected: np.ndarray) -> np.ndarray:
        base = self._base_predictions(X_selected)
        if self.ensemble_model is not None:
            predictions = self.ensemble_model.predict(base)
        else:
            predictions = base.mean(axis=1)
        return np.clip(predictions, 300, 850)

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return self.predict_selected(self._prepare_inference(X))

    def explain_prediction(self, X: pd.DataFrame, index: int = 0) -> Dict[str, Any]:
        if self.explainer is None:
            return {"error": "Explainer not available"}
        selected = self._prepare_inference(X.iloc[[index]])
        values = np.asarray(self.explainer.shap_values(selected))
        names = self._selected_feature_names()
        return {
            "prediction": float(self.models["xgboost"].predict(selected)[0]),
            "base_value": float(np.ravel(self.explainer.expected_value)[0]),
            "shap_values": {n: float(v) for n, v in zip(names, values[0])},
            "feature_values": {n: float(v) for n, v in zip(names, selected[0])},
        }

    def save_model(self, model_path: str) -> None:
        payload = {
            "models": self.models,
            "ensemble_model": self.ensemble_model,
            "scaler": self.scaler,
            "feature_selector": self.feature_selector,
            "category_maps": self.category_maps,
            "outlier_bounds": self.outlier_bounds,
            "feature_names": self.feature_names,
            "config": self.config,
            "model_metrics": self.model_metrics,
            "feature_importance": self.feature_importance,
            "fairness_metrics": self.fairness_metrics,
            "training_data_stats": self.training_data_stats,
        }
        Path(model_path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(payload, model_path)
        logger.info("Model saved to %s", model_path)

    @classmethod
    def load_model(cls, model_path: str) -> "AdvancedCreditScoringModel":
        payload = joblib.load(model_path)
        instance = cls(payload["config"])
        instance.models = payload["models"]
        instance.ensemble_model = payload["ensemble_model"]
        instance.scaler = payload["scaler"]
        instance.feature_selector = payload["feature_selector"]
        instance.category_maps = payload["category_maps"]
        instance.outlier_bounds = payload["outlier_bounds"]
        instance.feature_names = payload["feature_names"]
        instance.model_metrics = payload["model_metrics"]
        instance.feature_importance = payload["feature_importance"]
        instance.fairness_metrics = payload["fairness_metrics"]
        instance.training_data_stats = payload["training_data_stats"]
        if (
            instance.config.explainability_required
            and shap is not None
            and "xgboost" in instance.models
        ):
            instance.explainer = shap.TreeExplainer(instance.models["xgboost"])
        logger.info("Model loaded from %s", model_path)
        return instance

    def generate_model_report(self) -> Dict[str, Any]:
        return {
            "model_performance": self.model_metrics,
            "feature_importance": self.feature_importance,
            "fairness_metrics": self.fairness_metrics,
            "training_data_stats": self.training_data_stats,
            "model_config": {
                "model_type": self.config.model_type,
                "feature_selection": self.config.feature_selection,
                "fairness_constraints": self.config.fairness_constraints,
                "explainability_required": self.config.explainability_required,
                "excluded_protected_attributes": self.config.protected_attributes,
            },
            "regulatory_compliance": {
                "explainable": self.explainer is not None,
                "fair": (
                    all(
                        item["passes_four_fifths_rule"]
                        for item in self.fairness_metrics.values()
                    )
                    if self.fairness_metrics
                    else None
                ),
                "monitored": self.config.model_monitoring,
            },
        }


def _json_default(value: Any) -> Any:
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    return str(value)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    output_dir = Path(os.getenv("MODEL_OUTPUT_DIR", str(ARTIFACTS_DIR / "research")))
    model = AdvancedCreditScoringModel(ModelConfig())
    df = model.load_and_preprocess_data()
    X, y = model.prepare_features_and_target(df)
    model.train_models(X, y)
    model.save_model(str(output_dir / "advanced_credit_scoring_model.pkl"))
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / "model_report.json", "w", encoding="utf-8") as handle:
        json.dump(
            model.generate_model_report(), handle, indent=2, default=_json_default
        )
    best = min(model.model_metrics.items(), key=lambda item: item[1]["rmse"])
    logger.info("Best model: %s %s", best[0], best[1])


if __name__ == "__main__":
    main()
