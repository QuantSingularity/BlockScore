# BlockScore Automation Scripts

This directory contains automation scripts for the BlockScore project. These scripts are designed to streamline development workflows, improve consistency, and reduce manual effort.

All scripts resolve the project root relative to their own location, so they can be run from anywhere using `./scripts/<script-name>.sh` from the repository root, or via an absolute/relative path to the script itself.

## Scripts Overview

1. **unified_env_setup.sh** - Comprehensive environment setup script (system packages, Python, Node.js, blockchain tooling)
2. **setup_blockscore_env.sh** - Lightweight setup script that assumes prerequisites are already installed and just wires up each component's dependencies
3. **run_blockscore.sh** - Quick launcher for the backend only, for day-to-day development
4. **multi_component_build.sh** - Build orchestration for all components
5. **component_restart.sh** - Selective component restart automation
6. **smart_contract_deploy.sh** - Smart contract deployment automation (Hardhat)
7. **code_quality_check.sh** - Code quality and linting automation, with reporting
8. **lint-all.sh** - Linting and auto-fixing across the whole project in one pass

## Project Components

These scripts operate on the project's real components:

| Component    | Path              | Stack                                                                                                                                     |
| ------------ | ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `backend`    | `code/backend`    | Python / Flask (primary; also ships a minimal `package.json` for a few standalone Node.js service modules - see `code/backend/config.js`) |
| `ai`         | `code/ai_models`  | Python (dependencies in `requirements.txt`)                                                                                               |
| `blockchain` | `code/blockchain` | Solidity, Hardhat (see `hardhat.config.js` and `package.json`)                                                                            |
| `frontend`   | `web-frontend`    | React (Vite)                                                                                                                              |
| `mobile`     | `mobile-frontend` | React Native (CLI, not Expo)                                                                                                              |

The backend and AI models share a single Python virtual environment at
`<repo root>/venv`, created and populated by these scripts as needed.

The backend defaults to SQLite for local development and needs no database
service running. PostgreSQL and Redis are available via Docker Compose
(`code/docker-compose.yml`) for a fuller local stack.

This project uses **Hardhat**, not Truffle, for smart contracts. A local
chain is provided by Hardhat's own built-in node (`npx hardhat node`,
port 8545, matching the `development` network in `hardhat.config.js`) -
no separate Ganache install needed. Contracts compile fully offline via
the local `solc` npm package (see `code/blockchain/README.md` for why).

## Installation

The scripts are already part of this repository under `scripts/`. Just make sure they are executable:

```bash
chmod +x scripts/*.sh
```

## Usage Instructions

### Unified Environment Setup

This script automates the complete setup of the BlockScore development environment, including installing missing system packages (build tools, Python, Node.js, jq).

```bash
./scripts/unified_env_setup.sh
```

Features:

- Automatic OS detection and system package installation
- Python (backend + AI models) and Node.js (web-frontend, mobile-frontend) environment setup
- Blockchain development environment configuration (Hardhat)
- Environment variable management
- Project structure validation

### Lightweight Environment Setup

A minimal alternative to `unified_env_setup.sh` that assumes Python, Node.js, and Docker are already installed, and just installs each component's own dependencies.

```bash
./scripts/setup_blockscore_env.sh
```

### Run Backend Only

A quick launcher for the Flask backend during day-to-day development. For running multiple components together, use `component_restart.sh` instead.

```bash
./scripts/run_blockscore.sh
```

### Multi-Component Build

This script orchestrates the build/validation process for all BlockScore components.

```bash
./scripts/multi_component_build.sh [options] [components]
```

Options:

- `-h, --help`: Show help message
- `-p, --parallel`: Build components in parallel
- `-c, --clean`: Perform clean build

Components:

- `all`: Build all components (default)
- `blockchain`, `backend`, `frontend`, `mobile`, `ai`: Build specific components

"Build" means different things per component: compiling contracts (blockchain), installing Python dependencies (backend, ai), `npm run build` (frontend), and installing dependencies plus type-checking and testing (mobile, which has no universal native build command outside Xcode/Gradle/EAS).

Examples:

```bash
./scripts/multi_component_build.sh                         # Build all components sequentially
./scripts/multi_component_build.sh -p frontend backend     # Build frontend and backend in parallel
./scripts/multi_component_build.sh -c blockchain           # Clean and build blockchain contracts
```

### Component Restart

This script automates the process of selectively restarting only the components that have been modified, or watching for changes and restarting automatically.

```bash
./scripts/component_restart.sh [options] [components]
```

Options:

- `-h, --help`: Show help message
- `-f, --force`: Force restart even if no changes detected
- `-w, --watch`: Watch for changes and restart automatically

Components:

- `all`: Restart all components (default)
- `blockchain`, `backend`, `frontend`, `mobile`, `ai`: Restart specific components

Requires `jq` (installed by `unified_env_setup.sh`).

Examples:

```bash
./scripts/component_restart.sh                         # Restart all modified components
./scripts/component_restart.sh -f backend              # Force restart backend services
./scripts/component_restart.sh -w frontend backend     # Watch and restart frontend and backend when changes detected
```

### Smart Contract Deployment

This script automates the deployment of smart contracts to different blockchain networks via Hardhat. It deploys all five contracts (`GovernanceToken`, `CreditScore`, `CreditScoreV2`, `LoanContract`, `LoanContractV2`) and wires up the cross-contract roles they need (e.g. granting `LoanContractV2` `CREDIT_PROVIDER_ROLE` on `CreditScoreV2`) via `code/blockchain/scripts/deploy.js`.

```bash
./scripts/smart_contract_deploy.sh [options]
```

Options:

- `-h, --help`: Show help message
- `-n, --network <network>`: Specify network (development, test, mainnet)
- `-v, --verify`: Verify contracts on block explorer (requires `@nomicfoundation/hardhat-verify`, bundled in `@nomicfoundation/hardhat-toolbox`)
- `--no-gas-optimization`: Disable gas optimization
- `--no-security-check`: Disable security checks

`hardhat.config.js` currently only defines the `hardhat` (in-memory) and `development` (127.0.0.1:8545) networks. Deploying to `test` or `mainnet` requires adding a matching network entry there first (typically an RPC url + an account private key, using the `PROVIDER_URL`/`PRIVATE_KEY` environment variables this script already loads from `code/blockchain/.env.<network>`); the script checks for this and fails with a clear message if the network isn't configured yet.

Each deployment writes `code/blockchain/deployments/<network>/addresses.json` and `constructor-args.json` (the latter needed for `--verify`, since block explorer verification re-derives the deployed bytecode from each contract's constructor arguments).

Examples:

```bash
./scripts/smart_contract_deploy.sh                         # Deploy to development network
./scripts/smart_contract_deploy.sh -n test -v              # Deploy to test network and verify contracts
./scripts/smart_contract_deploy.sh -n mainnet -v           # Deploy to mainnet and verify contracts
```

### Code Quality Check

This script performs comprehensive code quality checks across all components and writes a Markdown report to `code_quality_reports/`. JavaScript/TypeScript checks run inside `web-frontend` and `mobile-frontend` using each project's own local ESLint configuration.

```bash
./scripts/code_quality_check.sh [options]
```

Options:

- `-h, --help`: Show help message
- `-f, --fix`: Automatically fix issues when possible
- `-v, --verbose`: Show detailed output
- `--js`, `--py`, `--sol`: Check only JavaScript/TypeScript, Python, or Solidity files

Examples:

```bash
./scripts/code_quality_check.sh                         # Check all file types
./scripts/code_quality_check.sh -f                      # Check all file types and fix issues
./scripts/code_quality_check.sh --js -f                 # Check JavaScript/TypeScript files and fix issues
```

### Lint All

A more direct, always-fix linting pass across the whole project in one command: Python (black, isort, flake8, pylint), JavaScript/TypeScript (ESLint, per-project), Solidity (solhint), YAML, and Terraform, plus trailing-whitespace and end-of-file cleanup repo-wide.

```bash
./scripts/lint-all.sh
```

## Integration with Development Workflow

These scripts can be integrated into your development workflow in several ways:

1. **Manual Execution**: Run scripts as needed during development
2. **Git Hooks**: `code_quality_check.sh` installs itself as a pre-commit hook on first run
3. **CI/CD Integration**: Scripts can be incorporated into CI/CD pipelines
4. **IDE Integration**: Configure your IDE to run these scripts for specific tasks

## Customization

All scripts are designed to be modular and customizable. You can modify them to fit your specific project requirements by editing the script files directly.

## Troubleshooting

If you encounter any issues with the scripts:

1. Check the log files in the `.blockscore_config` directory (and `build.log` / `deployment.log` at the repository root)
2. Ensure all dependencies are installed (`jq` is required by `component_restart.sh` and `smart_contract_deploy.sh`)
3. Verify that the project structure matches the expected structure (see Project Components above)
4. Run scripts with verbose output for more detailed information

## Contributing

Feel free to enhance these scripts by adding new features, fixing bugs, or improving documentation. Submit pull requests to the main BlockScore repository.
