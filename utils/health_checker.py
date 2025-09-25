#!/usr/bin/env python3
"""
Comprehensive Health Check System
Monitors external services and system health with detailed diagnostics.
"""

import os
import time
import asyncio
import requests
import socket
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import json
import logging


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ServiceType(Enum):
    AI_MODEL = "ai_model"
    DATABASE = "database"
    CACHE = "cache"
    EXTERNAL_API = "external_api"
    WEBHOOK = "webhook"
    FILESYSTEM = "filesystem"


@dataclass
class HealthCheck:
    """Individual health check result"""
    service_name: str
    service_type: ServiceType
    status: HealthStatus
    response_time_ms: Optional[float] = None
    last_checked: Optional[str] = None
    error_message: Optional[str] = None
    details: Dict[str, Any] = None
    uptime_percentage: Optional[float] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}
        if self.last_checked is None:
            self.last_checked = datetime.utcnow().isoformat()


class HealthChecker:
    """Comprehensive system health checker"""

    def __init__(self, data_dir: str = "synapseflow_data"):
        self.data_dir = data_dir
        self.health_dir = os.path.join(data_dir, "health")
        os.makedirs(self.health_dir, exist_ok=True)

        self.health_history_file = os.path.join(self.health_dir, "health_history.jsonl")
        self.service_configs = self._load_service_configs()
        self.timeout = 10  # Default timeout for checks

        # Health check results cache
        self.last_results: Dict[str, HealthCheck] = {}

    def _load_service_configs(self) -> Dict[str, Dict[str, Any]]:
        """Load service configurations for health checks"""
        return {
            'ollama': {
                'type': ServiceType.AI_MODEL,
                'url': os.getenv('OLLAMA_URL', 'http://127.0.0.1:11434'),
                'health_endpoint': '/api/tags',
                'timeout': 15,
                'enabled': bool(os.getenv('OLLAMA_URL'))
            },
            'openai': {
                'type': ServiceType.EXTERNAL_API,
                'url': 'https://api.openai.com/v1',
                'health_endpoint': '/models',
                'timeout': 10,
                'enabled': bool(os.getenv('OPENAI_API_KEY')),
                'headers': {'Authorization': f'Bearer {os.getenv("OPENAI_API_KEY", "")}'}
            },
            'redis': {
                'type': ServiceType.CACHE,
                'url': os.getenv('REDIS_URL', 'redis://localhost:6379'),
                'timeout': 5,
                'enabled': bool(os.getenv('REDIS_URL'))
            },
            'twilio': {
                'type': ServiceType.EXTERNAL_API,
                'url': 'https://api.twilio.com/2010-04-01',
                'health_endpoint': '/Accounts.json',
                'timeout': 10,
                'enabled': bool(os.getenv('TWILIO_ACCOUNT_SID')),
                'auth': (os.getenv('TWILIO_ACCOUNT_SID', ''), os.getenv('TWILIO_AUTH_TOKEN', ''))
            },
            'facebook': {
                'type': ServiceType.EXTERNAL_API,
                'url': 'https://graph.facebook.com/v18.0',
                'health_endpoint': '/me',
                'timeout': 10,
                'enabled': bool(os.getenv('FB_PAGE_TOKEN')),
                'params': {'access_token': os.getenv('FB_PAGE_TOKEN', '')}
            }
        }

    async def check_ollama_health(self) -> HealthCheck:
        """Check Ollama service health"""
        config = self.service_configs['ollama']
        start_time = time.time()

        try:
            if not config['enabled']:
                return HealthCheck(
                    service_name='ollama',
                    service_type=ServiceType.AI_MODEL,
                    status=HealthStatus.UNKNOWN,
                    details={'message': 'Service not configured'}
                )

            url = f"{config['url']}{config['health_endpoint']}"
            response = requests.get(url, timeout=config['timeout'])
            response_time = (time.time() - start_time) * 1000

            if response.status_code == 200:
                data = response.json()
                model_count = len(data.get('models', []))

                return HealthCheck(
                    service_name='ollama',
                    service_type=ServiceType.AI_MODEL,
                    status=HealthStatus.HEALTHY,
                    response_time_ms=response_time,
                    details={
                        'available_models': model_count,
                        'configured_model': os.getenv('OLLAMA_MODEL', 'unknown'),
                        'endpoint': url
                    }
                )
            else:
                return HealthCheck(
                    service_name='ollama',
                    service_type=ServiceType.AI_MODEL,
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=response_time,
                    error_message=f"HTTP {response.status_code}: {response.text[:200]}"
                )

        except requests.exceptions.ConnectTimeout:
            return HealthCheck(
                service_name='ollama',
                service_type=ServiceType.AI_MODEL,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                error_message="Connection timeout - service may be down"
            )
        except requests.exceptions.ConnectionError:
            return HealthCheck(
                service_name='ollama',
                service_type=ServiceType.AI_MODEL,
                status=HealthStatus.UNHEALTHY,
                error_message="Connection refused - service not running"
            )
        except Exception as e:
            return HealthCheck(
                service_name='ollama',
                service_type=ServiceType.AI_MODEL,
                status=HealthStatus.UNHEALTHY,
                error_message=f"Unexpected error: {str(e)}"
            )

    async def check_openai_health(self) -> HealthCheck:
        """Check OpenAI API health"""
        config = self.service_configs['openai']
        start_time = time.time()

        try:
            if not config['enabled']:
                return HealthCheck(
                    service_name='openai',
                    service_type=ServiceType.EXTERNAL_API,
                    status=HealthStatus.UNKNOWN,
                    details={'message': 'API key not configured'}
                )

            url = f"{config['url']}{config['health_endpoint']}"
            headers = config.get('headers', {})

            response = requests.get(url, headers=headers, timeout=config['timeout'])
            response_time = (time.time() - start_time) * 1000

            if response.status_code == 200:
                data = response.json()
                model_count = len(data.get('data', []))

                return HealthCheck(
                    service_name='openai',
                    service_type=ServiceType.EXTERNAL_API,
                    status=HealthStatus.HEALTHY,
                    response_time_ms=response_time,
                    details={
                        'available_models': model_count,
                        'configured_model': os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo'),
                        'api_version': 'v1'
                    }
                )
            elif response.status_code == 401:
                return HealthCheck(
                    service_name='openai',
                    service_type=ServiceType.EXTERNAL_API,
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=response_time,
                    error_message="Authentication failed - check API key"
                )
            else:
                return HealthCheck(
                    service_name='openai',
                    service_type=ServiceType.EXTERNAL_API,
                    status=HealthStatus.DEGRADED,
                    response_time_ms=response_time,
                    error_message=f"HTTP {response.status_code}: {response.text[:200]}"
                )

        except Exception as e:
            return HealthCheck(
                service_name='openai',
                service_type=ServiceType.EXTERNAL_API,
                status=HealthStatus.UNHEALTHY,
                error_message=f"Error: {str(e)}"
            )

    async def check_redis_health(self) -> HealthCheck:
        """Check Redis cache health"""
        config = self.service_configs['redis']
        start_time = time.time()

        try:
            if not config['enabled']:
                return HealthCheck(
                    service_name='redis',
                    service_type=ServiceType.CACHE,
                    status=HealthStatus.UNKNOWN,
                    details={'message': 'Redis URL not configured'}
                )

            # Try Redis import
            try:
                import redis
            except ImportError:
                return HealthCheck(
                    service_name='redis',
                    service_type=ServiceType.CACHE,
                    status=HealthStatus.UNHEALTHY,
                    error_message="Redis Python library not installed"
                )

            # Parse Redis URL
            redis_url = config['url']
            r = redis.from_url(redis_url, socket_timeout=config['timeout'])

            # Test connection
            info = r.info()
            response_time = (time.time() - start_time) * 1000

            return HealthCheck(
                service_name='redis',
                service_type=ServiceType.CACHE,
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time,
                details={
                    'version': info.get('redis_version'),
                    'connected_clients': info.get('connected_clients'),
                    'used_memory_human': info.get('used_memory_human'),
                    'uptime_in_seconds': info.get('uptime_in_seconds')
                }
            )

        except Exception as e:
            return HealthCheck(
                service_name='redis',
                service_type=ServiceType.CACHE,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                error_message=f"Redis connection failed: {str(e)}"
            )

    async def check_filesystem_health(self) -> HealthCheck:
        """Check filesystem health"""
        start_time = time.time()

        try:
            # Check data directory accessibility
            if not os.path.exists(self.data_dir):
                return HealthCheck(
                    service_name='filesystem',
                    service_type=ServiceType.FILESYSTEM,
                    status=HealthStatus.UNHEALTHY,
                    error_message=f"Data directory does not exist: {self.data_dir}"
                )

            # Check write permissions
            test_file = os.path.join(self.data_dir, '.health_check')
            try:
                with open(test_file, 'w') as f:
                    f.write('health_check')
                os.remove(test_file)
            except (OSError, IOError) as e:
                return HealthCheck(
                    service_name='filesystem',
                    service_type=ServiceType.FILESYSTEM,
                    status=HealthStatus.UNHEALTHY,
                    error_message=f"Write permission denied: {str(e)}"
                )

            # Check disk space
            import shutil
            _, _, free_bytes = shutil.disk_usage(self.data_dir)
            free_mb = free_bytes // (1024 * 1024)

            status = HealthStatus.HEALTHY
            if free_mb < 100:  # Less than 100MB
                status = HealthStatus.UNHEALTHY
            elif free_mb < 1000:  # Less than 1GB
                status = HealthStatus.DEGRADED

            response_time = (time.time() - start_time) * 1000

            return HealthCheck(
                service_name='filesystem',
                service_type=ServiceType.FILESYSTEM,
                status=status,
                response_time_ms=response_time,
                details={
                    'data_directory': self.data_dir,
                    'free_space_mb': free_mb,
                    'writable': True
                }
            )

        except Exception as e:
            return HealthCheck(
                service_name='filesystem',
                service_type=ServiceType.FILESYSTEM,
                status=HealthStatus.UNHEALTHY,
                error_message=f"Filesystem check failed: {str(e)}"
            )

    async def check_twilio_health(self) -> HealthCheck:
        """Check Twilio API health"""
        config = self.service_configs['twilio']
        start_time = time.time()

        try:
            if not config['enabled']:
                return HealthCheck(
                    service_name='twilio',
                    service_type=ServiceType.EXTERNAL_API,
                    status=HealthStatus.UNKNOWN,
                    details={'message': 'Twilio credentials not configured'}
                )

            url = f"{config['url']}{config['health_endpoint']}"
            auth = config.get('auth')

            response = requests.get(url, auth=auth, timeout=config['timeout'])
            response_time = (time.time() - start_time) * 1000

            if response.status_code == 200:
                return HealthCheck(
                    service_name='twilio',
                    service_type=ServiceType.EXTERNAL_API,
                    status=HealthStatus.HEALTHY,
                    response_time_ms=response_time,
                    details={
                        'account_sid': os.getenv('TWILIO_ACCOUNT_SID', '')[:10] + '...',
                        'from_number': os.getenv('TWILIO_FROM', 'Not configured')
                    }
                )
            elif response.status_code == 401:
                return HealthCheck(
                    service_name='twilio',
                    service_type=ServiceType.EXTERNAL_API,
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=response_time,
                    error_message="Authentication failed - check credentials"
                )
            else:
                return HealthCheck(
                    service_name='twilio',
                    service_type=ServiceType.EXTERNAL_API,
                    status=HealthStatus.DEGRADED,
                    response_time_ms=response_time,
                    error_message=f"HTTP {response.status_code}"
                )

        except Exception as e:
            return HealthCheck(
                service_name='twilio',
                service_type=ServiceType.EXTERNAL_API,
                status=HealthStatus.UNHEALTHY,
                error_message=f"Error: {str(e)}"
            )

    async def check_all_services(self) -> Dict[str, HealthCheck]:
        """Check health of all configured services"""
        health_checks = {}

        # Run health checks concurrently
        tasks = [
            ('ollama', self.check_ollama_health()),
            ('openai', self.check_openai_health()),
            ('redis', self.check_redis_health()),
            ('filesystem', self.check_filesystem_health()),
            ('twilio', self.check_twilio_health()),
        ]

        results = await asyncio.gather(*[task[1] for task in tasks], return_exceptions=True)

        for i, (service_name, _) in enumerate(tasks):
            result = results[i]
            if isinstance(result, Exception):
                health_checks[service_name] = HealthCheck(
                    service_name=service_name,
                    service_type=ServiceType.EXTERNAL_API,
                    status=HealthStatus.UNHEALTHY,
                    error_message=f"Health check failed: {str(result)}"
                )
            else:
                health_checks[service_name] = result

        # Cache results
        self.last_results = health_checks

        # Save to history
        self._save_health_history(health_checks)

        return health_checks

    def _save_health_history(self, health_checks: Dict[str, HealthCheck]) -> None:
        """Save health check results to history"""
        try:
            timestamp = datetime.utcnow().isoformat()
            history_entry = {
                'timestamp': timestamp,
                'checks': {name: asdict(check) for name, check in health_checks.items()}
            }

            with open(self.health_history_file, 'a') as f:
                f.write(json.dumps(history_entry) + '\n')

        except Exception as e:
            logging.error(f"Failed to save health history: {e}")

    def get_overall_status(self, health_checks: Dict[str, HealthCheck]) -> HealthStatus:
        """Determine overall system health status"""
        if not health_checks:
            return HealthStatus.UNKNOWN

        statuses = [check.status for check in health_checks.values()]

        # If any critical service is unhealthy, system is unhealthy
        critical_services = ['filesystem']  # Services critical for basic operation
        for service_name in critical_services:
            if service_name in health_checks:
                if health_checks[service_name].status == HealthStatus.UNHEALTHY:
                    return HealthStatus.UNHEALTHY

        # Count status types
        unhealthy_count = statuses.count(HealthStatus.UNHEALTHY)
        degraded_count = statuses.count(HealthStatus.DEGRADED)
        healthy_count = statuses.count(HealthStatus.HEALTHY)

        # Determine overall status
        if unhealthy_count > 0:
            return HealthStatus.UNHEALTHY
        elif degraded_count > 0:
            return HealthStatus.DEGRADED
        elif healthy_count > 0:
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN

    def get_health_summary(self) -> Dict[str, Any]:
        """Get a summary of system health"""
        if not self.last_results:
            return {
                'overall_status': HealthStatus.UNKNOWN.value,
                'message': 'No health checks performed yet',
                'services': {}
            }

        overall_status = self.get_overall_status(self.last_results)

        services_summary = {}
        for name, check in self.last_results.items():
            services_summary[name] = {
                'status': check.status.value,
                'response_time_ms': check.response_time_ms,
                'last_checked': check.last_checked,
                'error': check.error_message,
                'enabled': self.service_configs.get(name, {}).get('enabled', True)
            }

        return {
            'overall_status': overall_status.value,
            'last_check': max(check.last_checked for check in self.last_results.values()),
            'services': services_summary,
            'summary': {
                'total_services': len(self.last_results),
                'healthy': sum(1 for c in self.last_results.values() if c.status == HealthStatus.HEALTHY),
                'degraded': sum(1 for c in self.last_results.values() if c.status == HealthStatus.DEGRADED),
                'unhealthy': sum(1 for c in self.last_results.values() if c.status == HealthStatus.UNHEALTHY),
                'unknown': sum(1 for c in self.last_results.values() if c.status == HealthStatus.UNKNOWN)
            }
        }


# Global health checker instance
_health_checker = None

def get_health_checker() -> HealthChecker:
    """Get the global health checker instance"""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker


async def perform_health_check() -> Dict[str, Any]:
    """Perform a complete system health check"""
    health_checker = get_health_checker()
    health_checks = await health_checker.check_all_services()
    return health_checker.get_health_summary()


async def get_system_health() -> Dict[str, Any]:
    """
    Get comprehensive system health status.
    Convenience function for external use.
    """
    return await perform_health_check()


if __name__ == "__main__":
    # Command line health check
    import asyncio

    async def main():
        print("🏥 Running system health check...")
        summary = await perform_health_check()

        print(f"\n📊 Overall Status: {summary['overall_status'].upper()}")
        print(f"🕒 Last Check: {summary['last_check']}")

        print("\n📋 Service Status:")
        for service, info in summary['services'].items():
            status_icon = {
                'healthy': '✅',
                'degraded': '⚠️',
                'unhealthy': '❌',
                'unknown': '❓'
            }.get(info['status'], '❓')

            print(f"  {status_icon} {service}: {info['status']}")
            if info['response_time_ms']:
                print(f"    Response time: {info['response_time_ms']:.1f}ms")
            if info['error']:
                print(f"    Error: {info['error']}")

    asyncio.run(main())