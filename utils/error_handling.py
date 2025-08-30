#!/usr/bin/env python3
"""
Comprehensive Error Handling and Validation System
Robust error handling, input validation, and recovery mechanisms.
"""

import re
import json
import traceback
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Callable
from functools import wraps
from dataclasses import dataclass
from enum import Enum

class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    RATE_LIMIT = "rate_limit"
    EXTERNAL_API = "external_api"
    DATABASE = "database"
    SYSTEM = "system"
    USER_INPUT = "user_input"
    NETWORK = "network"

@dataclass
class ErrorDetails:
    """Detailed error information"""
    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    user_message: str
    timestamp: str
    context: Dict[str, Any]
    stack_trace: Optional[str] = None
    recovery_suggestions: List[str] = None

class ValidationError(Exception):
    """Custom validation error"""
    def __init__(self, message: str, field: str = None, value: Any = None):
        self.message = message
        self.field = field
        self.value = value
        super().__init__(message)

class APIError(Exception):
    """Custom API error"""
    def __init__(self, message: str, status_code: int = 500, error_code: str = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(message)

class InputValidator:
    """Comprehensive input validation"""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        if not email or not isinstance(email, str):
            return False
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email.strip()) is not None
    
    @staticmethod
    def validate_username(username: str) -> tuple[bool, str]:
        """Validate username format and requirements"""
        if not username or not isinstance(username, str):
            return False, "Username is required"
        
        username = username.strip()
        
        if len(username) < 3:
            return False, "Username must be at least 3 characters long"
        
        if len(username) > 50:
            return False, "Username must be less than 50 characters"
        
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            return False, "Username can only contain letters, numbers, underscores, and hyphens"
        
        if username.startswith('_') or username.startswith('-'):
            return False, "Username cannot start with underscore or hyphen"
        
        return True, ""
    
    @staticmethod
    def validate_password(password: str) -> tuple[bool, List[str]]:
        """Validate password strength"""
        if not password or not isinstance(password, str):
            return False, ["Password is required"]
        
        issues = []
        
        if len(password) < 8:
            issues.append("Password must be at least 8 characters long")
        
        if len(password) > 128:
            issues.append("Password must be less than 128 characters")
        
        if not re.search(r'[a-z]', password):
            issues.append("Password must contain at least one lowercase letter")
        
        if not re.search(r'[A-Z]', password):
            issues.append("Password must contain at least one uppercase letter")
        
        if not re.search(r'\d', password):
            issues.append("Password must contain at least one number")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            issues.append("Password must contain at least one special character")
        
        # Check for common weak passwords
        weak_patterns = [
            r'password', r'123456', r'qwerty', r'admin', r'letmein',
            r'welcome', r'monkey', r'dragon', r'master', r'shadow'
        ]
        
        for pattern in weak_patterns:
            if re.search(pattern, password.lower()):
                issues.append("Password contains common weak patterns")
                break
        
        return len(issues) == 0, issues
    
    @staticmethod
    def validate_phone_number(phone: str) -> tuple[bool, str]:
        """Validate phone number format"""
        if not phone or not isinstance(phone, str):
            return False, "Phone number is required"
        
        # Remove all non-digit characters
        digits_only = re.sub(r'\D', '', phone)
        
        if len(digits_only) < 10:
            return False, "Phone number must have at least 10 digits"
        
        if len(digits_only) > 15:
            return False, "Phone number must have less than 15 digits"
        
        # Check for valid patterns
        valid_patterns = [
            r'^\+?1?[2-9]\d{2}[2-9]\d{2}\d{4}$',  # US format
            r'^\+?[1-9]\d{1,14}$'  # International format
        ]
        
        for pattern in valid_patterns:
            if re.match(pattern, digits_only):
                return True, ""
        
        return False, "Invalid phone number format"
    
    @staticmethod
    def validate_message_content(content: str, max_length: int = 1600) -> tuple[bool, str]:
        """Validate message content"""
        if not content or not isinstance(content, str):
            return False, "Message content is required"
        
        content = content.strip()
        
        if len(content) == 0:
            return False, "Message cannot be empty"
        
        if len(content) > max_length:
            return False, f"Message must be less than {max_length} characters"
        
        # Check for potentially harmful content
        suspicious_patterns = [
            r'<script[^>]*>.*?</script>',  # Script tags
            r'javascript:',  # JavaScript URLs
            r'on\w+\s*=',  # Event handlers
            r'<iframe[^>]*>.*?</iframe>',  # Iframes
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return False, "Message contains potentially harmful content"
        
        return True, ""
    
    @staticmethod
    def sanitize_input(text: str) -> str:
        """Sanitize user input"""
        if not isinstance(text, str):
            return str(text) if text is not None else ""
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        # Remove potentially dangerous characters
        dangerous_chars = ['<', '>', '"', "'", '&', '\r', '\n']
        for char in dangerous_chars:
            text = text.replace(char, '')
        
        return text.strip()

class ErrorHandler:
    """Centralized error handling"""
    
    def __init__(self, log_file: str = "dayle_data/errors.log"):
        self.log_file = log_file
        self.setup_logging()
        self.error_counts = {}
    
    def setup_logging(self):
        """Setup error logging"""
        logging.basicConfig(
            filename=self.log_file,
            level=logging.ERROR,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def handle_error(self, error: Exception, context: Dict[str, Any] = None, 
                    category: ErrorCategory = ErrorCategory.SYSTEM,
                    severity: ErrorSeverity = ErrorSeverity.MEDIUM) -> ErrorDetails:
        """Handle and log error with context"""
        
        error_id = f"{category.value}_{int(datetime.utcnow().timestamp())}"
        
        # Determine user-friendly message
        user_message = self._get_user_message(error, category)
        
        # Create error details
        error_details = ErrorDetails(
            error_id=error_id,
            category=category,
            severity=severity,
            message=str(error),
            user_message=user_message,
            timestamp=datetime.utcnow().isoformat(),
            context=context or {},
            stack_trace=traceback.format_exc(),
            recovery_suggestions=self._get_recovery_suggestions(category)
        )
        
        # Log error
        self._log_error(error_details)
        
        # Update error counts
        self.error_counts[category.value] = self.error_counts.get(category.value, 0) + 1
        
        return error_details
    
    def _get_user_message(self, error: Exception, category: ErrorCategory) -> str:
        """Get user-friendly error message"""
        if isinstance(error, ValidationError):
            return f"Invalid input: {error.message}"
        
        if isinstance(error, APIError):
            return error.message
        
        category_messages = {
            ErrorCategory.VALIDATION: "Please check your input and try again.",
            ErrorCategory.AUTHENTICATION: "Authentication failed. Please check your credentials.",
            ErrorCategory.AUTHORIZATION: "You don't have permission to perform this action.",
            ErrorCategory.RATE_LIMIT: "Too many requests. Please wait a moment and try again.",
            ErrorCategory.EXTERNAL_API: "External service is temporarily unavailable. Please try again later.",
            ErrorCategory.DATABASE: "Database error occurred. Please try again later.",
            ErrorCategory.SYSTEM: "An internal error occurred. Please try again later.",
            ErrorCategory.USER_INPUT: "Invalid input provided. Please check and try again.",
            ErrorCategory.NETWORK: "Network error occurred. Please check your connection."
        }
        
        return category_messages.get(category, "An unexpected error occurred. Please try again.")
    
    def _get_recovery_suggestions(self, category: ErrorCategory) -> List[str]:
        """Get recovery suggestions for error category"""
        suggestions = {
            ErrorCategory.VALIDATION: [
                "Check input format and requirements",
                "Ensure all required fields are provided",
                "Verify data types and constraints"
            ],
            ErrorCategory.AUTHENTICATION: [
                "Verify username and password",
                "Check if account is active",
                "Try resetting password if needed"
            ],
            ErrorCategory.AUTHORIZATION: [
                "Contact administrator for permissions",
                "Check user role and access level",
                "Verify token is valid and not expired"
            ],
            ErrorCategory.RATE_LIMIT: [
                "Wait before making another request",
                "Reduce request frequency",
                "Consider upgrading account limits"
            ],
            ErrorCategory.EXTERNAL_API: [
                "Retry request after delay",
                "Check external service status",
                "Use fallback mechanisms if available"
            ],
            ErrorCategory.DATABASE: [
                "Retry operation",
                "Check database connectivity",
                "Contact system administrator"
            ],
            ErrorCategory.SYSTEM: [
                "Retry operation",
                "Check system resources",
                "Contact technical support"
            ],
            ErrorCategory.NETWORK: [
                "Check internet connection",
                "Retry request",
                "Verify network configuration"
            ]
        }
        
        return suggestions.get(category, ["Retry the operation", "Contact support if problem persists"])
    
    def _log_error(self, error_details: ErrorDetails):
        """Log error details"""
        log_entry = {
            "error_id": error_details.error_id,
            "category": error_details.category.value,
            "severity": error_details.severity.value,
            "message": error_details.message,
            "timestamp": error_details.timestamp,
            "context": error_details.context
        }
        
        logging.error(json.dumps(log_entry))
        
        # Also log to console for critical errors
        if error_details.severity == ErrorSeverity.CRITICAL:
            print(f"CRITICAL ERROR [{error_details.error_id}]: {error_details.message}")

def handle_exceptions(category: ErrorCategory = ErrorCategory.SYSTEM, 
                     severity: ErrorSeverity = ErrorSeverity.MEDIUM):
    """Decorator for automatic exception handling"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_handler = ErrorHandler()
                context = {
                    "function": func.__name__,
                    "args": str(args)[:200],  # Limit context size
                    "kwargs": str(kwargs)[:200]
                }
                error_details = error_handler.handle_error(e, context, category, severity)
                
                # Re-raise as APIError for API endpoints
                raise APIError(
                    error_details.user_message,
                    status_code=500,
                    error_code=error_details.error_id
                )
        return wrapper
    return decorator

def validate_json_input(required_fields: List[str] = None, 
                       optional_fields: List[str] = None):
    """Decorator for JSON input validation"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            from flask import request
            
            # Get JSON data
            try:
                data = request.get_json(force=True) or {}
            except Exception:
                raise ValidationError("Invalid JSON format")
            
            # Validate required fields
            if required_fields:
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
            
            # Remove unexpected fields
            allowed_fields = (required_fields or []) + (optional_fields or [])
            if allowed_fields:
                filtered_data = {k: v for k, v in data.items() if k in allowed_fields}
                # Store filtered data in request context instead of overwriting json
                request._filtered_json = filtered_data
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Global error handler instance
_error_handler = None

def get_error_handler() -> ErrorHandler:
    """Get global error handler instance"""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler
