# BlockScore Configuration Guide

Comprehensive configuration guide for all BlockScore components.

## Table of Contents

- [Environment Variables](#environment-variables)
- [Backend Configuration](#backend-configuration)
- [Frontend Configuration](#frontend-configuration)
- [Smart Contract Configuration](#smart-contract-configuration)
- [Infrastructure Configuration](#infrastructure-configuration)

## Environment Variables

### Backend Environment Variables

Configuration file: `code/backend/.env`

| Option                      | Type   | Default                                      | Description                                               | Where to set           |
| --------------------------- | ------ | -------------------------------------------- | --------------------------------------------------------- | ---------------------- |
| `SECRET_KEY`                | string | `dev-secret-key-change-in-production`        | Flask secret key for session management                   | `.env`                 |
| `FLASK_ENV`                 | string | `development`                                | Flask environment: `development`, `production`, `testing` | `.env`                 |
| `DATABASE_URL`              | string | `sqlite:///blockscore.db`                    | Database connection string                                | `.env`                 |
| `JWT_SECRET_KEY`            | string | `jwt-secret-key-change-in-production`        | Secret key for JWT token signing                          | `.env`                 |
| `JWT_ACCESS_TOKEN_EXPIRES`  | int    | `900`                                        | Access token expiration time (seconds)                    | `.env`                 |
| `JWT_REFRESH_TOKEN_EXPIRES` | int    | `604800`                                     | Refresh token expiration time (seconds)                   | `.env`                 |
| `REDIS_URL`                 | string | `redis://localhost:6379/0`                   | Redis connection string                                   | `.env`                 |
| `BLOCKCHAIN_PROVIDER_URL`   | string | `http://localhost:8545`                      | Ethereum/Polygon RPC endpoint                             | `.env`                 |
| `CONTRACT_ADDRESS`          | string | `0x0000000000000000000000000000000000000000` | Deployed CreditScore contract address                     | `.env`                 |
| `PRIVATE_KEY`               | string | ``                                           | Private key for blockchain transactions                   | `.env` (never commit!) |
| `BCRYPT_LOG_ROUNDS`         | int    | `12`                                         | Bcrypt hashing rounds (higher = more secure, slower)      | `.env`                 |
| `RATE_LIMIT_DEFAULT`        | string | `100 per hour`                               | Default API rate limit                                    | `.env`                 |
| `RATE_LIMIT_LOGIN`          | string | `5 per minute`                               | Login endpoint rate limit                                 | `.env`                 |
| `LOG_LEVEL`                 | string | `INFO`                                       | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`        | `.env`                 |
| `CELERY_BROKER_URL`         | string | `redis://localhost:6379/1`                   | Celery message broker URL                                 | `.env`                 |
| `CELERY_RESULT_BACKEND`     | string | `redis://localhost:6379/2`                   | Celery result backend URL                                 | `.env`                 |
| `MIN_CREDIT_SCORE`          | int    | `300`                                        | Minimum possible credit score                             | `config.py`            |
| `MAX_CREDIT_SCORE`          | int    | `850`                                        | Maximum possible credit score                             | `config.py`            |
| `DEFAULT_CREDIT_SCORE`      | int    | `300`                                        | Default score for new users                               | `config.py`            |
| `DATA_RETENTION_DAYS`       | int    | `2555`                                       | User data retention period (days)                         | `config.py`            |
| `AUDIT_LOG_RETENTION_DAYS`  | int    | `3650`                                       | Audit log retention period (days)                         | `config.py`            |

### Frontend Environment Variables

Configuration file: `web-frontend/.env`

| Option                         | Type   | Default                     | Description                                                    | Where to set |
| ------------------------------ | ------ | --------------------------- | -------------------------------------------------------------- | ------------ |
| `REACT_APP_API_URL`            | string | `http://localhost:5000/api` | Backend API base URL                                           | `.env`       |
| `REACT_APP_BLOCKCHAIN_NETWORK` | string | `localhost`                 | Blockchain network: `localhost`, `testnet`, `mainnet`          | `.env`       |
| `REACT_APP_CONTRACT_ADDRESS`   | string | ``                          | CreditScore contract address                                   | `.env`       |
| `REACT_APP_CHAIN_ID`           | int    | `1337`                      | Chain ID (1337 for Ganache, 80001 for Mumbai, 137 for Polygon) | `.env`       |

### Mobile Frontend Environment Variables

Configuration file: `mobile-frontend/.env`

| Option               | Type   | Default                     | Description                  | Where to set |
| -------------------- | ------ | --------------------------- | ---------------------------- | ------------ |
| `API_URL`            | string | `http://localhost:5000/api` | Backend API base URL         | `.env`       |
| `BLOCKCHAIN_NETWORK` | string | `testnet`                   | Target blockchain network    | `.env`       |
| `CONTRACT_ADDRESS`   | string | ``                          | CreditScore contract address | `.env`       |

## Backend Configuration

### Database Configuration

#### SQLite (Development)

```bash
# .env
DATABASE_URL=sqlite:///blockscore.db
```

**Pros**: No setup required, file-based  
**Cons**: Not suitable for production, no concurrent writes

#### PostgreSQL (Production)

```bash
# .env
DATABASE_URL=postgresql://username:password@localhost:5432/blockscore
SQLALCHEMY_ENGINE_OPTIONS='{"pool_size": 10, "max_overflow": 20}'
```

**Installation:**

```bash
# Ubuntu/Debian
sudo apt install postgresql postgresql-contrib

# Create database
sudo -u postgres psql
CREATE DATABASE blockscore;
CREATE USER blockscore_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE blockscore TO blockscore_user;
```

#### MongoDB (Alternative)

```bash
# .env
MONGO_URI=mongodb://localhost:27017/blockscore
```

### Security Configuration

#### Password Policy

Configured in `code/backend/config.py`:

```python
PASSWORD_MIN_LENGTH = 8
PASSWORD_REQUIRE_UPPERCASE = True
PASSWORD_REQUIRE_LOWERCASE = True
PASSWORD_REQUIRE_NUMBERS = True
PASSWORD_REQUIRE_SPECIAL = True
```

#### JWT Configuration

```bash
# Generate secure keys
python3 -c "import secrets; print(secrets.token_hex(32))"

# .env
JWT_SECRET_KEY=your-generated-secret-key
JWT_ACCESS_TOKEN_EXPIRES=900        # 15 minutes
JWT_REFRESH_TOKEN_EXPIRES=604800    # 7 days
JWT_ALGORITHM=HS256
```

#### Rate Limiting

```bash
# .env
RATE_LIMIT_DEFAULT=100 per hour      # General API endpoints
RATE_LIMIT_LOGIN=5 per minute        # Login endpoint
RATE_LIMIT_REGISTER=5 per minute     # Registration endpoint
RATE_LIMIT_CREDIT_SCORE=10 per minute # Credit score calculation
```

**Rate limit syntax:**

- `100 per hour`
- `5 per minute`
- `1000 per day`

### Redis Configuration

```bash
# .env
REDIS_URL=redis://localhost:6379/0

# With password
REDIS_URL=redis://:password@localhost:6379/0

# Redis Cluster
REDIS_URL=redis://node1:6379,node2:6379,node3:6379/0
```

**Usage in BlockScore:**

- Session management
- Rate limiting storage
- Caching
- Celery message broker

### Logging Configuration

```bash
# .env
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE=logs/blockscore.log
LOG_MAX_BYTES=10485760  # 10MB
LOG_BACKUP_COUNT=5
```

**Log files location**: `code/backend/logs/`

### Blockchain Configuration

```bash
# Local Development (Ganache)
BLOCKCHAIN_PROVIDER_URL=http://localhost:8545
CONTRACT_ADDRESS=0x5FbDB2315678afecb367f032d93F642f64180aa3

# Polygon Mumbai Testnet
BLOCKCHAIN_PROVIDER_URL=https://rpc-mumbai.maticvigil.com
CONTRACT_ADDRESS=0x... # Your deployed contract
PRIVATE_KEY=0x... # Your wallet private key

# Polygon Mainnet
BLOCKCHAIN_PROVIDER_URL=https://polygon-rpc.com
CONTRACT_ADDRESS=0x... # Your deployed contract
PRIVATE_KEY=0x... # Your wallet private key (use secret management!)
```

**Security Note**: Never commit private keys! Use environment variables or secret management services.

## Frontend Configuration

### React Environment Variables

Create `web-frontend/.env`:

```bash
# API Configuration
REACT_APP_API_URL=http://localhost:5000/api

# Blockchain Configuration
REACT_APP_BLOCKCHAIN_NETWORK=localhost
REACT_APP_CONTRACT_ADDRESS=0x5FbDB2315678afecb367f032d93F642f64180aa3
REACT_APP_CHAIN_ID=1337

# Feature Flags
REACT_APP_ENABLE_WALLET_CONNECT=true
REACT_APP_ENABLE_BIOMETRIC_AUTH=false

# Analytics (optional)
REACT_APP_GOOGLE_ANALYTICS_ID=
```

### Build Configuration

```bash
# Development build
npm start

# Production build
npm run build

# Environment-specific builds
REACT_APP_ENV=staging npm run build
```

## Smart Contract Configuration

### Hardhat Configuration

File: `code/blockchain/hardhat.config.js`

Currently defines an in-memory `hardhat` network and a `development` network (`127.0.0.1:8545`, matching `npx hardhat node`). To deploy to a real network (e.g. Polygon Amoy), add a matching entry to the `networks` block:

```javascript
require("@nomicfoundation/hardhat-toolbox");
// ...existing offline-solc subtask override (see the file for why)...

module.exports = {
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: { enabled: true, runs: 200 },
      viaIR: true, // needed for CreditScoreV2/LoanContractV2 - see README.md
    },
  },
  networks: {
    hardhat: { chainId: 1337 },
    development: { url: "http://127.0.0.1:8545", chainId: 1337 },
    amoy: {
      url:
        process.env.POLYGON_AMOY_RPC_URL ||
        "https://rpc-amoy.polygon.technology",
      accounts: process.env.DEPLOYER_PRIVATE_KEY
        ? [process.env.DEPLOYER_PRIVATE_KEY]
        : [],
    },
    polygon: {
      url: process.env.POLYGON_RPC_URL || "https://polygon-rpc.com",
      accounts: process.env.DEPLOYER_PRIVATE_KEY
        ? [process.env.DEPLOYER_PRIVATE_KEY]
        : [],
    },
  },
  // Needed for `npx hardhat verify` (bundled in @nomicfoundation/hardhat-toolbox)
  etherscan: {
    apiKey: {
      polygonAmoy: process.env.POLYGONSCAN_API_KEY || "",
      polygon: process.env.POLYGONSCAN_API_KEY || "",
    },
  },
};
```

### Contract Deployment Configuration

```bash
# .env for smart contract deployment (code/blockchain/.env, or
# code/blockchain/.env.<network> - loaded by scripts/smart_contract_deploy.sh)
PROVIDER_URL=https://rpc-amoy.polygon.technology
PRIVATE_KEY=your-deployer-private-key
DEPLOYER_PRIVATE_KEY=your-deployer-private-key
POLYGONSCAN_API_KEY=your-polygonscan-api-key
# Only needed on non-local networks - see code/blockchain/scripts/deploy.js
LENDING_TOKEN_ADDRESS=0x...
TREASURY_ADDRESS=0x...
```

## Infrastructure Configuration

### Ansible Configuration

File: `infrastructure/ansible/inventory/hosts.yml`

```yaml
all:
  children:
    webservers:
      hosts:
        web01:
          ansible_host: 192.168.1.10
          ansible_user: ubuntu
        web02:
          ansible_host: 192.168.1.11
          ansible_user: ubuntu
    databases:
      hosts:
        db01:
          ansible_host: 192.168.1.20
          ansible_user: ubuntu
          postgresql_version: 14
```

### Docker Configuration

File: `docker-compose.yml` (to be created)

```yaml
version: "3.8"

services:
  backend:
    build: ./code/backend
    ports:
      - "5000:5000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/blockscore
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  frontend:
    build: ./web-frontend
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_API_URL=http://localhost:5000/api

  db:
    image: postgres:14
    environment:
      - POSTGRES_DB=blockscore
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

## Configuration Examples

### Development Environment

```bash
# code/backend/.env
FLASK_ENV=development
DEBUG=True
DATABASE_URL=sqlite:///blockscore.db
SECRET_KEY=dev-secret-key
JWT_SECRET_KEY=dev-jwt-secret
BLOCKCHAIN_PROVIDER_URL=http://localhost:8545
LOG_LEVEL=DEBUG
```

### Staging Environment

```ini
# code/backend/.env
FLASK_ENV=production
DEBUG=False
DATABASE_URL=postgresql://user:pass@staging-db:5432/blockscore
SECRET_KEY=<generate-strong-key>
JWT_SECRET_KEY=<generate-strong-key>
BLOCKCHAIN_PROVIDER_URL=https://rpc-mumbai.maticvigil.com
CONTRACT_ADDRESS=0x...
LOG_LEVEL=INFO
```

### Production Environment

```ini
# code/backend/.env
FLASK_ENV=production
DEBUG=False
DATABASE_URL=postgresql://user:pass@prod-db:5432/blockscore
SECRET_KEY=<use-secret-manager>
JWT_SECRET_KEY=<use-secret-manager>
PRIVATE_KEY=<use-secret-manager>
BLOCKCHAIN_PROVIDER_URL=https://polygon-rpc.com
CONTRACT_ADDRESS=0x...
REDIS_URL=redis://:password@prod-redis:6379/0
LOG_LEVEL=WARNING
FORCE_HTTPS=True
SESSION_COOKIE_SECURE=True
```

## Configuration Validation

### Validate Backend Configuration

```python
# code/backend/validate_config.py
from config import get_config

config = get_config()
print("Configuration loaded successfully!")
print(f"Environment: {config.FLASK_ENV}")
print(f"Database: {config.SQLALCHEMY_DATABASE_URI}")
print(f"Blockchain: {config.BLOCKCHAIN_PROVIDER_URL}")
```

### Check Required Variables

```bash
#!/bin/bash
# check_env.sh

REQUIRED_VARS=("SECRET_KEY" "JWT_SECRET_KEY" "DATABASE_URL")

for var in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!var}" ]; then
    echo "ERROR: $var is not set!"
    exit 1
  fi
done

echo "All required environment variables are set!"
```

## Troubleshooting Configuration

### Common Issues

**Issue**: Configuration not loading

**Solution**: Check `.env` file location and syntax

```bash
# Verify .env file
cat code/backend/.env | grep -v '^#' | grep -v '^$'
```

**Issue**: Database connection fails

**Solution**: Verify DATABASE_URL format

```bash
# Test PostgreSQL connection
psql $DATABASE_URL -c "SELECT version();"
```

**Issue**: Redis connection fails

**Solution**: Check Redis is running

```bash
redis-cli -u $REDIS_URL ping
```

## Next Steps

- [API Reference](API.md) - Explore available endpoints
- [Deployment Guide](deployment.md) - Deploy to production
- [Security Guide](SECURITY.md) - Security best practices

---

**Need Help?** Check the [Troubleshooting Guide](troubleshooting.md) for common configuration issues.
