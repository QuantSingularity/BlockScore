# BlockScore Quick Start Guide

Get BlockScore up and running in 3 simple steps. This guide assumes you have the prerequisites installed.

## Prerequisites Check

Before starting, ensure you have:

- ✅ Python 3.8+ (`python3 --version`)
- ✅ Node.js 16+ (`node --version`)
- ✅ MongoDB running (`mongod --version`)
- ✅ Git (`git --version`)

## 🚀 3-Step Quick Start

### Step 1: Clone and Setup (2 minutes)

```bash
# Clone the repository
git clone https://github.com/quantsingularity/BlockScore.git
cd BlockScore

# Run automated setup script
./scripts/setup_blockscore_env.sh
```

This script will:

- Create Python virtual environments for AI models and backend
- Install all Node.js dependencies for backend and frontend
- Prepare the development environment

### Step 2: Configure Environment (1 minute)

```bash
# Copy example environment files
cp code/backend/.env.example code/backend/.env
cp web-frontend/.env.example web-frontend/.env

# Edit backend configuration (minimal required)
nano code/backend/.env
```

**Minimal `.env` configuration:**

```bash
# Database
DATABASE_URL=sqlite:///blockscore.db

# Security (change these!)
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-here

# Blockchain (optional for local development)
BLOCKCHAIN_PROVIDER_URL=http://localhost:8545
CONTRACT_ADDRESS=0x0000000000000000000000000000000000000000
```

### Step 3: Start the Application (1 minute)

```bash
# Option A: Use the run script (recommended)
./scripts/run_blockscore.sh

# Option B: Start services manually
# Terminal 1 - Backend API
cd code/backend
source venv_blockscore_backend_py/bin/activate
python app.py

# Terminal 2 - Web Frontend
cd web-frontend
npm start
```

## ✅ Verify Installation

Open your browser and navigate to:

- **Web Frontend**: <http://localhost:3000>
- **Backend API**: <http://localhost:5000/api/health>

You should see:

- Frontend: BlockScore dashboard login page
- Backend: JSON health check response

**Expected health check response:**

```json
{
  "success": true,
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "database": "up",
    "redis": "not_configured",
    "blockchain": "down",
    "ai_model": "up"
  }
}
```

## 🎯 Next Steps

### 1. Create Your First Account

```bash
# Using curl
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!"
  }'
```

### 2. Calculate a Credit Score

```bash
# Login first to get access token
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!"
  }'

# Calculate credit score (replace TOKEN with your access token)
curl -X POST http://localhost:5000/api/credit/calculate-score \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "walletAddress": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
  }'
```

### 3. Explore the Dashboard

Visit <http://localhost:3000> and:

1. Register a new account
2. Connect your wallet (MetaMask recommended)
3. View your credit profile
4. Explore credit score factors

## 🔧 Common Quick Start Issues

### Issue: `setup_blockscore_env.sh` fails

**Solution**: Check prerequisites are installed

```bash
python3 --version  # Should be 3.8+
node --version     # Should be 16+
npm --version      # Should be 8+
```

### Issue: Port 5000 already in use

**Solution**: Stop conflicting service or change port

```bash
# Find process using port 5000
lsof -i :5000

# Kill the process (replace PID)
kill -9 PID

# Or change Flask port in code/backend/app.py
# app.run(host="0.0.0.0", port=5001, debug=True)
```

### Issue: Database connection errors

**Solution**: Verify SQLite or configure PostgreSQL

```bash
# For SQLite (default), ensure write permissions
chmod 755 code/backend/

# For PostgreSQL, update DATABASE_URL in .env
DATABASE_URL=postgresql://user:password@localhost:5432/blockscore
```

### Issue: Frontend can't connect to backend

**Solution**: Check proxy configuration

```bash
# Verify web-frontend/package.json has:
"proxy": "http://localhost:5000"

# Restart frontend after changes
cd web-frontend && npm start
```

## 📚 What's Next?

- **Read the [Usage Guide](usage.md)** - Learn common workflows
- **Explore [API Documentation](API.md)** - Integrate with your applications
- **Review [Configuration Guide](CONFIGURATION.md)** - Advanced configuration options
- **Check [Examples](examples/)** - Working code samples

## 🐛 Still Having Issues?

1. Check [Troubleshooting Guide](troubleshooting.md)
2. Review logs in `code/backend/` directory
3. Open an issue on [GitHub](https://github.com/quantsingularity/BlockScore/issues)

---
