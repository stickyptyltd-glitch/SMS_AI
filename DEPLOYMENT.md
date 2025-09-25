# SynapseFlow AI - Deployment Guide

This guide provides comprehensive instructions for deploying SynapseFlow AI in various environments.

## 🚀 Quick Start

### Local Development Deployment

The fastest way to get started with SynapseFlow AI:

```bash
# Clone the repository
git clone <repository-url>
cd SMS_AI

# Run automated deployment script
./scripts/deploy_local.py
```

This script will:
- Check prerequisites
- Set up virtual environment
- Install dependencies
- Configure the application
- Initialize databases
- Run tests
- Start services

### Docker Deployment

For containerized deployment:

```bash
# Run Docker deployment script
./scripts/docker_deploy.py
```

This will create Docker containers with:
- Main application
- Redis cache
- Prometheus monitoring
- Persistent data volumes

## 📋 Prerequisites

### System Requirements

- **Operating System**: Linux, macOS, or Windows (with WSL2)
- **Python**: 3.8 or higher
- **Memory**: Minimum 2GB RAM, 4GB+ recommended
- **Storage**: At least 5GB free space
- **Network**: Internet access for AI services

### Required Services

#### Core Services
- **Python 3.8+**: Application runtime
- **pip**: Package management

#### Optional Services
- **Docker**: For containerized deployment
- **Redis**: For caching and session storage
- **PostgreSQL**: For production database (alternative to SQLite)

#### External APIs (Choose One)
- **OpenAI API**: GPT models
- **Ollama**: Local LLM server

## 🔧 Installation Methods

### Method 1: Automated Local Deployment

```bash
# Make script executable
chmod +x scripts/deploy_local.py

# Run deployment
./scripts/deploy_local.py
```

The script provides interactive prompts and handles:
- Environment setup
- Dependency installation
- Database initialization
- Configuration validation
- Test execution

### Method 2: Manual Installation

#### 1. Set up Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

#### 2. Install Dependencies

```bash
# Production dependencies
pip install -r requirements-server.txt

# Development dependencies (optional)
pip install -r requirements-dev.txt
```

#### 3. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env  # or your preferred editor
```

#### 4. Initialize Database

```bash
# Run database initialization
python scripts/init_database.py

# Optionally migrate to secure config
python scripts/migrate_config.py migrate
```

#### 5. Start Services

```bash
# Start main server
python server.py

# In another terminal, start admin interface
python admin_server.py
```

### Method 3: Docker Deployment

#### Prerequisites
- Docker 20.10+
- Docker Compose 2.0+

#### Deployment Steps

```bash
# Run automated Docker deployment
./scripts/docker_deploy.py
```

Or manually:

```bash
# Build and start containers
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f synapseflow-ai
```

## ⚙️ Configuration

### Environment Variables

Key configuration options in `.env`:

#### Core AI Configuration
```env
# OpenAI (Cloud)
OPENAI_API_KEY=your_openai_api_key
USE_OPENAI=1
OPENAI_MODEL=gpt-3.5-turbo

# Ollama (Local)
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3
OLLAMA_DISABLE=0
```

#### Server Configuration
```env
ENVIRONMENT=production  # or development
DEBUG=0                 # Set to 1 for development
SERVER_HOST=0.0.0.0
SERVER_PORT=8081
```

#### Security Configuration
```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD=secure-password-change-me
ADMIN_SECRET=generate-secure-random-string
LICENSE_ENFORCE=1
RATE_LIMIT_PER_MIN=120
```

#### External Integrations
```env
# Twilio SMS
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_FROM=your_phone_number

# Facebook Messenger
FB_PAGE_TOKEN=your_page_token
FB_VERIFY_TOKEN=your_verify_token
FB_APP_SECRET=your_app_secret
```

### Secure Configuration Management

For production environments, use encrypted configuration:

```bash
# Migrate to secure storage
python scripts/migrate_config.py migrate

# Create environment-specific configs
python scripts/migrate_config.py prod-env
python scripts/migrate_config.py dev-env
```

## 🗄️ Database Setup

### SQLite (Default)

SQLite databases are automatically created and managed:

```bash
# Initialize all databases
python scripts/init_database.py

# Custom data directory
python scripts/init_database.py /path/to/data
```

Database files will be created in:
- `synapseflow_data/webhooks/webhooks.db`
- `synapseflow_data/users/users.db`
- `synapseflow_data/analytics/analytics.db`
- `synapseflow_data/security/security.db`

### PostgreSQL (Production Alternative)

For high-traffic production environments:

1. Install PostgreSQL
2. Create database and user
3. Update connection string in `.env`
4. Run migration scripts

## 🔒 Security Configuration

### Production Security Checklist

- [ ] Change default admin credentials
- [ ] Generate secure random secrets
- [ ] Enable HTTPS/TLS
- [ ] Configure firewall rules
- [ ] Set up intrusion detection
- [ ] Enable audit logging
- [ ] Regular security updates

### Generating Secure Secrets

```bash
# Generate secure admin secret
python -c "import secrets; print(secrets.token_urlsafe(48))"

# Use built-in secret generation
python scripts/migrate_config.py migrate
```

### Rate Limiting

Configure rate limiting to prevent abuse:

```env
RATE_LIMIT_PER_MIN=120      # Requests per minute per IP
ADMIN_ENFORCE_USERS=1       # Require user authentication
```

## 🐳 Docker Configuration

### Docker Compose Services

The Docker deployment includes:

#### SynapseFlow AI Application
- Port: 8081 (main app), 5050 (admin)
- Health checks enabled
- Auto-restart on failure
- Persistent data volumes

#### Redis Cache
- Port: 6379
- Data persistence
- Health monitoring

#### Prometheus Monitoring
- Port: 9090
- Metrics collection
- Dashboard available

### Docker Volume Management

Data is persisted in Docker volumes:

```bash
# List volumes
docker volume ls

# Backup data
docker run --rm -v synapseflow_data:/data -v $(pwd):/backup alpine \
  tar czf /backup/synapseflow-backup.tar.gz -C /data .

# Restore data
docker run --rm -v synapseflow_data:/data -v $(pwd):/backup alpine \
  tar xzf /backup/synapseflow-backup.tar.gz -C /data
```

## 🔍 Health Checks and Monitoring

### Built-in Health Endpoints

```bash
# Application health
curl http://localhost:8081/health

# Detailed system health
curl http://localhost:8081/monitoring/api/health

# Prometheus metrics
curl http://localhost:8081/metrics
```

### Monitoring Dashboard

Access the web dashboard at:
- http://localhost:8081/monitoring/dashboard

Features:
- Real-time system metrics
- Request statistics
- AI usage tracking
- Error monitoring
- Auto-refresh every 30 seconds

### Log Files

Logs are organized by category:

```
synapseflow_data/logs/
├── app/           # Application logs
├── security/      # Security events
├── webhook/       # Webhook delivery logs
├── health/        # Health check logs
└── performance/   # Performance metrics
```

## 🧪 Testing and Validation

### Run Test Suite

```bash
# Comprehensive test suite
python scripts/run_tests.py

# Specific test categories
pytest tests/test_config_validator.py -v
pytest tests/test_health_checker.py -v
pytest tests/test_integration.py -v
```

### Validate Configuration

```bash
# Validate current configuration
python scripts/migrate_config.py validate

# Check system health
curl http://localhost:8081/health
```

## 🔄 Updates and Maintenance

### Updating the Application

```bash
# Stop services
docker-compose down  # For Docker
# Or stop Python processes for local deployment

# Pull updates
git pull origin main

# Update dependencies
pip install -r requirements-server.txt

# Run database migrations (if any)
python scripts/init_database.py

# Restart services
docker-compose up -d  # For Docker
# Or restart Python processes
```

### Backup and Restore

#### Backup

```bash
# Create backup directory
mkdir -p backups/$(date +%Y%m%d_%H%M%S)

# Backup configuration
python -c "
from utils.secure_config import get_config_manager
manager = get_config_manager()
manager.backup_config('backups/config_backup.enc')
"

# Backup data directory
tar czf backups/data_backup.tar.gz synapseflow_data/
```

#### Restore

```bash
# Restore configuration
python -c "
from utils.secure_config import get_config_manager
manager = get_config_manager()
manager.restore_config('backups/config_backup.enc')
"

# Restore data
tar xzf backups/data_backup.tar.gz
```

## 🚨 Troubleshooting

### Common Issues

#### Port Already in Use
```bash
# Find process using port
sudo lsof -i :8081

# Kill process
sudo kill -9 <PID>
```

#### Permission Denied
```bash
# Fix file permissions
chmod +x scripts/*.py
chmod 755 synapseflow_data/
```

#### Database Connection Issues
```bash
# Check database files
ls -la synapseflow_data/*/

# Reinitialize databases
rm -rf synapseflow_data/
python scripts/init_database.py
```

#### Memory Issues
```bash
# Check memory usage
free -h

# Monitor application memory
docker stats synapseflow-ai
```

### Log Analysis

#### Application Logs
```bash
# View recent logs
tail -f synapseflow_data/logs/app/app.log

# Search for errors
grep -r "ERROR" synapseflow_data/logs/
```

#### Docker Logs
```bash
# Container logs
docker-compose logs -f synapseflow-ai

# System events
docker events
```

### Performance Tuning

#### Memory Optimization
```env
# Adjust worker processes
WORKERS=2

# Optimize cache settings
CACHE_TIMEOUT=3600
MAX_CACHE_SIZE=1000
```

#### Database Optimization
```bash
# SQLite optimization
sqlite3 synapseflow_data/webhooks/webhooks.db "VACUUM;"
sqlite3 synapseflow_data/webhooks/webhooks.db "ANALYZE;"
```

## 📞 Support

### Getting Help

1. **Check Logs**: Review application and system logs
2. **Health Checks**: Verify all services are running
3. **Configuration**: Validate configuration settings
4. **Documentation**: Review relevant documentation sections
5. **Community**: Check GitHub issues and discussions

### Reporting Issues

When reporting issues, include:
- Operating system and version
- Python version
- Deployment method (local/Docker)
- Error logs and stack traces
- Configuration details (sanitized)
- Steps to reproduce

### Performance Monitoring

Use the built-in monitoring dashboard to track:
- System resource usage
- Request response times
- Error rates
- AI model performance
- Webhook delivery success rates

The dashboard auto-refreshes and provides real-time insights into system health and performance.

---

For additional support and advanced configuration options, refer to the other documentation files in this repository.