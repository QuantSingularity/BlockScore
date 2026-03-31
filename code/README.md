# BlockScore — Docker Setup & Bug Fix Summary

## Quick Start

```bash
# 1. Copy and configure environment variables
cp .env.example .env   # then edit .env with your secrets

# 2. Build and start all services
docker-compose up --build -d

# 3. Check service health
docker-compose ps
curl http://localhost:5000/api/health
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| `backend` | 5000 | Flask REST API |
| `ai_model` | 5001 | Credit scoring ML server |
| `postgres` | 5432 | PostgreSQL 15 database |
| `redis` | 6379 | Cache + rate limiting + token blocklist |
| `celery_worker` | — | Async background jobs |

## Development Mode

```bash
docker-compose -f docker-compose.yml up postgres redis -d  # infra only
cd backend && flask run --debug                             # local backend
cd ai_models && python server.py                           # local AI server
```

## Useful Commands

```bash
# View logs
docker-compose logs -f backend
docker-compose logs -f ai_model

# Run migrations / create tables
docker-compose exec backend flask shell -c "from models import db; db.create_all()"

# Restart a single service
docker-compose restart backend

# Stop everything
docker-compose down

# Stop and remove volumes (destructive!)
docker-compose down -v
```

## Bug Fixes Applied

| # | File | Bug | Fix |
|---|------|-----|-----|
| 1 | All 5 model files | `db = SQLAlchemy()` duplicated → separate metadata, broken relationships | Import shared `db` from `models/__init__.py` |
| 2 | `models/user.py` | `validate_passwords_match` missing `@validates_schema` → passwords never checked | Added `@validates_schema` decorator |
| 3 | `models/user.py` | `fields.Bool(missing=False)` deprecated in marshmallow ≥3.13 | Changed to `load_default=False` |
| 4 | `models/loan.py` | `fields.Dict(missing={})` deprecated | Changed to `load_default={}` |
| 5 | `models/loan.py` | Instance methods used as static; insecure `random` for IDs | Converted to `@staticmethod`, replaced with `secrets` |
| 6 | `app.py` | `LoanApplication().generate_application_number()` — orphan DB object | Changed to `LoanApplication.generate_application_number()` |
| 7 | `app.py` | `loan_type=data["loan_type"]` — raw string into Enum column | Changed to `LoanType(data["loan_type"])` |
| 8 | `app.py` | `Limiter(app, key_func=...)` — flask-limiter 3.x API change | Changed to `Limiter(key_func=..., app=app, storage_uri="memory://")` |
| 9 | `app.py` | `blacklisted_tokens = set()` — revoked tokens valid after restart | Redis-backed `_revoke_token()` / `_is_token_revoked()` |
| 10 | `app.py` + 3 services | `Model.query.get(id)` deprecated in SQLAlchemy 2.x | Replaced with `db.session.get(Model, id)` |
| 11 | `compliance_service.py` | `KYCStatus.VERIFIED` / `KYCStatus.PENDING` — enum values don't exist | Fixed to `APPROVED` / `PENDING_REVIEW` |
| 12 | `blockchain_service.py` | `signed_txn.rawTransaction` renamed in web3.py v6 | Changed to `signed_txn.raw_transaction` |
| 13 | `credit_service.py` | Hardcoded `"../ai_models/..."` relative path breaks in Docker | Fixed with `os.path` from `__file__` |
| 14 | `app.py` | `CORS(origins="*")` insecure wildcard | Reads from `CORS_ORIGINS` env var |
| 15 | `app.py` | Missing `/api/auth/refresh` endpoint | Added with refresh-token rotation |
| 16 | `model_integration.py`, `api.py` | `joblib.load()` at import time crashes if `.pkl` missing | Wrapped in `try/except` with rule-based fallback |
| 17 | `model_integration.py`, `api.py` | `datetime.now().timestamp()` — dead unused call | Removed |
| 18 | `predict_score()` | Calls `model.predict()` with no `None` guard | Added rule-based fallback when model is `None` |
| 19 | `ai_models/server.py` | Default port 5000 conflicts with backend | Changed default to 5001 |
| 20 | `ai_models/server.py` | Naive `datetime.now()` in health endpoint | Changed to `datetime.now(timezone.utc)` |
