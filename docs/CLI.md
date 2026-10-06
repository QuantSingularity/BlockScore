# BlockScore CLI Reference

Command-line interface documentation for BlockScore scripts and tools.

## Table of Contents

- [Setup Scripts](#setup-scripts)
- [Deployment Scripts](#deployment-scripts)
- [Development Scripts](#development-scripts)
- [Smart Contract Commands](#smart-contract-commands)
- [Database Commands](#database-commands)

## Setup Scripts

### setup_blockscore_env.sh

Automated environment setup for BlockScore.

**Location**: `scripts/setup_blockscore_env.sh`

**Usage**:

```bash
./scripts/setup_blockscore_env.sh
```

**What it does**:

1. Creates Python virtual environments (AI models + backend)
2. Installs Python dependencies from requirements.txt
3. Installs Node.js dependencies (backend + frontend)
4. Sets up project structure

**Requirements**: Python 3.8+, Node.js 16+, npm

### run_blockscore.sh

Start all BlockScore services.

**Location**: `scripts/run_blockscore.sh`

**Usage**:

```bash
./scripts/run_blockscore.sh
```

**Services started**:

- Backend API (Port 5000)
- Web Frontend (Port 3000)
- AI Model Server (if configured)

## Deployment Scripts

### smart_contract_deploy.sh

Deploy smart contracts to blockchain network.

**Location**: `scripts/smart_contract_deploy.sh`

**Usage**:

```bash
./scripts/smart_contract_deploy.sh [network]
```

**Arguments**:

| Argument  | Description               | Example                             |
| --------- | ------------------------- | ----------------------------------- |
| `network` | Target blockchain network | `development`, `testnet`, `mainnet` |

**Examples**:

```bash
# Deploy to local Ganache
./scripts/smart_contract_deploy.sh development

# Deploy to Polygon Mumbai testnet
./scripts/smart_contract_deploy.sh testnet

# Deploy to Polygon mainnet
./scripts/smart_contract_deploy.sh mainnet
```

### component_restart.sh

Restart specific BlockScore components.

**Location**: `scripts/component_restart.sh`

**Usage**:

```bash
./scripts/component_restart.sh [component]
```

**Components**:

| Component  | Description               |
| ---------- | ------------------------- |
| `backend`  | Restart Flask backend API |
| `frontend` | Restart React frontend    |
| `ai_model` | Restart AI model server   |
| `all`      | Restart all components    |

**Examples**:

```bash
# Restart backend only
./scripts/component_restart.sh backend

# Restart all services
./scripts/component_restart.sh all
```

## Development Scripts

### lint-all.sh

Run linters on entire codebase.

**Location**: `scripts/lint-all.sh`

**Usage**:

```bash
./scripts/lint-all.sh [--fix]
```

**Flags**:

- `--fix`: Automatically fix linting issues

**What it checks**:

- Python: Black, Flake8, isort
- JavaScript/TypeScript: ESLint, Prettier
- Solidity: Solhint

**Example**:

```bash
# Check for issues
./scripts/lint-all.sh

# Auto-fix issues
./scripts/lint-all.sh --fix
```

### code_quality_check.sh

Comprehensive code quality analysis.

**Location**: `scripts/code_quality_check.sh`

**Usage**:

```bash
./scripts/code_quality_check.sh
```

**Checks performed**:

1. Linting (syntax, style)
2. Static analysis
3. Security vulnerabilities
4. Code complexity
5. Test coverage

## Smart Contract Commands

### Hardhat Commands

**Compile contracts** (fully offline, via the local `solc` npm package):

```bash
cd code/blockchain
npm run compile
```

**Run tests**:

```bash
cd code/blockchain
npm test
```

**Deploy contracts**:

```bash
cd code/blockchain

# Local development (deploys all 5 contracts and wires up their roles)
npm run deploy:local
# equivalent to: npx hardhat run scripts/deploy.js --network development

# A real network - first add a matching entry to hardhat.config.js's
# networks block (RPC url + account key), then:
npx hardhat run scripts/deploy.js --network mumbai
npx hardhat run scripts/deploy.js --network polygon
```

**Console**:

```bash
cd code/blockchain
npx hardhat console --network development
```

### Contract Interaction Examples

```javascript
// In hardhat console
const CreditScore = await ethers.getContractFactory("CreditScore");
const creditScore = await CreditScore.attach("<deployed address>");

// Add credit record
await creditScore.addCreditRecord(
  "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
  1000,
  "loan",
  5,
);

// Get credit profile
const profile = await CreditScore.getCreditProfile(
  "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
);
console.log(profile);
```

## Database Commands

### Flask-SQLAlchemy (Database Initialization)

**Initialize database**:

```bash
cd code/backend
source venv/bin/activate
python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all()"
```

### Alembic Migrations (If configured)

**Create migration**:

```bash
cd code/backend
alembic revision --autogenerate -m "Description of changes"
```

**Apply migrations**:

```bash
cd code/backend
alembic upgrade head
```

**Rollback migration**:

```bash
cd code/backend
alembic downgrade -1
```

## Backend API Commands

### Start Development Server

```bash
cd code/backend
source venv/bin/activate
python app.py
```

### Start Production Server (Gunicorn)

```bash
cd code/backend
source venv/bin/activate
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Run Tests

```bash
cd code/backend
source venv/bin/activate
pytest
pytest --cov=. --cov-report=html
```

## Frontend Commands

### Web Frontend

**Start development server**:

```bash
cd web-frontend
npm start
```

**Build for production**:

```bash
cd web-frontend
npm run build
```

**Run tests**:

```bash
cd web-frontend
npm test
```

### Mobile Frontend

**Start Metro bundler**:

```bash
cd mobile-frontend
npm start
```

**Run on iOS**:

```bash
cd mobile-frontend
npm run ios
```

**Run on Android**:

```bash
cd mobile-frontend
npm run android
```

## AI Model Commands

### Train Model

```bash
cd code/ai_models
source venv_ai/bin/activate
make train
```

### Start AI Model Server

```bash
cd code/ai_models
source venv_ai/bin/activate
make serve
```

## CLI Command Reference Table

| Command                         | Arguments           | Description                                | Example                                              |
| ------------------------------- | ------------------- | ------------------------------------------ | ---------------------------------------------------- |
| `setup_blockscore_env.sh`       | None                | Setup development environment              | `./scripts/setup_blockscore_env.sh`                  |
| `run_blockscore.sh`             | None                | Start all services                         | `./scripts/run_blockscore.sh`                        |
| `smart_contract_deploy.sh`      | `-n [network] [-v]` | Deploy smart contracts                     | `./scripts/smart_contract_deploy.sh -n test`         |
| `component_restart.sh`          | `[component]`       | Restart specific component                 | `./scripts/component_restart.sh backend`             |
| `lint-all.sh`                   | `[--fix]`           | Run code linters                           | `./scripts/lint-all.sh --fix`                        |
| `code_quality_check.sh`         | None                | Run quality checks                         | `./scripts/code_quality_check.sh`                    |
| `hardhat compile`               | None                | Compile Solidity contracts                 | `cd code/blockchain && npm run compile`              |
| `hardhat test`                  | None                | Run contract tests                         | `cd code/blockchain && npm test`                     |
| `hardhat run scripts/deploy.js` | `--network [name]`  | Deploy contracts (all 5, with roles wired) | `npx hardhat run scripts/deploy.js --network mumbai` |
| `python app.py`                 | None                | Start Flask backend                        | `cd code/backend && python app.py`                   |
| `npm start`                     | None                | Start React frontend                       | `cd web-frontend && npm start`                       |
| `pytest`                        | `[options]`         | Run backend tests                          | `cd code/backend && pytest`                          |

## Environment-Specific Commands

### Development

```bash
# Start local blockchain
ganache-cli -p 8545

# Start backend (development mode)
cd code/backend && FLASK_ENV=development python app.py

# Start frontend (development mode)
cd web-frontend && npm start
```

### Production

```bash
# Start backend (production mode)
cd code/backend && gunicorn -w 4 -b 0.0.0.0:5000 app:app

# Serve frontend build
cd web-frontend && npm run build
# Then serve with nginx or similar
```

## Troubleshooting Commands

### Check Service Status

```bash
# Check if backend is running
curl http://localhost:5000/api/health

# Check if frontend is accessible
curl http://localhost:3000

# Check blockchain connection
curl -X POST http://localhost:8545 -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

### View Logs

```bash
# Backend logs
tail -f code/backend/logs/blockscore.log

# Frontend logs (development)
# Check terminal where npm start is running

# Smart contract deployment logs
cat code/blockchain/deployment.log
```

## Next Steps

- [API Reference](API.md) - Explore API endpoints
- [Configuration](CONFIGURATION.md) - Configure services
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues

---

**Need Help?** Check the [Troubleshooting Guide](TROUBLESHOOTING.md) or [GitHub Issues](https://github.com/quantsingularity/BlockScore/issues).
