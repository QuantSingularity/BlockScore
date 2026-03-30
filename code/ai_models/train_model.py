from typing import Any
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor
from core.logging import get_logger

logger = get_logger(__name__)


def generate_synthetic_data(n_samples: Any = 1000) -> Any:
    """
    Generate synthetic financial data for training the credit scoring model
    """
    np.random.seed(42)
    income = np.random.normal(50000, 20000, n_samples)
    debt_ratio = np.random.beta(2, 5, n_samples)
    payment_history = np.random.binomial(10, 0.8, n_samples) / 10
    loan_count = np.random.poisson(3, n_samples)
    loan_amount = np.random.lognormal(8, 1, n_samples)
    age = np.random.normal(35, 10, n_samples)
    age = np.clip(age, 18, 80)
    credit_utilization = np.random.beta(2, 4, n_samples)
    base_score = (
        300
        + payment_history * 300
        + income / 100000 * 150
        - debt_ratio * 200
        + np.log1p(loan_count) * 50
        - credit_utilization * 100
    )
    noise = np.random.normal(0, 30, n_samples)
    credit_score = base_score + noise
    credit_score = np.clip(credit_score, 300, 850).astype(int)
    data = pd.DataFrame(
        {
            "income": income,
            "debt_ratio": debt_ratio,
            "payment_history": payment_history,
            "loan_count": loan_count,
            "loan_amount": loan_amount,
            "age": age,
            "credit_utilization": credit_utilization,
            "credit_score": credit_score,
        }
    )
    return data


def preprocess_data(df: Any) -> Any:
    """
    Preprocess data for model training
    """
    X = df.drop("credit_score", axis=1)
    y = df["credit_score"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    return (X_train, X_test, y_train, y_test)


def train_model(X_train: Any, y_train: Any) -> Any:
    """
    Train XGBoost model for credit scoring
    """
    model = XGBRegressor(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=5,
        objective="reg:squarederror",
        random_state=42,
    )
    model.fit(X_train, y_train)
    return model


def evaluate_model(model: Any, X_test: Any, y_test: Any) -> Any:
    """
    Evaluate model performance
    """
    predictions = model.predict(X_test)
    mse = np.mean((predictions - y_test) ** 2)
    rmse = np.sqrt(mse)
    mae = np.mean(np.abs(predictions - y_test))
    logger.info("Model Performance:")
    logger.info(f"Mean Squared Error: {mse:.2f}")
    logger.info(f"Root Mean Squared Error: {rmse:.2f}")
    logger.info(f"Mean Absolute Error: {mae:.2f}")
    return (mse, rmse, mae)


def save_model(model: Any, output_path: Any) -> Any:
    """
    Save trained model to disk
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    joblib.dump(model, output_path)
    logger.info(f"Model saved to {output_path}")


def main() -> Any:
    os.makedirs("../ai_models", exist_ok=True)
    logger.info("Generating synthetic financial data...")
    data = generate_synthetic_data(n_samples=5000)
    data_path = "../ai_models/financial_data.csv"
    data.to_csv(data_path, index=False)
    logger.info(f"Data saved to {data_path}")
    logger.info("Preprocessing data...")
    X_train, X_test, y_train, y_test = preprocess_data(data)
    logger.info("Training credit scoring model...")
    model = train_model(X_train, y_train)
    logger.info("Evaluating model performance...")
    evaluate_model(model, X_test, y_test)
    model_path = "../ai_models/credit_scoring_model.pkl"
    save_model(model, model_path)
    logger.info("Model training complete!")


if __name__ == "__main__":
    main()
