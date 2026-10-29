#!/bin/bash
# ========================================================================
# BlockScore Backend Run Script
#
# Starts the BlockScore Flask backend for local development. This is a
# lightweight, single-component launcher; use component_restart.sh to
# manage the backend alongside the frontend, mobile, blockchain, and AI
# model services together.
# ========================================================================

set -e

# Resolve the project root relative to this script's own location, so it
# works no matter which directory it is invoked from.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND_DIR="${PROJECT_DIR}/code/backend"

# Colors for terminal output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting BlockScore backend...${NC}"

if [ ! -d "$BACKEND_DIR" ]; then
  echo -e "${RED}Backend directory not found: ${BACKEND_DIR}${NC}"
  exit 1
fi

if [ ! -f "${BACKEND_DIR}/requirements.txt" ]; then
  echo -e "${RED}requirements.txt not found in ${BACKEND_DIR}${NC}"
  exit 1
fi

# Create a shared Python virtual environment at the project root if one
# doesn't already exist.
if [ ! -d "${PROJECT_DIR}/venv" ]; then
  echo -e "${BLUE}Creating Python virtual environment...${NC}"
  python3 -m venv "${PROJECT_DIR}/venv"
fi

# shellcheck source=/dev/null
source "${PROJECT_DIR}/venv/bin/activate"

echo -e "${BLUE}Installing backend dependencies...${NC}"
pip install --upgrade pip > /dev/null
pip install -r "${BACKEND_DIR}/requirements.txt" > /dev/null

# Create a .env file from the example if one doesn't exist yet, so the
# Flask app has the configuration it expects.
if [ ! -f "${BACKEND_DIR}/.env" ] && [ -f "${BACKEND_DIR}/.env.example" ]; then
  cp "${BACKEND_DIR}/.env.example" "${BACKEND_DIR}/.env"
  echo -e "${BLUE}Created ${BACKEND_DIR}/.env from .env.example${NC}"
fi

echo -e "${BLUE}Starting Flask application...${NC}"
(cd "$BACKEND_DIR" && python app.py) &
APP_PID=$!

echo -e "${GREEN}BlockScore backend is running!${NC}"
echo -e "${GREEN}Application running with PID: ${APP_PID}${NC}"
echo -e "${GREEN}Access the API at: http://localhost:5000${NC}"
echo -e "${BLUE}Press Ctrl+C to stop${NC}"

# Handle graceful shutdown on both interrupt and termination signals.
cleanup() {
  echo -e "${BLUE}Stopping backend...${NC}"
  kill "$APP_PID" 2>/dev/null || true
  wait "$APP_PID" 2>/dev/null || true
  echo -e "${GREEN}Backend stopped${NC}"
  exit 0
}

trap cleanup SIGINT SIGTERM

# Keep script running while the backend is up.
wait "$APP_PID"
