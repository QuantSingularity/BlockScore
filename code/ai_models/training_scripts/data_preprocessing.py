"""
Comprehensive data preprocessing script for the Decentralized Credit Scoring System (BlockScore).

This script handles loading raw data (simulating aggregated on-chain and off-chain data),
performs feature engineering relevant to DeFi and credit scoring, cleans the data,
and applies necessary transformations (scaling, encoding) to prepare it for
machine learning model training.
"""

import logging
import os
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

FEATURE_SCHEMA = {
    "numerical": [
        "wallet_age_days",
        "total_eth_balance",
        "avg_daily_tx_volume",
        "loan_to_value_ratio",
        "total_loan_amount",
        "num_active_loans",
        "num_liquidations",
        "credit_score_history_avg",
        "defi_protocol_count",
        "token_diversity_score",
    ],
    "categorical": ["primary_defi_protocol", "wallet_type", "country_code"],
    "target": "credit_risk_score",
}
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def _engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Performs feature engineering specific to decentralized finance and credit scoring.
    This is a placeholder for more complex logic that would be applied to raw blockchain data.
    """
    logger.info("Starting feature engineering...")
    epsilon = 1e-06
    df["liquidation_rate"] = df["num_liquidations"] / (df["num_active_loans"] + epsilon)
    df["loan_utilization_ratio"] = df["total_loan_amount"] / (
        df["total_eth_balance"] + epsilon
    )
    df["activity_score"] = (
        df["avg_daily_tx_volume"] * 0.5
        + df["defi_protocol_count"] * 0.3
        + df["token_diversity_score"] * 0.2
    )
    logger.info(
        f"New features created: {['liquidation_rate', 'loan_utilization_ratio', 'activity_score']}"
    )
    return df


def create_preprocessor_pipeline(
    numerical_features: list, categorical_features: list
) -> ColumnTransformer:
    """
    Creates the scikit-learn ColumnTransformer pipeline for preprocessing.
    """
    numerical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numerical_pipeline, numerical_features),
            ("cat", categorical_pipeline, categorical_features),
        ],
        remainder="drop",
        n_jobs=-1,
    )
    logger.info("Preprocessing ColumnTransformer pipeline created.")
    return preprocessor


def preprocess_data(
    data_path: str,
    test_size: float = 0.2,
    random_state: int = 42,
    output_dir: str = "processed_data",
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Loads, preprocesses, and splits the data into training and testing sets.

    Args:
        data_path: Path to the raw data CSV file.
        test_size: Proportion of the data to be used as the test set.
        random_state: Seed for random number generation for reproducibility.
        output_dir: Directory to save the fitted preprocessor object.

    Returns:
        A tuple containing (X_train_processed, X_test_processed, y_train, y_test).
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    logger.info(f"Loading data from: {data_path}")
    try:
        df = pd.read_csv(data_path)
    except FileNotFoundError:
        logger.error(
            f"Data file not found at {data_path}. Please ensure the file exists."
        )
        raise
    df = _engineer_features(df)
    numerical_features = FEATURE_SCHEMA["numerical"] + [
        "liquidation_rate",
        "loan_utilization_ratio",
        "activity_score",
    ]
    categorical_features = FEATURE_SCHEMA["categorical"]
    target_feature = FEATURE_SCHEMA["target"]
    X = df.drop(columns=[target_feature])
    y = df[target_feature]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )
    logger.info(
        f"Data split into training ({len(X_train)} samples) and testing ({len(X_test)} samples)."
    )
    preprocessor = create_preprocessor_pipeline(
        numerical_features, categorical_features
    )
    logger.info("Fitting preprocessor to training data...")
    preprocessor.fit(X_train)
    logger.info("Transforming training and testing data...")
    X_train_processed = preprocessor.transform(X_train)
    X_test_processed = preprocessor.transform(X_test)
    preprocessor_path = os.path.join(output_dir, "preprocessor.joblib")
    joblib.dump(preprocessor, preprocessor_path)
    logger.info(f"Fitted preprocessor saved to: {preprocessor_path}")
    logger.info("Data preprocessing complete.")
    return (X_train_processed, X_test_processed, y_train.values, y_test.values)


def generate_dummy_data(path: str = "raw_data.csv", n_samples: int = 1000) -> Any:
    """Generates a dummy dataset for demonstration purposes."""
    logger.info(f"Generating dummy data with {n_samples} samples...")
    np.random.seed(42)
    data = {
        "wallet_age_days": np.random.randint(30, 1500, n_samples),
        "total_eth_balance": np.random.lognormal(mean=1.0, sigma=1.0, size=n_samples),
        "avg_daily_tx_volume": np.random.lognormal(mean=0.5, sigma=0.5, size=n_samples),
        "loan_to_value_ratio": np.random.rand(n_samples) * 0.8,
        "total_loan_amount": np.random.lognormal(mean=0.8, sigma=0.8, size=n_samples),
        "num_active_loans": np.random.randint(0, 10, n_samples),
        "num_liquidations": np.random.choice(
            [0, 1, 2, 3], n_samples, p=[0.8, 0.1, 0.05, 0.05]
        ),
        "credit_score_history_avg": np.random.randint(500, 850, n_samples),
        "defi_protocol_count": np.random.randint(1, 15, n_samples),
        "token_diversity_score": np.random.rand(n_samples),
        "primary_defi_protocol": np.random.choice(
            ["Aave", "Compound", "MakerDAO", "Uniswap"], n_samples
        ),
        "wallet_type": np.random.choice(["EVM", "Non-EVM", "Custodial"], n_samples),
        "country_code": np.random.choice(
            ["USA", "CHN", "IND", "DEU", "BRA", np.nan], n_samples
        ),
        "credit_risk_score": np.random.choice([0, 1], n_samples, p=[0.7, 0.3]),
    }
    df = pd.DataFrame(data)
    for col in ["total_eth_balance", "loan_to_value_ratio", "country_code"]:
        df.loc[df.sample(frac=0.05).index, col] = np.nan
    df.to_csv(path, index=False)
    logger.info(f"Dummy data saved to {path}")
    return path


if __name__ == "__main__":
    dummy_data_path = generate_dummy_data()
    try:
        X_train_proc, X_test_proc, y_train, y_test = preprocess_data(
            data_path=dummy_data_path, output_dir="BlockScore/processed_data"
        )
        logger.info("\n--- Preprocessing Results ---")
        logger.info(f"Shape of X_train_processed: {X_train_proc.shape}")
        logger.info(f"Shape of X_test_processed: {X_test_proc.shape}")
        logger.info(f"Shape of y_train: {y_train.shape}")
        logger.info(f"Shape of y_test: {y_test.shape}")
        logger.info(
            f"First 5 rows of processed training data (features):\n{X_train_proc[:5]}"
        )
        logger.info(f"First 5 rows of training labels:\n{y_train[:5]}")
    except Exception as e:
        logger.error(f"An error occurred during preprocessing: {e}")
