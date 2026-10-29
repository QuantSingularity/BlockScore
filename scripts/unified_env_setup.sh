#!/bin/bash
# ========================================================================
# BlockScore Unified Environment Setup Script
#
# This script automates the complete setup of the BlockScore development
# environment, including all dependencies, configurations, and initial
# setup.
#
# Features:
# - Automatic OS detection and system package installation
# - Python (backend + AI models), Node.js (web-frontend, mobile-frontend)
#   environment setup
# - Blockchain development environment configuration (Hardhat)
# - Environment variable management
# - Project structure validation
#
# Note: the backend defaults to SQLite for local development and does not
# require any database service to be running. PostgreSQL and Redis are
# available via Docker Compose (code/docker-compose.yml) for a fuller
# local stack, or production-like configurations.
# ========================================================================

# Set strict error handling
set -e

# Define colors for terminal output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print banner
echo -e "${BLUE}================================================================${NC}"
echo -e "${BLUE}          BlockScore Development Environment Setup              ${NC}"
echo -e "${BLUE}================================================================${NC}"

# Resolve the project root relative to this script's own location, so it
# works no matter which directory it is invoked from.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONFIG_DIR="${PROJECT_DIR}/.blockscore_config"

cd "${PROJECT_DIR}"

# Create configuration directory if it doesn't exist
mkdir -p "${CONFIG_DIR}"

# Function to check if a command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Run a command with sudo only when sudo is available and we are not
# already root (common in containers/CI, where sudo may not even be
# installed).
maybe_sudo() {
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
  elif command_exists sudo; then
    sudo "$@"
  else
    echo -e "${RED}This step requires root privileges and sudo is not available. Please run as root or install sudo.${NC}"
    return 1
  fi
}

# Function to detect OS
detect_os() {
  echo -e "${BLUE}Detecting operating system...${NC}"

  if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    if command_exists apt-get; then
      PACKAGE_MANAGER="apt-get"
    elif command_exists yum; then
      PACKAGE_MANAGER="yum"
    elif command_exists dnf; then
      PACKAGE_MANAGER="dnf"
    else
      echo -e "${RED}Unsupported Linux distribution. Please install dependencies manually.${NC}"
      exit 1
    fi
  elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    if command_exists brew; then
      PACKAGE_MANAGER="brew"
    else
      echo -e "${YELLOW}Homebrew not found. Installing Homebrew...${NC}"
      /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
      PACKAGE_MANAGER="brew"
    fi
  else
    echo -e "${RED}Unsupported operating system: $OSTYPE${NC}"
    exit 1
  fi

  echo -e "${GREEN}Detected OS: $OS using $PACKAGE_MANAGER${NC}"
}

# Function to install system dependencies
install_system_dependencies() {
  echo -e "${BLUE}Installing system dependencies...${NC}"

  if [[ "$PACKAGE_MANAGER" == "apt-get" ]]; then
    maybe_sudo apt-get update || echo -e "${YELLOW}Warning: some package indices could not be updated; continuing with what is available.${NC}"
    maybe_sudo apt-get install -y build-essential curl wget git python3 python3-pip python3-venv jq
  elif [[ "$PACKAGE_MANAGER" == "yum" || "$PACKAGE_MANAGER" == "dnf" ]]; then
    maybe_sudo "$PACKAGE_MANAGER" update -y
    maybe_sudo "$PACKAGE_MANAGER" install -y gcc gcc-c++ make curl wget git python3 python3-pip python3-devel jq
  elif [[ "$PACKAGE_MANAGER" == "brew" ]]; then
    brew update
    brew install git python@3 wget jq
  fi

  echo -e "${GREEN}System dependencies installed successfully.${NC}"
}

# Function to setup Python environment (backend + AI models)
setup_python_environment() {
  echo -e "${BLUE}Setting up Python environment...${NC}"

  if ! command_exists python3; then
    echo -e "${RED}Python 3 not found. Please install Python 3.9 or higher.${NC}"
    exit 1
  fi

  PYTHON_VERSION=$(python3 --version | cut -d ' ' -f 2)
  echo -e "${GREEN}Found Python $PYTHON_VERSION${NC}"

  # Create a shared virtual environment for the backend and AI models if it
  # doesn't exist yet.
  if [ ! -d "${PROJECT_DIR}/venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    python3 -m venv "${PROJECT_DIR}/venv"
  fi

  echo -e "${YELLOW}Activating Python virtual environment...${NC}"
  # shellcheck source=/dev/null
  source "${PROJECT_DIR}/venv/bin/activate"

  echo -e "${YELLOW}Upgrading pip...${NC}"
  pip install --upgrade pip

  # Install backend dependencies
  BACKEND_REQUIREMENTS="${PROJECT_DIR}/code/backend/requirements.txt"
  if [ -f "$BACKEND_REQUIREMENTS" ]; then
    echo -e "${YELLOW}Installing backend Python dependencies...${NC}"
    if ! pip install -r "$BACKEND_REQUIREMENTS"; then
      echo -e "${RED}Warning: failed to install one or more backend dependencies.${NC}"
    fi
  else
    echo -e "${YELLOW}Warning: backend requirements.txt not found at ${BACKEND_REQUIREMENTS}${NC}"
  fi

  # Install AI model training dependencies
  AI_MODELS_REQUIREMENTS="${PROJECT_DIR}/code/ai_models/requirements.txt"
  if [ -f "$AI_MODELS_REQUIREMENTS" ]; then
    echo -e "${YELLOW}Installing AI model Python dependencies...${NC}"
    if ! pip install -r "$AI_MODELS_REQUIREMENTS"; then
      echo -e "${RED}Warning: failed to install one or more AI model dependencies.${NC}"
      echo -e "${YELLOW}This is often caused by an old pinned package lacking a prebuilt wheel for your Python version.${NC}"
    fi
  else
    echo -e "${YELLOW}Warning: AI model requirements.txt not found at ${AI_MODELS_REQUIREMENTS}${NC}"
  fi

  deactivate

  echo -e "${GREEN}Python environment setup complete.${NC}"
  echo -e "${GREEN}Activate it later with: source ${PROJECT_DIR}/venv/bin/activate${NC}"
}

# Function to setup Node.js environment
setup_node_environment() {
  echo -e "${BLUE}Setting up Node.js environment...${NC}"

  # Check if Node.js is installed
  if command_exists node; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}Found Node.js $NODE_VERSION${NC}"
  else
    echo -e "${YELLOW}Node.js not found. Installing Node.js...${NC}"

    if [[ "$OS" == "linux" ]]; then
      curl -fsSL https://deb.nodesource.com/setup_20.x | maybe_sudo -E bash -
      maybe_sudo "$PACKAGE_MANAGER" install -y nodejs
    elif [[ "$OS" == "macos" ]]; then
      brew install node@20
    fi

    NODE_VERSION=$(node --version)
    echo -e "${GREEN}Installed Node.js $NODE_VERSION${NC}"
  fi

  # Install web-frontend dependencies (React, via Vite)
  if [ -d "${PROJECT_DIR}/web-frontend" ]; then
    echo -e "${YELLOW}Installing web-frontend dependencies...${NC}"
    (
      cd "${PROJECT_DIR}/web-frontend"
      npm install
      if [ ! -f ".env" ] && [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${YELLOW}Created .env file for web-frontend from .env.example.${NC}"
      fi
    )
  fi

  # Install mobile-frontend dependencies (React Native)
  if [ -d "${PROJECT_DIR}/mobile-frontend" ]; then
    echo -e "${YELLOW}Installing mobile-frontend dependencies...${NC}"
    (
      cd "${PROJECT_DIR}/mobile-frontend"
      npm install
      if [ ! -f ".env" ] && [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${YELLOW}Created .env file for mobile-frontend from .env.example.${NC}"
      fi
    )
  fi

  echo -e "${GREEN}Node.js environment setup complete.${NC}"
}

# Function to remind the developer how to bring up PostgreSQL and Redis.
# The backend works standalone against SQLite with no extra services
# running; Docker Compose provides PostgreSQL and Redis for a fuller local
# stack or production-like configuration.
setup_datastores() {
  echo -e "${BLUE}Checking local data store options...${NC}"

  if command_exists docker; then
    echo -e "${GREEN}Docker found. You can start PostgreSQL and Redis with:${NC}"
    echo -e "${GREEN}  (cd ${PROJECT_DIR}/code && docker-compose up -d postgres redis)${NC}"
  else
    echo -e "${YELLOW}Docker not found. The backend will use SQLite by default (see code/backend/.env.example).${NC}"
    echo -e "${YELLOW}Install Docker if you want to run against PostgreSQL and Redis locally.${NC}"
  fi
}

# Function to set up the Hardhat blockchain development environment.
# This project uses Hardhat (see code/blockchain/hardhat.config.js), with
# contracts compiled fully offline via the local `solc` npm package - no
# global Truffle/Ganache installation, and no network access to
# binaries.soliditylang.org, is needed or used.
setup_blockchain_environment() {
  echo -e "${BLUE}Setting up blockchain development environment...${NC}"

  if ! command_exists npm; then
    echo -e "${YELLOW}npm not found; skipping blockchain dependency installation.${NC}"
    return 0
  fi

  if [ -d "${PROJECT_DIR}/code/blockchain/node_modules" ]; then
    echo -e "${GREEN}Blockchain dependencies already installed.${NC}"
  else
    echo -e "${YELLOW}Installing blockchain dependencies (Hardhat, OpenZeppelin, solc)...${NC}"
    (cd "${PROJECT_DIR}/code/blockchain" && npm install)
  fi

  echo -e "${GREEN}Blockchain development environment setup complete.${NC}"
  echo -e "${GREEN}Compile contracts with: (cd ${PROJECT_DIR}/code/blockchain && npm run compile)${NC}"
  echo -e "${GREEN}Run contract tests with: (cd ${PROJECT_DIR}/code/blockchain && npm test)${NC}"
  echo -e "${GREEN}Start a local chain with: (cd ${PROJECT_DIR}/code/blockchain && npx hardhat node)${NC}"
}

# Function to validate project structure
validate_project_structure() {
  echo -e "${BLUE}Validating project structure...${NC}"

  # Check if essential directories exist
  MISSING_DIRS=()

  for dir in "code" "code/backend" "code/blockchain" "code/ai_models" "web-frontend" "mobile-frontend"; do
    if [ ! -d "${PROJECT_DIR}/${dir}" ]; then
      MISSING_DIRS+=("$dir")
    fi
  done

  if [ ${#MISSING_DIRS[@]} -ne 0 ]; then
    echo -e "${YELLOW}Warning: The following expected directories are missing:${NC}"
    for dir in "${MISSING_DIRS[@]}"; do
      echo -e "${YELLOW}  - $dir${NC}"
    done
    echo -e "${YELLOW}Continuing setup for the components that are present.${NC}"
  else
    echo -e "${GREEN}Project structure validation passed.${NC}"
  fi
}

# Function to setup environment variables
setup_environment_variables() {
  echo -e "${BLUE}Setting up environment variables...${NC}"

  ENV_FILE="${CONFIG_DIR}/environment.sh"

  # Create a top-level environment variables file if it doesn't exist,
  # reflecting the project's real ports and defaults.
  if [ ! -f "$ENV_FILE" ]; then
    cat > "$ENV_FILE" << EOF
#!/bin/bash
# BlockScore Environment Variables

# Backend Configuration (Flask, see code/backend/.env.example)
export BLOCKSCORE_API_PORT=5000
export BLOCKSCORE_API_URL="http://localhost:5000"

# Web Frontend Configuration (Vite dev server, configured for CRA's default port 3000 - see web-frontend/vite.config.js)
export BLOCKSCORE_FRONTEND_PORT=3000

# AI Model Server Configuration (see code/ai_models)
export BLOCKSCORE_AI_MODEL_PORT=5001

# Blockchain Configuration (Hardhat; see code/blockchain/hardhat.config.js)
export BLOCKSCORE_NETWORK="development"
export BLOCKSCORE_PROVIDER_URL="http://localhost:8545"
export BLOCKSCORE_PRIVATE_KEY="" # Add your private key for non-development deployments

# AI Model Paths
export MODEL_PATH="${PROJECT_DIR}/code/ai_models/artifacts/credit_scoring_model.pkl"
EOF

    chmod +x "$ENV_FILE"
    echo -e "${GREEN}Created environment variables file: $ENV_FILE${NC}"
    echo -e "${YELLOW}Please update the environment variables with your configuration.${NC}"
  else
    echo -e "${GREEN}Environment variables file already exists: $ENV_FILE${NC}"
  fi

  # shellcheck source=/dev/null
  source "$ENV_FILE"

  # Create component .env files from their own .env.example where
  # available, rather than fabricating generic ones that don't match what
  # each component actually reads.
  if [ -d "${PROJECT_DIR}/code/backend" ]; then
    if [ ! -f "${PROJECT_DIR}/code/backend/.env" ] && [ -f "${PROJECT_DIR}/code/backend/.env.example" ]; then
      cp "${PROJECT_DIR}/code/backend/.env.example" "${PROJECT_DIR}/code/backend/.env"
      echo -e "${GREEN}Created .env file for backend from .env.example.${NC}"
    fi
  fi

  if [ -d "${PROJECT_DIR}/web-frontend" ]; then
    if [ ! -f "${PROJECT_DIR}/web-frontend/.env" ] && [ -f "${PROJECT_DIR}/web-frontend/.env.example" ]; then
      cp "${PROJECT_DIR}/web-frontend/.env.example" "${PROJECT_DIR}/web-frontend/.env"
      echo -e "${GREEN}Created .env file for web-frontend from .env.example.${NC}"
    fi
  fi

  if [ -d "${PROJECT_DIR}/mobile-frontend" ]; then
    if [ ! -f "${PROJECT_DIR}/mobile-frontend/.env" ] && [ -f "${PROJECT_DIR}/mobile-frontend/.env.example" ]; then
      cp "${PROJECT_DIR}/mobile-frontend/.env.example" "${PROJECT_DIR}/mobile-frontend/.env"
      echo -e "${GREEN}Created .env file for mobile-frontend from .env.example.${NC}"
    fi
  fi

  echo -e "${GREEN}Environment variables setup complete.${NC}"
}

# Function to create a setup completion marker
create_setup_marker() {
  echo -e "${BLUE}Creating setup completion marker...${NC}"

  SETUP_DATE=$(date "+%Y-%m-%d %H:%M:%S")
  cat > "${CONFIG_DIR}/setup_complete.json" << EOF
{
  "setup_completed": true,
  "setup_date": "$SETUP_DATE",
  "os": "$OS",
  "python_version": "$PYTHON_VERSION",
  "node_version": "$NODE_VERSION"
}
EOF

  echo -e "${GREEN}Setup completion marker created.${NC}"
}

# Main execution
main() {
  # Check if setup has already been completed
  if [ -f "${CONFIG_DIR}/setup_complete.json" ]; then
    echo -e "${YELLOW}Environment setup has already been completed.${NC}"
    read -r -p "Do you want to run the setup again? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      echo -e "${GREEN}Setup skipped. Using existing environment.${NC}"
      return 0
    fi
  fi

  # Run setup steps
  detect_os
  install_system_dependencies
  validate_project_structure
  setup_python_environment
  setup_node_environment
  setup_datastores
  setup_blockchain_environment
  setup_environment_variables
  create_setup_marker

  echo -e "${GREEN}BlockScore development environment setup completed successfully!${NC}"
  echo -e "${BLUE}================================================================${NC}"
  echo -e "${YELLOW}Next steps:${NC}"
  echo -e "${YELLOW}1. Update environment variables in ${CONFIG_DIR}/environment.sh${NC}"
  echo -e "${YELLOW}2. Start the backend using ./scripts/run_blockscore.sh${NC}"
  echo -e "${YELLOW}   or all components using ./scripts/component_restart.sh start all${NC}"
  echo -e "${YELLOW}3. Visit http://localhost:3000 for the web app (API at http://localhost:5000)${NC}"
  echo -e "${BLUE}================================================================${NC}"
}

# Execute main function
main
