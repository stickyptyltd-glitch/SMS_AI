#!/usr/bin/env python3
"""
Docker Deployment Script
Automates Docker-based deployment for SynapseFlow AI system.
"""

import os
import sys
import subprocess
import json
import tempfile
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def print_header(title):
    """Print section header"""
    print(f"\n{'='*60}")
    print(f"🐳 {title}")
    print(f"{'='*60}")


def print_step(step, description):
    """Print deployment step"""
    print(f"\n{step}. {description}")
    print("-" * 40)


def run_command(cmd, description="", check=True, capture_output=True):
    """Run a command with proper error handling"""
    print(f"  ▶️  {description or cmd}")

    try:
        if capture_output:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                check=check
            )

            if result.returncode == 0:
                print(f"  ✅ Success")
                if result.stdout.strip():
                    # Only print first few lines to avoid clutter
                    lines = result.stdout.strip().split('\n')
                    for line in lines[:3]:
                        print(f"  📝 {line}")
                    if len(lines) > 3:
                        print(f"  📝 ... ({len(lines) - 3} more lines)")
            else:
                print(f"  ❌ Failed (exit code: {result.returncode})")
                if result.stderr.strip():
                    print(f"  🚨 {result.stderr.strip()}")

            return result.returncode == 0, result.stdout, result.stderr
        else:
            result = subprocess.run(cmd, shell=True, check=check)
            return result.returncode == 0, "", ""

    except subprocess.CalledProcessError as e:
        print(f"  ❌ Command failed: {e}")
        return False, "", str(e)


def check_docker_prerequisites():
    """Check Docker prerequisites"""
    print_step("1", "Checking Docker Prerequisites")

    # Check Docker
    success, stdout, stderr = run_command("docker --version", "Checking Docker installation")
    if not success:
        print("  ❌ Docker is not installed or not in PATH")
        print("  📝 Install Docker: https://docs.docker.com/get-docker/")
        return False

    # Check Docker Compose
    success, stdout, stderr = run_command("docker-compose --version", "Checking Docker Compose")
    if not success:
        print("  ⚠️  docker-compose not found, trying docker compose...")
        success, stdout, stderr = run_command("docker compose version", "Checking Docker Compose (new syntax)")
        if not success:
            print("  ❌ Docker Compose is not available")
            print("  📝 Install Docker Compose: https://docs.docker.com/compose/install/")
            return False

    # Check Docker daemon
    success, stdout, stderr = run_command("docker info", "Checking Docker daemon")
    if not success:
        print("  ❌ Docker daemon is not running")
        print("  📝 Start Docker daemon and try again")
        return False

    print("  ✅ Docker environment ready")
    return True


def create_dockerfile():
    """Create optimized Dockerfile"""
    print_step("2", "Creating Dockerfile")

    dockerfile_content = '''# SynapseFlow AI Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    g++ \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements-server.txt .
RUN pip install --no-cache-dir -r requirements-server.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash synapseflow && \\
    chown -R synapseflow:synapseflow /app
USER synapseflow

# Create data directory
RUN mkdir -p /app/synapseflow_data

# Expose port
EXPOSE 8081

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8081/health || exit 1

# Default command
CMD ["python", "server.py"]
'''

    with open("Dockerfile", "w") as f:
        f.write(dockerfile_content)

    print("  ✅ Dockerfile created")
    return True


def create_docker_compose():
    """Create Docker Compose configuration"""
    print_step("3", "Creating Docker Compose Configuration")

    compose_content = '''version: '3.8'

services:
  synapseflow-ai:
    build: .
    container_name: synapseflow-ai
    ports:
      - "8081:8081"
      - "5050:5050"  # Admin interface
    environment:
      - ENVIRONMENT=production
      - SERVER_HOST=0.0.0.0
      - SERVER_PORT=8081
      - ADMIN_HOST=0.0.0.0
      - ADMIN_PORT=5050
      - DATA_DIR=/app/synapseflow_data
    volumes:
      - ./synapseflow_data:/app/synapseflow_data
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8081/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  redis:
    image: redis:7-alpine
    container_name: synapseflow-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  prometheus:
    image: prom/prometheus:latest
    container_name: synapseflow-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./docker/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=200h'
      - '--web.enable-lifecycle'
    restart: unless-stopped

volumes:
  redis_data:
  prometheus_data:

networks:
  default:
    name: synapseflow-network
'''

    with open("docker-compose.yml", "w") as f:
        f.write(compose_content)

    print("  ✅ Docker Compose configuration created")
    return True


def create_docker_configs():
    """Create Docker configuration files"""
    print_step("4", "Creating Docker Configuration Files")

    # Create docker directory
    docker_dir = Path("docker")
    docker_dir.mkdir(exist_ok=True)

    # Prometheus configuration
    prometheus_config = '''global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  # - "first_rules.yml"
  # - "second_rules.yml"

scrape_configs:
  - job_name: 'synapseflow-ai'
    static_configs:
      - targets: ['synapseflow-ai:9090']
    scrape_interval: 30s
    metrics_path: /metrics

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
'''

    with open(docker_dir / "prometheus.yml", "w") as f:
        f.write(prometheus_config)

    # Docker ignore file
    dockerignore_content = '''# Version control
.git
.gitignore

# Python cache
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.venv/
venv/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Logs
*.log
logs/

# Data directories (will be mounted)
synapseflow_data/

# Environment files
.env
.env.local
.env.production

# Testing
.pytest_cache/
.coverage
htmlcov/

# Documentation
docs/_build/

# OS
.DS_Store
Thumbs.db

# Temporary files
*.tmp
*.bak
'''

    with open(".dockerignore", "w") as f:
        f.write(dockerignore_content)

    print("  ✅ Docker configuration files created")
    return True


def create_production_env():
    """Create production environment template"""
    print_step("5", "Creating Production Environment Template")

    if os.path.exists(".env.production"):
        print("  ℹ️  .env.production already exists")
        return True

    # Copy from .env.example if it exists
    if os.path.exists(".env.example"):
        with open(".env.example", "r") as f:
            env_content = f.read()

        # Modify for production
        env_content = env_content.replace("ENVIRONMENT=development", "ENVIRONMENT=production")
        env_content = env_content.replace("DEBUG=1", "DEBUG=0")
        env_content = env_content.replace("ADMIN_DEBUG=1", "ADMIN_DEBUG=0")
        env_content = env_content.replace("CONFIG_VALIDATION_STRICT=0", "CONFIG_VALIDATION_STRICT=1")

        with open(".env.production", "w") as f:
            f.write(env_content)

        print("  ✅ .env.production created from .env.example")
        print("  ⚠️  Please review and update .env.production with production values")
    else:
        print("  ❌ .env.example not found, cannot create .env.production")
        return False

    return True


def build_docker_image():
    """Build Docker image"""
    print_step("6", "Building Docker Image")

    success, stdout, stderr = run_command(
        "docker build -t synapseflow-ai:latest .",
        "Building Docker image",
        capture_output=True
    )

    if not success:
        print("  ❌ Docker build failed")
        return False

    print("  ✅ Docker image built successfully")
    return True


def initialize_data_directories():
    """Initialize data directories for Docker volumes"""
    print_step("7", "Initializing Data Directories")

    # Create directories that will be mounted as volumes
    directories = ["synapseflow_data", "logs"]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"  ✅ Created {directory}/")

    # Initialize database if needed
    if not os.path.exists("synapseflow_data/webhooks"):
        success, stdout, stderr = run_command(
            "python scripts/init_database.py synapseflow_data",
            "Initializing databases",
            capture_output=True
        )

        if success:
            print("  ✅ Databases initialized")
        else:
            print("  ⚠️  Database initialization encountered issues")

    return True


def start_docker_services():
    """Start Docker services"""
    print_step("8", "Starting Docker Services")

    # Check for docker-compose vs docker compose
    compose_cmd = "docker-compose"
    success, _, _ = run_command("docker-compose --version", check=False)
    if not success:
        compose_cmd = "docker compose"

    # Start services
    success, stdout, stderr = run_command(
        f"{compose_cmd} up -d",
        "Starting Docker services",
        capture_output=True
    )

    if not success:
        print("  ❌ Failed to start Docker services")
        return False

    print("  ✅ Docker services started")

    # Wait for services to be healthy
    print("  ⏳ Waiting for services to be healthy...")

    success, stdout, stderr = run_command(
        f"{compose_cmd} ps",
        "Checking service status",
        capture_output=True
    )

    if success:
        print("  📋 Service status:")
        for line in stdout.strip().split('\n')[1:]:  # Skip header
            if line.strip():
                print(f"    {line}")

    return True


def run_health_checks():
    """Run health checks on deployed services"""
    print_step("9", "Running Health Checks")

    import time
    import requests

    # Wait a bit for services to fully start
    print("  ⏳ Waiting for services to initialize...")
    time.sleep(10)

    # Check main application
    try:
        response = requests.get("http://localhost:8081/health", timeout=10)
        if response.status_code == 200:
            print("  ✅ Main application is healthy")
        else:
            print(f"  ⚠️  Main application returned status {response.status_code}")
    except requests.RequestException as e:
        print(f"  ❌ Main application health check failed: {e}")

    # Check Redis
    success, stdout, stderr = run_command(
        "docker exec synapseflow-redis redis-cli ping",
        "Checking Redis health",
        capture_output=True,
        check=False
    )

    if success and "PONG" in stdout:
        print("  ✅ Redis is healthy")
    else:
        print("  ⚠️  Redis health check failed")

    return True


def print_deployment_summary():
    """Print deployment summary"""
    print_header("Docker Deployment Complete!")

    print("🎉 SynapseFlow AI has been deployed with Docker!")

    print("\n🌐 Service URLs:")
    print("  • Main Application: http://localhost:8081")
    print("  • Admin Interface: http://localhost:5050")
    print("  • Prometheus Metrics: http://localhost:9090")
    print("  • Redis: localhost:6379")

    print("\n🔧 Docker Commands:")
    print("  • View logs: docker-compose logs -f synapseflow-ai")
    print("  • Stop services: docker-compose down")
    print("  • Restart services: docker-compose restart")
    print("  • Update and rebuild: docker-compose up -d --build")

    print("\n📊 Monitoring:")
    print("  • Health check: curl http://localhost:8081/health")
    print("  • Service status: docker-compose ps")
    print("  • Container stats: docker stats")

    print("\n📁 Data Persistence:")
    print("  • Application data: ./synapseflow_data")
    print("  • Logs: ./logs")
    print("  • Redis data: Docker volume")
    print("  • Prometheus data: Docker volume")

    print("\n🔒 Security Notes:")
    print("  • Review and update .env.production with secure values")
    print("  • Consider using Docker secrets for sensitive data")
    print("  • Ensure firewall rules are properly configured")
    print("  • Regularly update Docker images for security patches")


def main():
    """Main Docker deployment function"""
    print_header("SynapseFlow AI Docker Deployment")

    print("This script will set up SynapseFlow AI using Docker containers.")
    print("The deployment includes:")
    print("  • Main application container")
    print("  • Redis for caching")
    print("  • Prometheus for monitoring")
    print("  • Persistent data volumes")
    print("  • Health checks and auto-restart")

    # Confirm with user
    response = input("\n❓ Continue with Docker deployment? (y/N): ").lower()
    if response not in ['y', 'yes']:
        print("❌ Deployment cancelled by user")
        sys.exit(0)

    # Change to project directory
    project_dir = Path(__file__).parent.parent
    os.chdir(project_dir)
    print(f"📁 Working directory: {project_dir}")

    # Deployment steps
    deployment_steps = [
        ("Docker Prerequisites", check_docker_prerequisites),
        ("Dockerfile", create_dockerfile),
        ("Docker Compose", create_docker_compose),
        ("Docker Configs", create_docker_configs),
        ("Production Environment", create_production_env),
        ("Build Image", build_docker_image),
        ("Data Directories", initialize_data_directories),
        ("Start Services", start_docker_services),
        ("Health Checks", run_health_checks),
    ]

    failed_steps = []

    for step_name, step_func in deployment_steps:
        try:
            success = step_func()

            if not success:
                failed_steps.append(step_name)
                if step_name in ["Docker Prerequisites", "Build Image"]:
                    print(f"\n❌ Critical step '{step_name}' failed. Cannot continue.")
                    sys.exit(1)
                else:
                    print(f"\n⚠️  Step '{step_name}' failed but deployment can continue.")

        except KeyboardInterrupt:
            print(f"\n\n⚠️  Deployment interrupted during '{step_name}'")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ Unexpected error during '{step_name}': {e}")
            failed_steps.append(step_name)

    # Print summary
    print_deployment_summary()

    if failed_steps:
        print(f"\n⚠️  Some steps failed: {', '.join(failed_steps)}")
        print("Check the logs above for details.")

    print(f"\n✅ Docker deployment completed at {datetime.now()}")


if __name__ == "__main__":
    main()