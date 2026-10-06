import logging
import os
from pathlib import Path
from typing import Any, List, Tuple

import joblib
import numpy as np
import pandas as pd
from blockscore_ai.config import ARTIFACTS_DIR
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
DERIVED_FEATURES = ["liquidation_rate", "loan_utilization_ratio", "activity_score"]
EPSILON = 1e-06

logger = logging.getLogger(__name__)


def _engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    required = set(FEATURE_SCHEMA["numerical"])
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    df = df.copy()
    df["liquidation_rate"] = df["num_liquidations"] / (df["num_active_loans"] + EPSILON)
    df["loan_utilization_ratio"] = df["total_loan_amount"] / (
        df["total_eth_balance"] + EPSILON
    )
    df["activity_score"] = (
        df["avg_daily_tx_volume"] * 0.5
        + df["defi_protocol_count"] * 0.3
        + df["token_diversity_score"] * 0.2
    )
    return df


def create_preprocessor_pipeline(
    numerical_features: List[str], categorical_features: List[str]
) -> ColumnTransformer:
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
    return ColumnTransformer(
        transformers=[
            ("num", numerical_pipeline, numerical_features),
            ("cat", categorical_pipeline, categorical_features),
        ],
        remainder="drop",
    )


def preprocess_data(
    data_path: str,
    test_size: float = 0.2,
    random_state: int = 42,
    output_dir: str = str(ARTIFACTS_DIR / "preprocessing"),
) -> Tuple[Any, Any, np.ndarray, np.ndarray]:
    os.makedirs(output_dir, exist_ok=True)
    df = pd.read_csv(data_path)
    df = _engineer_features(df)
    target_feature = FEATURE_SCHEMA["target"]
    if target_feature not in df.columns:
        raise ValueError(f"Missing target column: {target_feature}")
    numerical_features = FEATURE_SCHEMA["numerical"] + DERIVED_FEATURES
    categorical_features = [c for c in FEATURE_SCHEMA["categorical"] if c in df.columns]
    X = df.drop(columns=[target_feature])
    y = df[target_feature]
    stratify = y if y.nunique() > 1 and y.value_counts().min() >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=stratify
    )
    preprocessor = create_preprocessor_pipeline(
        numerical_features, categorical_features
    )
    preprocessor.fit(X_train)
    X_train_processed = preprocessor.transform(X_train)
    X_test_processed = preprocessor.transform(X_test)
    joblib.dump(preprocessor, os.path.join(output_dir, "preprocessor.joblib"))
    logger.info(
        "Preprocessed %s training and %s test samples", len(X_train), len(X_test)
    )
    return X_train_processed, X_test_processed, y_train.to_numpy(), y_test.to_numpy()


def generate_dummy_data(
    path: str = "raw_data.csv", n_samples: int = 1000, seed: int = 42
) -> str:
    rng = np.random.default_rng(seed)
    countries = np.array(["USA", "CHN", "IND", "DEU", "BRA"], dtype=object)
    data = {
        "wallet_age_days": rng.integers(30, 1500, n_samples),
        "total_eth_balance": rng.lognormal(mean=1.0, sigma=1.0, size=n_samples),
        "avg_daily_tx_volume": rng.lognormal(mean=0.5, sigma=0.5, size=n_samples),
        "loan_to_value_ratio": rng.random(n_samples) * 0.8,
        "total_loan_amount": rng.lognormal(mean=0.8, sigma=0.8, size=n_samples),
        "num_active_loans": rng.integers(0, 10, n_samples),
        "num_liquidations": rng.choice(
            [0, 1, 2, 3], n_samples, p=[0.8, 0.1, 0.05, 0.05]
        ),
        "credit_score_history_avg": rng.integers(500, 850, n_samples),
        "defi_protocol_count": rng.integers(1, 15, n_samples),
        "token_diversity_score": rng.random(n_samples),
        "primary_defi_protocol": rng.choice(
            ["Aave", "Compound", "MakerDAO", "Uniswap"], n_samples
        ),
        "wallet_type": rng.choice(["EVM", "Non-EVM", "Custodial"], n_samples),
        "country_code": rng.choice(countries, n_samples),
        "credit_risk_score": rng.choice([0, 1], n_samples, p=[0.7, 0.3]),
    }
    df = pd.DataFrame(data)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    for column in ["total_eth_balance", "loan_to_value_ratio", "country_code"]:
        df.loc[df.sample(frac=0.05, random_state=seed).index, column] = np.nan
    df.to_csv(path, index=False)
    return path


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    dummy_data_path = generate_dummy_data()
    X_train_proc, X_test_proc, y_train, y_test = preprocess_data(
        data_path=dummy_data_path
    )
    logger.info("X_train: %s, X_test: %s", X_train_proc.shape, X_test_proc.shape)
