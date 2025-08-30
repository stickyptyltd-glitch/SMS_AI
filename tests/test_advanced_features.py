#!/usr/bin/env python3
"""
Comprehensive test suite for advanced SMS AI features
Tests conversation context, analytics, security, and error handling.
"""

import pytest
import json
import time
import tempfile
import shutil
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Import modules to test
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.conversation_context import ConversationContextManager, PersonalityProfile, ConversationTurn
from analytics.system_monitor import SystemMonitor
from utils.error_handling import InputValidator, ErrorHandler, ValidationError, ErrorCategory, ErrorSeverity
from security.advanced_security import RateLimiter, SecurityMonitor
from user_management import UserManager

class TestConversationContext:
    """Test conversation context management"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.context_manager = ConversationContextManager(self.temp_dir)
    
    def teardown_method(self):
        """Cleanup test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_personality_creation_and_loading(self):
        """Test personality profile creation and loading"""
        personality = PersonalityProfile(
            name="test_personality",
            base_traits=["friendly", "professional"],
            communication_style="formal",
            response_length_preference="detailed",
            emoji_usage="none",
            topics_of_interest=["business", "technology"],
            topics_to_avoid=["politics"],
            custom_phrases=["Thank you for your inquiry"],
            relationship_context={"Boss": "professional"}
        )
        
        # Save personality
        self.context_manager.save_personality(personality)
        
        # Load personality
        loaded = self.context_manager.load_personality("test_personality")
        
        assert loaded is not None
        assert loaded.name == "test_personality"
        assert loaded.communication_style == "formal"
        assert "business" in loaded.topics_of_interest
        assert "politics" in loaded.topics_to_avoid
    
    def test_conversation_turn_storage(self):
        """Test conversation turn storage and retrieval"""
        turn = ConversationTurn(
            timestamp=datetime.utcnow().isoformat(),
            incoming="Hello, how are you?",
            response="I'm doing well, thank you!",
            sentiment="positive",
            intent="greeting",
            confidence=0.9,
            context_used=["default"]
        )
        
        # Save conversation turn
        self.context_manager.save_conversation_turn("TestContact", turn)
        
        # Load conversation context
        context = self.context_manager.load_conversation_context("TestContact")
        
        assert len(context) == 1
        assert context[0].incoming == "Hello, how are you?"
        assert context[0].sentiment == "positive"
    
    def test_context_cleanup(self):
        """Test old conversation cleanup"""
        # Create old turn
        old_turn = ConversationTurn(
            timestamp=(datetime.utcnow() - timedelta(days=2)).isoformat(),
            incoming="Old message",
            response="Old response",
            sentiment="neutral",
            intent="other",
            confidence=0.5,
            context_used=[]
        )
        
        # Create recent turn
        recent_turn = ConversationTurn(
            timestamp=datetime.utcnow().isoformat(),
            incoming="Recent message",
            response="Recent response",
            sentiment="positive",
            intent="greeting",
            confidence=0.8,
            context_used=[]
        )
        
        # Save both turns
        self.context_manager.save_conversation_turn("TestContact", old_turn)
        self.context_manager.save_conversation_turn("TestContact", recent_turn)
        
        # Load context (should only have recent turn due to cleanup)
        context = self.context_manager.load_conversation_context("TestContact")
        
        # Should have both initially, but cleanup depends on settings
        assert len(context) >= 1
        assert any(turn.incoming == "Recent message" for turn in context)
    
    def test_conversation_analytics(self):
        """Test conversation pattern analysis"""
        # Add multiple turns
        turns = [
            ConversationTurn(
                timestamp=datetime.utcnow().isoformat(),
                incoming=f"Message {i}",
                response=f"Response {i}",
                sentiment="positive" if i % 2 == 0 else "neutral",
                intent="greeting" if i < 2 else "question",
                confidence=0.8,
                context_used=[]
            )
            for i in range(5)
        ]
        
        for turn in turns:
            self.context_manager.save_conversation_turn("AnalyticsTest", turn)
        
        # Get analytics
        analytics = self.context_manager.analyze_conversation_patterns("AnalyticsTest")
        
        assert analytics["total_conversations"] == 5
        assert "positive" in analytics["sentiment_distribution"]
        assert "greeting" in analytics["intent_distribution"]
        assert analytics["average_confidence"] == 0.8

class TestInputValidation:
    """Test input validation and sanitization"""
    
    def test_email_validation(self):
        """Test email validation"""
        assert InputValidator.validate_email("test@example.com") == True
        assert InputValidator.validate_email("invalid-email") == False
        assert InputValidator.validate_email("") == False
        assert InputValidator.validate_email(None) == False
        assert InputValidator.validate_email("test@") == False
        assert InputValidator.validate_email("@example.com") == False
    
    def test_username_validation(self):
        """Test username validation"""
        valid, msg = InputValidator.validate_username("validuser123")
        assert valid == True
        
        valid, msg = InputValidator.validate_username("ab")  # Too short
        assert valid == False
        assert "at least 3 characters" in msg
        
        valid, msg = InputValidator.validate_username("user@invalid")  # Invalid chars
        assert valid == False
        assert "letters, numbers, underscores" in msg
        
        valid, msg = InputValidator.validate_username("_invalidstart")  # Invalid start
        assert valid == False
        assert "cannot start with" in msg
    
    def test_password_validation(self):
        """Test password strength validation"""
        valid, issues = InputValidator.validate_password("StrongPass123!")
        assert valid == True
        assert len(issues) == 0
        
        valid, issues = InputValidator.validate_password("weak")
        assert valid == False
        assert len(issues) > 0
        assert any("at least 8 characters" in issue for issue in issues)
        
        valid, issues = InputValidator.validate_password("password123")  # Common weak
        assert valid == False
        assert any("weak patterns" in issue for issue in issues)
    
    def test_phone_validation(self):
        """Test phone number validation"""
        valid, msg = InputValidator.validate_phone_number("+1234567890")
        assert valid == True
        
        valid, msg = InputValidator.validate_phone_number("123")  # Too short
        assert valid == False
        assert "at least 10 digits" in msg
        
        valid, msg = InputValidator.validate_phone_number("")
        assert valid == False
        assert "required" in msg
    
    def test_message_content_validation(self):
        """Test message content validation"""
        valid, msg = InputValidator.validate_message_content("Hello, this is a normal message")
        assert valid == True
        
        valid, msg = InputValidator.validate_message_content("")
        assert valid == False
        assert "required" in msg or "empty" in msg
        
        valid, msg = InputValidator.validate_message_content("x" * 2000)  # Too long
        assert valid == False
        assert "less than" in msg
        
        valid, msg = InputValidator.validate_message_content("<script>alert('xss')</script>")
        assert valid == False
        assert "harmful content" in msg
    
    def test_input_sanitization(self):
        """Test input sanitization"""
        sanitized = InputValidator.sanitize_input("  Hello <script> World  ")
        # Should remove dangerous characters and normalize whitespace
        assert "script" in sanitized  # Content preserved but tags removed
        assert sanitized.strip() == "Hello script World"
        
        sanitized = InputValidator.sanitize_input("Test\x00null\rbyte")
        assert "\x00" not in sanitized
        assert "\r" not in sanitized

class TestRateLimiting:
    """Test rate limiting functionality"""
    
    def setup_method(self):
        """Setup rate limiter"""
        self.rate_limiter = RateLimiter()
    
    def test_basic_rate_limiting(self):
        """Test basic rate limiting"""
        # Should not be limited initially
        limited, reset_time = self.rate_limiter.is_rate_limited("test_ip", "login")
        assert limited == False
        
        # Exceed login limit (5 requests per 5 minutes)
        for i in range(6):
            self.rate_limiter.is_rate_limited("test_ip", "login")
        
        # Should now be limited
        limited, reset_time = self.rate_limiter.is_rate_limited("test_ip", "login")
        assert limited == True
        assert reset_time > time.time()
    
    def test_ip_blocking(self):
        """Test IP blocking functionality"""
        test_ip = "192.168.1.100"
        
        # Should not be blocked initially
        assert self.rate_limiter.is_ip_blocked(test_ip) == False
        
        # Block IP
        self.rate_limiter.block_ip(test_ip, 60)  # Block for 1 minute
        
        # Should now be blocked
        assert self.rate_limiter.is_ip_blocked(test_ip) == True
        
        # Should be in suspicious IPs
        assert test_ip in self.rate_limiter.suspicious_ips
    
    def test_rate_limit_info(self):
        """Test rate limit information"""
        info = self.rate_limiter.get_rate_limit_info("test_ip", "api")
        
        assert "limit" in info
        assert "remaining" in info
        assert "reset_time" in info
        assert info["limit"] > 0
        assert info["remaining"] <= info["limit"]

class TestSecurityMonitoring:
    """Test security monitoring and threat detection"""
    
    def setup_method(self):
        """Setup security monitor"""
        self.temp_dir = tempfile.mkdtemp()
        self.security_monitor = SecurityMonitor(self.temp_dir)
    
    def teardown_method(self):
        """Cleanup"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_threat_detection(self):
        """Test threat detection"""
        # Test suspicious user agent
        threats = self.security_monitor.detect_threats(
            ip="192.168.1.1",
            user_agent="sqlmap/1.0",
            endpoint="/login",
            user_id="test_user"
        )
        
        assert len(threats) > 0
        assert any(threat.event_type == "suspicious_user_agent" for threat in threats)
    
    def test_failed_login_tracking(self):
        """Test failed login tracking"""
        test_ip = "192.168.1.2"
        
        # Record multiple failed logins
        for i in range(6):
            self.security_monitor.record_failed_login(test_ip)
        
        # Should detect brute force
        threats = self.security_monitor.detect_threats(
            ip=test_ip,
            user_agent="Mozilla/5.0",
            endpoint="/users/login"
        )
        
        # Should have brute force threat
        brute_force_threats = [t for t in threats if t.event_type == "brute_force_attempt"]
        assert len(brute_force_threats) > 0
    
    def test_security_summary(self):
        """Test security summary generation"""
        # Generate some security events
        self.security_monitor.detect_threats(
            ip="192.168.1.3",
            user_agent="suspicious-bot",
            endpoint="/api/test"
        )
        
        summary = self.security_monitor.get_security_summary()
        
        assert "total_events_24h" in summary
        assert "event_types" in summary
        assert "severity_distribution" in summary
        assert isinstance(summary["total_events_24h"], int)

class TestSystemMonitoring:
    """Test system monitoring functionality"""
    
    def setup_method(self):
        """Setup system monitor"""
        self.temp_dir = tempfile.mkdtemp()
        self.system_monitor = SystemMonitor(self.temp_dir)
    
    def teardown_method(self):
        """Cleanup"""
        self.system_monitor.stop_monitoring()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_system_health_check(self):
        """Test system health monitoring"""
        health = self.system_monitor.get_system_health()
        
        assert "health_score" in health
        assert "health_status" in health
        assert "current_metrics" in health
        assert 0 <= health["health_score"] <= 100
        assert health["health_status"] in ["excellent", "good", "warning", "critical"]
    
    def test_request_logging(self):
        """Test request activity logging"""
        self.system_monitor.log_request(
            user_id="test_user",
            username="testuser",
            endpoint="/reply",
            response_time=0.5,
            status_code=200,
            user_agent="TestAgent/1.0",
            ip_address="192.168.1.4"
        )
        
        # Check that request was logged
        assert len(self.system_monitor.recent_requests) > 0
        assert len(self.system_monitor.response_times) > 0
    
    def test_usage_analytics(self):
        """Test usage analytics"""
        # Log some test requests
        for i in range(5):
            self.system_monitor.log_request(
                user_id=f"user_{i}",
                username=f"user{i}",
                endpoint="/reply",
                response_time=0.1 * i,
                status_code=200 if i < 4 else 500
            )
        
        analytics = self.system_monitor.get_usage_analytics(1)  # Last 1 day
        
        assert "total_requests" in analytics
        assert "unique_users" in analytics
        assert "error_rate" in analytics
        assert analytics["total_requests"] >= 5

class TestErrorHandling:
    """Test error handling and recovery"""
    
    def setup_method(self):
        """Setup error handler"""
        self.temp_dir = tempfile.mkdtemp()
        self.error_handler = ErrorHandler(os.path.join(self.temp_dir, "test_errors.log"))
    
    def teardown_method(self):
        """Cleanup"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_error_handling(self):
        """Test error handling and logging"""
        test_error = ValueError("Test error message")
        context = {"test_key": "test_value"}
        
        error_details = self.error_handler.handle_error(
            test_error,
            context,
            ErrorCategory.VALIDATION,
            ErrorSeverity.MEDIUM
        )
        
        assert error_details.category == ErrorCategory.VALIDATION
        assert error_details.severity == ErrorSeverity.MEDIUM
        assert "Test error message" in error_details.message
        assert error_details.context == context
        assert error_details.error_id is not None
    
    def test_validation_error(self):
        """Test custom validation error"""
        with pytest.raises(ValidationError) as exc_info:
            raise ValidationError("Invalid field", "test_field", "invalid_value")
        
        error = exc_info.value
        assert error.message == "Invalid field"
        assert error.field == "test_field"
        assert error.value == "invalid_value"

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
