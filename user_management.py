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
USERS_DIR = os.path.join("dayle_data", "users")
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
