# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SynapseFlow AI is an enterprise SMS automation platform that combines AI-powered conversation handling with multi-platform integration (Twilio, Facebook Messenger, KDE Connect). The system features dual AI support (OpenAI/ChatGPT and local Ollama models), adaptive learning, advanced security, and comprehensive user management.

## Architecture

### Core Components
- **Flask Server** (`server.py`): Main API orchestrator with enterprise features (rate limiting, security, user management)
- **AI Engine** (`ai/`): Modular AI system with analysis, generation, context management, and adaptive learning
- **Test Client** (`test_client.py`): Development CLI with webhook support for multiple platforms
- **Android App** (`app/`): Kotlin-based SMS AutoReply companion app
- **Enterprise Modules**: Security (`security/`), licensing (`licensing/`), analytics (`analytics/`), performance (`performance/`)

### Data Flow
```
Client/Platform → Flask API → AI Analysis → Multi-Model AI → Response Generation → Platform Integration
                      ↓
                 User Management & Security & Caching & Analytics
```

### Key Architecture Patterns
- **Modular AI System**: Separate modules for analysis, generation, context, and adaptive learning
- **Multi-Model Support**: Abstraction layer supporting both OpenAI and Ollama models
- **Enterprise Security**: Advanced threat detection, hardware-bound licensing, rate limiting
- **Event-Driven**: Webhook-based integrations with comprehensive error handling
- **Stateful Conversations**: Persistent context management with memory summarization

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements-server.txt      # Server dependencies
pip install -r requirements-test-client.txt # Development/testing dependencies

# Configure environment
cp .env.example .env
# Edit .env with your API keys and configuration
```

### Running the System
```bash
# Start main server (Flask API)
python server.py

# Start admin server (separate process)
python admin_server.py

# Interactive development client
python test_client.py interactive --contact "TestUser"

# Send test message
python test_client.py reply "Hello, can you help me?" --contact "Customer"
```

### Platform-Specific Development
```bash
# Twilio webhook (development)
python test_client.py twilio webhook --host 0.0.0.0 --port 5005 --auto

# Messenger webhook (development)
python test_client.py messenger webhook --host 0.0.0.0 --port 5006 --auto

# KDE Connect integration
python test_client.py kde send --device-id YOUR_DEVICE --to +1234567890 --text "Test message"
```

### Testing
```bash
# Run all tests
pytest -v

# Run specific test categories
pytest tests/test_server_analysis.py -v
pytest tests/test_api_endpoints.py -v
pytest tests/test_advanced_features.py -v

# Run with coverage
pytest -v --cov=ai --cov=server
```

### Docker Deployment
```bash
# Development environment
docker compose up --build

# Production deployment
docker compose -f docker-compose.prod.yml up -d

# Scale services
docker compose up --scale api=3 --scale worker=5
```

### Android Development
```bash
# Build Android app (from app/ directory)
cd app
./gradlew assembleDebug

# Run Android tests
./gradlew test

# Generate signed APK (requires keystore configuration)
./gradlew assembleRelease
```

## Code Organization

### AI Module (`ai/`)
- `analysis.py`: Message sentiment and intent analysis
- `generator.py`: Reply generation with prompt building and postprocessing
- `conversation_context.py`: Context management and memory persistence
- `multi_model_manager.py`: Abstraction layer for OpenAI/Ollama models
- `adaptive_learning.py`: Machine learning system for conversation improvement
- `summary.py`: Memory summarization for long conversations

### Enterprise Features
- `security/advanced_security.py`: Threat detection and security monitoring
- `licensing/license_manager.py`: Hardware-bound licensing system
- `user_management.py`: Multi-tenant user authentication and permissions
- `analytics/system_monitor.py`: Performance and usage analytics
- `performance/cache_manager.py`: Intelligent caching system
- `integrations/webhook_manager.py`: Platform integration management

### Key Configuration
- **AI Models**: Configure via `OLLAMA_URL`, `OLLAMA_MODEL`, `OPENAI_API_KEY`
- **Platform Keys**: Twilio (`TWILIO_*`), Facebook (`FB_*`), KDE Connect settings
- **Security**: Admin tokens (`ADMIN_TOKEN`), licensing (`LICENSE_ENFORCE`)
- **Performance**: Rate limiting (`RATE_LIMIT_PER_MIN`), caching settings

### Runtime Data
- `synapseflow_data/`: Persistent state directory (users, policies, learning data)
- Not version controlled - contains runtime user data and system state

### Integration Points
- **Webhooks**: Platform-specific endpoints in `server.py` (`/twilio`, `/messenger`)
- **REST API**: Full programmatic access via Flask routes
- **Database**: JSON-based persistence with planned PostgreSQL migration
- **Cache**: Redis integration for performance optimization

### Security Considerations
- All inputs validated through `utils/error_handling.py`
- Secrets managed via environment variables
- Enterprise-grade security monitoring and threat detection
- Hardware-bound licensing for production deployments

## Testing Strategy
- **Unit Tests**: Pure functions in `ai/` modules
- **Integration Tests**: API endpoints and platform integrations
- **Mock External Services**: Offline testing with mocked HTTP calls
- **Security Tests**: Authentication, authorization, and threat detection
- **Performance Tests**: Load testing and caching validation

## Key Dependencies
- **Flask**: Web framework and API layer
- **OpenAI/Anthropic**: AI model APIs
- **Requests/aiohttp**: HTTP client libraries
- **Cryptography**: Security and licensing
- **Redis**: Caching and session management
- **Scikit-learn/NumPy**: Machine learning components