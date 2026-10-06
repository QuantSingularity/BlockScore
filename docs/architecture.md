# BlockScore Architecture Overview

## System Architecture

BlockScore follows a modular microservices architecture combining blockchain, AI, and traditional web technologies.

```
┌─────────────────────────────────────────────────────────────┐
│                         FRONTEND LAYER                       │
│  ┌──────────────────┐           ┌──────────────────┐       │
│  │   Web Dashboard  │           │   Mobile App     │       │
│  │   (React)        │           │  (React Native)  │       │
│  └─────────┬────────┘           └─────────┬────────┘       │
└────────────┼──────────────────────────────┼────────────────┘
             │                               │
             │         HTTP/REST             │
             └───────────────┬───────────────┘
                             │
┌────────────────────────────┼────────────────────────────────┐
│                      BACKEND API LAYER                       │
│             ┌───────────────┴──────────────┐                │
│             │   Flask API Server           │                │
│             │   (Python 3.8+)              │                │
│             │                               │                │
│             │  - Authentication (JWT)       │                │
│             │  - Credit API                 │                │
│             │  - Loan API                   │                │
│             │  - Audit Logging              │                │
│             └─────────┬──────┬──────┬──────┘                │
└───────────────────────┼──────┼──────┼───────────────────────┘
                        │      │      │
         ┌──────────────┘      │      └─────────────────┐
         │                     │                         │
┌────────┴────────┐   ┌────────┴─────────┐   ┌─────────┴──────────┐
│   AI/ML Layer   │   │  Blockchain      │   │    Data Layer      │
│                 │   │     Layer        │   │                    │
│  ┌───────────┐  │   │  ┌────────────┐ │   │  ┌──────────────┐  │
│  │ XGBoost   │  │   │  │ Ethereum/  │ │   │  │ PostgreSQL   │  │
│  │ Models    │  │   │  │ Polygon    │ │   │  │    or        │  │
│  ├───────────┤  │   │  ├────────────┤ │   │  │  SQLite      │  │
│  │ Fraud     │  │   │  │ Smart      │ │   │  └──────────────┘  │
│  │ Detection │  │   │  │ Contracts  │ │   │                    │
│  ├───────────┤  │   │  │ (Solidity) │ │   │  ┌──────────────┐  │
│  │ Risk      │  │   │  └────────────┘ │   │  │    Redis     │  │
│  │ Analytics │  │   │                 │   │  │  (Optional)  │  │
│  └───────────┘  │   └─────────────────┘   │  └──────────────┘  │
└─────────────────┘                          └────────────────────┘
```

## Component Details

### Frontend Layer

- **Web Dashboard**: React + Material-UI, Web3 integration
- **Mobile App**: React Native for iOS & Android

### Backend API Layer

- **Framework**: Flask (Python)
- **Authentication**: JWT with Flask-JWT-Extended
- **Rate Limiting**: Flask-Limiter with Redis
- **Database ORM**: SQLAlchemy
- **Validation**: Marshmallow schemas

### AI/ML Layer

- **Credit Scoring**: XGBoost, Random Forest
- **Fraud Detection**: Anomaly detection algorithms
- **Risk Analytics**: VaR, Sharpe ratio calculations
- **Feature Engineering**: Automated from blockchain data

### Blockchain Layer

- **Networks**: Ethereum, Polygon
- **Smart Contracts**: Solidity 0.8.0
- **Web3 Library**: Web3.py (backend), Web3.js (frontend)

### Data Layer

- **Primary DB**: PostgreSQL (production), SQLite (development)
- **Cache**: Redis for sessions and rate limiting
- **Blockchain**: On-chain credit records

## Data Flow

### Credit Score Calculation

```
User Request → API Authentication → Fetch Blockchain Data
                                           ↓
                              AI Model Preprocessing
                                           ↓
                              Credit Score Calculation
                                           ↓
                              Store in Database
                                           ↓
                              Return Score + Factors
```

### Loan Application

```
User Submits → API Validation → Check Credit Score
                                       ↓
                              Calculate Approval Probability
                                       ↓
                              Store Application in DB
                                       ↓
                              Optional: Create Smart Contract
                                       ↓
                              Return Application Status
```

## Module Mapping

| Module          | Files                              | Purpose                |
| --------------- | ---------------------------------- | ---------------------- |
| Backend API     | `code/backend/app.py`              | Main Flask application |
| Models          | `code/backend/models/*.py`         | Database models        |
| Services        | `code/backend/services/*.py`       | Business logic         |
| AI Models       | `code/ai_models/src/blockscore_ai` | ML models and training |
| Smart Contracts | `code/blockchain/contracts/*.sol`  | Solidity contracts     |
| Web Frontend    | `web-frontend/src/`                | React components       |
| Mobile Frontend | `mobile-frontend/`                 | React Native app       |

## Deployment Architecture

```
┌──────────────────────────────────────────────────────┐
│                    Load Balancer                      │
│                    (Nginx/ALB)                        │
└────────────────────────┬─────────────────────────────┘
                         │
          ┌──────────────┼──────────────┐
          │              │               │
    ┌─────┴────┐   ┌─────┴────┐   ┌─────┴────┐
    │ Backend  │   │ Backend  │   │ Backend  │
    │ Instance │   │ Instance │   │ Instance │
    └─────┬────┘   └─────┬────┘   └─────┬────┘
          │              │               │
          └──────────────┼───────────────┘
                         │
          ┌──────────────┴──────────────┐
          │                              │
    ┌─────┴────────┐           ┌────────┴──────┐
    │  PostgreSQL  │           │     Redis     │
    │   Cluster    │           │    Cluster    │
    └──────────────┘           └───────────────┘
```

## Security Architecture

- **Authentication**: JWT tokens (15min access, 7day refresh)
- **Authorization**: Role-based access control
- **Encryption**: Bcrypt for passwords, HTTPS for transport
- **Rate Limiting**: Per-endpoint and per-user limits
- **Audit Logging**: All sensitive operations logged
- **Input Validation**: Schema-based validation on all endpoints

See [Security Guide](SECURITY.md) for details.
