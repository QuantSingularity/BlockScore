from typing import Any

import joblib
import pandas as pd
from xgboost import XGBClassifier


def train_credit_model() -> Any:
    df = pd.read_csv("../../resources/datasets/financial_data.csv")
    X = df[["income", "debt_ratio", "payment_history"]]
    y = df["default_risk"]
    model = XGBClassifier(n_estimators=100)
    model.fit(X, y)
    joblib.dump(model, "../../credit_scoring_model.pkl")


if __name__ == "__main__":
    train_credit_model()
