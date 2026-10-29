#!/bin/bash
# ========================================================================
# BlockScore Code Quality Check Script
#
# This script performs comprehensive code quality checks across all
# components of the BlockScore project, including linting, formatting,
# security analysis, and best practice enforcement.
#
# Features:
# - Multi-language support (JavaScript, TypeScript, Python, Solidity)
# - Automatic fixing of common issues
# - Detailed reporting
# - Configurable severity levels
# - Pre-commit hook integration
#
# JavaScript/TypeScript checks run inside web-frontend and mobile-frontend
# using each project's own local ESLint installation and configuration
# (react-app / @react-native presets), rather than a generic root-level
# config, so results reflect what each project's own tooling actually
# reports.
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
REPORT_DIR="${PROJECT_DIR}/code_quality_reports"
REPORT_FILE="${REPORT_DIR}/code_quality_report_$(date +%Y%m%d%H%M%S).md"

# Print banner
echo -e "${BLUE}================================================================${NC}"
echo -e "${BLUE}          BlockScore Code Quality Check System                  ${NC}"
echo -e "${BLUE}================================================================${NC}"

# Parse command line arguments
FIX_ISSUES=false
CHECK_ALL=true
CHECK_JS=false
CHECK_PY=false
CHECK_SOL=false
VERBOSE=false

print_usage() {
  echo "Usage: $0 [options]"
  echo ""
  echo "Options:"
  echo "  -h, --help                 Show this help message"
  echo "  -f, --fix                  Automatically fix issues when possible"
  echo "  -v, --verbose              Show detailed output"
  echo "  --js                       Check only JavaScript/TypeScript files (web-frontend, mobile-frontend)"
  echo "  --py                       Check only Python files (code/backend, code/ai_models)"
  echo "  --sol                      Check only Solidity files (code/blockchain)"
  echo ""
  echo "Examples:"
  echo "  $0                         Check all file types"
  echo "  $0 -f                      Check all file types and fix issues"
  echo "  $0 --js -f                 Check JavaScript/TypeScript files and fix issues"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -h|--help)
      print_usage
      exit 0
      ;;
    -f|--fix)
      FIX_ISSUES=true
      shift
      ;;
    -v|--verbose)
      VERBOSE=true
      shift
      ;;
    --js)
      CHECK_JS=true
      CHECK_ALL=false
      shift
      ;;
    --py)
      CHECK_PY=true
      CHECK_ALL=false
      shift
      ;;
    --sol)
      CHECK_SOL=true
      CHECK_ALL=false
      shift
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      print_usage
      exit 1
      ;;
  esac
done

# If no specific file types are selected, check all
if [ "$CHECK_ALL" = true ]; then
  CHECK_JS=true
  CHECK_PY=true
  CHECK_SOL=true
fi

# Create report directory
mkdir -p "$REPORT_DIR"

# Initialize report file
{
  echo "# BlockScore Code Quality Report"
  echo ""
  echo "Generated on: $(date)"
  echo ""
  echo "## Summary"
  echo ""
} > "$REPORT_FILE"

# Function to log messages
log_message() {
  local level=$1
  local message=$2

  case $level in
    INFO)
      echo -e "${BLUE}[$level] $message${NC}"
      ;;
    SUCCESS)
      echo -e "${GREEN}[$level] $message${NC}"
      ;;
    WARNING)
      echo -e "${YELLOW}[$level] $message${NC}"
      ;;
    ERROR)
      echo -e "${RED}[$level] $message${NC}"
      ;;
    *)
      echo "[$level] $message"
      ;;
  esac

  # Add to report if not verbose output
  if [[ "$level" != "INFO" || "$VERBOSE" = true ]]; then
    echo "- **$level**: $message" >> "$REPORT_FILE"
  fi
}

# Function to check if a command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Ensure the shared Python virtual environment exists and is activated.
ensure_venv() {
  if [ ! -d "${PROJECT_DIR}/venv" ]; then
    python3 -m venv "${PROJECT_DIR}/venv"
  fi
  # shellcheck source=/dev/null
  source "${PROJECT_DIR}/venv/bin/activate"
}

# Function to install Python linting dependencies into the shared venv
install_python_dependencies() {
  if [ "$CHECK_PY" = true ]; then
    log_message "INFO" "Checking Python linting dependencies"

    if ! command_exists python3; then
      log_message "ERROR" "python3 not found. Please install Python 3 to check Python code."
      CHECK_PY=false
      return
    fi

    ensure_venv

    for pkg in flake8 black isort bandit; do
      if ! pip show "$pkg" >/dev/null 2>&1; then
        log_message "INFO" "Installing $pkg"
        pip install "$pkg" >/dev/null
      fi
    done

    deactivate

    log_message "SUCCESS" "Python dependencies installed"
  fi
}

# Function to create configuration files
create_config_files() {
  log_message "INFO" "Creating configuration files if needed"

  cd "$PROJECT_DIR"

  # Create flake8 configuration if it doesn't exist
  if [ "$CHECK_PY" = true ] && [ ! -f ".flake8" ]; then
    cat > ".flake8" << 'EOF'
[flake8]
max-line-length = 100
exclude = .git,__pycache__,build,dist,venv,node_modules,.pytest_cache
EOF
    log_message "INFO" "Created flake8 configuration"
  fi

  log_message "SUCCESS" "Configuration files created"
}

# Function to check JavaScript/TypeScript files, using each project's own
# local ESLint setup rather than a generic root config.
check_js_ts_files() {
  if [ "$CHECK_JS" = true ]; then
    log_message "INFO" "Checking JavaScript/TypeScript files"

    {
      echo ""
      echo "## JavaScript/TypeScript"
      echo ""
    } >> "$REPORT_FILE"

    # --- web-frontend (Vite) ---
    if [ -d "${PROJECT_DIR}/web-frontend" ]; then
      cd "${PROJECT_DIR}/web-frontend"

      if [ ! -d "node_modules" ]; then
        log_message "INFO" "Installing web-frontend dependencies"
        npm install
      fi

      log_message "INFO" "Running ESLint on web-frontend"

      # shellcheck disable=SC2054  # --ext takes one comma-separated value, not an array
      ESLINT_ARGS=(src --ext .js,.jsx,.ts,.tsx)
      if [ "$FIX_ISSUES" = true ]; then
        ESLINT_ARGS+=(--fix)
      fi

      {
        echo "### web-frontend ESLint"
        echo '```'
      } >> "$REPORT_FILE"

      ESLINT_OUTPUT=$(npx eslint "${ESLINT_ARGS[@]}" 2>&1) && ESLINT_STATUS=0 || ESLINT_STATUS=$?
      echo "$ESLINT_OUTPUT" >> "$REPORT_FILE"
      echo '```' >> "$REPORT_FILE"

      if [ "$ESLINT_STATUS" -ne 0 ]; then
        log_message "ERROR" "ESLint found errors in web-frontend"
      elif [[ "$ESLINT_OUTPUT" == *"warning"* ]]; then
        log_message "WARNING" "ESLint found warnings in web-frontend"
      else
        log_message "SUCCESS" "web-frontend ESLint check passed"
      fi
    else
      log_message "WARNING" "web-frontend directory not found, skipping"
    fi

    # --- mobile-frontend (React Native) ---
    if [ -d "${PROJECT_DIR}/mobile-frontend" ]; then
      cd "${PROJECT_DIR}/mobile-frontend"

      if [ ! -d "node_modules" ]; then
        log_message "INFO" "Installing mobile-frontend dependencies"
        npm install
      fi

      log_message "INFO" "Running ESLint on mobile-frontend"

      {
        echo "### mobile-frontend ESLint"
        echo '```'
      } >> "$REPORT_FILE"

      if [ "$FIX_ISSUES" = true ]; then
        MOBILE_ESLINT_OUTPUT=$(npx eslint . --ext .js,.jsx,.ts,.tsx --fix 2>&1) && MOBILE_ESLINT_STATUS=0 || MOBILE_ESLINT_STATUS=$?
      else
        MOBILE_ESLINT_OUTPUT=$(npm run lint 2>&1) && MOBILE_ESLINT_STATUS=0 || MOBILE_ESLINT_STATUS=$?
      fi
      echo "$MOBILE_ESLINT_OUTPUT" >> "$REPORT_FILE"
      echo '```' >> "$REPORT_FILE"

      if [ "$MOBILE_ESLINT_STATUS" -ne 0 ]; then
        log_message "ERROR" "ESLint found errors in mobile-frontend"
      elif [[ "$MOBILE_ESLINT_OUTPUT" == *"warning"* ]]; then
        log_message "WARNING" "ESLint found warnings in mobile-frontend"
      else
        log_message "SUCCESS" "mobile-frontend ESLint check passed"
      fi
    else
      log_message "WARNING" "mobile-frontend directory not found, skipping"
    fi

    cd "$PROJECT_DIR"
  fi
}

# Function to check Python files (code/backend, code/ai_models)
check_python_files() {
  if [ "$CHECK_PY" = true ]; then
    log_message "INFO" "Checking Python files"

    {
      echo ""
      echo "## Python"
      echo ""
    } >> "$REPORT_FILE"

    ensure_venv

    PY_TARGETS=()
    [ -d "${PROJECT_DIR}/code/backend" ] && PY_TARGETS+=("code/backend")
    [ -d "${PROJECT_DIR}/code/ai_models" ] && PY_TARGETS+=("code/ai_models")

    if [ ${#PY_TARGETS[@]} -eq 0 ]; then
      log_message "WARNING" "No Python components found, skipping"
      deactivate
      return
    fi

    cd "$PROJECT_DIR"

    # flake8
    log_message "INFO" "Running flake8"
    {
      echo "### flake8"
      echo '```'
    } >> "$REPORT_FILE"
    FLAKE8_OUTPUT=$(flake8 "${PY_TARGETS[@]}" 2>&1 || true)
    echo "$FLAKE8_OUTPUT" >> "$REPORT_FILE"
    echo '```' >> "$REPORT_FILE"
    if [ -n "$FLAKE8_OUTPUT" ]; then
      log_message "WARNING" "flake8 found issues"
    else
      log_message "SUCCESS" "flake8 check passed"
    fi

    # black
    log_message "INFO" "Running black"
    BLACK_ARGS=("${PY_TARGETS[@]}")
    if [ "$FIX_ISSUES" = false ]; then
      BLACK_ARGS=(--check "${PY_TARGETS[@]}")
    fi
    {
      echo "### black"
      echo '```'
    } >> "$REPORT_FILE"
    BLACK_OUTPUT=$(black "${BLACK_ARGS[@]}" 2>&1 || true)
    echo "$BLACK_OUTPUT" >> "$REPORT_FILE"
    echo '```' >> "$REPORT_FILE"
    if [[ "$BLACK_OUTPUT" == *"would reformat"* ]]; then
      log_message "WARNING" "black found formatting issues"
    elif [[ "$BLACK_OUTPUT" == *"reformatted"* ]]; then
      log_message "WARNING" "black fixed formatting issues"
    else
      log_message "SUCCESS" "black check passed"
    fi

    # isort
    log_message "INFO" "Running isort"
    ISORT_ARGS=(--profile black "${PY_TARGETS[@]}")
    if [ "$FIX_ISSUES" = false ]; then
      ISORT_ARGS=(--check-only --profile black "${PY_TARGETS[@]}")
    fi
    {
      echo "### isort"
      echo '```'
    } >> "$REPORT_FILE"
    ISORT_OUTPUT=$(isort "${ISORT_ARGS[@]}" 2>&1 || true)
    echo "$ISORT_OUTPUT" >> "$REPORT_FILE"
    echo '```' >> "$REPORT_FILE"
    if [[ "$ISORT_OUTPUT" == *"ERROR"* || "$ISORT_OUTPUT" == *"would be"* ]]; then
      log_message "WARNING" "isort found import order issues"
    elif [[ "$ISORT_OUTPUT" == *"Fixing"* ]]; then
      log_message "WARNING" "isort fixed import order issues"
    else
      log_message "SUCCESS" "isort check passed"
    fi

    # bandit
    log_message "INFO" "Running bandit"
    {
      echo "### bandit"
      echo '```'
    } >> "$REPORT_FILE"
    BANDIT_OUTPUT=$(bandit -r "${PY_TARGETS[@]}" -x "*/tests/*,*/venv/*,*/node_modules/*" 2>&1 || true)
    echo "$BANDIT_OUTPUT" >> "$REPORT_FILE"
    echo '```' >> "$REPORT_FILE"
    if [[ "$BANDIT_OUTPUT" == *"Issue:"* ]]; then
      log_message "ERROR" "bandit found security issues"
    else
      log_message "SUCCESS" "bandit check passed"
    fi

    deactivate
  fi
}

# Ensure code/blockchain has a package.json for devDependency installs
# (e.g. solhint). code/blockchain now ships its own package.json
# (Hardhat, OpenZeppelin, solc), so this is a defensive fallback rather
# than the normal path.
ensure_blockchain_package_json() {
  cd "${PROJECT_DIR}/code/blockchain"
  if [ ! -f "package.json" ]; then
    npm init -y > /dev/null
  fi
}

# Function to check Solidity files (code/blockchain)
check_solidity_files() {
  if [ "$CHECK_SOL" = true ]; then
    if [ ! -d "${PROJECT_DIR}/code/blockchain" ]; then
      log_message "WARNING" "Blockchain directory not found, skipping Solidity checks"
      return
    fi

    log_message "INFO" "Checking Solidity files"

    {
      echo ""
      echo "## Solidity"
      echo ""
    } >> "$REPORT_FILE"

    cd "${PROJECT_DIR}/code/blockchain"
    ensure_blockchain_package_json

    # Create Solhint configuration if it doesn't exist
    if [ ! -f ".solhint.json" ]; then
      cat > ".solhint.json" << 'EOF'
{
  "extends": "solhint:recommended",
  "rules": {
    "compiler-version": ["error", "^0.8.0"],
    "func-visibility": ["warn", {"ignoreConstructors": true}]
  }
}
EOF
      log_message "INFO" "Created Solhint configuration"
    fi

    if ! npm list solhint > /dev/null 2>&1 && ! command_exists solhint; then
      log_message "INFO" "Installing solhint"
      npm install --save-dev solhint
    fi

    log_message "INFO" "Running solhint"

    SOLHINT_ARGS=("contracts/**/*.sol")
    if [ "$FIX_ISSUES" = true ]; then
      SOLHINT_ARGS+=(--fix --noPrompt)
    fi

    {
      echo "### solhint"
      echo '```'
    } >> "$REPORT_FILE"
    SOLHINT_OUTPUT=$(npx solhint "${SOLHINT_ARGS[@]}" 2>&1 || true)
    echo "$SOLHINT_OUTPUT" >> "$REPORT_FILE"
    echo '```' >> "$REPORT_FILE"

    if [[ "$SOLHINT_OUTPUT" == *"Error"* ]]; then
      log_message "ERROR" "solhint found errors"
    elif [[ "$SOLHINT_OUTPUT" == *"Warning"* ]]; then
      log_message "WARNING" "solhint found warnings"
    else
      log_message "SUCCESS" "solhint check passed"
    fi

    # Run slither if available (Python-based Solidity analyzer)
    if command_exists slither; then
      log_message "INFO" "Running slither"

      {
        echo "### slither"
        echo '```'
      } >> "$REPORT_FILE"

      SLITHER_OUTPUT=$(slither . 2>&1 || true)
      echo "$SLITHER_OUTPUT" >> "$REPORT_FILE"
      echo '```' >> "$REPORT_FILE"

      if [[ "$SLITHER_OUTPUT" == *"Error"* || "$SLITHER_OUTPUT" == *"Warning"* ]]; then
        log_message "WARNING" "slither found issues"
      fi
    else
      log_message "WARNING" "slither not available, skipping advanced Solidity analysis"
    fi

    cd "$PROJECT_DIR"
  fi
}

# Function to create pre-commit hook
create_pre_commit_hook() {
  log_message "INFO" "Creating pre-commit hook"

  cd "$PROJECT_DIR"

  # Create .git/hooks directory if it doesn't exist
  mkdir -p ".git/hooks"

  # Create pre-commit hook
  PRE_COMMIT_HOOK=".git/hooks/pre-commit"

  cat > "$PRE_COMMIT_HOOK" << 'EOF'
#!/bin/bash
# BlockScore pre-commit hook

# Run code quality check script
if ! ./scripts/code_quality_check.sh --fix; then
  echo "Code quality check failed. Please fix the issues before committing."
  exit 1
fi

exit 0
EOF

  # Make pre-commit hook executable
  chmod +x "$PRE_COMMIT_HOOK"

  log_message "SUCCESS" "Pre-commit hook created"
}

# Function to generate summary
generate_summary() {
  log_message "INFO" "Generating summary"

  # Count issues (matches this script's own report bullet format,
  # "- **LEVEL**: message", so raw tool output containing these words
  # incidentally does not inflate the counts)
  local error_count warning_count success_count
  error_count=$(grep -c -- "- \*\*ERROR\*\*:" "$REPORT_FILE" || true)
  warning_count=$(grep -c -- "- \*\*WARNING\*\*:" "$REPORT_FILE" || true)
  success_count=$(grep -c -- "- \*\*SUCCESS\*\*:" "$REPORT_FILE" || true)

  # Update summary in report
  sed -i "s/## Summary/## Summary\n\n- Errors: $error_count\n- Warnings: $warning_count\n- Successes: $success_count/" "$REPORT_FILE"

  # Print summary
  echo -e "${BLUE}================================================================${NC}"
  echo -e "${BLUE}                      Summary                                  ${NC}"
  echo -e "${BLUE}================================================================${NC}"
  echo -e "${RED}Errors: $error_count${NC}"
  echo -e "${YELLOW}Warnings: $warning_count${NC}"
  echo -e "${GREEN}Successes: $success_count${NC}"
  echo -e "${BLUE}================================================================${NC}"
  echo -e "${BLUE}Report: $REPORT_FILE${NC}"
  echo -e "${BLUE}================================================================${NC}"

  # Return error if there are errors
  if [ "$error_count" -gt 0 ]; then
    return 1
  fi

  return 0
}

# Main execution
main() {
  log_message "INFO" "Starting code quality check"

  # Install dependencies
  install_python_dependencies

  # Create configuration files
  create_config_files

  # Check files
  check_js_ts_files
  check_python_files
  check_solidity_files

  # Create pre-commit hook
  create_pre_commit_hook

  # Generate summary
  local status=0
  generate_summary || status=$?

  if [ "$status" -eq 0 ]; then
    log_message "SUCCESS" "Code quality check completed successfully"
  else
    log_message "ERROR" "Code quality check completed with errors"
  fi

  return "$status"
}

# Execute main function
main
