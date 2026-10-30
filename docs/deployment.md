# BlockScore Deployment Guide

## Deployment Options

### 1. Manual Deployment (VPS/VM)

**Requirements**:

- Ubuntu 20.04+ server
- 4GB RAM minimum
- PostgreSQL 12+
- Redis 6+
- Nginx

**Steps**:

1. Install dependencies:

   ```bash
   sudo apt update
   sudo apt install python3 python3-pip nodejs npm postgresql redis-server nginx
   ```

2. Clone and setup:

   ```bash
   git clone https://github.com/quantsingularity/BlockScore.git
   cd BlockScore
   ./scripts/setup_blockscore_env.sh
   ```

3. Configure environment:

   ```bash
   cd code/backend
   cp .env.example .env
   # Edit .env with production values
   ```

4. Start with Gunicorn:

   ```bash
   cd code/backend
   source venv/bin/activate
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

5. Configure Nginx:

   ```nginx
   server {
       listen 80;
       server_name api.blockscore.io;

       location / {
           proxy_pass http://127.0.0.1:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

### 2. Docker Deployment (Coming Soon)

```bash
docker-compose up -d
```

### 3. Kubernetes Deployment

Use Ansible playbooks in `infrastructure/ansible/`:

```bash
cd infrastructure/ansible
ansible-playbook -i inventory/hosts.yml playbooks/main.yml
```

## Production Checklist

- [ ] Use PostgreSQL (not SQLite)
- [ ] Enable HTTPS/TLS
- [ ] Configure Redis for caching
- [ ] Set strong SECRET_KEY and JWT_SECRET_KEY
- [ ] Enable rate limiting
- [ ] Setup monitoring (Prometheus/Grafana)
- [ ] Configure backups
- [ ] Use environment variables for secrets
- [ ] Enable audit logging
- [ ] Setup firewall rules

## Monitoring

Monitor these metrics:

- API response times
- Error rates
- Database connection pool
- Credit score calculation latency
- Blockchain transaction success rate

See [Configuration Guide](CONFIGURATION.md) for production settings.
