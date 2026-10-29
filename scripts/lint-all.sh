#!/bin/bash

# Linting and Fixing Script for BlockScore Project (Python, JavaScript, Solidity, YAML, Terraform)
#
# JavaScript/TypeScript linting runs inside web-frontend and mobile-frontend
# using each project's own local ESLint installation and configuration
# (react-app / @react-native presets), rather than a generic root config.
# Python linting targets code/backend and code/ai_models, the project's
# actual Python components, using the shared virtual environment at
# <repo root>/venv.

set -e  # Exit immediately if a command exits with a non-zero status

# Resolve the project root relative to this script's own location, so it
# works no matter which directory it is invoked from.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_DIR}"

echo "----------------------------------------"
echo "Starting linting and fixing process for BlockScore..."
echo "----------------------------------------"

# Function to check if a command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Check for required tools
echo "Checking for required tools..."

# Check for Python
if ! command_exists python3; then
  echo "Error: python3 is required but not installed. Please install Python 3."
  exit 1
else
  echo "python3 is installed."
fi

# Check for Node.js and npm
if ! command_exists node; then
  echo "Error: node is required but not installed. Please install Node.js."
  exit 1
else
  echo "node is installed."
fi

if ! command_exists npm; then
  echo "Error: npm is required but not installed. Please install npm."
  exit 1
else
  echo "npm is installed."
fi

# Check for solc (Solidity compiler)
# shellcheck disable=SC2034  # informational only, matches solc/terraform/yamllint availability checks
if ! command_exists solc; then
  echo "Warning: solc is not installed. Solidity linting will be limited."
  SOLC_AVAILABLE=false
else
  echo "solc is installed."
  SOLC_AVAILABLE=true
fi

# Check for terraform
if ! command_exists terraform; then
  echo "Warning: terraform is not installed. Terraform validation will be limited."
  TERRAFORM_AVAILABLE=false
else
  echo "terraform is installed."
  TERRAFORM_AVAILABLE=true
fi

# Check for yamllint
if ! command_exists yamllint; then
  echo "Warning: yamllint is not installed. YAML validation will be limited."
  YAMLLINT_AVAILABLE=false
else
  echo "yamllint is installed."
  YAMLLINT_AVAILABLE=true
fi

# Install required Python linting tools into the shared virtual environment
echo "----------------------------------------"
echo "Installing/Updating Python linting tools..."
if [ ! -d "${PROJECT_DIR}/venv" ]; then
  python3 -m venv "${PROJECT_DIR}/venv"
fi
# shellcheck source=/dev/null
source "${PROJECT_DIR}/venv/bin/activate"
pip install --upgrade pip > /dev/null
pip install --upgrade black isort flake8 pylint

# Define directories to process. code/backend and code/ai_models are
# processed as whole trees (covering their root-level files as well as
# subdirectories like middleware/, models/, services/, utils/, tests/, and
# training_scripts/) rather than an enumerated, easily stale subdirectory
# list.
PYTHON_DIRECTORIES=(
  "code/backend"
  "code/ai_models"
)

SOLIDITY_DIRECTORIES=(
  "code/blockchain/contracts"
)

YAML_DIRECTORIES=(
  "infrastructure/kubernetes"
  "infrastructure/ansible"
  ".github/workflows"
)

TERRAFORM_DIRECTORIES=(
  "infrastructure/terraform"
)

# 1. Python Linting
echo "----------------------------------------"
echo "Running Python linting tools..."

# 1.1 Run Black (code formatter)
echo "Running Black code formatter..."
for dir in "${PYTHON_DIRECTORIES[@]}"; do
  if [ -d "$dir" ]; then
    echo "Formatting Python files in $dir..."
    black "$dir" || {
      echo "Black encountered issues in $dir. Please review the above errors."
    }
  else
    echo "Directory $dir not found. Skipping Black formatting for this directory."
  fi
done
echo "Black formatting completed."

# 1.2 Run isort (import sorter)
echo "Running isort to sort imports..."
for dir in "${PYTHON_DIRECTORIES[@]}"; do
  if [ -d "$dir" ]; then
    echo "Sorting imports in Python files in $dir..."
    isort --profile black "$dir" || {
      echo "isort encountered issues in $dir. Please review the above errors."
    }
  else
    echo "Directory $dir not found. Skipping isort for this directory."
  fi
done
echo "Import sorting completed."

# 1.3 Run flake8 (linter)
echo "Running flake8 linter..."
for dir in "${PYTHON_DIRECTORIES[@]}"; do
  if [ -d "$dir" ]; then
    echo "Linting Python files in $dir with flake8..."
    flake8 --max-line-length=100 "$dir" || {
      echo "Flake8 found issues in $dir. Please review the above warnings/errors."
    }
  else
    echo "Directory $dir not found. Skipping flake8 for this directory."
  fi
done
echo "Flake8 linting completed."

# 1.4 Run pylint (more comprehensive linter)
echo "Running pylint for more comprehensive linting..."
for dir in "${PYTHON_DIRECTORIES[@]}"; do
  if [ -d "$dir" ]; then
    echo "Linting Python files in $dir with pylint..."
    PY_FILES=$(find "$dir" -type f -name "*.py" -not -path "*/venv/*" -not -path "*/node_modules/*")
    if [ -n "$PY_FILES" ]; then
      echo "$PY_FILES" | xargs pylint --disable=C0111,C0103,C0303,W0621,C0301,W0612,W0611,R0913,R0914,R0915 || {
        echo "Pylint found issues in $dir. Please review the above warnings/errors."
      }
    fi
  else
    echo "Directory $dir not found. Skipping pylint for this directory."
  fi
done
echo "Pylint linting completed."

deactivate

# 2. JavaScript/TypeScript Linting
echo "----------------------------------------"
echo "Running JavaScript/TypeScript linting tools..."

# 2.1 web-frontend (Vite): use its own local ESLint and config
if [ -d "web-frontend" ]; then
  (
    cd web-frontend
    if [ ! -d "node_modules" ]; then
      echo "Installing web-frontend dependencies..."
      npm install
    fi
    echo "Linting JavaScript/TypeScript files in web-frontend with ESLint..."
    npx eslint src --ext .js,.jsx,.ts,.tsx --fix || {
      echo "ESLint found issues in web-frontend. Please review the above warnings/errors."
    }
  )
else
  echo "Directory web-frontend not found. Skipping ESLint for this directory."
fi

# 2.2 mobile-frontend (React Native): use its own local ESLint and config
if [ -d "mobile-frontend" ]; then
  (
    cd mobile-frontend
    if [ ! -d "node_modules" ]; then
      echo "Installing mobile-frontend dependencies..."
      npm install
    fi
    echo "Linting JavaScript/TypeScript files in mobile-frontend with ESLint..."
    npx eslint . --ext .js,.jsx,.ts,.tsx --fix || {
      echo "ESLint found issues in mobile-frontend. Please review the above warnings/errors."
    }
  )
else
  echo "Directory mobile-frontend not found. Skipping ESLint for this directory."
fi
echo "ESLint linting completed."

# 3. Solidity Linting
echo "----------------------------------------"
echo "Running Solidity linting tools..."

if [ -d "code/blockchain" ]; then
  (
    cd code/blockchain

    # Ensure a package.json exists so devDependency installs (solhint) have
    # somewhere to record themselves. code/blockchain now ships its own
    # package.json (Hardhat, OpenZeppelin, solc), so this is a defensive
    # fallback rather than the normal path.
    if [ ! -f "package.json" ]; then
      npm init -y > /dev/null
    fi

    # 3.1 Create solhint config if it doesn't exist
    if [ ! -f ".solhint.json" ]; then
      echo "Creating solhint configuration..."
      cat > .solhint.json << 'EOF'
{
  "extends": "solhint:recommended",
  "rules": {
    "compiler-version": ["error", "^0.8.0"],
    "func-visibility": ["warn", {"ignoreConstructors": true}]
  }
}
EOF
    fi

    if ! npm list solhint > /dev/null 2>&1 && ! command -v solhint &> /dev/null; then
      echo "Installing solhint..."
      npm install --save-dev solhint
    fi
  )

  # 3.2 Run solhint
  echo "Running solhint for Solidity files..."
  for dir in "${SOLIDITY_DIRECTORIES[@]}"; do
    if [ -d "$dir" ]; then
      echo "Linting Solidity files in $dir with solhint..."
      (cd code/blockchain && npx solhint "contracts/**/*.sol" --fix --noPrompt) || {
        echo "solhint found issues in $dir. Please review the above warnings/errors."
      }
    else
      echo "Directory $dir not found. Skipping solhint for this directory."
    fi
  done
  echo "solhint linting completed."
else
  echo "Directory code/blockchain not found. Skipping Solidity linting."
fi

# 4. YAML Linting
echo "----------------------------------------"
echo "Running YAML linting tools..."

# 4.1 Run yamllint if available
if [ "$YAMLLINT_AVAILABLE" = true ]; then
  echo "Running yamllint for YAML files..."
  for dir in "${YAML_DIRECTORIES[@]}"; do
    if [ -d "$dir" ]; then
      echo "Linting YAML files in $dir with yamllint..."
      yamllint "$dir" || {
        echo "yamllint found issues in $dir. Please review the above warnings/errors."
      }
    else
      echo "Directory $dir not found. Skipping yamllint for this directory."
    fi
  done
  echo "yamllint completed."
else
  echo "Skipping yamllint (not installed)."

  # 4.2 Basic YAML validation using Python
  echo "Performing basic YAML validation using Python..."
  # shellcheck source=/dev/null
  source "${PROJECT_DIR}/venv/bin/activate"
  pip install --upgrade pyyaml > /dev/null

  for dir in "${YAML_DIRECTORIES[@]}"; do
    if [ -d "$dir" ]; then
      echo "Validating YAML files in $dir..."
      find "$dir" -type f \( -name "*.yaml" -o -name "*.yml" \) -exec python3 -c "import yaml; yaml.safe_load(open('{}', 'r'))" \; || {
        echo "YAML validation found issues in $dir. Please review the above errors."
      }
    else
      echo "Directory $dir not found. Skipping YAML validation for this directory."
    fi
  done
  echo "Basic YAML validation completed."
  deactivate
fi

# 5. Terraform Linting
echo "----------------------------------------"
echo "Running Terraform linting tools..."

# 5.1 Run terraform fmt if available
if [ "$TERRAFORM_AVAILABLE" = true ]; then
  echo "Running terraform fmt for Terraform files..."
  for dir in "${TERRAFORM_DIRECTORIES[@]}"; do
    if [ -d "$dir" ]; then
      echo "Formatting Terraform files in $dir..."
      terraform fmt -recursive "$dir" || {
        echo "terraform fmt encountered issues in $dir. Please review the above errors."
      }
    else
      echo "Directory $dir not found. Skipping terraform fmt for this directory."
    fi
  done
  echo "terraform fmt completed."

  # 5.2 Run terraform validate if available
  echo "Running terraform validate for Terraform files..."
  for dir in "${TERRAFORM_DIRECTORIES[@]}"; do
    if [ -d "$dir" ]; then
      echo "Validating Terraform files in $dir..."
      (cd "$dir" && terraform init -backend=false && terraform validate) || {
        echo "terraform validate encountered issues in $dir. Please review the above errors."
      }
    else
      echo "Directory $dir not found. Skipping terraform validate for this directory."
    fi
  done
  echo "terraform validate completed."
else
  echo "Skipping Terraform linting (terraform not installed)."
fi

# 6. Common Fixes for All File Types
echo "----------------------------------------"
echo "Applying common fixes to all file types..."

# 6.1 Fix trailing whitespace
echo "Fixing trailing whitespace..."
find . -type f \( -name "*.py" -o -name "*.js" -o -name "*.jsx" -o -name "*.ts" -o -name "*.tsx" -o -name "*.sol" -o -name "*.yaml" -o -name "*.yml" -o -name "*.tf" -o -name "*.tfvars" \) \
  -not -path "*/node_modules/*" -not -path "*/venv/*" -not -path "*/.git/*" -not -path "*/build/*" -not -path "*/dist/*" \
  -exec sed -i 's/[ \t]*$//' {} \;
echo "Fixed trailing whitespace."

# 6.2 Ensure newline at end of file
echo "Ensuring newline at end of files..."
find . -type f \( -name "*.py" -o -name "*.js" -o -name "*.jsx" -o -name "*.ts" -o -name "*.tsx" -o -name "*.sol" -o -name "*.yaml" -o -name "*.yml" -o -name "*.tf" -o -name "*.tfvars" \) \
  -not -path "*/node_modules/*" -not -path "*/venv/*" -not -path "*/.git/*" -not -path "*/build/*" -not -path "*/dist/*" \
  -exec sh -c '[ -n "$(tail -c1 "$1")" ] && echo "" >> "$1"' sh {} \;
echo "Ensured newline at end of files."

echo "----------------------------------------"
echo "Linting and fixing process for BlockScore completed!"
echo "----------------------------------------"
