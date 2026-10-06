# BlockScore Installation Guide

Complete installation guide for BlockScore across different platforms and deployment scenarios.

## Table of Contents

- [System Requirements](#system-requirements)
- [Installation Methods](#installation-methods)
- [Platform-Specific Instructions](#platform-specific-instructions)
- [Post-Installation Steps](#post-installation-steps)
- [Verification](#verification)

## System Requirements

### Minimum Requirements

- **CPU**: 2 cores
- **RAM**: 4 GB
- **Storage**: 10 GB free space
- **OS**: Ubuntu 20.04+, macOS 11+, Windows 10+ (with WSL2)

### Recommended Requirements

- **CPU**: 4+ cores
- **RAM**: 8 GB+
- **Storage**: 20 GB+ SSD
- **Network**: Stable internet for blockchain connectivity

### Software Prerequisites

| Software | Min Version | Purpose             | Installation Check    |
| -------- | ----------- | ------------------- | --------------------- |
| Python   | 3.8+        | Backend & AI models | `python3 --version`   |
| Node.js  | 16+         | Backend & Frontend  | `node --version`      |
| npm      | 8+          | Package management  | `npm --version`       |
| MongoDB  | 4.4+        | Database (optional) | `mongod --version`    |
| Git      | 2.25+       | Version control     | `git --version`       |
| Redis    | 6.0+        | Caching (optional)  | `redis-cli --version` |

## Installation Methods

### Method 1: Automated Setup Script (Recommended)

The fastest way to get started. Suitable for development and testing.

```bash
# Clone repository
git clone https://github.com/quantsingularity/BlockScore.git
cd BlockScore

# Make setup script executable
chmod +x scripts/setup_blockscore_env.sh

# Run setup
./scripts/setup_blockscore_env.sh
```

**What the script does:**

1. Creates Python virtual environments
2. Installs Python dependencies (backend & AI)
3. Installs Node.js dependencies (backend & frontend)
4. Sets up project structure

**Time required**: 5-10 minutes (depending on internet speed)

### Method 2: Manual Installation

For advanced users who want full control over the installation process.

#### Step 1: Clone Repository

```bash
git clone https://github.com/quantsingularity/BlockScore.git
cd BlockScore
```

#### Step 2: Backend Setup (Python/Flask)

```bash
cd code/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env
```

#### Step 3: AI Models Setup

```bash
cd ../ai_models

# Create virtual environment
python3 -m venv venv_ai
source venv_ai/bin/activate

# Install dependencies
pip install -r requirements.txt

# Return to project root
cd ../../..
```

#### Step 4: Web Frontend Setup

```bash
cd web-frontend

# Install dependencies
npm install

# Copy environment template
cp .env.example .env

# Edit .env if needed
nano .env
```

#### Step 5: Smart Contracts Setup (Optional)

```bash
cd ../code/blockchain

# Install dependencies (includes Hardhat)
npm install

# Compile contracts (fully offline, via the local solc npm package)
npm run compile
```

### Method 3: Docker Installation (Coming Soon)

Docker-based installation for containerized deployment.

```bash
# Build and run with Docker Compose
docker-compose up -d

# Verify services
docker-compose ps
```

## Platform-Specific Instructions

### Ubuntu/Debian Linux

| Component   | Installation Command                                                                                              | Notes                              |
| ----------- | ----------------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| Python 3.8+ | `sudo apt update && sudo apt install python3 python3-pip python3-venv`                                            | Already installed on Ubuntu 20.04+ |
| Node.js 16+ | `curl -fsSL https://deb.nodesource.com/setup_18.x \| sudo -E bash - && sudo apt install -y nodejs`                | Installs Node.js 18 LTS            |
| MongoDB     | `sudo apt install mongodb` or [MongoDB Docs](https://docs.mongodb.com/manual/tutorial/install-mongodb-on-ubuntu/) | Optional for development           |
| Redis       | `sudo apt install redis-server`                                                                                   | Optional but recommended           |
| Build tools | `sudo apt install build-essential`                                                                                | Required for native modules        |

**Complete Ubuntu Setup:**

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3 python3-pip python3-venv nodejs npm mongodb redis-server build-essential git

# Start services
sudo systemctl start mongodb
sudo systemctl start redis-server

# Verify installations
python3 --version && node --version && mongod --version
```

### macOS

| Component   | Installation Command                                                                              | Notes           |
| ----------- | ------------------------------------------------------------------------------------------------- | --------------- |
| Homebrew    | `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"` | Package manager |
| Python 3.8+ | `brew install python@3.11`                                                                        | Latest Python 3 |
| Node.js 16+ | `brew install node@18`                                                                            | Node.js 18 LTS  |
| MongoDB     | `brew tap mongodb/brew && brew install mongodb-community`                                         | Optional        |
| Redis       | `brew install redis`                                                                              | Optional        |

**Complete macOS Setup:**

```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python@3.11 node@18 mongodb-community redis git

# Start services
brew services start mongodb-community
brew services start redis

# Verify installations
python3 --version && node --version && mongod --version
```

### Windows (WSL2 Recommended)

**Option A: WSL2 (Recommended)**

1. Enable WSL2:

```powershell
# Run in PowerShell as Administrator
wsl --install
wsl --set-default-version 2
```

2. Install Ubuntu from Microsoft Store
3. Follow Ubuntu instructions above inside WSL2

**Option B: Native Windows**

| Component   | Installation Method                                                         | Notes                   |
| ----------- | --------------------------------------------------------------------------- | ----------------------- |
| Python 3.8+ | Download from [python.org](https://www.python.org/downloads/)               | Check "Add to PATH"     |
| Node.js 16+ | Download from [nodejs.org](https://nodejs.org/)                             | LTS version recommended |
| MongoDB     | Download from [mongodb.com](https://www.mongodb.com/try/download/community) | Windows installer       |
| Git         | Download from [git-scm.com](https://git-scm.com/)                           | Git Bash included       |

## Post-Installation Steps

### 1. Configure Environment Variables

Edit `code/backend/.env`:

```bash
# Database Configuration
DATABASE_URL=sqlite:///blockscore.db
# For PostgreSQL: postgresql://user:password@localhost:5432/blockscore

# Security Keys (CHANGE THESE!)
SECRET_KEY=generate-a-random-secret-key-here
JWT_SECRET_KEY=generate-another-random-key-here

# JWT Token Expiration (seconds)
JWT_ACCESS_TOKEN_EXPIRES=900        # 15 minutes
JWT_REFRESH_TOKEN_EXPIRES=604800    # 7 days

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# Blockchain Configuration
BLOCKCHAIN_PROVIDER_URL=http://localhost:8545
CONTRACT_ADDRESS=0x0000000000000000000000000000000000000000
PRIVATE_KEY=your-private-key-here

# Rate Limiting
RATE_LIMIT_DEFAULT=100 per hour
RATE_LIMIT_LOGIN=5 per minute

# Logging
LOG_LEVEL=INFO
```

### 2. Initialize Database

```bash
cd code/backend
source venv/bin/activate

# Database will auto-initialize on first run
python app.py
```

### 3. Compile Smart Contracts (Optional)

```bash
cd code/blockchain

# Start a local blockchain node (Hardhat's built-in node)
npx hardhat node

# In another terminal, compile and deploy
npm run compile
npm run deploy:local
```

### 4. Generate Secret Keys

```bash
# Generate secure random keys
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"
python3 -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_hex(32))"
```

## Verification

### Quick Health Check

```bash
# Start backend
cd code/backend
source venv/bin/activate
python app.py &

# Test health endpoint
curl http://localhost:5000/api/health
```

**Expected output:**

```json
{
  "success": true,
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "database": "up",
    "redis": "up" or "not_configured",
    "blockchain": "up" or "down",
    "ai_model": "up"
  }
}
```

### Run Test Suite

```bash
# Backend tests
cd code/backend
source venv/bin/activate
pytest

# Smart contract tests
cd code/blockchain
npm test

# Frontend tests
cd web-frontend
npm test
```

### Verify All Services

| Service     | Test Command                            | Expected Result            |
| ----------- | --------------------------------------- | -------------------------- |
| Backend API | `curl http://localhost:5000/api/health` | HTTP 200, "healthy" status |
| Frontend    | Open `http://localhost:3000`            | Dashboard loads            |
| MongoDB     | `mongo --eval "db.version()"`           | Version number             |
| Redis       | `redis-cli ping`                        | "PONG"                     |
| Blockchain  | `curl -X POST http://localhost:8545`    | JSON-RPC response          |

## Troubleshooting Installation

### Python Installation Issues

**Problem**: `python3: command not found`

**Solution**:

```bash
# Ubuntu/Debian
sudo apt install python3 python3-pip

# macOS
brew install python@3.11

# Verify
python3 --version
```

### Node.js Installation Issues

**Problem**: `node: command not found`

**Solution**:

```bash
# Ubuntu/Debian
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# macOS
brew install node@18

# Verify
node --version && npm --version
```

### Permission Errors

**Problem**: `EACCES: permission denied`

**Solution**:

```bash
# Fix npm permissions (Linux/macOS)
sudo chown -R $USER:$GROUP ~/.npm
sudo chown -R $USER:$GROUP ~/.config

# Or use nvm (recommended)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
```

### Virtual Environment Issues

**Problem**: `venv` module not found

**Solution**:

```bash
# Ubuntu/Debian
sudo apt install python3-venv

# Verify
python3 -m venv --help
```

### MongoDB Connection Issues

**Problem**: Can't connect to MongoDB

**Solution**:

```bash
# Check if MongoDB is running
sudo systemctl status mongodb  # Linux
brew services list | grep mongo  # macOS

# Start MongoDB
sudo systemctl start mongodb  # Linux
brew services start mongodb-community  # macOS

# Use SQLite for development (no MongoDB required)
# In .env: DATABASE_URL=sqlite:///blockscore.db
```

## Next Steps

✅ Installation complete! Continue with:

1. [Quick Start Guide](QUICKSTART.md) - Get up and running
2. [Configuration Guide](CONFIGURATION.md) - Advanced configuration
3. [Usage Guide](USAGE.md) - Learn how to use BlockScore

## Additional Resources

- [Official Repository](https://github.com/quantsingularity/BlockScore)
- [Troubleshooting Guide](TROUBLESHOOTING.md)
- [Architecture Overview](ARCHITECTURE.md)

---
