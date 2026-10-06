#!/bin/bash
# ========================================================================
# BlockScore Component Restart Automation Script
#
# This script automates the process of selectively restarting only the
# components that have been modified during development.
#
# Features:
# - Selective component restarting
# - Change detection
# - Hot reload configuration
# - Process management
#
# Components map to real project directories as follows:
#   backend    -> code/backend       (Python/Flask, started with `python app.py`)
#   blockchain -> code/blockchain    (Hardhat; a local chain is started with
#                                      `npx hardhat node`, matching hardhat.config.js's
#                                      development network)
#   frontend   -> web-frontend       (Vite dev server)
#   mobile     -> mobile-frontend    (React Native / Metro dev server)
#   ai         -> code/ai_models     (Python; blockscore_ai package)
# ========================================================================

# Set strict error handling
set -e

# Define colors for terminal output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Resolve the project root relative to this script's own location.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONFIG_DIR="${PROJECT_DIR}/.blockscore_config"
PROCESS_FILE="${CONFIG_DIR}/processes.json"

# Print banner
echo -e "${BLUE}================================================================${NC}"
echo -e "${BLUE}          BlockScore Component Restart System                   ${NC}"
echo -e "${BLUE}================================================================${NC}"

if ! command -v jq &> /dev/null; then
  echo -e "${RED}jq is required by this script but was not found. Install it (e.g. apt-get install jq / brew install jq) and try again.${NC}"
  exit 1
fi

# Parse command line arguments
COMPONENTS=()
FORCE_RESTART=false
WATCH_MODE=false

print_usage() {
  echo "Usage: $0 [options] [components]"
  echo ""
  echo "Options:"
  echo "  -h, --help                 Show this help message"
  echo "  -f, --force                Force restart even if no changes detected"
  echo "  -w, --watch                Watch for changes and restart automatically"
  echo ""
  echo "Components:"
  echo "  all                        Restart all components (default)"
  echo "  blockchain                 Restart the local blockchain (Hardhat node)"
  echo "  backend                    Restart backend services"
  echo "  frontend                   Restart frontend development server"
  echo "  mobile                     Restart mobile development server"
  echo "  ai                         Restart AI services"
  echo ""
  echo "Examples:"
  echo "  $0                         Restart all modified components"
  echo "  $0 -f backend              Force restart backend services"
  echo "  $0 -w frontend backend     Watch and restart frontend and backend when changes detected"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -h|--help)
      print_usage
      exit 0
      ;;
    -f|--force)
      FORCE_RESTART=true
      shift
      ;;
    -w|--watch)
      WATCH_MODE=true
      shift
      ;;
    all|blockchain|backend|frontend|mobile|ai)
      COMPONENTS+=("$1")
      shift
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      print_usage
      exit 1
      ;;
  esac
done

# If no components specified, use all
if [ ${#COMPONENTS[@]} -eq 0 ]; then
  COMPONENTS=("blockchain" "backend" "frontend" "mobile" "ai")
fi

# "all" expands to every real component
if [[ " ${COMPONENTS[*]} " == *" all "* ]]; then
  COMPONENTS=("blockchain" "backend" "frontend" "mobile" "ai")
fi

# Function to check if a component exists
component_exists() {
  local component=$1

  case $component in
    blockchain)
      [ -d "${PROJECT_DIR}/code/blockchain" ]
      ;;
    backend)
      [ -d "${PROJECT_DIR}/code/backend" ]
      ;;
    frontend)
      [ -d "${PROJECT_DIR}/web-frontend" ]
      ;;
    mobile)
      [ -d "${PROJECT_DIR}/mobile-frontend" ]
      ;;
    ai)
      [ -d "${PROJECT_DIR}/code/ai_models" ]
      ;;
    *)
      return 1
      ;;
  esac
}

# Portable "most recent modification time" scan: prefers GNU find's
# -printf (Linux), falls back to a stat-based loop that works on both GNU
# and BSD/macOS stat.
latest_mtime_in() {
  local dir=$1

  if find "$dir" -maxdepth 0 -printf '' 2>/dev/null; then
    find "$dir" -type f \
      -not -path "*/node_modules/*" \
      -not -path "*/venv/*" \
      -not -path "*/.git/*" \
      -not -path "*/build/*" \
      -printf '%T@\n' 2>/dev/null | cut -d. -f1 | sort -nr | head -1
  else
    find "$dir" -type f \
      -not -path "*/node_modules/*" \
      -not -path "*/venv/*" \
      -not -path "*/.git/*" \
      -not -path "*/build/*" \
      -exec stat -f '%m' {} \; 2>/dev/null | sort -nr | head -1
  fi
}

# Function to check if a component has been modified
component_modified() {
  local component=$1

  if [ "$FORCE_RESTART" = true ]; then
    return 0
  fi

  local component_dir=""
  local last_check_file="${CONFIG_DIR}/last_check_${component}.txt"

  case $component in
    blockchain)
      component_dir="${PROJECT_DIR}/code/blockchain"
      ;;
    backend)
      component_dir="${PROJECT_DIR}/code/backend"
      ;;
    frontend)
      component_dir="${PROJECT_DIR}/web-frontend"
      ;;
    mobile)
      component_dir="${PROJECT_DIR}/mobile-frontend"
      ;;
    ai)
      component_dir="${PROJECT_DIR}/code/ai_models"
      ;;
    *)
      return 1
      ;;
  esac

  # Create config directory if it doesn't exist
  mkdir -p "${CONFIG_DIR}"

  # Get the latest modification time (integer epoch seconds)
  local latest_mod_time
  latest_mod_time=$(latest_mtime_in "$component_dir")
  latest_mod_time=${latest_mod_time:-0}

  # If last check file doesn't exist, create it and return modified
  if [ ! -f "$last_check_file" ]; then
    echo "$latest_mod_time" > "$last_check_file"
    return 0
  fi

  # Get the last check time
  local last_check_time
  last_check_time=$(cat "$last_check_file")

  # Update the last check time
  echo "$latest_mod_time" > "$last_check_file"

  # Compare times (plain integer arithmetic; no bc dependency)
  if [ "$latest_mod_time" -gt "$last_check_time" ]; then
    return 0
  else
    return 1
  fi
}

# Function to get process ID from process file
get_process_id() {
  local component=$1

  if [ ! -f "$PROCESS_FILE" ]; then
    return 1
  fi

  local pid
  pid=$(jq -r ".$component // \"\"" "$PROCESS_FILE")

  if [ -z "$pid" ] || [ "$pid" = "null" ]; then
    return 1
  fi

  # Check if process is still running
  if ! ps -p "$pid" > /dev/null; then
    return 1
  fi

  echo "$pid"
  return 0
}

# Function to save process ID to process file
save_process_id() {
  local component=$1
  local pid=$2

  mkdir -p "${CONFIG_DIR}"

  if [ ! -f "$PROCESS_FILE" ]; then
    echo "{}" > "$PROCESS_FILE"
  fi

  local json
  json=$(cat "$PROCESS_FILE")
  json=$(echo "$json" | jq ".$component = \"$pid\"")
  echo "$json" > "$PROCESS_FILE"
}

# Function to stop a component
stop_component() {
  local component=$1

  echo -e "${BLUE}Stopping $component...${NC}"

  local pid
  pid=$(get_process_id "$component") || true

  if [ -n "$pid" ]; then
    echo -e "${YELLOW}Stopping process $pid...${NC}"
    kill -15 "$pid" 2>/dev/null || true

    # Wait for process to stop
    for _ in $(seq 1 10); do
      if ! ps -p "$pid" > /dev/null; then
        break
      fi
      sleep 1
    done

    # Force kill if still running
    if ps -p "$pid" > /dev/null 2>&1; then
      echo -e "${RED}Process $pid still running, force killing...${NC}"
      kill -9 "$pid" 2>/dev/null || true
    fi

    # Update process file
    if [ -f "$PROCESS_FILE" ]; then
      local json
      json=$(cat "$PROCESS_FILE")
      json=$(echo "$json" | jq "del(.$component)")
      echo "$json" > "$PROCESS_FILE"
    fi

    echo -e "${GREEN}$component stopped${NC}"
  else
    echo -e "${YELLOW}No running process found for $component${NC}"
  fi
}

# Function to start a component
start_component() {
  local component=$1

  echo -e "${BLUE}Starting $component...${NC}"

  case $component in
    blockchain)
      if [ -d "${PROJECT_DIR}/code/blockchain" ]; then
        cd "${PROJECT_DIR}/code/blockchain"
        # This project uses Hardhat (hardhat.config.js), which bundles
        # its own in-process dev chain - no separate Ganache install
        # needed. This matches the configured "development" network
        # (127.0.0.1:8545).
        if [ ! -d "node_modules" ] && command -v npm &> /dev/null; then
          npm install
        fi
        if command -v npx &> /dev/null; then
          npx hardhat node > "${CONFIG_DIR}/blockchain.log" 2>&1 &
        else
          echo -e "${RED}npx not found. Install Node.js.${NC}"
          return 1
        fi
        local pid=$!
        save_process_id "$component" "$pid"
        echo -e "${GREEN}Local blockchain (Hardhat node) started with PID $pid${NC}"
      else
        echo -e "${RED}Blockchain directory not found${NC}"
        return 1
      fi
      ;;
    backend)
      if [ -d "${PROJECT_DIR}/code/backend" ]; then
        cd "${PROJECT_DIR}/code/backend"
        if [ -f "app.py" ]; then
          if [ -d "${PROJECT_DIR}/venv" ]; then
            # shellcheck source=/dev/null
            source "${PROJECT_DIR}/venv/bin/activate"
            python app.py > "${CONFIG_DIR}/backend.log" 2>&1 &
            local pid=$!
            deactivate
          else
            python3 app.py > "${CONFIG_DIR}/backend.log" 2>&1 &
            local pid=$!
          fi
          save_process_id "$component" "$pid"
          echo -e "${GREEN}Backend services started with PID $pid${NC}"
        else
          echo -e "${RED}Backend entry point (app.py) not found${NC}"
          return 1
        fi
      else
        echo -e "${RED}Backend directory not found${NC}"
        return 1
      fi
      ;;
    frontend)
      if [ -d "${PROJECT_DIR}/web-frontend" ]; then
        cd "${PROJECT_DIR}/web-frontend"
        if [ -f "package.json" ]; then
          if grep -q "\"dev\"" package.json; then
            npm run dev > "${CONFIG_DIR}/frontend.log" 2>&1 &
          else
            npm start > "${CONFIG_DIR}/frontend.log" 2>&1 &
          fi
          local pid=$!
          save_process_id "$component" "$pid"
          echo -e "${GREEN}Frontend development server started with PID $pid${NC}"
        else
          echo -e "${RED}Frontend package.json not found${NC}"
          return 1
        fi
      else
        echo -e "${RED}Frontend directory not found${NC}"
        return 1
      fi
      ;;
    mobile)
      if [ -d "${PROJECT_DIR}/mobile-frontend" ]; then
        cd "${PROJECT_DIR}/mobile-frontend"
        if [ -f "package.json" ]; then
          npm start > "${CONFIG_DIR}/mobile.log" 2>&1 &
          local pid=$!
          save_process_id "$component" "$pid"
          echo -e "${GREEN}Mobile development server started with PID $pid${NC}"
        else
          echo -e "${RED}Mobile package.json not found${NC}"
          return 1
        fi
      else
        echo -e "${RED}Mobile directory not found${NC}"
        return 1
      fi
      ;;
    ai)
      if [ -d "${PROJECT_DIR}/code/ai_models" ]; then
        cd "${PROJECT_DIR}/code/ai_models"
        # Activate virtual environment if it exists
        local python_cmd="python3"
        if [ -d "${PROJECT_DIR}/venv" ]; then
          # shellcheck source=/dev/null
          source "${PROJECT_DIR}/venv/bin/activate"
          python_cmd="python"
        fi
        # Run the AI service
        if [ -f "wsgi.py" ]; then
          PYTHONPATH="src${PYTHONPATH:+:$PYTHONPATH}" "$python_cmd" -m blockscore_ai > "${CONFIG_DIR}/ai.log" 2>&1 &
          local pid=$!
          save_process_id "$component" "$pid"
          echo -e "${GREEN}AI services started with PID $pid${NC}"
        else
          echo -e "${RED}AI service entry point not found (expected wsgi.py)${NC}"
          return 1
        fi
      else
        echo -e "${RED}AI models directory not found${NC}"
        return 1
      fi
      ;;
  esac

  cd "${PROJECT_DIR}"
  return 0
}

# Function to restart a component
restart_component() {
  local component=$1

  if ! component_exists "$component"; then
    echo -e "${RED}Component $component does not exist${NC}"
    return 1
  fi

  if component_modified "$component" || [ "$FORCE_RESTART" = true ]; then
    echo -e "${BLUE}Changes detected in $component, restarting...${NC}"
    stop_component "$component"
    start_component "$component"
  else
    echo -e "${GREEN}No changes detected in $component, skipping restart${NC}"
  fi
}

# Function to watch for changes
watch_for_changes() {
  echo -e "${BLUE}Watching for changes in: ${COMPONENTS[*]}${NC}"
  echo -e "${BLUE}Press Ctrl+C to stop watching${NC}"

  while true; do
    for component in "${COMPONENTS[@]}"; do
      if component_exists "$component" && component_modified "$component"; then
        echo -e "${YELLOW}Changes detected in $component, restarting...${NC}"
        stop_component "$component"
        start_component "$component"
      fi
    done

    sleep 2
  done
}

# Function to create a status report
create_status_report() {
  local report="${CONFIG_DIR}/component_status.json"

  mkdir -p "${CONFIG_DIR}"

  echo "{" > "$report"

  local first=true

  for component in blockchain backend frontend mobile ai; do
    local pid
    pid=$(get_process_id "$component") || true
    local status="stopped"

    if [ -n "$pid" ]; then
      status="running"
    fi

    if [ "$first" = true ]; then
      first=false
    else
      echo "," >> "$report"
    fi

    echo "  \"$component\": {" >> "$report"
    echo "    \"status\": \"$status\"," >> "$report"
    if [ -n "$pid" ]; then
      echo "    \"pid\": $pid," >> "$report"
    else
      echo "    \"pid\": null," >> "$report"
    fi

    local log_file="${CONFIG_DIR}/${component}.log"
    if [ -f "$log_file" ]; then
      echo "    \"log\": \"$log_file\"" >> "$report"
    else
      echo "    \"log\": null" >> "$report"
    fi

    echo -n "  }" >> "$report"
  done

  echo "" >> "$report"
  echo "}" >> "$report"

  echo -e "${GREEN}Status report created: $report${NC}"
}

# Main execution
main() {
  # Create config directory if it doesn't exist
  mkdir -p "${CONFIG_DIR}"

  # Create process file if it doesn't exist
  if [ ! -f "$PROCESS_FILE" ]; then
    echo "{}" > "$PROCESS_FILE"
  fi

  if [ "$WATCH_MODE" = true ]; then
    # Initial restart of all components
    for component in "${COMPONENTS[@]}"; do
      restart_component "$component"
    done

    # Watch for changes
    watch_for_changes
  else
    # Restart components
    for component in "${COMPONENTS[@]}"; do
      restart_component "$component"
    done

    # Create status report
    create_status_report

    echo -e "${GREEN}All components processed successfully${NC}"
    echo -e "${BLUE}================================================================${NC}"
    echo -e "${BLUE}Component logs are available in ${CONFIG_DIR}/${NC}"
    echo -e "${BLUE}================================================================${NC}"
  fi
}

# Execute main function
main
