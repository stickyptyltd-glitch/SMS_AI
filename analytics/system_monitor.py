#!/usr/bin/env python3
"""
Advanced System Analytics and Monitoring
Real-time performance monitoring, usage analytics, and system health checks.
"""

import os
import json
import time
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import sqlite3

@dataclass
class SystemMetrics:
    """System performance metrics"""
    timestamp: str
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    active_connections: int
    response_time_avg: float
    error_rate: float
    requests_per_minute: int

@dataclass
class UserActivity:
    """User activity tracking"""
    user_id: str
    username: str
    endpoint: str
    timestamp: str
    response_time: float
    status_code: int
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None

class SystemMonitor:
    """Advanced system monitoring and analytics"""
    
    def __init__(self, data_dir: str = "synapseflow_data"):
        self.data_dir = data_dir
        self.analytics_dir = os.path.join(data_dir, "analytics")
        os.makedirs(self.analytics_dir, exist_ok=True)
        
        # Initialize database
        self.db_path = os.path.join(self.analytics_dir, "system_metrics.db")
        self._init_database()
        
        # In-memory metrics for real-time monitoring
        self.recent_requests = deque(maxlen=1000)
        self.response_times = deque(maxlen=100)
        self.error_counts = defaultdict(int)
        self.user_sessions = {}
        
        # Monitoring thread
        self.monitoring_active = False
        self.monitoring_thread = None
        
        # Performance thresholds
        self.cpu_threshold = 80.0
        self.memory_threshold = 85.0
        self.response_time_threshold = 2.0
        self.error_rate_threshold = 0.05
    
    def _init_database(self):
        """Initialize SQLite database for metrics storage"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS system_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        cpu_percent REAL,
                        memory_percent REAL,
                        disk_usage_percent REAL,
                        active_connections INTEGER,
                        response_time_avg REAL,
                        error_rate REAL,
                        requests_per_minute INTEGER
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_activity (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT,
                        username TEXT,
                        endpoint TEXT,
                        timestamp TEXT NOT NULL,
                        response_time REAL,
                        status_code INTEGER,
                        user_agent TEXT,
                        ip_address TEXT
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS alerts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        alert_type TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        message TEXT NOT NULL,
                        resolved BOOLEAN DEFAULT FALSE,
                        resolved_at TEXT
                    )
                """)
                
                # Create indexes for better performance
                conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON system_metrics(timestamp)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON user_activity(timestamp)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_activity_user ON user_activity(user_id)")
                
        except Exception as e:
            print(f"Error initializing database: {e}")
    
    def start_monitoring(self, interval: int = 60):
        """Start background system monitoring"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval,),
            daemon=True
        )
        self.monitoring_thread.start()
        print(f"System monitoring started (interval: {interval}s)")
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        print("System monitoring stopped")
    
    def _monitoring_loop(self, interval: int):
        """Background monitoring loop"""
        while self.monitoring_active:
            try:
                metrics = self._collect_system_metrics()
                self._store_metrics(metrics)
                self._check_alerts(metrics)
                time.sleep(interval)
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                time.sleep(interval)
    
    def _collect_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics"""
        # System resources
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Network connections (approximate)
        connections = len(psutil.net_connections(kind='inet'))
        
        # Calculate recent performance metrics
        now = time.time()
        recent_window = now - 60  # Last minute
        
        recent_requests = [r for r in self.recent_requests if r['timestamp'] > recent_window]
        requests_per_minute = len(recent_requests)
        
        # Average response time
        if self.response_times:
            response_time_avg = sum(self.response_times) / len(self.response_times)
        else:
            response_time_avg = 0.0
        
        # Error rate
        total_recent = len(recent_requests)
        error_recent = sum(1 for r in recent_requests if r.get('status_code', 200) >= 400)
        error_rate = error_recent / total_recent if total_recent > 0 else 0.0
        
        return SystemMetrics(
            timestamp=datetime.utcnow().isoformat(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            disk_usage_percent=disk.percent,
            active_connections=connections,
            response_time_avg=response_time_avg,
            error_rate=error_rate,
            requests_per_minute=requests_per_minute
        )
    
    def _store_metrics(self, metrics: SystemMetrics):
        """Store metrics in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO system_metrics 
                    (timestamp, cpu_percent, memory_percent, disk_usage_percent,
                     active_connections, response_time_avg, error_rate, requests_per_minute)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metrics.timestamp, metrics.cpu_percent, metrics.memory_percent,
                    metrics.disk_usage_percent, metrics.active_connections,
                    metrics.response_time_avg, metrics.error_rate, metrics.requests_per_minute
                ))
        except Exception as e:
            print(f"Error storing metrics: {e}")
    
    def _check_alerts(self, metrics: SystemMetrics):
        """Check for alert conditions"""
        alerts = []
        
        if metrics.cpu_percent > self.cpu_threshold:
            alerts.append(("cpu_high", "warning", f"High CPU usage: {metrics.cpu_percent:.1f}%"))
        
        if metrics.memory_percent > self.memory_threshold:
            alerts.append(("memory_high", "warning", f"High memory usage: {metrics.memory_percent:.1f}%"))
        
        if metrics.response_time_avg > self.response_time_threshold:
            alerts.append(("response_slow", "warning", f"Slow response time: {metrics.response_time_avg:.2f}s"))
        
        if metrics.error_rate > self.error_rate_threshold:
            alerts.append(("error_rate_high", "error", f"High error rate: {metrics.error_rate:.1%}"))
        
        # Store alerts
        for alert_type, severity, message in alerts:
            self._store_alert(alert_type, severity, message)
    
    def _store_alert(self, alert_type: str, severity: str, message: str):
        """Store alert in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO alerts (timestamp, alert_type, severity, message)
                    VALUES (?, ?, ?, ?)
                """, (datetime.utcnow().isoformat(), alert_type, severity, message))
        except Exception as e:
            print(f"Error storing alert: {e}")
    
    def log_request(self, user_id: str, username: str, endpoint: str, 
                   response_time: float, status_code: int, 
                   user_agent: str = None, ip_address: str = None):
        """Log user request activity"""
        activity = UserActivity(
            user_id=user_id,
            username=username,
            endpoint=endpoint,
            timestamp=datetime.utcnow().isoformat(),
            response_time=response_time,
            status_code=status_code,
            user_agent=user_agent,
            ip_address=ip_address
        )
        
        # Store in database
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO user_activity 
                    (user_id, username, endpoint, timestamp, response_time, 
                     status_code, user_agent, ip_address)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    activity.user_id, activity.username, activity.endpoint,
                    activity.timestamp, activity.response_time, activity.status_code,
                    activity.user_agent, activity.ip_address
                ))
        except Exception as e:
            print(f"Error logging user activity: {e}")
        
        # Update in-memory metrics
        self.recent_requests.append({
            'timestamp': time.time(),
            'status_code': status_code,
            'response_time': response_time
        })
        self.response_times.append(response_time)
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get current system health status"""
        try:
            current_metrics = self._collect_system_metrics()
            
            # Get recent alerts
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT alert_type, severity, message, timestamp 
                    FROM alerts 
                    WHERE resolved = FALSE 
                    ORDER BY timestamp DESC 
                    LIMIT 10
                """)
                active_alerts = [dict(zip([col[0] for col in cursor.description], row)) 
                               for row in cursor.fetchall()]
            
            # Health score calculation
            health_score = 100.0
            if current_metrics.cpu_percent > self.cpu_threshold:
                health_score -= 20
            if current_metrics.memory_percent > self.memory_threshold:
                health_score -= 20
            if current_metrics.response_time_avg > self.response_time_threshold:
                health_score -= 15
            if current_metrics.error_rate > self.error_rate_threshold:
                health_score -= 25
            
            health_status = "excellent" if health_score >= 90 else \
                           "good" if health_score >= 70 else \
                           "warning" if health_score >= 50 else "critical"
            
            return {
                "health_score": max(0, health_score),
                "health_status": health_status,
                "current_metrics": asdict(current_metrics),
                "active_alerts": active_alerts,
                "monitoring_active": self.monitoring_active,
                "uptime_hours": self._get_uptime_hours()
            }
            
        except Exception as e:
            return {"error": f"Failed to get system health: {e}"}
    
    def _get_uptime_hours(self) -> float:
        """Get system uptime in hours"""
        try:
            return (time.time() - psutil.boot_time()) / 3600
        except:
            return 0.0
    
    def get_usage_analytics(self, days: int = 7) -> Dict[str, Any]:
        """Get usage analytics for specified period"""
        try:
            cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                # Total requests
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM user_activity 
                    WHERE timestamp > ?
                """, (cutoff_date,))
                total_requests = cursor.fetchone()[0]
                
                # Unique users
                cursor = conn.execute("""
                    SELECT COUNT(DISTINCT user_id) FROM user_activity 
                    WHERE timestamp > ?
                """, (cutoff_date,))
                unique_users = cursor.fetchone()[0]
                
                # Top endpoints
                cursor = conn.execute("""
                    SELECT endpoint, COUNT(*) as count 
                    FROM user_activity 
                    WHERE timestamp > ? 
                    GROUP BY endpoint 
                    ORDER BY count DESC 
                    LIMIT 10
                """, (cutoff_date,))
                top_endpoints = [dict(zip([col[0] for col in cursor.description], row)) 
                               for row in cursor.fetchall()]
                
                # Error rate
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) as errors
                    FROM user_activity 
                    WHERE timestamp > ?
                """, (cutoff_date,))
                result = cursor.fetchone()
                error_rate = (result[1] / result[0]) if result[0] > 0 else 0
                
                return {
                    "period_days": days,
                    "total_requests": total_requests,
                    "unique_users": unique_users,
                    "requests_per_day": total_requests / days,
                    "error_rate": error_rate,
                    "top_endpoints": top_endpoints
                }
                
        except Exception as e:
            return {"error": f"Failed to get usage analytics: {e}"}

    def get_predictive_analytics(self) -> Dict[str, Any]:
        """Get predictive analytics and forecasting"""
        try:
            # Get historical metrics for trend analysis
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT cpu_percent, memory_percent, requests_per_minute,
                           response_time_avg, error_rate, timestamp
                    FROM system_metrics
                    WHERE timestamp > datetime('now', '-24 hours')
                    ORDER BY timestamp DESC
                """)

                historical_data = cursor.fetchall()

            if len(historical_data) < 10:
                return {"error": "Insufficient historical data for predictions"}

            # Analyze trends
            cpu_trend = self._calculate_trend([row[0] for row in historical_data])
            memory_trend = self._calculate_trend([row[1] for row in historical_data])
            response_time_trend = self._calculate_trend([row[3] for row in historical_data])

            # Generate predictions
            predictions = {
                "cpu_forecast_1h": self._forecast_metric([row[0] for row in historical_data[-12:]], 1),
                "memory_forecast_1h": self._forecast_metric([row[1] for row in historical_data[-12:]], 1),
                "response_time_forecast_1h": self._forecast_metric([row[3] for row in historical_data[-12:]], 1),
                "capacity_warnings": self._generate_capacity_warnings(historical_data)
            }

            return {
                "trends": {
                    "cpu_trend": cpu_trend,
                    "memory_trend": memory_trend,
                    "response_time_trend": response_time_trend
                },
                "predictions": predictions,
                "data_points": len(historical_data),
                "analysis_period_hours": 24
            }

        except Exception as e:
            return {"error": f"Predictive analytics failed: {e}"}

    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from values"""
        if len(values) < 2:
            return "insufficient_data"

        # Simple linear regression slope
        n = len(values)
        x_values = list(range(n))

        x_mean = sum(x_values) / n
        y_mean = sum(values) / n

        numerator = sum((x_values[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return "stable"

        slope = numerator / denominator

        if slope > 0.1:
            return "increasing"
        elif slope < -0.1:
            return "decreasing"
        else:
            return "stable"

    def _forecast_metric(self, values: List[float], hours_ahead: int) -> Dict[str, Any]:
        """Simple forecasting for a metric"""
        if len(values) < 3:
            return {"error": "Insufficient data"}

        # Simple moving average forecast
        recent_avg = sum(values[-3:]) / 3
        overall_avg = sum(values) / len(values)

        # Weight recent values more heavily
        forecast = (recent_avg * 0.7) + (overall_avg * 0.3)

        # Calculate confidence based on variance
        variance = sum((v - overall_avg) ** 2 for v in values) / len(values)
        confidence = max(0.1, min(0.9, 1 - (variance / (overall_avg + 1))))

        return {
            "forecast_value": round(forecast, 2),
            "confidence": round(confidence, 2),
            "trend": self._calculate_trend(values)
        }

    def _generate_capacity_warnings(self, historical_data: List) -> List[Dict]:
        """Generate capacity planning warnings"""
        warnings = []

        if not historical_data:
            return warnings

        # Check CPU capacity
        recent_cpu = [row[0] for row in historical_data[-12:]]  # Last 12 hours
        if recent_cpu:
            avg_cpu = sum(recent_cpu) / len(recent_cpu)

            if avg_cpu > 70:
                warnings.append({
                    "type": "cpu_capacity",
                    "severity": "high" if avg_cpu > 85 else "medium",
                    "message": f"Average CPU usage is {avg_cpu:.1f}% over last 12 hours",
                    "recommendation": "Consider scaling up CPU resources"
                })

        # Check memory capacity
        recent_memory = [row[1] for row in historical_data[-12:]]
        if recent_memory:
            avg_memory = sum(recent_memory) / len(recent_memory)

            if avg_memory > 75:
                warnings.append({
                    "type": "memory_capacity",
                    "severity": "high" if avg_memory > 90 else "medium",
                    "message": f"Average memory usage is {avg_memory:.1f}% over last 12 hours",
                    "recommendation": "Consider scaling up memory resources"
                })

        return warnings

# Global monitor instance
_system_monitor = None

def get_system_monitor() -> SystemMonitor:
    """Get global system monitor instance"""
    global _system_monitor
    if _system_monitor is None:
        _system_monitor = SystemMonitor()
    return _system_monitor
