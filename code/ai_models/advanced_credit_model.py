"""
Advanced Credit Scoring Model for Financial Industry
Implements state-of-the-art machine learning techniques with regulatory compliance
"""

import logging
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Tuple

import joblib
import numpy as np
import pandas as pd
import shap
import xgboost as xgb
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.feature_selection import SelectKBest, f_regression
from sklearn.inspection import permutation_importance
from sklearn.linear_model import ElasticNet
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.preprocessing import LabelEncoder, RobustScaler

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Configuration for credit scoring model"""

    model_type: str = "ensemble"
    target_variable: str = "credit_score"
    test_size: float = 0.2
    validation_size: float = 0.2
    random_state: int = 42
    cv_folds: int = 5
    xgb_params: Dict = None
    rf_params: Dict = None
    gb_params: Dict = None
    feature_selection: bool = True
    feature_selection_k: int = 20
    polynomial_features: bool = False
    interaction_features: bool = True
    fairness_constraints: bool = True
    explainability_required: bool = True
    model_monitoring: bool = True

    def __post_init__(self) -> Any:
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
            }
        if self.rf_params is None:
            self.rf_params = {
                "n_estimators": 200,
                "max_depth": 10,
                "min_samples_split": 5,
                "min_samples_leaf": 2,
                "random_state": self.random_state,
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
    """
    Advanced credit scoring model with regulatory compliance and fairness considerations
    """

    def __init__(self, config: ModelConfig) -> None:
        self.config = config
        self.models = {}
        self.ensemble_model = None
        self.feature_names = []
        self.scaler = None
        self.feature_selector = None
        self.label_encoders = {}
        self.feature_importance = {}
        self.model_metrics = {}
        self.fairness_metrics = {}
        self.explainer = None
        self.training_data_stats = {}
        self.drift_detector = None

    def load_and_preprocess_data(
        self, data_path: str = None, data: pd.DataFrame = None
    ) -> pd.DataFrame:
        """Load and preprocess financial data with comprehensive feature engineering"""
        if data is not None:
            df = data.copy()
        elif data_path:
            df = pd.read_csv(data_path)
        else:
            df = self._generate_comprehensive_synthetic_data()
        logger.info(f"Loaded data with shape: {df.shape}")
        self._perform_data_quality_checks(df)
        df = self._engineer_features(df)
        df = self._handle_missing_values(df)
        df = self._handle_outliers(df)
        self._store_training_statistics(df)
        return df

    def _generate_comprehensive_synthetic_data(
        self, n_samples: int = 10000
    ) -> pd.DataFrame:
        """Generate comprehensive synthetic financial data"""
        np.random.seed(self.config.random_state)
        age = np.random.normal(40, 12, n_samples)
        age = np.clip(age, 18, 80)
        income = np.random.lognormal(10.5, 0.8, n_samples)
        employment_length = np.random.exponential(5, n_samples)
        employment_length = np.clip(employment_length, 0, 40)
        credit_history_length = np.random.exponential(8, n_samples)
        credit_history_length = np.clip(credit_history_length, 0, age - 18)
        payment_history_score = np.random.beta(8, 2, n_samples)
        late_payments_12m = np.random.poisson(0.5, n_samples)
        total_credit_limit = income * np.random.uniform(0.1, 2.0, n_samples)
        credit_utilization = np.random.beta(2, 5, n_samples)
        current_balance = total_credit_limit * credit_utilization
        total_debt = current_balance + np.random.exponential(income * 0.1, n_samples)
        debt_to_income = total_debt / income
        num_open_accounts = np.random.poisson(3, n_samples)
        num_closed_accounts = np.random.poisson(5, n_samples)
        hard_inquiries_6m = np.random.poisson(0.3, n_samples)
        hard_inquiries_12m = np.random.poisson(0.8, n_samples)
        homeownership = np.random.choice(
            ["own", "rent", "mortgage"], n_samples, p=[0.3, 0.4, 0.3]
        )
        state = np.random.choice(
            ["CA", "NY", "TX", "FL", "IL", "PA", "OH", "GA", "NC", "MI"], n_samples
        )
        gender = np.random.choice(["M", "F"], n_samples, p=[0.52, 0.48])
        race = np.random.choice(
            ["White", "Black", "Hispanic", "Asian", "Other"],
            n_samples,
            p=[0.6, 0.13, 0.18, 0.06, 0.03],
        )
        base_score = (
            300
            + payment_history_score * 250
            + np.clip(1 - credit_utilization, 0, 1) * 150
            + np.log1p(credit_history_length) * 40
            + np.log1p(num_open_accounts + num_closed_accounts) * 30
            + np.clip(1 - hard_inquiries_12m / 10, 0, 1) * 50
            + np.log1p(income) * 10
            + np.clip(1 - debt_to_income / 5, 0, 1) * 30
            - late_payments_12m * 20
        )
        noise = np.random.normal(0, 25, n_samples)
        credit_score = np.clip(base_score + noise, 300, 850).astype(int)
        df = pd.DataFrame(
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
        return df

    def _perform_data_quality_checks(self, df: pd.DataFrame) -> Any:
        """Perform comprehensive data quality checks"""
        logger.info("Performing data quality checks...")
        missing_pct = df.isnull().sum() / len(df) * 100
        if missing_pct.max() > 50:
            logger.warning(
                f"High missing values detected: {missing_pct[missing_pct > 50]}"
            )
        duplicates = df.duplicated().sum()
        if duplicates > 0:
            logger.warning(f"Found {duplicates} duplicate rows")
        logger.info(f"Data types: {df.dtypes.value_counts()}")
        if self.config.target_variable in df.columns:
            target_stats = df[self.config.target_variable].describe()
            logger.info(f"Target variable statistics:\n{target_stats}")

    def _engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Comprehensive feature engineering for credit scoring"""
        logger.info("Engineering features...")
        df["income_to_debt_ratio"] = df["annual_income"] / (df["total_debt"] + 1)
        df["available_credit"] = df["total_credit_limit"] - df["current_balance"]
        df["available_credit_ratio"] = df["available_credit"] / (
            df["total_credit_limit"] + 1
        )
        df["age_group"] = pd.cut(
            df["age"],
            bins=[0, 25, 35, 45, 55, 100],
            labels=["young", "young_adult", "middle_age", "mature", "senior"],
        )
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
        df["employment_stability"] = np.where(df["employment_length"] > 2, 1, 0)
        df["credit_maturity"] = np.where(df["credit_history_length"] > 5, 1, 0)
        return df

    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle missing values with appropriate strategies"""
        logger.info("Handling missing values...")
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        categorical_cols = df.select_dtypes(include=["object"]).columns
        for col in numeric_cols:
            if df[col].isnull().sum() > 0:
                if col in ["annual_income", "total_debt"]:
                    df[col].fillna(df[col].median(), inplace=True)
                else:
                    df[col].fillna(df[col].mean(), inplace=True)
        for col in categorical_cols:
            if df[col].isnull().sum() > 0:
                df[col].fillna(df[col].mode()[0], inplace=True)
        return df

    def _handle_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detect and handle outliers using IQR method"""
        logger.info("Handling outliers...")
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        numeric_cols = [
            col for col in numeric_cols if col != self.config.target_variable
        ]
        for col in numeric_cols:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            df[col] = np.clip(df[col], lower_bound, upper_bound)
        return df

    def _store_training_statistics(self, df: pd.DataFrame) -> Any:
        """Store training data statistics for model monitoring"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        self.training_data_stats = {
            "mean": df[numeric_cols].mean().to_dict(),
            "std": df[numeric_cols].std().to_dict(),
            "min": df[numeric_cols].min().to_dict(),
            "max": df[numeric_cols].max().to_dict(),
            "quantiles": {
                "25%": df[numeric_cols].quantile(0.25).to_dict(),
                "50%": df[numeric_cols].quantile(0.5).to_dict(),
                "75%": df[numeric_cols].quantile(0.75).to_dict(),
            },
        }

    def prepare_features_and_target(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare features and target variable"""
        X = df.drop(columns=[self.config.target_variable])
        y = df[self.config.target_variable]
        categorical_cols = X.select_dtypes(include=["object"]).columns
        for col in categorical_cols:
            if col not in self.label_encoders:
                self.label_encoders[col] = LabelEncoder()
                X[col] = self.label_encoders[col].fit_transform(X[col].astype(str))
            else:
                X[col] = self.label_encoders[col].transform(X[col].astype(str))
        self.feature_names = X.columns.tolist()
        return (X, y)

    def train_models(self, X: pd.DataFrame, y: pd.Series) -> Any:
        """Train multiple models and create ensemble"""
        logger.info("Training models...")
        X_train, X_temp, y_train, y_temp = train_test_split(
            X,
            y,
            test_size=self.config.test_size + self.config.validation_size,
            random_state=self.config.random_state,
            stratify=pd.cut(y, bins=5),
        )
        X_val, X_test, y_val, y_test = train_test_split(
            X_temp,
            y_temp,
            test_size=self.config.test_size
            / (self.config.test_size + self.config.validation_size),
            random_state=self.config.random_state,
            stratify=pd.cut(y_temp, bins=5),
        )
        self.scaler = RobustScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)
        X_test_scaled = self.scaler.transform(X_test)
        if self.config.feature_selection:
            self.feature_selector = SelectKBest(
                score_func=f_regression, k=self.config.feature_selection_k
            )
            X_train_selected = self.feature_selector.fit_transform(
                X_train_scaled, y_train
            )
            X_val_selected = self.feature_selector.transform(X_val_scaled)
            X_test_selected = self.feature_selector.transform(X_test_scaled)
        else:
            X_train_selected = X_train_scaled
            X_val_selected = X_val_scaled
            X_test_selected = X_test_scaled
        self._train_xgboost(X_train_selected, y_train, X_val_selected, y_val)
        self._train_random_forest(X_train_selected, y_train, X_val_selected, y_val)
        self._train_gradient_boosting(X_train_selected, y_train, X_val_selected, y_val)
        self._create_ensemble(X_train_selected, y_train, X_val_selected, y_val)
        self._evaluate_models(X_test_selected, y_test)
        self._analyze_feature_importance(X_train, y_train)
        if self.config.fairness_constraints:
            self._analyze_fairness(X_test, y_test)
        if self.config.explainability_required:
            self._setup_explainability(X_train_selected, y_train)
        return (X_test_selected, y_test)

    def _train_xgboost(self, X_train: Any, y_train: Any, X_val: Any, y_val: Any) -> Any:
        """Train XGBoost model with hyperparameter tuning"""
        logger.info("Training XGBoost model...")
        param_grid = {
            "n_estimators": [100, 200, 300],
            "learning_rate": [0.05, 0.1, 0.15],
            "max_depth": [4, 6, 8],
            "subsample": [0.8, 0.9, 1.0],
            "colsample_bytree": [0.8, 0.9, 1.0],
        }
        xgb_model = xgb.XGBRegressor(**self.config.xgb_params)
        grid_search = GridSearchCV(
            xgb_model,
            param_grid,
            cv=3,
            scoring="neg_mean_squared_error",
            n_jobs=-1,
            verbose=0,
        )
        grid_search.fit(X_train, y_train)
        self.models["xgboost"] = grid_search.best_estimator_
        logger.info(f"Best XGBoost parameters: {grid_search.best_params_}")

    def _train_random_forest(
        self, X_train: Any, y_train: Any, X_val: Any, y_val: Any
    ) -> Any:
        """Train Random Forest model"""
        logger.info("Training Random Forest model...")
        rf_model = RandomForestRegressor(**self.config.rf_params)
        rf_model.fit(X_train, y_train)
        self.models["random_forest"] = rf_model

    def _train_gradient_boosting(
        self, X_train: Any, y_train: Any, X_val: Any, y_val: Any
    ) -> Any:
        """Train Gradient Boosting model"""
        logger.info("Training Gradient Boosting model...")
        gb_model = GradientBoostingRegressor(**self.config.gb_params)
        gb_model.fit(X_train, y_train)
        self.models["gradient_boosting"] = gb_model

    def _create_ensemble(
        self, X_train: Any, y_train: Any, X_val: Any, y_val: Any
    ) -> Any:
        """Create ensemble model using stacking"""
        logger.info("Creating ensemble model...")
        train_predictions = np.column_stack(
            [model.predict(X_train) for model in self.models.values()]
        )
        val_predictions = np.column_stack(
            [model.predict(X_val) for model in self.models.values()]
        )
        meta_learner = ElasticNet(
            alpha=0.1, l1_ratio=0.5, random_state=self.config.random_state
        )
        meta_learner.fit(train_predictions, y_train)
        self.ensemble_model = meta_learner
        ensemble_pred = meta_learner.predict(val_predictions)
        ensemble_mse = mean_squared_error(y_val, ensemble_pred)
        logger.info(f"Ensemble validation MSE: {ensemble_mse:.2f}")

    def _evaluate_models(self, X_test: Any, y_test: Any) -> Any:
        """Evaluate all models on test set"""
        logger.info("Evaluating models...")
        for name, model in self.models.items():
            predictions = model.predict(X_test)
            mse = mean_squared_error(y_test, predictions)
            rmse = np.sqrt(mse)
            mae = mean_absolute_error(y_test, predictions)
            r2 = r2_score(y_test, predictions)
            self.model_metrics[name] = {"mse": mse, "rmse": rmse, "mae": mae, "r2": r2}
            logger.info(
                f"{name} - MSE: {mse:.2f}, RMSE: {rmse:.2f}, MAE: {mae:.2f}, R²: {r2:.3f}"
            )
        if self.ensemble_model:
            test_predictions = np.column_stack(
                [model.predict(X_test) for model in self.models.values()]
            )
            ensemble_pred = self.ensemble_model.predict(test_predictions)
            mse = mean_squared_error(y_test, ensemble_pred)
            rmse = np.sqrt(mse)
            mae = mean_absolute_error(y_test, ensemble_pred)
            r2 = r2_score(y_test, ensemble_pred)
            self.model_metrics["ensemble"] = {
                "mse": mse,
                "rmse": rmse,
                "mae": mae,
                "r2": r2,
            }
            logger.info(
                f"Ensemble - MSE: {mse:.2f}, RMSE: {rmse:.2f}, MAE: {mae:.2f}, R²: {r2:.3f}"
            )

    def _analyze_feature_importance(self, X_train: Any, y_train: Any) -> Any:
        """Analyze feature importance across models"""
        logger.info("Analyzing feature importance...")
        if self.feature_selector:
            selected_features = np.array(self.feature_names)[
                self.feature_selector.get_support()
            ]
        else:
            selected_features = self.feature_names
        if "xgboost" in self.models:
            xgb_importance = self.models["xgboost"].feature_importances_
            self.feature_importance["xgboost"] = dict(
                zip(selected_features, xgb_importance)
            )
        if "random_forest" in self.models:
            rf_importance = self.models["random_forest"].feature_importances_
            self.feature_importance["random_forest"] = dict(
                zip(selected_features, rf_importance)
            )
        if "xgboost" in self.models:
            X_train_selected = (
                self.feature_selector.transform(self.scaler.transform(X_train))
                if self.feature_selector
                else self.scaler.transform(X_train)
            )
            perm_importance = permutation_importance(
                self.models["xgboost"],
                X_train_selected,
                y_train,
                n_repeats=5,
                random_state=self.config.random_state,
            )
            self.feature_importance["permutation"] = dict(
                zip(selected_features, perm_importance.importances_mean)
            )

    def _analyze_fairness(self, X_test: Any, y_test: Any) -> Any:
        """Analyze model fairness across protected attributes"""
        logger.info("Analyzing model fairness...")
        protected_attributes = ["gender", "race"]
        for attr in protected_attributes:
            if attr in X_test.columns:
                unique_values = X_test[attr].unique()
                fairness_results = {}
                for value in unique_values:
                    mask = X_test[attr] == value
                    if mask.sum() > 0:
                        group_scores = y_test[mask]
                        fairness_results[value] = {
                            "mean_score": group_scores.mean(),
                            "std_score": group_scores.std(),
                            "count": mask.sum(),
                        }
                self.fairness_metrics[attr] = fairness_results
                logger.info(f"Fairness analysis for {attr}:")
                for value, metrics in fairness_results.items():
                    logger.info(
                        f"  {value}: Mean={metrics['mean_score']:.1f}, Std={metrics['std_score']:.1f}, N={metrics['count']}"
                    )

    def _setup_explainability(self, X_train: Any, y_train: Any) -> Any:
        """Setup model explainability tools"""
        logger.info("Setting up model explainability...")
        if "xgboost" in self.models:
            self.explainer = shap.TreeExplainer(self.models["xgboost"])
            sample_size = min(100, len(X_train))
            sample_indices = np.random.choice(len(X_train), sample_size, replace=False)
            self.explainer.shap_values(X_train[sample_indices])
            logger.info("SHAP explainer setup complete")

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Make predictions using the ensemble model"""
        X_processed = X.copy()
        categorical_cols = X_processed.select_dtypes(include=["object"]).columns
        for col in categorical_cols:
            if col in self.label_encoders:
                X_processed[col] = self.label_encoders[col].transform(
                    X_processed[col].astype(str)
                )
        X_scaled = self.scaler.transform(X_processed)
        if self.feature_selector:
            X_selected = self.feature_selector.transform(X_scaled)
        else:
            X_selected = X_scaled
        base_predictions = np.column_stack(
            [model.predict(X_selected) for model in self.models.values()]
        )
        if self.ensemble_model:
            return self.ensemble_model.predict(base_predictions)
        else:
            return np.mean(base_predictions, axis=1)

    def explain_prediction(self, X: pd.DataFrame, index: int = 0) -> Dict:
        """Explain a single prediction using SHAP"""
        if self.explainer is None:
            return {"error": "Explainer not available"}
        X_processed = X.iloc[[index]].copy()
        categorical_cols = X_processed.select_dtypes(include=["object"]).columns
        for col in categorical_cols:
            if col in self.label_encoders:
                X_processed[col] = self.label_encoders[col].transform(
                    X_processed[col].astype(str)
                )
        X_scaled = self.scaler.transform(X_processed)
        if self.feature_selector:
            X_selected = self.feature_selector.transform(X_scaled)
        else:
            X_selected = X_scaled
        shap_values = self.explainer.shap_values(X_selected)
        if self.feature_selector:
            feature_names = np.array(self.feature_names)[
                self.feature_selector.get_support()
            ]
        else:
            feature_names = self.feature_names
        explanation = {
            "prediction": self.models["xgboost"].predict(X_selected)[0],
            "base_value": self.explainer.expected_value,
            "shap_values": dict(zip(feature_names, shap_values[0])),
            "feature_values": dict(zip(feature_names, X_selected[0])),
        }
        return explanation

    def save_model(self, model_path: str) -> Any:
        """Save the complete model pipeline"""
        model_data = {
            "models": self.models,
            "ensemble_model": self.ensemble_model,
            "scaler": self.scaler,
            "feature_selector": self.feature_selector,
            "label_encoders": self.label_encoders,
            "feature_names": self.feature_names,
            "config": self.config,
            "model_metrics": self.model_metrics,
            "feature_importance": self.feature_importance,
            "fairness_metrics": self.fairness_metrics,
            "training_data_stats": self.training_data_stats,
        }
        Path(model_path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model_data, model_path)
        logger.info(f"Model saved to {model_path}")

    @classmethod
    def load_model(cls: Any, model_path: str) -> Any:
        """Load a saved model"""
        model_data = joblib.load(model_path)
        instance = cls(model_data["config"])
        instance.models = model_data["models"]
        instance.ensemble_model = model_data["ensemble_model"]
        instance.scaler = model_data["scaler"]
        instance.feature_selector = model_data["feature_selector"]
        instance.label_encoders = model_data["label_encoders"]
        instance.feature_names = model_data["feature_names"]
        instance.model_metrics = model_data["model_metrics"]
        instance.feature_importance = model_data["feature_importance"]
        instance.fairness_metrics = model_data["fairness_metrics"]
        instance.training_data_stats = model_data["training_data_stats"]
        logger.info(f"Model loaded from {model_path}")
        return instance

    def generate_model_report(self) -> Dict:
        """Generate comprehensive model report"""
        report = {
            "model_performance": self.model_metrics,
            "feature_importance": self.feature_importance,
            "fairness_metrics": self.fairness_metrics,
            "training_data_stats": self.training_data_stats,
            "model_config": {
                "model_type": self.config.model_type,
                "feature_selection": self.config.feature_selection,
                "fairness_constraints": self.config.fairness_constraints,
                "explainability_required": self.config.explainability_required,
            },
            "regulatory_compliance": {
                "explainable": self.config.explainability_required,
                "fair": self.config.fairness_constraints,
                "monitored": self.config.model_monitoring,
            },
        }
        return report


def main() -> Any:
    """Main training pipeline"""
    config = ModelConfig(
        model_type="ensemble",
        feature_selection=True,
        fairness_constraints=True,
        explainability_required=True,
        model_monitoring=True,
    )
    model = AdvancedCreditScoringModel(config)
    df = model.load_and_preprocess_data()
    X, y = model.prepare_features_and_target(df)
    X_test, y_test = model.train_models(X, y)
    model.save_model("models/advanced_credit_scoring_model.pkl")
    report = model.generate_model_report()
    import json

    with open("models/model_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    logger.info("Model training and evaluation complete!")
    logger.info(
        f"Best model performance: {min(model.model_metrics.values(), key=lambda x: x['rmse'])}"
    )


if __name__ == "__main__":
    main()
