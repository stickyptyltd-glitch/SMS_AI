#!/usr/bin/env python3
"""
Advanced Security Features
Rate limiting, IP blocking, security headers, and threat detection.
"""

import time
import hashlib
import hmac
import secrets
import ipaddress
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass
from functools import wraps
import json
import os

@dataclass
class SecurityEvent:
    """Security event for logging and analysis"""
    event_type: str
    severity: str  # low, medium, high, critical
    source_ip: str
    user_agent: str
    timestamp: str
    details: Dict
    blocked: bool = False

class RateLimiter:
    """Advanced rate limiting with multiple strategies"""
    
    def __init__(self):
        self.requests = defaultdict(deque)  # IP -> deque of timestamps
        self.user_requests = defaultdict(deque)  # user_id -> deque of timestamps
        self.blocked_ips = {}  # IP -> block_until_timestamp
        self.suspicious_ips = set()
        
        # Rate limit configurations
        self.limits = {
            'default': {'requests': 100, 'window': 3600},  # 100 requests per hour
            'login': {'requests': 5, 'window': 300},       # 5 login attempts per 5 minutes
            'api': {'requests': 1000, 'window': 3600},     # 1000 API calls per hour
            'register': {'requests': 3, 'window': 3600},   # 3 registrations per hour
        }
    
    def is_rate_limited(self, identifier: str, limit_type: str = 'default') -> Tuple[bool, int]:
        """Check if identifier is rate limited"""
        now = time.time()
        limit_config = self.limits.get(limit_type, self.limits['default'])
        
        # Clean old requests
        requests = self.requests[identifier]
        cutoff = now - limit_config['window']
        while requests and requests[0] < cutoff:
            requests.popleft()
        
        # Check limit
        if len(requests) >= limit_config['requests']:
            # Calculate reset time
            reset_time = int(requests[0] + limit_config['window'])
            return True, reset_time
        
        # Add current request
        requests.append(now)
        return False, 0
    
    def is_ip_blocked(self, ip: str) -> bool:
        """Check if IP is blocked"""
        if ip in self.blocked_ips:
            if time.time() < self.blocked_ips[ip]:
                return True
            else:
                # Block expired, remove it
                del self.blocked_ips[ip]
        return False
    
    def block_ip(self, ip: str, duration: int = 3600):
        """Block IP for specified duration (seconds)"""
        self.blocked_ips[ip] = time.time() + duration
        self.suspicious_ips.add(ip)
    
    def add_suspicious_ip(self, ip: str):
        """Mark IP as suspicious"""
        self.suspicious_ips.add(ip)
    
    def get_rate_limit_info(self, identifier: str, limit_type: str = 'default') -> Dict:
        """Get rate limit information"""
        now = time.time()
        limit_config = self.limits.get(limit_type, self.limits['default'])
        
        requests = self.requests[identifier]
        cutoff = now - limit_config['window']
        
        # Count recent requests
        recent_requests = sum(1 for req_time in requests if req_time > cutoff)
        
        return {
            'limit': limit_config['requests'],
            'remaining': max(0, limit_config['requests'] - recent_requests),
            'reset_time': int(now + limit_config['window']),
            'window': limit_config['window']
        }

class SecurityMonitor:
    """Advanced security monitoring and threat detection"""
    
    def __init__(self, data_dir: str = "dayle_data"):
        self.data_dir = data_dir
        self.security_dir = os.path.join(data_dir, "security")
        os.makedirs(self.security_dir, exist_ok=True)
        
        self.rate_limiter = RateLimiter()
        self.security_events = deque(maxlen=10000)
        self.failed_logins = defaultdict(list)  # IP -> list of timestamps
        self.suspicious_patterns = []
        
        # Load IP whitelist/blacklist
        self.load_ip_lists()
        
        # Security thresholds
        self.max_failed_logins = 5
        self.failed_login_window = 300  # 5 minutes
        self.suspicious_user_agents = [
            'sqlmap', 'nikto', 'nmap', 'masscan', 'zap', 'burp',
            'python-requests', 'curl', 'wget'  # Be careful with these
        ]
    
    def load_ip_lists(self):
        """Load IP whitelist and blacklist"""
        self.ip_whitelist = set()
        self.ip_blacklist = set()
        
        # Load whitelist
        whitelist_file = os.path.join(self.security_dir, "ip_whitelist.txt")
        if os.path.exists(whitelist_file):
            with open(whitelist_file, 'r') as f:
                for line in f:
                    ip = line.strip()
                    if ip and not ip.startswith('#'):
                        self.ip_whitelist.add(ip)
        
        # Load blacklist
        blacklist_file = os.path.join(self.security_dir, "ip_blacklist.txt")
        if os.path.exists(blacklist_file):
            with open(blacklist_file, 'r') as f:
                for line in f:
                    ip = line.strip()
                    if ip and not ip.startswith('#'):
                        self.ip_blacklist.add(ip)
    
    def is_ip_allowed(self, ip: str) -> bool:
        """Check if IP is allowed"""
        # Check blacklist first
        if ip in self.ip_blacklist:
            return False
        
        # Check if IP is blocked by rate limiter
        if self.rate_limiter.is_ip_blocked(ip):
            return False
        
        # If whitelist exists and IP not in it, block
        if self.ip_whitelist and ip not in self.ip_whitelist:
            return False
        
        return True
    
    def detect_threats(self, ip: str, user_agent: str, endpoint: str, 
                      user_id: str = None) -> List[SecurityEvent]:
        """Detect potential security threats"""
        threats = []
        now = datetime.utcnow().isoformat()
        
        # Check for suspicious user agents
        if any(pattern.lower() in user_agent.lower() for pattern in self.suspicious_user_agents):
            threats.append(SecurityEvent(
                event_type="suspicious_user_agent",
                severity="medium",
                source_ip=ip,
                user_agent=user_agent,
                timestamp=now,
                details={"endpoint": endpoint, "user_id": user_id}
            ))
        
        # Check for rapid requests (potential DoS)
        if self.rate_limiter.is_rate_limited(ip, 'default')[0]:
            threats.append(SecurityEvent(
                event_type="rate_limit_exceeded",
                severity="high",
                source_ip=ip,
                user_agent=user_agent,
                timestamp=now,
                details={"endpoint": endpoint, "user_id": user_id}
            ))
        
        # Check for failed login patterns
        if endpoint in ['/users/login', '/admin/login']:
            failed_count = len([t for t in self.failed_logins[ip] 
                              if time.time() - t < self.failed_login_window])
            if failed_count >= self.max_failed_logins:
                threats.append(SecurityEvent(
                    event_type="brute_force_attempt",
                    severity="critical",
                    source_ip=ip,
                    user_agent=user_agent,
                    timestamp=now,
                    details={"failed_attempts": failed_count, "endpoint": endpoint}
                ))
        
        # Check for SQL injection patterns
        sql_patterns = ['union', 'select', 'drop', 'insert', 'delete', 'update', 
                       'script', 'alert', 'onload', 'onerror']
        request_data = endpoint.lower()
        if any(pattern in request_data for pattern in sql_patterns):
            threats.append(SecurityEvent(
                event_type="sql_injection_attempt",
                severity="critical",
                source_ip=ip,
                user_agent=user_agent,
                timestamp=now,
                details={"endpoint": endpoint, "patterns_detected": 
                        [p for p in sql_patterns if p in request_data]}
            ))
        
        # Log all threats
        for threat in threats:
            self.log_security_event(threat)
        
        return threats
    
    def log_security_event(self, event: SecurityEvent):
        """Log security event"""
        self.security_events.append(event)
        
        # Write to file
        log_file = os.path.join(self.security_dir, "security_events.jsonl")
        try:
            with open(log_file, 'a') as f:
                f.write(json.dumps({
                    'event_type': event.event_type,
                    'severity': event.severity,
                    'source_ip': event.source_ip,
                    'user_agent': event.user_agent,
                    'timestamp': event.timestamp,
                    'details': event.details,
                    'blocked': event.blocked
                }) + '\n')
        except Exception as e:
            print(f"Error logging security event: {e}")
        
        # Auto-block for critical threats
        if event.severity == "critical":
            self.rate_limiter.block_ip(event.source_ip, 3600)  # Block for 1 hour
            event.blocked = True
    
    def record_failed_login(self, ip: str):
        """Record failed login attempt"""
        self.failed_logins[ip].append(time.time())
        
        # Clean old attempts
        cutoff = time.time() - self.failed_login_window
        self.failed_logins[ip] = [t for t in self.failed_logins[ip] if t > cutoff]
    
    def get_security_summary(self) -> Dict:
        """Get security summary"""
        now = time.time()
        last_24h = now - 86400
        
        recent_events = [e for e in self.security_events 
                        if datetime.fromisoformat(e.timestamp.replace('Z', '+00:00')).timestamp() > last_24h]
        
        event_counts = defaultdict(int)
        severity_counts = defaultdict(int)
        
        for event in recent_events:
            event_counts[event.event_type] += 1
            severity_counts[event.severity] += 1
        
        return {
            "total_events_24h": len(recent_events),
            "event_types": dict(event_counts),
            "severity_distribution": dict(severity_counts),
            "blocked_ips": len(self.rate_limiter.blocked_ips),
            "suspicious_ips": len(self.rate_limiter.suspicious_ips),
            "active_rate_limits": len(self.rate_limiter.requests)
        }

class SecurityHeaders:
    """Security headers management"""
    
    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """Get recommended security headers"""
        return {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
        }

def require_security_check(check_rate_limit: bool = True, 
                          check_ip_whitelist: bool = False,
                          limit_type: str = 'default'):
    """Decorator for security checks"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from flask import request, Response
            
            # Get client info
            ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
            if ip and ',' in ip:
                ip = ip.split(',')[0].strip()
            
            user_agent = request.headers.get('User-Agent', '')
            endpoint = request.endpoint or request.path
            
            # Get security monitor
            security_monitor = get_security_monitor()
            
            # Check IP allowlist
            if not security_monitor.is_ip_allowed(ip):
                return Response("Access denied", status=403, mimetype="text/plain")
            
            # Check rate limits
            if check_rate_limit:
                is_limited, reset_time = security_monitor.rate_limiter.is_rate_limited(ip, limit_type)
                if is_limited:
                    response = Response("Rate limit exceeded", status=429, mimetype="text/plain")
                    response.headers['X-RateLimit-Reset'] = str(reset_time)
                    return response
            
            # Detect threats
            threats = security_monitor.detect_threats(ip, user_agent, endpoint)
            
            # Block if critical threats detected
            critical_threats = [t for t in threats if t.severity == "critical"]
            if critical_threats:
                return Response("Security violation detected", status=403, mimetype="text/plain")
            
            # Add security headers to response
            response = func(*args, **kwargs)
            if hasattr(response, 'headers'):
                for header, value in SecurityHeaders.get_security_headers().items():
                    response.headers[header] = value
            
            return response
        return wrapper
    return decorator

# Global security monitor instance
_security_monitor = None

def get_security_monitor() -> SecurityMonitor:
    """Get global security monitor instance"""
    global _security_monitor
    if _security_monitor is None:
        _security_monitor = SecurityMonitor()
    return _security_monitor
