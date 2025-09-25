#!/usr/bin/env python3
"""
Monitoring Dashboard
Provides web-based monitoring dashboard for SynapseFlow AI system.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List
from flask import Blueprint, render_template_string, jsonify, request

from .prometheus_metrics import get_metrics_collector


# Create Flask blueprint for monitoring
monitoring_bp = Blueprint('monitoring', __name__)


def format_bytes(bytes_value: int) -> str:
    """Format bytes into human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f} PB"


def format_duration(seconds: float) -> str:
    """Format duration in human readable format"""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds / 60:.1f}m"
    else:
        return f"{seconds / 3600:.1f}h"


@monitoring_bp.route('/dashboard')
def dashboard():
    """Main monitoring dashboard"""
    dashboard_html = '''
<!DOCTYPE html>
<html>
<head>
    <title>SynapseFlow AI - Monitoring Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f5f5;
            color: #333;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 1rem 2rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header h1 { font-size: 2rem; margin-bottom: 0.5rem; }
        .header .subtitle { opacity: 0.8; font-size: 1rem; }
        .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; }
        .card {
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border-left: 4px solid #667eea;
        }
        .card h3 {
            color: #667eea;
            margin-bottom: 1rem;
            font-size: 1.2rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .metric {
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.5rem;
            padding: 0.5rem 0;
            border-bottom: 1px solid #f0f0f0;
        }
        .metric:last-child { border-bottom: none; }
        .metric-label { font-weight: 500; }
        .metric-value {
            font-family: 'Courier New', monospace;
            font-weight: bold;
        }
        .health-good { color: #28a745; }
        .health-warning { color: #ffc107; }
        .health-danger { color: #dc3545; }
        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 0.5rem;
        }
        .status-healthy { background: #28a745; }
        .status-warning { background: #ffc107; }
        .status-error { background: #dc3545; }
        .refresh-btn {
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 50px;
            padding: 1rem 2rem;
            cursor: pointer;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            font-size: 1rem;
            transition: transform 0.2s;
        }
        .refresh-btn:hover { transform: translateY(-2px); }
        .auto-refresh {
            position: fixed;
            top: 1rem;
            right: 1rem;
            background: rgba(255,255,255,0.9);
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 0.9rem;
        }
        .chart-container {
            height: 200px;
            margin-top: 1rem;
            display: flex;
            align-items: end;
            justify-content: space-around;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            padding: 1rem;
            background: #fafafa;
        }
        .chart-bar {
            background: #667eea;
            border-radius: 2px;
            min-height: 2px;
            width: 20px;
            opacity: 0.8;
        }
        .error {
            background: #f8d7da;
            color: #721c24;
            padding: 1rem;
            border-radius: 4px;
            margin-bottom: 1rem;
        }
        @media (max-width: 768px) {
            .container { padding: 1rem; }
            .grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 SynapseFlow AI Dashboard</h1>
        <div class="subtitle">System Monitoring & Health Overview</div>
    </div>

    <div class="auto-refresh">
        <span id="refresh-indicator">🔄</span>
        Auto-refresh: <span id="countdown">30</span>s
    </div>

    <div class="container">
        <div id="content">
            <div class="error">📡 Loading monitoring data...</div>
        </div>
    </div>

    <button class="refresh-btn" onclick="loadDashboard()">🔄 Refresh Now</button>

    <script>
        let refreshInterval;
        let countdown = 30;

        function updateCountdown() {
            document.getElementById('countdown').textContent = countdown;
            countdown--;

            if (countdown < 0) {
                countdown = 30;
                loadDashboard();
            }
        }

        function loadDashboard() {
            document.getElementById('refresh-indicator').textContent = '🔄';

            fetch('/monitoring/api/metrics')
                .then(response => response.json())
                .then(data => {
                    renderDashboard(data);
                    document.getElementById('refresh-indicator').textContent = '✅';
                    countdown = 30;
                })
                .catch(error => {
                    console.error('Error loading dashboard:', error);
                    document.getElementById('content').innerHTML =
                        '<div class="error">❌ Error loading monitoring data: ' + error.message + '</div>';
                    document.getElementById('refresh-indicator').textContent = '❌';
                });
        }

        function formatBytes(bytes) {
            const units = ['B', 'KB', 'MB', 'GB', 'TB'];
            let size = bytes;
            let unitIndex = 0;

            while (size >= 1024 && unitIndex < units.length - 1) {
                size /= 1024;
                unitIndex++;
            }

            return size.toFixed(1) + ' ' + units[unitIndex];
        }

        function formatDuration(seconds) {
            if (seconds < 1) return Math.round(seconds * 1000) + 'ms';
            if (seconds < 60) return seconds.toFixed(1) + 's';
            if (seconds < 3600) return (seconds / 60).toFixed(1) + 'm';
            return (seconds / 3600).toFixed(1) + 'h';
        }

        function getStatusClass(value, goodThreshold, warningThreshold) {
            if (value <= goodThreshold) return 'health-good';
            if (value <= warningThreshold) return 'health-warning';
            return 'health-danger';
        }

        function renderDashboard(data) {
            const system = data.system || {};
            const requests = data.requests || {};
            const errors = data.errors || {};
            const aiUsage = data.ai_usage || {};
            const webhookEvents = data.webhook_events || {};
            const responseStats = data.response_time_stats || {};

            let html = '<div class="grid">';

            // System Health Card
            html += `
                <div class="card">
                    <h3>🖥️ System Health</h3>
                    <div class="metric">
                        <span class="metric-label">CPU Usage</span>
                        <span class="metric-value ${getStatusClass(system.cpu_percent || 0, 50, 80)}">
                            ${(system.cpu_percent || 0).toFixed(1)}%
                        </span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Memory Usage</span>
                        <span class="metric-value ${getStatusClass(system.memory_percent || 0, 70, 85)}">
                            ${formatBytes(system.memory_bytes || 0)} (${(system.memory_percent || 0).toFixed(1)}%)
                        </span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Disk Usage</span>
                        <span class="metric-value ${getStatusClass(system.disk_percent || 0, 80, 90)}">
                            ${(system.disk_percent || 0).toFixed(1)}%
                        </span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Free Disk Space</span>
                        <span class="metric-value">
                            ${formatBytes(system.disk_free_bytes || 0)}
                        </span>
                    </div>
                </div>
            `;

            // Request Statistics Card
            const totalRequests = Object.values(requests).reduce((a, b) => a + b, 0);
            const totalErrors = Object.values(errors).reduce((a, b) => a + b, 0);
            const errorRate = totalRequests > 0 ? (totalErrors / totalRequests * 100) : 0;

            html += `
                <div class="card">
                    <h3>📊 Request Statistics</h3>
                    <div class="metric">
                        <span class="metric-label">Total Requests</span>
                        <span class="metric-value">${totalRequests.toLocaleString()}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Total Errors</span>
                        <span class="metric-value ${totalErrors > 0 ? 'health-danger' : 'health-good'}">
                            ${totalErrors.toLocaleString()}
                        </span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Error Rate</span>
                        <span class="metric-value ${getStatusClass(errorRate, 1, 5)}">
                            ${errorRate.toFixed(2)}%
                        </span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Active Since</span>
                        <span class="metric-value">
                            ${system.timestamp ? new Date(system.timestamp * 1000).toLocaleString() : 'N/A'}
                        </span>
                    </div>
                </div>
            `;

            // AI Usage Card
            const totalAiRequests = Object.values(aiUsage).reduce((a, b) => a + b, 0);
            html += `
                <div class="card">
                    <h3>🤖 AI Model Usage</h3>
                    <div class="metric">
                        <span class="metric-label">Total AI Requests</span>
                        <span class="metric-value">${totalAiRequests.toLocaleString()}</span>
                    </div>
            `;

            // Show individual AI usage
            Object.entries(aiUsage).slice(0, 5).forEach(([key, count]) => {
                html += `
                    <div class="metric">
                        <span class="metric-label">${key}</span>
                        <span class="metric-value">${count.toLocaleString()}</span>
                    </div>
                `;
            });

            html += '</div>';

            // Webhook Events Card
            const totalWebhooks = Object.values(webhookEvents).reduce((a, b) => a + b, 0);
            html += `
                <div class="card">
                    <h3>🔗 Webhook Events</h3>
                    <div class="metric">
                        <span class="metric-label">Total Deliveries</span>
                        <span class="metric-value">${totalWebhooks.toLocaleString()}</span>
                    </div>
            `;

            Object.entries(webhookEvents).slice(0, 5).forEach(([key, count]) => {
                const isSuccess = key.includes('success');
                html += `
                    <div class="metric">
                        <span class="metric-label">${key}</span>
                        <span class="metric-value ${isSuccess ? 'health-good' : 'health-danger'}">
                            ${count.toLocaleString()}
                        </span>
                    </div>
                `;
            });

            html += '</div>';

            // Response Time Statistics Card
            html += `
                <div class="card">
                    <h3>⚡ Response Times</h3>
            `;

            Object.entries(responseStats).slice(0, 6).forEach(([endpoint, stats]) => {
                html += `
                    <div class="metric">
                        <span class="metric-label">${endpoint.split(':')[1] || endpoint}</span>
                        <span class="metric-value">
                            avg: ${formatDuration(stats.avg)} (${stats.count} req)
                        </span>
                    </div>
                `;
            });

            html += '</div>';

            // Recent Activity Card
            html += `
                <div class="card">
                    <h3>📋 System Status</h3>
                    <div class="metric">
                        <span class="metric-label">
                            <span class="status-indicator ${data.prometheus_available ? 'status-healthy' : 'status-warning'}"></span>
                            Prometheus Metrics
                        </span>
                        <span class="metric-value">${data.prometheus_available ? 'Available' : 'Unavailable'}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">
                            <span class="status-indicator ${totalRequests > 0 ? 'status-healthy' : 'status-warning'}"></span>
                            API Status
                        </span>
                        <span class="metric-value">${totalRequests > 0 ? 'Active' : 'Idle'}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">
                            <span class="status-indicator ${errorRate < 5 ? 'status-healthy' : 'status-error'}"></span>
                            Error Rate
                        </span>
                        <span class="metric-value">${errorRate < 1 ? 'Low' : errorRate < 5 ? 'Medium' : 'High'}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Last Updated</span>
                        <span class="metric-value">${new Date().toLocaleTimeString()}</span>
                    </div>
                </div>
            `;

            html += '</div>';
            document.getElementById('content').innerHTML = html;
        }

        // Initialize dashboard
        loadDashboard();
        refreshInterval = setInterval(updateCountdown, 1000);
    </script>
</body>
</html>
    '''
    return render_template_string(dashboard_html)


@monitoring_bp.route('/api/metrics')
def api_metrics():
    """API endpoint for metrics data"""
    collector = get_metrics_collector()
    return jsonify(collector.get_metrics_summary())


@monitoring_bp.route('/api/health')
def api_health():
    """API endpoint for health status"""
    collector = get_metrics_collector()
    health_score = collector.get_health_score()

    status = "healthy"
    if health_score < 0.5:
        status = "unhealthy"
    elif health_score < 0.8:
        status = "degraded"

    return jsonify({
        'status': status,
        'health_score': health_score,
        'timestamp': datetime.utcnow().isoformat()
    })


@monitoring_bp.route('/prometheus')
def prometheus_metrics():
    """Prometheus metrics endpoint"""
    collector = get_metrics_collector()
    from ..monitoring.prometheus_metrics import CONTENT_TYPE_LATEST

    return collector.get_prometheus_metrics(), 200, {'Content-Type': CONTENT_TYPE_LATEST}


@monitoring_bp.route('/api/alerts')
def api_alerts():
    """API endpoint for active alerts"""
    collector = get_metrics_collector()
    metrics = collector.get_metrics_summary()
    alerts = []

    # Check for system resource alerts
    system = metrics.get('system', {})

    if system.get('cpu_percent', 0) > 80:
        alerts.append({
            'type': 'cpu_high',
            'severity': 'warning' if system['cpu_percent'] < 90 else 'critical',
            'message': f"High CPU usage: {system['cpu_percent']:.1f}%",
            'timestamp': datetime.utcnow().isoformat()
        })

    if system.get('memory_percent', 0) > 85:
        alerts.append({
            'type': 'memory_high',
            'severity': 'warning' if system['memory_percent'] < 95 else 'critical',
            'message': f"High memory usage: {system['memory_percent']:.1f}%",
            'timestamp': datetime.utcnow().isoformat()
        })

    if system.get('disk_percent', 0) > 90:
        alerts.append({
            'type': 'disk_full',
            'severity': 'warning' if system['disk_percent'] < 95 else 'critical',
            'message': f"Low disk space: {system['disk_percent']:.1f}% used",
            'timestamp': datetime.utcnow().isoformat()
        })

    # Check for high error rates
    total_requests = sum(metrics.get('requests', {}).values())
    total_errors = sum(metrics.get('errors', {}).values())

    if total_requests > 10 and total_errors / total_requests > 0.1:
        alerts.append({
            'type': 'high_error_rate',
            'severity': 'critical',
            'message': f"High error rate: {(total_errors/total_requests*100):.1f}%",
            'timestamp': datetime.utcnow().isoformat()
        })

    return jsonify({'alerts': alerts, 'count': len(alerts)})


def register_monitoring_routes(app):
    """Register monitoring routes with Flask app"""
    app.register_blueprint(monitoring_bp, url_prefix='/monitoring')

    # Add metrics endpoint at root level for Prometheus scraping
    @app.route('/metrics')
    def metrics():
        return monitoring_bp.view_functions['prometheus_metrics']()

    return app