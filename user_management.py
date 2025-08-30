#!/usr/bin/env python3
"""
User Management System for SMS AI
Handles user accounts, API tokens, permissions, and usage tracking.
"""

import os
import json
import time
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from functools import wraps
from flask import request, jsonify, Response

# User data storage
USERS_DIR = os.path.join("synapseflow_data", "users")
TOKENS_FILE = os.path.join(USERS_DIR, "tokens.json")
USERS_FILE = os.path.join(USERS_DIR, "users.json")
USAGE_FILE = os.path.join(USERS_DIR, "usage.jsonl")

os.makedirs(USERS_DIR, exist_ok=True)

# User roles and permissions
ROLES = {
    "admin": {
        "permissions": ["*"],  # All permissions
        "description": "Full system access"
    },
    "user": {
        "permissions": ["reply", "profile_read", "memory_read"],
        "description": "Basic SMS AI access"
    },
    "premium": {
        "permissions": ["reply", "profile_read", "profile_write", "memory_read", "memory_write", "feedback"],
        "description": "Enhanced SMS AI access"
    },
    "api": {
        "permissions": ["reply"],
        "description": "API-only access for integrations"
    }
}

class UserManager:
    def __init__(self):
        self.users = self._load_users()
        self.tokens = self._load_tokens()
    
    def _load_users(self) -> Dict:
        """Load users from storage"""
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_users(self):
        """Save users to storage"""
        with open(USERS_FILE, 'w') as f:
            json.dump(self.users, f, indent=2)
    
    def _load_tokens(self) -> Dict:
        """Load tokens from storage"""
        if os.path.exists(TOKENS_FILE):
            with open(TOKENS_FILE, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_tokens(self):
        """Save tokens to storage"""
        with open(TOKENS_FILE, 'w') as f:
            json.dump(self.tokens, f, indent=2)
    
    def _hash_password(self, password: str) -> str:
        """Hash password with salt"""
        salt = secrets.token_hex(16)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}:{pwd_hash.hex()}"
    
    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        try:
            salt, pwd_hash = hashed.split(':')
            return hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex() == pwd_hash
        except:
            return False
    
    def create_user(self, username: str, password: str, email: str, role: str = "user") -> Tuple[bool, str]:
        """Create a new user"""
        if username in self.users:
            return False, "User already exists"
        
        if role not in ROLES:
            return False, f"Invalid role. Available: {list(ROLES.keys())}"
        
        user_id = secrets.token_urlsafe(16)
        self.users[username] = {
            "user_id": user_id,
            "email": email,
            "role": role,
            "password_hash": self._hash_password(password),
            "created_at": datetime.utcnow().isoformat(),
            "last_login": None,
            "active": True,
            "usage_stats": {
                "total_requests": 0,
                "last_request": None,
                "daily_limit": 1000,
                "monthly_limit": 30000
            }
        }
        self._save_users()
        return True, user_id
    
    def authenticate_user(self, username: str, password: str) -> Tuple[bool, Optional[Dict]]:
        """Authenticate user with username/password"""
        if username not in self.users:
            return False, None
        
        user = self.users[username]
        if not user.get("active", True):
            return False, None
        
        if self._verify_password(password, user["password_hash"]):
            # Update last login
            user["last_login"] = datetime.utcnow().isoformat()
            self._save_users()
            return True, user
        
        return False, None
    
    def generate_token(self, username: str, expires_days: int = 30, description: str = "") -> Tuple[bool, str]:
        """Generate API token for user"""
        if username not in self.users:
            return False, "User not found"
        
        token = f"sms-ai-{secrets.token_urlsafe(32)}"
        expires_at = (datetime.utcnow() + timedelta(days=expires_days)).isoformat()
        
        self.tokens[token] = {
            "username": username,
            "user_id": self.users[username]["user_id"],
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": expires_at,
            "description": description,
            "last_used": None,
            "usage_count": 0,
            "active": True
        }
        self._save_tokens()
        return True, token
    
    def validate_token(self, token: str) -> Tuple[bool, Optional[Dict], Optional[Dict]]:
        """Validate API token and return user info"""
        if token not in self.tokens:
            return False, None, None
        
        token_info = self.tokens[token]
        if not token_info.get("active", True):
            return False, None, None
        
        # Check expiration
        expires_at = datetime.fromisoformat(token_info["expires_at"])
        if datetime.utcnow() > expires_at:
            return False, None, None
        
        username = token_info["username"]
        if username not in self.users:
            return False, None, None
        
        user = self.users[username]
        if not user.get("active", True):
            return False, None, None
        
        # Update token usage
        token_info["last_used"] = datetime.utcnow().isoformat()
        token_info["usage_count"] += 1
        self._save_tokens()
        
        return True, user, token_info
    
    def has_permission(self, user: Dict, permission: str) -> bool:
        """Check if user has specific permission"""
        role = user.get("role", "user")
        if role not in ROLES:
            return False
        
        permissions = ROLES[role]["permissions"]
        return "*" in permissions or permission in permissions
    
    def revoke_token(self, token: str) -> bool:
        """Revoke an API token"""
        if token in self.tokens:
            self.tokens[token]["active"] = False
            self._save_tokens()
            return True
        return False
    
    def list_user_tokens(self, username: str) -> List[Dict]:
        """List all tokens for a user"""
        user_tokens = []
        for token, info in self.tokens.items():
            if info["username"] == username and info.get("active", True):
                # Don't expose the full token
                safe_info = info.copy()
                safe_info["token_preview"] = f"{token[:12]}...{token[-4:]}"
                user_tokens.append(safe_info)
        return user_tokens
    
    def log_usage(self, username: str, endpoint: str, success: bool = True):
        """Log API usage"""
        usage_entry = {
            "username": username,
            "endpoint": endpoint,
            "timestamp": datetime.utcnow().isoformat(),
            "success": success
        }
        
        with open(USAGE_FILE, 'a') as f:
            f.write(json.dumps(usage_entry) + '\n')
        
        # Update user stats
        if username in self.users:
            stats = self.users[username]["usage_stats"]
            stats["total_requests"] += 1
            stats["last_request"] = usage_entry["timestamp"]
            self._save_users()

    def get_user_analytics(self) -> Dict[str, any]:
        """Get comprehensive user analytics and statistics"""
        try:
            # Role distribution
            role_distribution = {}
            active_users = 0
            total_requests = 0

            for username, user in self.users.items():
                if user.get("active", True):
                    active_users += 1
                    role = user.get("role", "user")
                    role_distribution[role] = role_distribution.get(role, 0) + 1
                    total_requests += user.get("usage_stats", {}).get("total_requests", 0)

            # Token statistics
            active_tokens = 0
            expired_tokens = 0
            now = datetime.utcnow()

            for token, info in self.tokens.items():
                if info.get("active", True):
                    expires_at = datetime.fromisoformat(info["expires_at"])
                    if now <= expires_at:
                        active_tokens += 1
                    else:
                        expired_tokens += 1

            # Recent activity (last 7 days)
            recent_cutoff = (now - timedelta(days=7)).isoformat()
            recent_users = 0

            for username, user in self.users.items():
                last_request = user.get("usage_stats", {}).get("last_request")
                if last_request and last_request > recent_cutoff:
                    recent_users += 1

            return {
                "total_users": len(self.users),
                "active_users": active_users,
                "role_distribution": role_distribution,
                "total_tokens": len(self.tokens),
                "active_tokens": active_tokens,
                "expired_tokens": expired_tokens,
                "total_api_requests": total_requests,
                "weekly_active_users": recent_users,
                "avg_requests_per_user": total_requests / active_users if active_users > 0 else 0,
                "timestamp": now.isoformat()
            }

        except Exception as e:
            return {"error": f"Failed to get user analytics: {e}"}

    def get_user_activity_report(self, username: str = None, days: int = 30) -> Dict[str, any]:
        """Get detailed user activity report"""
        try:
            if username:
                # Specific user report
                if username not in self.users:
                    return {"error": "User not found"}

                user = self.users[username]
                user_tokens = [info for token, info in self.tokens.items()
                             if info["username"] == username and info.get("active", True)]

                # Load usage history
                usage_history = []
                if os.path.exists(USAGE_FILE):
                    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
                    with open(USAGE_FILE, 'r') as f:
                        for line in f:
                            try:
                                entry = json.loads(line.strip())
                                if entry["username"] == username and entry["timestamp"] > cutoff:
                                    usage_history.append(entry)
                            except:
                                continue

                return {
                    "username": username,
                    "user_info": {
                        "role": user.get("role"),
                        "email": user.get("email"),
                        "created_at": user.get("created_at"),
                        "last_login": user.get("last_login"),
                        "active": user.get("active", True)
                    },
                    "usage_stats": user.get("usage_stats", {}),
                    "active_tokens": len(user_tokens),
                    "recent_activity": usage_history,
                    "activity_count": len(usage_history),
                    "analysis_period_days": days
                }
            else:
                # System-wide activity report
                all_activity = []
                if os.path.exists(USAGE_FILE):
                    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
                    with open(USAGE_FILE, 'r') as f:
                        for line in f:
                            try:
                                entry = json.loads(line.strip())
                                if entry["timestamp"] > cutoff:
                                    all_activity.append(entry)
                            except:
                                continue

                # Analyze activity patterns
                endpoint_usage = {}
                user_activity = {}
                daily_activity = {}

                for entry in all_activity:
                    # Endpoint usage
                    endpoint = entry.get("endpoint", "unknown")
                    endpoint_usage[endpoint] = endpoint_usage.get(endpoint, 0) + 1

                    # User activity
                    username = entry.get("username", "unknown")
                    user_activity[username] = user_activity.get(username, 0) + 1

                    # Daily activity
                    date = entry["timestamp"][:10]  # Extract date part
                    daily_activity[date] = daily_activity.get(date, 0) + 1

                return {
                    "analysis_period_days": days,
                    "total_activities": len(all_activity),
                    "unique_users": len(user_activity),
                    "unique_endpoints": len(endpoint_usage),
                    "most_active_users": sorted(user_activity.items(), key=lambda x: x[1], reverse=True)[:10],
                    "popular_endpoints": sorted(endpoint_usage.items(), key=lambda x: x[1], reverse=True)[:10],
                    "daily_activity": daily_activity
                }

        except Exception as e:
            return {"error": f"Failed to get activity report: {e}"}

    def get_security_audit_log(self, days: int = 7) -> Dict[str, any]:
        """Get security audit log for user management activities"""
        try:
            now = datetime.utcnow()
            cutoff = (now - timedelta(days=days)).isoformat()

            # Recent user registrations
            recent_users = []
            for username, user in self.users.items():
                if user.get("created_at", "") > cutoff:
                    recent_users.append({
                        "username": username,
                        "role": user.get("role"),
                        "email": user.get("email"),
                        "created_at": user.get("created_at"),
                        "active": user.get("active", True)
                    })

            # Recent token activities
            token_activities = []
            for token, info in self.tokens.items():
                if info.get("created_at", "") > cutoff:
                    token_activities.append({
                        "username": info.get("username"),
                        "created_at": info.get("created_at"),
                        "expires_at": info.get("expires_at"),
                        "description": info.get("description", ""),
                        "usage_count": info.get("usage_count", 0),
                        "active": info.get("active", True)
                    })

            # Suspicious activities
            suspicious_activities = []

            # Check for users with excessive token creation
            user_token_counts = {}
            for token, info in self.tokens.items():
                if info.get("created_at", "") > cutoff:
                    username = info.get("username")
                    user_token_counts[username] = user_token_counts.get(username, 0) + 1

            for username, count in user_token_counts.items():
                if count > 5:  # More than 5 tokens in the period
                    suspicious_activities.append({
                        "type": "excessive_token_creation",
                        "username": username,
                        "details": f"Created {count} tokens in {days} days",
                        "severity": "medium"
                    })

            # Check for inactive users with recent token creation
            for token, info in self.tokens.items():
                username = info.get("username")
                if username in self.users and not self.users[username].get("active", True):
                    if info.get("created_at", "") > cutoff:
                        suspicious_activities.append({
                            "type": "inactive_user_token_creation",
                            "username": username,
                            "details": "Token created for inactive user",
                            "severity": "high"
                        })

            return {
                "audit_period_days": days,
                "recent_user_registrations": recent_users,
                "token_activities": token_activities,
                "suspicious_activities": suspicious_activities,
                "summary": {
                    "new_users": len(recent_users),
                    "new_tokens": len(token_activities),
                    "security_alerts": len(suspicious_activities)
                }
            }

        except Exception as e:
            return {"error": f"Failed to get security audit log: {e}"}

# Global user manager instance
_user_manager = None

def get_user_manager() -> UserManager:
    """Get global user manager instance"""
    global _user_manager
    if _user_manager is None:
        _user_manager = UserManager()
    return _user_manager

def require_permission(permission: str):
    """Decorator to require specific permission"""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # Check admin token first (backward compatibility)
            admin_token = os.environ.get("ADMIN_TOKEN", "").strip()
            if admin_token:
                token = request.headers.get("X-Admin-Token") or request.args.get("token")
                if token == admin_token:
                    return fn(*args, **kwargs)
            
            # Check user token
            user_token = request.headers.get("X-API-Token") or request.headers.get("Authorization", "").replace("Bearer ", "")
            if not user_token:
                return Response("Unauthorized: missing API token", status=401, mimetype="text/plain")
            
            um = get_user_manager()
            valid, user, token_info = um.validate_token(user_token)
            
            if not valid:
                return Response("Unauthorized: invalid or expired token", status=401, mimetype="text/plain")
            
            if not um.has_permission(user, permission):
                return Response(f"Forbidden: insufficient permissions for {permission}", status=403, mimetype="text/plain")
            
            # Log usage
            um.log_usage(user.get("username", "unknown"), request.endpoint or request.path)
            
            # Add user info to request context
            request.current_user = user
            request.current_token = token_info
            
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def require_user_auth(fn):
    """Decorator to require any valid user authentication"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        # Check admin token first (backward compatibility)
        admin_token = os.environ.get("ADMIN_TOKEN", "").strip()
        if admin_token:
            token = request.headers.get("X-Admin-Token") or request.args.get("token")
            if token == admin_token:
                return fn(*args, **kwargs)

        # Check user token
        user_token = request.headers.get("X-API-Token") or request.headers.get("Authorization", "").replace("Bearer ", "")
        if not user_token:
            return Response("Unauthorized: missing API token", status=401, mimetype="text/plain")

        um = get_user_manager()
        valid, user, token_info = um.validate_token(user_token)

        if not valid:
            return Response("Unauthorized: invalid or expired token", status=401, mimetype="text/plain")

        # Log usage
        um.log_usage(user.get("username", "unknown"), request.endpoint or request.path)

        # Add user info to request context
        request.current_user = user
        request.current_token = token_info

        return fn(*args, **kwargs)
    return wrapper
