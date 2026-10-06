# AI Model Integration Example

Examples for integrating with BlockScore AI models.

## Using AI Models Directly (Python)

```python
import joblib
import pandas as pd

# Load credit scoring model
model = joblib.load('code/ai_models/artifacts/credit_scoring_model.pkl')

# Prepare features
features = {
    'income': 50000,
    'debt_ratio': 0.35,
    'payment_history': 0.95,
    'loan_count': 3,
    'loan_amount': 5000,
    'age': 30,
    'credit_utilization': 0.25
}

# Predict credit score
X = pd.DataFrame([features])
score = model.predict(X)[0]
print(f"Predicted Credit Score: {score:.0f}")

# Get feature importance
importance = model.feature_importances_
for feature, imp in zip(features.keys(), importance):
    print(f"{feature}: {imp:.3f}")
```

## Via API (Python)

```python
import requests

# AI Model API
AI_API_URL = "http://localhost:5001"  # If running code/ai_models (make serve)

# Prepare blockchain data
blockchain_data = {
    "credit_history": [
        {
            "timestamp": 1640000000,
            "amount": 5000,
            "recordType": "loan",
            "repaid": True,
            "repaymentTimestamp": 1642592000
        }
    ]
}

# Calculate score
response = requests.post(
    f"{AI_API_URL}/calculate_score",
    json=blockchain_data
)

result = response.json()
print(f"Credit Score: {result['score']}")
print(f"Factors: {result['factors']}")
```
