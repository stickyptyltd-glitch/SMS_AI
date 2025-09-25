# SynapseFlow AI - Configuration Guide

This guide provides detailed information about configuring SynapseFlow AI for different environments and use cases.

## 📝 Configuration Overview

SynapseFlow AI uses a layered configuration approach:

1. **Environment Variables** (.env file)
2. **Secure Configuration** (encrypted storage)
3. **Runtime Configuration** (JSON files)
4. **Command Line Arguments** (for scripts)

## 🔧 Environment Configuration

### Configuration Files

#### `.env` - Main Environment Configuration
Primary configuration file for environment variables.

#### `.env.example` - Configuration Template
Template file showing all available options with documentation.

#### `.env.production` - Production Configuration
Production-specific configuration (created by migration script).

#### `.env.development` - Development Configuration
Development-specific configuration with debug options enabled.

### Environment-Specific Configuration

#### Development Environment
```env
ENVIRONMENT=development
DEBUG=1
ADMIN_DEBUG=1
LOG_FORMAT=text
CONFIG_VALIDATION_STRICT=0
LICENSE_ENFORCE=0
```

#### Production Environment
```env
ENVIRONMENT=production
DEBUG=0
ADMIN_DEBUG=0
LOG_FORMAT=json
CONFIG_VALIDATION_STRICT=1
LICENSE_ENFORCE=1
```

## 🤖 AI Configuration

### OpenAI Configuration

#### Basic Setup
```env
# Enable OpenAI
USE_OPENAI=1
OPENAI_API_KEY=sk-your_openai_api_key_here

# Model Selection
OPENAI_MODEL=gpt-3.5-turbo
# Alternatives: gpt-4, gpt-4-turbo, gpt-3.5-turbo-16k
```

#### Advanced OpenAI Settings
```env
# Request Configuration
OPENAI_MAX_TOKENS=1000
OPENAI_TEMPERATURE=0.7
OPENAI_TIMEOUT=30

# Rate Limiting
OPENAI_MAX_REQUESTS_PER_MINUTE=60
OPENAI_MAX_TOKENS_PER_MINUTE=90000
```

### Ollama Configuration (Local LLM)

#### Basic Setup
```env
# Ollama Server
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3
OLLAMA_DISABLE=0

# Alternative models: codellama, mistral, neural-chat
```

#### Advanced Ollama Settings
```env
# Performance Tuning
OLLAMA_NUM_THREAD=4
OLLAMA_NUM_GPU=1
OLLAMA_TIMEOUT=60

# Model Parameters
OLLAMA_TEMPERATURE=0.7
OLLAMA_TOP_K=40
OLLAMA_TOP_P=0.9
```

### AI Fallback Configuration

```env
# Fallback Strategy
AI_FALLBACK_ENABLED=1
AI_CIRCUIT_BREAKER_ENABLED=1
AI_MAX_RETRIES=3

# Circuit Breaker Settings
AI_CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
AI_CIRCUIT_BREAKER_RECOVERY_TIMEOUT=300
```

## 🌐 Server Configuration

### Main Application Server

```env
# Server Binding
SERVER_HOST=0.0.0.0    # 127.0.0.1 for local only
SERVER_PORT=8081

# Worker Configuration
SERVER_WORKERS=2       # Number of worker processes
SERVER_THREADS=4       # Threads per worker
```

### Admin Interface

```env
# Admin Server
ADMIN_HOST=127.0.0.1   # Restrict admin access
ADMIN_PORT=5050

# Admin Authentication
ADMIN_USERNAME=admin
ADMIN_PASSWORD=secure-password-change-me-in-production
ADMIN_SECRET=generate-secure-random-string-48-chars-minimum
```

### SSL/TLS Configuration

```env
# HTTPS Configuration
SSL_ENABLED=1
SSL_CERT_PATH=/path/to/certificate.pem
SSL_KEY_PATH=/path/to/private_key.pem

# SSL Options
SSL_REDIRECT=1         # Redirect HTTP to HTTPS
SSL_VERIFY_PEER=1      # Verify client certificates
```

## 🔒 Security Configuration

### Authentication and Authorization

```env
# User Management
ADMIN_ENFORCE_USERS=1  # Require user authentication
DEFAULT_USER_ROLE=user # New user default role

# Session Configuration
SESSION_TIMEOUT=3600   # Session timeout in seconds
MAX_LOGIN_ATTEMPTS=5   # Before account lockout
LOCKOUT_DURATION=900   # Account lockout duration in seconds
```

### Rate Limiting

```env
# General Rate Limiting
RATE_LIMIT_PER_MIN=120        # Requests per minute per IP
RATE_LIMIT_WINDOW=60          # Time window in seconds
RATE_LIMIT_BURST=10           # Burst allowance

# API-Specific Rate Limits
API_RATE_LIMIT_PER_MIN=60     # API endpoint limits
ADMIN_RATE_LIMIT_PER_MIN=30   # Admin interface limits
```

### Security Secrets

```env
# Application Secrets
SECRET_KEY=your-flask-secret-key-here
JWT_SECRET=your-jwt-secret-key-here

# License Configuration
LICENSE_ENFORCE=1
LICENSE_ISSUER_SECRET=your-license-signing-secret
```

### IP Access Control

```env
# IP Whitelist/Blacklist
ALLOWED_IPS=192.168.1.0/24,10.0.0.0/8
BLOCKED_IPS=

# Geographic Restrictions
ALLOWED_COUNTRIES=US,CA,UK,DE,FR
BLOCKED_COUNTRIES=
```

## 🗄️ Database Configuration

### SQLite Configuration (Default)

```env
# Data Directory
DATA_DIR=synapseflow_data

# Database Settings
DB_BACKUP_ENABLED=1
DB_BACKUP_INTERVAL_HOURS=24
DB_VACUUM_INTERVAL_HOURS=168  # Weekly
```

### PostgreSQL Configuration (Production)

```env
# PostgreSQL Connection
DATABASE_URL=postgresql://username:password@host:port/database

# Connection Pool
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
```

### Redis Configuration

```env
# Redis Connection
REDIS_URL=redis://localhost:6379/0

# Redis Settings
REDIS_TIMEOUT=5
REDIS_MAX_CONNECTIONS=10
REDIS_HEALTH_CHECK_INTERVAL=30
```

## 📡 External Service Integration

### Twilio SMS Configuration

```env
# Twilio Credentials
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_FROM=+1234567890

# Twilio Settings
TWILIO_TIMEOUT=10
TWILIO_RETRY_ATTEMPTS=3
```

### Facebook Messenger Configuration

```env
# Facebook App Credentials
FB_PAGE_TOKEN=your_page_access_token
FB_VERIFY_TOKEN=your_webhook_verify_token
FB_APP_SECRET=your_app_secret

# Facebook Settings
FB_API_VERSION=v18.0
FB_TIMEOUT=15
```

### Webhook Configuration

```env
# Webhook Settings
WEBHOOK_TIMEOUT=30
WEBHOOK_RETRY_ATTEMPTS=3
WEBHOOK_RETRY_DELAY=5

# Webhook Security
WEBHOOK_SIGNATURE_HEADER=X-Hub-Signature-256
WEBHOOK_VERIFY_SSL=1
```

## 🔍 Monitoring Configuration

### Health Checks

```env
# Health Check Settings
HEALTH_CHECK_INTERVAL=60      # Seconds between checks
HEALTH_CHECK_TIMEOUT=10       # Timeout for health checks
HEALTH_CHECK_ENABLED=1        # Enable/disable health monitoring
```

### Metrics Collection

```env
# Prometheus Metrics
ENABLE_METRICS=1
METRICS_PORT=9090
METRICS_PATH=/metrics

# Metrics Collection
COLLECT_SYSTEM_METRICS=1
COLLECT_AI_METRICS=1
COLLECT_WEBHOOK_METRICS=1
```

### Logging Configuration

```env
# Log Format
LOG_FORMAT=json               # json or text
LOG_LEVEL=INFO               # DEBUG, INFO, WARNING, ERROR

# Log Rotation
LOG_ROTATE_SIZE=10MB
LOG_ROTATE_COUNT=5
LOG_COMPRESS=1
```

## 🚀 Performance Configuration

### Caching Configuration

```env
# Cache Settings
CACHE_TYPE=redis             # redis, memory, or filesystem
CACHE_TIMEOUT=3600           # Default timeout in seconds
CACHE_MAX_SIZE=1000          # Maximum cache entries
```

### Connection Pooling

```env
# HTTP Connection Pool
HTTP_POOL_SIZE=10
HTTP_POOL_MAXSIZE=20
HTTP_TIMEOUT=30
```

### Background Tasks

```env
# Task Queue Configuration
TASK_QUEUE_ENABLED=1
TASK_QUEUE_WORKERS=2
TASK_QUEUE_MAX_TASKS=1000
```

## 🛠️ Configuration Tools

### Configuration Validation

```bash
# Validate current configuration
python scripts/migrate_config.py validate

# Strict validation (production mode)
CONFIG_VALIDATION_STRICT=1 python scripts/migrate_config.py validate
```

### Secure Configuration Management

```bash
# Migrate to secure storage
python scripts/migrate_config.py migrate

# Create environment-specific configs
python scripts/migrate_config.py dev-env
python scripts/migrate_config.py prod-env
```

### Configuration Templates

```bash
# Generate .env from template
cp .env.example .env

# Create production config
python scripts/migrate_config.py prod-env
```

## 📋 Configuration Validation Rules

### Required Fields by Environment

#### Development Environment
- `ENVIRONMENT=development`
- `SERVER_PORT`
- One AI provider configured (OpenAI or Ollama)

#### Production Environment
- `ENVIRONMENT=production`
- `DEBUG=0`
- Secure admin credentials (password length > 12)
- `ADMIN_SECRET` (length > 32)
- HTTPS configuration recommended
- Rate limiting configured

### Validation Checks

#### Security Validation
- Admin password strength
- Secret key length and randomness
- Debug mode disabled in production
- Rate limiting configured

#### AI Configuration Validation
- At least one AI provider configured
- API keys format validation
- Model availability checks
- Timeout and retry settings

#### Network Configuration Validation
- Port availability
- SSL certificate validity
- External service connectivity

## 🔄 Configuration Migration

### From Plain Text to Secure Storage

```bash
# Step 1: Backup current configuration
cp .env .env.backup

# Step 2: Migrate to secure storage
python scripts/migrate_config.py migrate

# Step 3: Verify migration
python scripts/migrate_config.py validate

# Step 4: Test application
python server.py --test-config
```

### Environment Migration

```bash
# Development to Production
python scripts/migrate_config.py prod-env

# Update production-specific values
nano .env.production

# Deploy with production config
cp .env.production .env
```

## 📊 Configuration Best Practices

### Security Best Practices

1. **Never commit secrets to version control**
   ```bash
   # Add to .gitignore
   echo ".env*" >> .gitignore
   echo "*.key" >> .gitignore
   echo "*.pem" >> .gitignore
   ```

2. **Use strong, unique secrets**
   ```bash
   # Generate secure random strings
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

3. **Rotate secrets regularly**
   ```bash
   # Use secure config rotation
   python scripts/migrate_config.py rotate-keys
   ```

4. **Principle of least privilege**
   - Restrict admin interface access
   - Use IP whitelisting
   - Enable user authentication

### Performance Best Practices

1. **Optimize for your workload**
   - Adjust worker processes based on CPU cores
   - Configure appropriate timeouts
   - Enable caching for frequently accessed data

2. **Monitor resource usage**
   - Use built-in monitoring dashboard
   - Set up alerts for resource thresholds
   - Regular performance testing

3. **Scale appropriately**
   - Use Redis for high-traffic scenarios
   - Consider PostgreSQL for large datasets
   - Implement rate limiting

### Operational Best Practices

1. **Environment separation**
   - Use different configurations for dev/staging/prod
   - Test configuration changes in staging first
   - Use configuration validation

2. **Backup and recovery**
   - Regular configuration backups
   - Test restore procedures
   - Document configuration changes

3. **Monitoring and alerting**
   - Enable comprehensive logging
   - Set up health checks
   - Configure alerting for critical issues

## 🚨 Troubleshooting Configuration Issues

### Common Configuration Problems

#### Invalid API Keys
```bash
# Test OpenAI key
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/models

# Test Ollama connection
curl $OLLAMA_URL/api/tags
```

#### Port Conflicts
```bash
# Check port usage
sudo netstat -tlnp | grep :8081

# Find alternative port
python -c "import socket; s=socket.socket(); s.bind(('',0)); print(s.getsockname()[1]); s.close()"
```

#### Permission Issues
```bash
# Fix file permissions
chmod 600 .env*
chmod +x scripts/*.py
chown -R $(whoami):$(whoami) synapseflow_data/
```

#### Memory/Resource Issues
```bash
# Check system resources
free -h
df -h
ps aux | grep python
```

### Configuration Debugging

#### Enable Debug Logging
```env
DEBUG=1
LOG_LEVEL=DEBUG
CONFIG_DEBUG=1
```

#### Validate Configuration
```bash
# Check configuration syntax
python -c "from utils.config_validator import validate_environment; print(validate_environment())"

# Test specific components
python -c "from utils.health_checker import get_system_health; import asyncio; print(asyncio.run(get_system_health()))"
```

#### Monitor Configuration Usage
```bash
# Watch configuration access
tail -f synapseflow_data/logs/app/app.log | grep -i config

# Check secure config access
python -c "from utils.secure_config import get_config_manager; print(get_config_manager().list_configs())"
```

For more detailed troubleshooting, refer to the [Deployment Guide](DEPLOYMENT.md) and check the application logs for specific error messages.