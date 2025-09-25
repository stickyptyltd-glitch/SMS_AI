# SynapseFlow AI - API Documentation

This document provides comprehensive API documentation for the SynapseFlow AI platform.

## 🌐 API Overview

SynapseFlow AI provides RESTful APIs for:
- Message processing and AI responses
- User management and authentication
- System monitoring and health checks
- Webhook management
- Configuration management

### Base URLs

- **Main API**: `http://localhost:8081`
- **Admin API**: `http://localhost:5050`
- **Monitoring**: `http://localhost:8081/monitoring`

### API Versioning

Current API version: `v1`
All API endpoints are prefixed with `/api/v1` (except legacy endpoints for backward compatibility).

## 🔐 Authentication

### API Token Authentication

```bash
# Get API token (requires admin authentication)
curl -X POST http://localhost:8081/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your-password"}'

# Use token in requests
curl -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  http://localhost:8081/api/v1/user/profile
```

### Admin Authentication

Admin endpoints require admin token:

```bash
# Admin login
curl -X POST http://localhost:5050/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin-password"}'
```

## 📝 Core API Endpoints

### Health and Status

#### GET /health
Basic health check endpoint.

```bash
curl http://localhost:8081/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2023-01-01T12:00:00Z",
  "version": "2.0.0",
  "services": {
    "database": "healthy",
    "ai_service": "healthy",
    "cache": "healthy"
  }
}
```

#### GET /api/v1/health/detailed
Comprehensive health status with metrics.

```bash
curl http://localhost:8081/api/v1/health/detailed
```

**Response:**
```json
{
  "overall_status": "healthy",
  "health_score": 0.95,
  "services": [
    {
      "service": "openai",
      "status": "healthy",
      "response_time": 150,
      "details": {
        "models_available": 5,
        "last_request": "2023-01-01T12:00:00Z"
      }
    }
  ],
  "system_info": {
    "cpu_usage": 25.5,
    "memory_usage": 1024000000,
    "disk_usage": 45.2
  }
}
```

### Message Processing

#### POST /reply
Process incoming message and generate AI response.

```bash
curl -X POST http://localhost:8081/reply \
  -H "Content-Type: application/json" \
  -d '{
    "incoming": "Hello, how are you?",
    "contact": "user123",
    "platform": "sms"
  }'
```

**Request Parameters:**
- `incoming` (required): The incoming message text
- `contact` (required): Contact identifier
- `platform` (optional): Platform identifier (sms, messenger, etc.)
- `context` (optional): Additional context object

**Response:**
```json
{
  "success": true,
  "draft": "Hello! I'm doing well, thank you for asking. How can I help you today?",
  "analysis": {
    "sentiment": "positive",
    "intent": "greeting",
    "confidence": 0.95
  },
  "contact": "user123",
  "platform": "sms",
  "response_time": 0.25
}
```

#### POST /api/v1/messages/process
Enhanced message processing with full context.

```bash
curl -X POST http://localhost:8081/api/v1/messages/process \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "message": "What is the weather like?",
    "contact_id": "user123",
    "conversation_id": "conv_456",
    "metadata": {
      "platform": "messenger",
      "timestamp": "2023-01-01T12:00:00Z"
    }
  }'
```

**Response:**
```json
{
  "success": true,
  "response": {
    "text": "I'd be happy to help with weather information...",
    "confidence": 0.9,
    "processing_time": 0.18
  },
  "analysis": {
    "intent": "weather_inquiry",
    "entities": ["weather"],
    "sentiment": "neutral"
  },
  "conversation": {
    "id": "conv_456",
    "turn_count": 3,
    "context_used": ["friendly_assistant"]
  },
  "ai_model": {
    "provider": "openai",
    "model": "gpt-3.5-turbo",
    "tokens_used": {
      "prompt": 150,
      "completion": 75
    }
  }
}
```

### User Management

#### POST /api/v1/users/register
Register a new user (requires admin token).

```bash
curl -X POST http://localhost:8081/api/v1/users/register \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: YOUR_ADMIN_TOKEN" \
  -d '{
    "username": "newuser",
    "email": "user@example.com",
    "password": "SecurePass123!",
    "role": "user"
  }'
```

**Response:**
```json
{
  "success": true,
  "user": {
    "id": "user_789",
    "username": "newuser",
    "email": "user@example.com",
    "role": "user",
    "created_at": "2023-01-01T12:00:00Z",
    "active": true
  },
  "message": "User registered successfully"
}
```

#### POST /api/v1/users/login
Authenticate user and get access token.

```bash
curl -X POST http://localhost:8081/api/v1/users/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "password": "SecurePass123!"
  }'
```

**Response:**
```json
{
  "success": true,
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": "user_789",
    "username": "newuser",
    "role": "user"
  },
  "expires_at": "2023-01-01T13:00:00Z"
}
```

#### GET /api/v1/users/profile
Get current user profile.

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8081/api/v1/users/profile
```

### Configuration Management

#### GET /config
Get current configuration (public settings only).

```bash
curl http://localhost:8081/config
```

**Response:**
```json
{
  "openai_enabled": true,
  "model": "gpt-3.5-turbo",
  "ollama_enabled": true,
  "version": "2.0.0",
  "features": {
    "webhooks": true,
    "user_management": true,
    "monitoring": true
  }
}
```

#### GET /api/v1/config/validation
Validate current configuration.

```bash
curl -H "Authorization: Bearer ADMIN_TOKEN" \
  http://localhost:8081/api/v1/config/validation
```

### Webhook Management

#### POST /api/v1/webhooks
Create a new webhook.

```bash
curl -X POST http://localhost:8081/api/v1/webhooks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "Slack Notifications",
    "integration_type": "notification",
    "platform": "slack",
    "endpoint_url": "https://hooks.slack.com/services/...",
    "secret_key": "webhook_secret",
    "active": true
  }'
```

**Response:**
```json
{
  "success": true,
  "webhook": {
    "id": "webhook_123",
    "name": "Slack Notifications",
    "integration_type": "notification",
    "platform": "slack",
    "endpoint_url": "https://hooks.slack.com/services/...",
    "active": true,
    "created_at": "2023-01-01T12:00:00Z"
  }
}
```

#### GET /api/v1/webhooks
List all webhooks.

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8081/api/v1/webhooks?platform=slack&active=true"
```

#### POST /api/v1/webhooks/{webhook_id}/test
Test webhook delivery.

```bash
curl -X POST http://localhost:8081/api/v1/webhooks/webhook_123/test \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"test_message": "Hello from SynapseFlow AI!"}'
```

#### GET /api/v1/webhooks/{webhook_id}/stats
Get webhook delivery statistics.

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8081/api/v1/webhooks/webhook_123/stats
```

**Response:**
```json
{
  "webhook_id": "webhook_123",
  "statistics": {
    "total_deliveries": 1250,
    "successful_deliveries": 1200,
    "failed_deliveries": 50,
    "success_rate": 96.0,
    "average_response_time": 0.25,
    "last_delivery": "2023-01-01T12:00:00Z"
  }
}
```

## 📊 Monitoring API

### GET /monitoring/api/metrics
Get comprehensive system metrics.

```bash
curl http://localhost:8081/monitoring/api/metrics
```

**Response:**
```json
{
  "timestamp": "2023-01-01T12:00:00Z",
  "system": {
    "cpu_percent": 25.5,
    "memory_bytes": 1073741824,
    "memory_percent": 65.2,
    "disk_percent": 45.0
  },
  "requests": {
    "POST:/reply": 1500,
    "GET:/health": 300
  },
  "ai_usage": {
    "openai:gpt-3.5-turbo:success": 1200,
    "ollama:llama3:success": 300
  },
  "response_time_stats": {
    "POST:/reply": {
      "count": 1500,
      "avg": 0.25,
      "min": 0.05,
      "max": 2.1
    }
  }
}
```

### GET /monitoring/api/alerts
Get active system alerts.

```bash
curl http://localhost:8081/monitoring/api/alerts
```

**Response:**
```json
{
  "alerts": [
    {
      "type": "cpu_high",
      "severity": "warning",
      "message": "High CPU usage: 85.5%",
      "timestamp": "2023-01-01T12:00:00Z"
    }
  ],
  "count": 1
}
```

### GET /metrics
Prometheus-compatible metrics endpoint.

```bash
curl http://localhost:8081/metrics
```

**Response:**
```
# HELP synapseflow_requests_total Total number of requests
# TYPE synapseflow_requests_total counter
synapseflow_requests_total{method="POST",endpoint="/reply",status_code="200"} 1500

# HELP synapseflow_system_cpu_usage_percent System CPU usage percentage
# TYPE synapseflow_system_cpu_usage_percent gauge
synapseflow_system_cpu_usage_percent 25.5
```

## 🔧 Admin API

### GET /admin/users
List all users (admin only).

```bash
curl -H "X-Admin-Token: YOUR_ADMIN_TOKEN" \
  "http://localhost:5050/admin/users?page=1&limit=20"
```

### GET /admin/system/status
Get detailed system status.

```bash
curl -H "X-Admin-Token: YOUR_ADMIN_TOKEN" \
  http://localhost:5050/admin/system/status
```

### POST /admin/system/maintenance
Put system in maintenance mode.

```bash
curl -X POST http://localhost:5050/admin/system/maintenance \
  -H "X-Admin-Token: YOUR_ADMIN_TOKEN" \
  -d '{"enabled": true, "message": "Scheduled maintenance"}'
```

## 🚨 Error Handling

### Standard Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": {
      "field": "contact",
      "issue": "required field missing"
    },
    "request_id": "req_123456789"
  },
  "timestamp": "2023-01-01T12:00:00Z"
}
```

### HTTP Status Codes

- `200 OK` - Request successful
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid request parameters
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error
- `503 Service Unavailable` - Service temporarily unavailable

### Error Codes

- `AUTHENTICATION_FAILED` - Invalid credentials
- `AUTHORIZATION_FAILED` - Insufficient permissions
- `VALIDATION_ERROR` - Invalid request parameters
- `RATE_LIMIT_EXCEEDED` - Too many requests
- `AI_SERVICE_ERROR` - AI service unavailable
- `DATABASE_ERROR` - Database operation failed
- `EXTERNAL_SERVICE_ERROR` - External service failure

## 🔄 Rate Limiting

### Rate Limit Headers

All API responses include rate limit headers:

```
X-RateLimit-Limit: 120
X-RateLimit-Remaining: 115
X-RateLimit-Reset: 1640995200
X-RateLimit-Window: 60
```

### Rate Limit Configuration

Default limits:
- General API: 120 requests/minute
- Authentication: 10 requests/minute
- Admin API: 30 requests/minute

## 📡 Webhooks

### Incoming Webhooks

#### POST /webhooks/twilio
Handle incoming Twilio SMS webhooks.

#### POST /webhooks/facebook
Handle incoming Facebook Messenger webhooks.

### Webhook Security

All incoming webhooks are verified using HMAC signatures:

```python
# Verification example (Python)
import hmac
import hashlib

def verify_webhook(payload, signature, secret):
    expected = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f'sha256={expected}', signature)
```

### Outgoing Webhook Format

```json
{
  "event": "message_processed",
  "data": {
    "contact": "user123",
    "message": "Hello, how are you?",
    "response": "Hello! I'm doing well...",
    "platform": "sms",
    "timestamp": "2023-01-01T12:00:00Z"
  },
  "webhook_id": "webhook_123",
  "delivery_attempt": 1
}
```

## 🧪 Testing the API

### Health Check
```bash
curl -v http://localhost:8081/health
```

### Basic Message Processing
```bash
curl -X POST http://localhost:8081/reply \
  -H "Content-Type: application/json" \
  -d '{"incoming": "Test message", "contact": "test_user"}'
```

### Authentication Test
```bash
# Get token
TOKEN=$(curl -s -X POST http://localhost:8081/api/v1/users/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}' | \
  python -c "import sys, json; print(json.load(sys.stdin)['token'])")

# Use token
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8081/api/v1/users/profile
```

## 📚 SDKs and Client Libraries

### Python Client Example

```python
import requests

class SynapseFlowClient:
    def __init__(self, base_url, token=None):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.session = requests.Session()
        if token:
            self.session.headers['Authorization'] = f'Bearer {token}'

    def process_message(self, message, contact, platform='api'):
        response = self.session.post(
            f'{self.base_url}/reply',
            json={
                'incoming': message,
                'contact': contact,
                'platform': platform
            }
        )
        response.raise_for_status()
        return response.json()

    def get_health(self):
        response = self.session.get(f'{self.base_url}/health')
        response.raise_for_status()
        return response.json()

# Usage
client = SynapseFlowClient('http://localhost:8081')
result = client.process_message('Hello!', 'user123')
print(result['draft'])
```

### JavaScript Client Example

```javascript
class SynapseFlowClient {
    constructor(baseUrl, token = null) {
        this.baseUrl = baseUrl.replace(/\/$/, '');
        this.token = token;
    }

    async request(method, path, data = null) {
        const headers = {
            'Content-Type': 'application/json',
        };

        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        const config = {
            method,
            headers,
        };

        if (data) {
            config.body = JSON.stringify(data);
        }

        const response = await fetch(`${this.baseUrl}${path}`, config);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return response.json();
    }

    async processMessage(message, contact, platform = 'api') {
        return this.request('POST', '/reply', {
            incoming: message,
            contact,
            platform
        });
    }

    async getHealth() {
        return this.request('GET', '/health');
    }
}

// Usage
const client = new SynapseFlowClient('http://localhost:8081');
client.processMessage('Hello!', 'user123')
    .then(result => console.log(result.draft));
```

## 🔍 API Monitoring

### Request Logging
All API requests are logged with:
- Request ID
- Timestamp
- Method and endpoint
- Response time
- Status code
- User information (if authenticated)

### Metrics Collection
The system automatically collects:
- Request counts by endpoint
- Response time histograms
- Error rates
- AI model usage
- Webhook delivery statistics

### Performance Monitoring
Monitor API performance using:
- `/monitoring/dashboard` - Web dashboard
- `/metrics` - Prometheus metrics
- Log analysis tools

For more detailed monitoring information, see the [Deployment Guide](DEPLOYMENT.md).