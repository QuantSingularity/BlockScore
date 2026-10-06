# BlockScore Feature Matrix

Complete feature list with implementation details and examples.

## Core Features

| Feature                  | Short description         | Module / File                                | CLI flag / API                     | Example (path)                                               | Notes                           |
| ------------------------ | ------------------------- | -------------------------------------------- | ---------------------------------- | ------------------------------------------------------------ | ------------------------------- |
| User Registration        | Create new user accounts  | `code/backend/app.py`                        | `POST /api/auth/register`          | [examples/auth_example.md](examples/auth_example.md)         | Email validation required       |
| User Login               | JWT-based authentication  | `code/backend/app.py`                        | `POST /api/auth/login`             | [examples/auth_example.md](examples/auth_example.md)         | Returns access & refresh tokens |
| Credit Score Calculation | AI-powered credit scoring | `code/ai_models/src/blockscore_ai/api/`      | `POST /api/credit/calculate-score` | [examples/credit_scoring.md](examples/credit_scoring.md)     | Uses ML models                  |
| Credit History           | View transaction history  | `code/backend/models/credit.py`              | `GET /api/credit/history`          | [examples/credit_scoring.md](examples/credit_scoring.md)     | Paginated results               |
| Loan Application         | Submit loan requests      | `code/backend/app.py`                        | `POST /api/loans/apply`            | [examples/loan_application.md](examples/loan_application.md) | Rate limited: 3/hour            |
| Loan Calculator          | Calculate loan terms      | `code/backend/app.py`                        | `POST /api/loans/calculate`        | [examples/loan_application.md](examples/loan_application.md) | No auth required                |
| Smart Contract - Credit  | On-chain credit records   | `code/blockchain/contracts/CreditScore.sol`  | Contract methods                   | [SMART_CONTRACTS.md](SMART_CONTRACTS.md)                     | Solidity 0.8.0                  |
| Smart Contract - Loans   | On-chain loan management  | `code/blockchain/contracts/LoanContract.sol` | Contract methods                   | [SMART_CONTRACTS.md](SMART_CONTRACTS.md)                     | Automated repayment             |
| Web Dashboard            | React-based UI            | `web-frontend/`                              | `npm start`                        | [USAGE.md#web-interface](USAGE.md)                           | Material-UI components          |
| Mobile App               | React Native app          | `mobile-frontend/`                           | `npm start`                        | [USAGE.md#mobile-app](USAGE.md)                              | iOS & Android                   |
| Health Monitoring        | System status checks      | `code/backend/app.py`                        | `GET /api/health`                  | [API.md#health-check](API.md)                                | No auth required                |
| MFA Authentication       | Two-factor authentication | `code/backend/services/mfa_service.py`       | API integration                    | [SECURITY.md#mfa](SECURITY.md)                               | TOTP-based                      |
| Audit Logging            | Security event tracking   | `code/backend/services/audit_service.py`     | Automatic                          | N/A                                                          | 10-year retention               |
| Rate Limiting            | API throttling            | `code/backend/app.py`                        | Flask-Limiter                      | [SECURITY.md#rate-limits](SECURITY.md)                       | Redis-backed                    |

## AI/ML Features

| Feature             | Short description         | Module / File                                | CLI flag / API                   | Example (path)                                           | Notes                  |
| ------------------- | ------------------------- | -------------------------------------------- | -------------------------------- | -------------------------------------------------------- | ---------------------- |
| Credit Score Model  | XGBoost-based scoring     | `code/ai_models/src/blockscore_ai/scoring/`  | `ScoringService.score_history()` | [examples/ai_integration.md](examples/ai_integration.md) | v1.2.0 model           |
| Fraud Detection     | Anomaly detection         | `code/ai_models/src/blockscore_ai/research/` | `detect_fraud()`                 | [examples/ai_integration.md](examples/ai_integration.md) | Real-time analysis     |
| Risk Analytics      | Portfolio risk assessment | `code/ai_models/src/blockscore_ai/research/` | `calculate_risk()`               | [examples/ai_integration.md](examples/ai_integration.md) | VaR, Sharpe ratio      |
| Behavioral Analysis | Payment pattern analysis  | `code/ai_models/src/blockscore_ai/research/` | Automatic                        | N/A                                                      | Time series analysis   |
| Model Training      | Train custom models       | `code/ai_models/src/blockscore_ai/training/` | `make train`                     | N/A                                                      | Requires training data |
| Feature Engineering | Extract credit features   | `code/ai_models/src/blockscore_ai/scoring/`  | `preprocess_blockchain_data()`   | [examples/ai_integration.md](examples/ai_integration.md) | 7 key features         |

## Blockchain Features

| Feature               | Short description      | Module / File                                      | CLI flag / API                  | Example (path)                           | Notes                             |
| --------------------- | ---------------------- | -------------------------------------------------- | ------------------------------- | ---------------------------------------- | --------------------------------- |
| Ethereum Integration  | Connect to Ethereum    | `code/backend/services/blockchain_service.py`      | Web3.py                         | [SMART_CONTRACTS.md](SMART_CONTRACTS.md) | Supports a local Hardhat node     |
| Polygon Integration   | Polygon support        | `code/backend/services/blockchain_service.py`      | Web3.py                         | [SMART_CONTRACTS.md](SMART_CONTRACTS.md) | Lower gas fees                    |
| Wallet Connect        | MetaMask integration   | `web-frontend/src/`                                | Web3                            | [USAGE.md#wallet](USAGE.md)              | Browser extension                 |
| Contract Deployment   | Deploy smart contracts | `code/blockchain/`                                 | `hardhat run scripts/deploy.js` | [CLI.md#deploy](CLI.md)                  | Requires network config           |
| On-Chain Verification | Verify credit data     | `CreditScoreV2.addCreditRecord` (`dataHash` param) | `getCreditHistory()`            | [SMART_CONTRACTS.md](SMART_CONTRACTS.md) | Off-chain data integrity via hash |
| Governance Token      | DAO governance         | `code/blockchain/contracts/GovernanceToken.sol`    | ERC20                           | [SMART_CONTRACTS.md](SMART_CONTRACTS.md) | Platform governance               |

## Security Features

| Feature                  | Short description      | Module / File                                 | CLI flag / API     | Example (path)                          | Notes                   |
| ------------------------ | ---------------------- | --------------------------------------------- | ------------------ | --------------------------------------- | ----------------------- |
| JWT Authentication       | Token-based auth       | `code/backend/app.py`                         | Flask-JWT-Extended | [API.md#authentication](API.md)         | 15min expiry            |
| Password Hashing         | Bcrypt hashing         | `code/backend/models/user.py`                 | 12 rounds          | [SECURITY.md#passwords](SECURITY.md)    | Industry standard       |
| Account Locking          | Brute force protection | `code/backend/models/user.py`                 | Automatic          | [SECURITY.md#account-lock](SECURITY.md) | 30min lockout           |
| CORS Protection          | Cross-origin policy    | `code/backend/app.py`                         | Flask-CORS         | [SECURITY.md#cors](SECURITY.md)         | Configurable origins    |
| Input Validation         | Request validation     | Marshmallow schemas                           | Automatic          | [API.md#validation](API.md)             | Schema-based            |
| SQL Injection Protection | ORM-based queries      | SQLAlchemy                                    | Automatic          | N/A                                     | Parameterized queries   |
| Compliance Service       | GDPR/regulatory        | `code/backend/services/compliance_service.py` | API integration    | [SECURITY.md#compliance](SECURITY.md)   | Data retention policies |

## Infrastructure Features

| Feature             | Short description      | Module / File                | CLI flag / API      | Example (path)                            | Notes                |
| ------------------- | ---------------------- | ---------------------------- | ------------------- | ----------------------------------------- | -------------------- |
| Docker Support      | Containerization       | `Dockerfile` (planned)       | `docker-compose up` | [DEPLOYMENT.md#docker](DEPLOYMENT.md)     | Coming soon          |
| Ansible Automation  | Infrastructure as Code | `infrastructure/ansible/`    | `ansible-playbook`  | [DEPLOYMENT.md#ansible](DEPLOYMENT.md)    | Role-based           |
| CI/CD Pipeline      | GitHub Actions         | `.github/workflows/cicd.yml` | Automatic           | N/A                                       | Test + Deploy        |
| Monitoring          | Prometheus/Grafana     | `infrastructure/`            | Metrics API         | [DEPLOYMENT.md#monitoring](DEPLOYMENT.md) | Performance tracking |
| Database Migrations | Schema versioning      | Alembic                      | `alembic upgrade`   | [CLI.md#migrations](CLI.md)               | Version controlled   |
| Backup Automation   | Scheduled backups      | Ansible scripts              | Cron jobs           | [DEPLOYMENT.md#backup](DEPLOYMENT.md)     | Daily backups        |

## Development Tools

| Feature               | Short description     | Module / File                      | CLI flag / API                     | Example (path)                     | Notes             |
| --------------------- | --------------------- | ---------------------------------- | ---------------------------------- | ---------------------------------- | ----------------- |
| Setup Script          | Automated environment | `scripts/setup_blockscore_env.sh`  | `./setup_blockscore_env.sh`        | [INSTALLATION.md](INSTALLATION.md) | Creates venvs     |
| Run Script            | Start all services    | `scripts/run_blockscore.sh`        | `./run_blockscore.sh`              | [QUICKSTART.md](QUICKSTART.md)     | One command start |
| Lint Script           | Code quality check    | `scripts/lint-all.sh`              | `./lint-all.sh`                    | [CONTRIBUTING.md](CONTRIBUTING.md) | ESLint + Prettier |
| Component Restart     | Restart services      | `scripts/component_restart.sh`     | `./component_restart.sh [service]` | [CLI.md#restart](CLI.md)           | Zero-downtime     |
| Smart Contract Deploy | Deploy contracts      | `scripts/smart_contract_deploy.sh` | `./smart_contract_deploy.sh`       | [CLI.md#deploy](CLI.md)            | Network selection |
| Code Quality Check    | Automated QA          | `scripts/code_quality_check.sh`    | `./code_quality_check.sh`          | [CONTRIBUTING.md](CONTRIBUTING.md) | Pre-commit hooks  |

## API Endpoints Summary

| Endpoint                      | Method | Auth | Rate Limit | Description            | Version |
| ----------------------------- | ------ | ---- | ---------- | ---------------------- | ------- |
| `/api/health`                 | GET    | No   | Unlimited  | Health check           | v1.0    |
| `/api/auth/register`          | POST   | No   | 5/min      | User registration      | v1.0    |
| `/api/auth/login`             | POST   | No   | 5/min      | User login             | v1.0    |
| `/api/auth/logout`            | POST   | Yes  | 100/hour   | User logout            | v1.0    |
| `/api/credit/calculate-score` | POST   | Yes  | 10/min     | Calculate credit score | v1.0    |
| `/api/credit/history`         | GET    | Yes  | 100/hour   | Get credit history     | v1.0    |
| `/api/loans/apply`            | POST   | Yes  | 3/hour     | Apply for loan         | v1.0    |
| `/api/loans/calculate`        | POST   | Yes  | 100/hour   | Calculate loan terms   | v1.0    |
| `/api/profile`                | GET    | Yes  | 100/hour   | Get user profile       | v1.0    |

## Platform Support

| Platform           | Component | Status         | Version | Notes                    |
| ------------------ | --------- | -------------- | ------- | ------------------------ |
| Ubuntu 20.04+      | Backend   | ✅ Supported   | 1.0.0   | Primary development OS   |
| Ubuntu 20.04+      | Frontend  | ✅ Supported   | 1.0.0   | Node.js 16+ required     |
| macOS 11+          | Backend   | ✅ Supported   | 1.0.0   | Homebrew recommended     |
| macOS 11+          | Frontend  | ✅ Supported   | 1.0.0   | Native support           |
| Windows 10+ (WSL2) | Backend   | ✅ Supported   | 1.0.0   | WSL2 recommended         |
| Windows 10+ (WSL2) | Frontend  | ✅ Supported   | 1.0.0   | Native or WSL2           |
| Docker             | All       | 🚧 Coming Soon | N/A     | Containerization planned |
| iOS 13+            | Mobile    | ✅ Supported   | 1.0.0   | React Native             |
| Android 8+         | Mobile    | ✅ Supported   | 1.0.0   | React Native             |

## Database Support

| Database   | Status       | Use Case         | Version | Notes                      |
| ---------- | ------------ | ---------------- | ------- | -------------------------- |
| SQLite     | ✅ Supported | Development      | 3.x     | Default, file-based        |
| PostgreSQL | ✅ Supported | Production       | 12+     | Recommended for production |
| MongoDB    | ⚠️ Partial   | Off-chain data   | 4.4+    | Optional, for analytics    |
| Redis      | ✅ Supported | Caching/Sessions | 6.0+    | Required for rate limiting |

## Blockchain Networks

| Network          | Status       | Chain ID | Use Case    | Gas Cost     |
| ---------------- | ------------ | -------- | ----------- | ------------ |
| Ganache (Local)  | ✅ Supported | 1337     | Development | Free         |
| Ethereum Goerli  | ✅ Supported | 5        | Testing     | Test ETH     |
| Polygon Mumbai   | ✅ Supported | 80001    | Testing     | Test MATIC   |
| Polygon Mainnet  | ✅ Supported | 137      | Production  | Low (~$0.01) |
| Ethereum Mainnet | ⚠️ Supported | 1        | Production  | High (~$10+) |

---
