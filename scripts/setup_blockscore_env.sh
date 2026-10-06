#!/bin/bash
# ========================================================================
# BlockScore Lightweight Project Setup Script
#
# A minimal setup script that assumes system prerequisites (Python 3,
# Node.js/npm, git) are already installed and just wires up each
# component's own dependencies. For a script that also installs system
# packages, see unified_env_setup.sh.
# ========================================================================

set -e

# Prerequisites (ensure these are installed and configured):
# - Python 3.x with venv support
# - Node.js and npm (for the Hardhat-based blockchain module in
#   code/blockchain, web-frontend, and mobile-frontend)
# - Docker and Docker Compose (recommended, for PostgreSQL and Redis; see
#   code/docker-compose.yml). The backend also works standalone against
#   SQLite for local development with no extra services running.

echo "Starting BlockScore project setup..."

# Resolve the project root relative to this script's own location.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_DIR}"
echo "Changed directory to $(pwd)"

# --- AI Models Setup (Python) ---
echo ""
echo "Setting up BlockScore AI Models environment..."
AI_MODELS_DIR="${PROJECT_DIR}/code/ai_models"
AI_MODELS_REQUIREMENTS="${AI_MODELS_DIR}/requirements.txt"

if [ ! -d "${AI_MODELS_DIR}" ]; then
    echo "Error: AI Models directory ${AI_MODELS_DIR} not found."
elif [ ! -f "${AI_MODELS_REQUIREMENTS}" ]; then
    echo "Warning: requirements.txt not found at ${AI_MODELS_REQUIREMENTS}. Skipping Python dependency installation for AI Models."
else
    echo "Installing AI Models Python dependencies into the shared virtual environment..."
    if [ ! -d "${PROJECT_DIR}/venv" ]; then
        echo "Creating shared Python virtual environment (venv)..."
        python3 -m venv "${PROJECT_DIR}/venv"
    fi
    # shellcheck source=/dev/null
    source "${PROJECT_DIR}/venv/bin/activate"
    pip install --upgrade pip
    if pip install -r "${AI_MODELS_REQUIREMENTS}"; then
        echo "AI Models dependencies installed."
    else
        echo "Warning: failed to install one or more AI Models dependencies."
        echo "This is often caused by an old pinned package lacking a prebuilt wheel for your Python version."
        echo "Continuing with the rest of the setup; see ${AI_MODELS_REQUIREMENTS} if you need to train AI models locally."
    fi
    deactivate
fi

# --- Backend Setup (Python/Flask) ---
echo ""
echo "Setting up BlockScore Backend environment..."
BACKEND_DIR="${PROJECT_DIR}/code/backend"

if [ ! -d "${BACKEND_DIR}" ]; then
    echo "Error: Backend directory ${BACKEND_DIR} not found."
elif [ ! -f "${BACKEND_DIR}/requirements.txt" ]; then
    echo "Warning: requirements.txt not found in ${BACKEND_DIR}. Skipping Python dependency installation for Backend."
else
    echo "Installing Backend Python dependencies into the shared virtual environment..."
    if [ ! -d "${PROJECT_DIR}/venv" ]; then
        echo "Creating shared Python virtual environment (venv)..."
        python3 -m venv "${PROJECT_DIR}/venv"
    fi
    # shellcheck source=/dev/null
    source "${PROJECT_DIR}/venv/bin/activate"
    pip install --upgrade pip
    pip install -r "${BACKEND_DIR}/requirements.txt"
    echo "Backend dependencies installed."

    if [ ! -f "${BACKEND_DIR}/.env" ] && [ -f "${BACKEND_DIR}/.env.example" ]; then
        cp "${BACKEND_DIR}/.env.example" "${BACKEND_DIR}/.env"
        echo "Created .env file for Backend from .env.example. Please review its configuration."
    fi

    deactivate
    echo "To activate the shared virtual environment later, run: source ${PROJECT_DIR}/venv/bin/activate"
fi

# --- Web Frontend Setup (React - Node.js) ---
echo ""
echo "Setting up BlockScore Web Frontend environment..."
WEB_FRONTEND_DIR="${PROJECT_DIR}/web-frontend"

if [ ! -d "${WEB_FRONTEND_DIR}" ]; then
    echo "Error: Web frontend directory ${WEB_FRONTEND_DIR} not found."
else
    cd "${WEB_FRONTEND_DIR}"
    echo "Changed directory to $(pwd) for Web Frontend setup."

    if [ ! -f "package.json" ]; then
        echo "Error: package.json not found in ${WEB_FRONTEND_DIR}. Cannot install frontend dependencies."
    elif ! command -v npm &> /dev/null; then
        echo "npm command could not be found. Please ensure Node.js and npm are installed and in your PATH."
    else
        echo "Installing Web Frontend Node.js dependencies using npm..."
        npm install
        echo "Web Frontend dependencies installed."
    fi
    echo "To start the web frontend development server (from ${WEB_FRONTEND_DIR}): npm start"
    echo "To build the web frontend for production (from ${WEB_FRONTEND_DIR}): npm run build"
    cd "${PROJECT_DIR}"
fi

# --- Mobile Frontend Setup (React Native - Node.js) ---
echo ""
echo "Setting up BlockScore Mobile Frontend environment..."
MOBILE_FRONTEND_DIR="${PROJECT_DIR}/mobile-frontend"

if [ ! -d "${MOBILE_FRONTEND_DIR}" ]; then
    echo "Error: Mobile frontend directory ${MOBILE_FRONTEND_DIR} not found."
else
    cd "${MOBILE_FRONTEND_DIR}"
    echo "Changed directory to $(pwd) for Mobile Frontend setup."

    if [ ! -f "package.json" ]; then
        echo "Error: package.json not found in ${MOBILE_FRONTEND_DIR}. Cannot install mobile dependencies."
    elif ! command -v npm &> /dev/null; then
        echo "npm command could not be found. Please ensure Node.js and npm are installed and in your PATH."
    else
        echo "Installing Mobile Frontend Node.js dependencies using npm..."
        npm install
        echo "Mobile Frontend dependencies installed."
    fi

    if [ ! -f ".env" ] && [ -f ".env.example" ]; then
        cp ".env.example" ".env"
        echo "Created .env file for Mobile Frontend from .env.example. Please review its configuration."
    fi

    echo "To run the mobile app (from ${MOBILE_FRONTEND_DIR}): npm start, then npm run android / npm run ios"
    cd "${PROJECT_DIR}"
fi

# --- Blockchain Setup (Hardhat) ---
echo ""
echo "Setting up BlockScore Blockchain environment..."
BLOCKCHAIN_DIR="${PROJECT_DIR}/code/blockchain"

if [ ! -d "${BLOCKCHAIN_DIR}" ]; then
    echo "Error: Blockchain directory ${BLOCKCHAIN_DIR} not found."
else
    if ! command -v npm &> /dev/null; then
        echo "npm not found. Please install Node.js to work with smart contracts."
    else
        if [ ! -d "${BLOCKCHAIN_DIR}/node_modules" ]; then
            echo "Installing blockchain dependencies (Hardhat, OpenZeppelin, solc)..."
            (cd "${BLOCKCHAIN_DIR}" && npm install)
        fi
        echo "Compile contracts with: (cd ${BLOCKCHAIN_DIR} && npm run compile)"
        echo "Run contract tests with: (cd ${BLOCKCHAIN_DIR} && npm test)"
    fi
    echo "This project uses Hardhat (see ${BLOCKCHAIN_DIR}/hardhat.config.js)."
    echo "Start a local chain with: (cd ${BLOCKCHAIN_DIR} && npx hardhat node) on port 8545, matching the development network config."
fi

# --- General Instructions & Reminders ---
echo ""
echo "BlockScore project setup script finished."
echo "Please ensure all prerequisites are met:"
echo "  - Python 3.x, pip"
echo "  - Node.js, npm (also covers Hardhat for smart contract development)"
echo "  - Docker and Docker Compose (for PostgreSQL and Redis; see code/docker-compose.yml)"
echo "Review the project's README.md for further instructions on smart contract deployment, running services, and .env configuration."
echo "The backend defaults to SQLite for local development (see code/backend/.env.example); Docker Compose provides PostgreSQL and Redis for a fuller local stack."
