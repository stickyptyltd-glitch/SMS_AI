#!/usr/bin/env python3
"""
Prometheus Metrics Collection
Provides comprehensive metrics collection for SynapseFlow AI system.
"""

import time
import psutil
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from collections import defaultdict, Counter

try:
    from prometheus_client import (
        Counter as PrometheusCounter,
        Histogram,
        Gauge,
        CollectorRegistry,
        generate_latest,
        CONTENT_TYPE_LATEST
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Create mock classes for when prometheus is not available
    class PrometheusCounter:
        def __init__(self, *args, **kwargs):
            self._value = 0
        def inc(self, amount=1):
            self._value += amount
        def labels(self, **kwargs):
            return self

    class Histogram:
        def __init__(self, *args, **kwargs):
            self._observations = []
        def observe(self, amount):
            self._observations.append(amount)
        def labels(self, **kwargs):
            return self

    class Gauge:
        def __init__(self, *args, **kwargs):
            self._value = 0
        def set(self, value):
            self._value = value
        def labels(self, **kwargs):
            return self

    CollectorRegistry = None
    generate_latest = lambda x: b"# Prometheus client not available\n"
    CONTENT_TYPE_LATEST = "text/plain"


class MetricsCollector:
    """Centralized metrics collection for the SynapseFlow AI system"""

    def __init__(self):
        """Initialize metrics collector"""
        self.registry = CollectorRegistry() if PROMETHEUS_AVAILABLE else None
        self._lock = threading.RLock()
        self._last_system_check = 0
        self._system_check_interval = 30  # seconds

        # Initialize Prometheus metrics
        self._init_prometheus_metrics()

        # Internal metrics storage
        self._internal_metrics = {
            'requests': defaultdict(int),
            'response_times': defaultdict(list),
            'errors': defaultdict(int),
            'ai_usage': defaultdict(int),
            'webhook_events': defaultdict(int),
            'system_metrics': {}
        }

    def _init_prometheus_metrics(self):
        """Initialize Prometheus metrics"""
        if not PROMETHEUS_AVAILABLE:
            return

        # Request metrics
        self.request_count = PrometheusCounter(
            'synapseflow_requests_total',
            'Total number of requests',
            ['method', 'endpoint', 'status_code'],
            registry=self.registry
        )

        self.request_duration = Histogram(
            'synapseflow_request_duration_seconds',
            'Request duration in seconds',
            ['method', 'endpoint'],
            registry=self.registry
        )

        # AI model metrics
        self.ai_requests = PrometheusCounter(
            'synapseflow_ai_requests_total',
            'Total AI model requests',
            ['provider', 'model', 'status'],
            registry=self.registry
        )

        self.ai_token_usage = PrometheusCounter(
            'synapseflow_ai_tokens_total',
            'Total AI tokens used',
            ['provider', 'model', 'type'],
            registry=self.registry
        )

        self.ai_response_time = Histogram(
            'synapseflow_ai_response_time_seconds',
            'AI model response time',
            ['provider', 'model'],
            registry=self.registry
        )

        # Webhook metrics
        self.webhook_deliveries = PrometheusCounter(
            'synapseflow_webhook_deliveries_total',
            'Total webhook deliveries',
            ['platform', 'status'],
            registry=self.registry
        )

        self.webhook_response_time = Histogram(
            'synapseflow_webhook_response_time_seconds',
            'Webhook delivery response time',
            ['platform'],
            registry=self.registry
        )

        # System metrics
        self.system_cpu_usage = Gauge(
            'synapseflow_system_cpu_usage_percent',
            'System CPU usage percentage',
            registry=self.registry
        )

        self.system_memory_usage = Gauge(
            'synapseflow_system_memory_usage_bytes',
            'System memory usage in bytes',
            registry=self.registry
        )

        self.system_disk_usage = Gauge(
            'synapseflow_system_disk_usage_percent',
            'System disk usage percentage',
            registry=self.registry
        )

        # Security metrics
        self.security_events = PrometheusCounter(
            'synapseflow_security_events_total',
            'Total security events',
            ['event_type', 'severity'],
            registry=self.registry
        )

        self.rate_limit_hits = PrometheusCounter(
            'synapseflow_rate_limit_hits_total',
            'Total rate limit hits',
            ['client_type'],
            registry=self.registry
        )

        # Health metrics
        self.service_health = Gauge(
            'synapseflow_service_health',
            'Service health status (1=healthy, 0=unhealthy)',
            ['service'],
            registry=self.registry
        )

    def record_request(self, method: str, endpoint: str, status_code: int,
                      response_time: float, user_id: Optional[str] = None):
        """Record HTTP request metrics"""
        with self._lock:
            # Prometheus metrics
            if PROMETHEUS_AVAILABLE:
                self.request_count.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code=str(status_code)
                ).inc()

                self.request_duration.labels(
                    method=method,
                    endpoint=endpoint
                ).observe(response_time)

            # Internal metrics
            key = f"{method}:{endpoint}"
            self._internal_metrics['requests'][key] += 1
            self._internal_metrics['response_times'][key].append(response_time)

            if status_code >= 400:
                self._internal_metrics['errors'][f"{key}:{status_code}"] += 1

    def record_ai_usage(self, provider: str, model: str, success: bool,
                       response_time: float, prompt_tokens: int = 0,
                       completion_tokens: int = 0):
        """Record AI model usage metrics"""
        with self._lock:
            status = 'success' if success else 'error'

            # Prometheus metrics
            if PROMETHEUS_AVAILABLE:
                self.ai_requests.labels(
                    provider=provider,
                    model=model,
                    status=status
                ).inc()

                if prompt_tokens > 0:
                    self.ai_token_usage.labels(
                        provider=provider,
                        model=model,
                        type='prompt'
                    ).inc(prompt_tokens)

                if completion_tokens > 0:
                    self.ai_token_usage.labels(
                        provider=provider,
                        model=model,
                        type='completion'
                    ).inc(completion_tokens)

                self.ai_response_time.labels(
                    provider=provider,
                    model=model
                ).observe(response_time)

            # Internal metrics
            key = f"{provider}:{model}:{status}"
            self._internal_metrics['ai_usage'][key] += 1

    def record_webhook_delivery(self, platform: str, success: bool,
                              response_time: Optional[float] = None):
        """Record webhook delivery metrics"""
        with self._lock:
            status = 'success' if success else 'error'

            # Prometheus metrics
            if PROMETHEUS_AVAILABLE:
                self.webhook_deliveries.labels(
                    platform=platform,
                    status=status
                ).inc()

                if response_time is not None:
                    self.webhook_response_time.labels(
                        platform=platform
                    ).observe(response_time)

            # Internal metrics
            key = f"{platform}:{status}"
            self._internal_metrics['webhook_events'][key] += 1

    def record_security_event(self, event_type: str, severity: str):
        """Record security event metrics"""
        with self._lock:
            # Prometheus metrics
            if PROMETHEUS_AVAILABLE:
                self.security_events.labels(
                    event_type=event_type,
                    severity=severity
                ).inc()

    def record_rate_limit_hit(self, client_type: str = 'general'):
        """Record rate limit hit"""
        with self._lock:
            # Prometheus metrics
            if PROMETHEUS_AVAILABLE:
                self.rate_limit_hits.labels(
                    client_type=client_type
                ).inc()

    def update_system_metrics(self):
        """Update system resource metrics"""
        current_time = time.time()

        # Only update if enough time has passed
        if current_time - self._last_system_check < self._system_check_interval:
            return

        try:
            with self._lock:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)

                # Memory usage
                memory = psutil.virtual_memory()
                memory_bytes = memory.used

                # Disk usage
                disk = psutil.disk_usage('/')
                disk_percent = disk.percent

                # Update Prometheus metrics
                if PROMETHEUS_AVAILABLE:
                    self.system_cpu_usage.set(cpu_percent)
                    self.system_memory_usage.set(memory_bytes)
                    self.system_disk_usage.set(disk_percent)

                # Update internal metrics
                self._internal_metrics['system_metrics'] = {
                    'cpu_percent': cpu_percent,
                    'memory_bytes': memory_bytes,
                    'memory_percent': memory.percent,
                    'disk_percent': disk_percent,
                    'disk_free_bytes': disk.free,
                    'timestamp': current_time
                }

                self._last_system_check = current_time

        except Exception as e:
            print(f"Error updating system metrics: {e}")

    def update_service_health(self, service: str, healthy: bool):
        """Update service health status"""
        with self._lock:
            if PROMETHEUS_AVAILABLE:
                self.service_health.labels(service=service).set(1 if healthy else 0)

    def get_prometheus_metrics(self) -> str:
        """Get Prometheus-formatted metrics"""
        if not PROMETHEUS_AVAILABLE or not self.registry:
            return "# Prometheus client not available\n"

        # Update system metrics before generating output
        self.update_system_metrics()

        return generate_latest(self.registry).decode('utf-8')

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics"""
        with self._lock:
            # Update system metrics
            self.update_system_metrics()

            summary = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'prometheus_available': PROMETHEUS_AVAILABLE,
                'system': self._internal_metrics['system_metrics'].copy(),
                'requests': dict(self._internal_metrics['requests']),
                'errors': dict(self._internal_metrics['errors']),
                'ai_usage': dict(self._internal_metrics['ai_usage']),
                'webhook_events': dict(self._internal_metrics['webhook_events'])
            }

            # Calculate response time statistics
            response_time_stats = {}
            for endpoint, times in self._internal_metrics['response_times'].items():
                if times:
                    response_time_stats[endpoint] = {
                        'count': len(times),
                        'avg': sum(times) / len(times),
                        'min': min(times),
                        'max': max(times)
                    }

            summary['response_time_stats'] = response_time_stats

            return summary

    def reset_metrics(self):
        """Reset all internal metrics (not Prometheus metrics)"""
        with self._lock:
            self._internal_metrics = {
                'requests': defaultdict(int),
                'response_times': defaultdict(list),
                'errors': defaultdict(int),
                'ai_usage': defaultdict(int),
                'webhook_events': defaultdict(int),
                'system_metrics': {}
            }

    def get_health_score(self) -> float:
        """Calculate overall health score (0.0 to 1.0)"""
        try:
            with self._lock:
                # Update system metrics
                self.update_system_metrics()

                score = 1.0
                system_metrics = self._internal_metrics.get('system_metrics', {})

                # Penalize high resource usage
                cpu_percent = system_metrics.get('cpu_percent', 0)
                if cpu_percent > 80:
                    score -= 0.3
                elif cpu_percent > 60:
                    score -= 0.1

                memory_percent = system_metrics.get('memory_percent', 0)
                if memory_percent > 90:
                    score -= 0.3
                elif memory_percent > 80:
                    score -= 0.1

                disk_percent = system_metrics.get('disk_percent', 0)
                if disk_percent > 95:
                    score -= 0.3
                elif disk_percent > 85:
                    score -= 0.1

                # Penalize high error rates
                total_requests = sum(self._internal_metrics['requests'].values())
                total_errors = sum(self._internal_metrics['errors'].values())

                if total_requests > 0:
                    error_rate = total_errors / total_requests
                    if error_rate > 0.1:  # >10% error rate
                        score -= 0.4
                    elif error_rate > 0.05:  # >5% error rate
                        score -= 0.2

                return max(0.0, score)

        except Exception:
            return 0.5  # Neutral score if we can't calculate


# Global metrics instance
metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance"""
    return metrics_collector