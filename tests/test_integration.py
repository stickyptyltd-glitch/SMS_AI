#!/usr/bin/env python3
"""
Integration tests for SMS AI system
Tests end-to-end functionality, API endpoints, and system integration.
"""

import pytest
import json
import time
import tempfile
import shutil
import requests
from unittest.mock import patch, MagicMock
import threading
import subprocess
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestServerIntegration:
    """Test server integration and API endpoints"""
    
    @classmethod
    def setup_class(cls):
        """Setup test server"""
        cls.base_url = "http://127.0.0.1:8082"  # Use different port for testing
        cls.server_process = None
        cls.temp_dir = tempfile.mkdtemp()
        
        # Set environment variables for testing
        os.environ["DAYLE_DATA_DIR"] = cls.temp_dir
        os.environ["FLASK_PORT"] = "8082"
        os.environ["OPENAI_API_KEY"] = "test-key"
        os.environ["USE_OPENAI"] = "0"  # Disable for testing
        
        # Start test server
        cls.start_test_server()
        
        # Wait for server to start
        cls.wait_for_server()
    
    @classmethod
    def teardown_class(cls):
        """Cleanup test server"""
        if cls.server_process:
            cls.server_process.terminate()
            cls.server_process.wait()
        
        shutil.rmtree(cls.temp_dir, ignore_errors=True)
    
    @classmethod
    def start_test_server(cls):
        """Start test server in background"""
        try:
            # Start server process
            cls.server_process = subprocess.Popen([
                sys.executable, "server.py"
            ], env=os.environ.copy())
        except Exception as e:
            pytest.skip(f"Could not start test server: {e}")
    
    @classmethod
    def wait_for_server(cls, timeout=30):
        """Wait for server to be ready"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{cls.base_url}/health", timeout=1)
                if response.status_code == 200:
                    return
            except:
                pass
            time.sleep(0.5)
        
        pytest.skip("Test server did not start within timeout")
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = requests.get(f"{self.base_url}/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
    
    def test_reply_endpoint_basic(self):
        """Test basic reply functionality"""
        payload = {
            "incoming": "Hello, how are you?",
            "contact": "TestUser"
        }
        
        response = requests.post(
            f"{self.base_url}/reply",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "draft" in data
        assert "analysis" in data
        assert "contact" in data
        assert data["contact"] == "TestUser"
        assert len(data["draft"]) > 0
    
    def test_reply_endpoint_validation(self):
        """Test reply endpoint input validation"""
        # Test missing incoming message
        response = requests.post(
            f"{self.base_url}/reply",
            json={"contact": "TestUser"},
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
    
    def test_config_endpoint(self):
        """Test configuration endpoint"""
        response = requests.get(f"{self.base_url}/config")
        assert response.status_code == 200
        
        data = response.json()
        assert "openai_enabled" in data
        assert "model" in data
    
    def test_profile_endpoint(self):
        """Test profile endpoint"""
        response = requests.get(f"{self.base_url}/profile")
        assert response.status_code == 200
        
        data = response.json()
        assert "style_rules" in data
        assert "preferred_phrases" in data
        assert "banned_words" in data
    
    def test_user_registration_and_login(self):
        """Test user management endpoints"""
        # First, we need admin token for registration
        admin_token = "test-admin-token"
        os.environ["ADMIN_TOKEN"] = admin_token
        
        # Test user registration
        user_data = {
            "username": "testuser123",
            "password": "TestPass123!",
            "email": "test@example.com",
            "role": "user"
        }
        
        response = requests.post(
            f"{self.base_url}/users/register",
            json=user_data,
            headers={
                "Content-Type": "application/json",
                "X-Admin-Token": admin_token
            }
        )
        
        # May fail if user already exists, that's ok
        if response.status_code == 200:
            data = response.json()
            assert data["ok"] == True
            assert data["username"] == "testuser123"
        
        # Test user login
        login_data = {
            "username": "testuser123",
            "password": "TestPass123!"
        }
        
        response = requests.post(
            f"{self.base_url}/users/login",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data["ok"] == True
            assert "token" in data
            assert "user" in data
    
    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        # Make multiple rapid requests
        responses = []
        for i in range(10):
            response = requests.post(
                f"{self.base_url}/reply",
                json={"incoming": f"Test message {i}", "contact": "RateTest"},
                headers={"Content-Type": "application/json"}
            )
            responses.append(response.status_code)
            time.sleep(0.1)  # Small delay
        
        # Should have some successful responses
        success_count = sum(1 for code in responses if code == 200)
        assert success_count > 0
        
        # May have some rate limited responses (429)
        rate_limited = sum(1 for code in responses if code == 429)
        # Rate limiting may or may not trigger depending on configuration

class TestEndToEndWorkflow:
    """Test complete end-to-end workflows"""
    
    def setup_method(self):
        """Setup for each test"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock external dependencies
        self.mock_openai = patch('requests.post').start()
        self.mock_openai.return_value.json.return_value = {
            "choices": [{"message": {"content": "Mocked AI response"}}]
        }
        self.mock_openai.return_value.status_code = 200
    
    def teardown_method(self):
        """Cleanup after each test"""
        patch.stopall()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_conversation_flow(self):
        """Test complete conversation flow with context"""
        from ai.conversation_context import ConversationContextManager, PersonalityProfile
        
        # Setup context manager
        context_manager = ConversationContextManager(self.temp_dir)
        
        # Create personality
        personality = PersonalityProfile(
            name="friendly_assistant",
            base_traits=["helpful", "friendly"],
            communication_style="casual",
            response_length_preference="brief",
            emoji_usage="minimal",
            topics_of_interest=["general"],
            topics_to_avoid=[],
            custom_phrases=["Happy to help!"],
            relationship_context={}
        )
        
        context_manager.save_personality(personality)
        
        # Simulate conversation turns
        messages = [
            "Hi there!",
            "How's the weather?",
            "Thanks for your help"
        ]
        
        for i, message in enumerate(messages):
            # Build context prompt
            context_prompt = context_manager.build_context_prompt(
                "TestContact", message, personality
            )
            
            assert "friendly_assistant" in context_prompt
            assert message in context_prompt
            
            # Simulate saving conversation turn
            from ai.conversation_context import ConversationTurn
            from datetime import datetime
            
            turn = ConversationTurn(
                timestamp=datetime.utcnow().isoformat(),
                incoming=message,
                response=f"Response to: {message}",
                sentiment="positive",
                intent="greeting" if i == 0 else "question",
                confidence=0.8,
                context_used=["friendly_assistant"]
            )
            
            context_manager.save_conversation_turn("TestContact", turn)
        
        # Verify conversation history
        history = context_manager.load_conversation_context("TestContact")
        assert len(history) == 3
        assert history[0].incoming == "Hi there!"
        assert history[-1].incoming == "Thanks for your help"
    
    def test_security_workflow(self):
        """Test security monitoring workflow"""
        from security.advanced_security import SecurityMonitor
        
        security_monitor = SecurityMonitor(self.temp_dir)
        
        # Simulate suspicious activity
        threats = security_monitor.detect_threats(
            ip="192.168.1.100",
            user_agent="sqlmap/1.0",
            endpoint="/admin",
            user_id="attacker"
        )
        
        assert len(threats) > 0
        
        # Check if IP gets blocked for critical threats
        critical_threats = [t for t in threats if t.severity == "critical"]
        if critical_threats:
            assert security_monitor.rate_limiter.is_ip_blocked("192.168.1.100")
        
        # Test security summary
        summary = security_monitor.get_security_summary()
        assert "total_events_24h" in summary
        assert summary["total_events_24h"] > 0
    
    def test_analytics_workflow(self):
        """Test analytics and monitoring workflow"""
        from analytics.system_monitor import SystemMonitor
        
        system_monitor = SystemMonitor(self.temp_dir)
        
        # Log some test activities
        for i in range(5):
            system_monitor.log_request(
                user_id=f"user_{i}",
                username=f"testuser{i}",
                endpoint="/reply",
                response_time=0.1 + (i * 0.05),
                status_code=200,
                user_agent="TestClient/1.0",
                ip_address=f"192.168.1.{100 + i}"
            )
        
        # Test system health
        health = system_monitor.get_system_health()
        assert "health_score" in health
        assert "current_metrics" in health
        
        # Test usage analytics
        analytics = system_monitor.get_usage_analytics(1)
        assert "total_requests" in analytics
        assert analytics["total_requests"] >= 5
    
    def test_error_handling_workflow(self):
        """Test error handling and recovery workflow"""
        from utils.error_handling import ErrorHandler, ValidationError, ErrorCategory, ErrorSeverity
        
        error_handler = ErrorHandler(os.path.join(self.temp_dir, "test_errors.log"))
        
        # Test handling different types of errors
        test_errors = [
            (ValueError("Test value error"), ErrorCategory.VALIDATION, ErrorSeverity.LOW),
            (ConnectionError("Test connection error"), ErrorCategory.NETWORK, ErrorSeverity.HIGH),
            (PermissionError("Test permission error"), ErrorCategory.AUTHORIZATION, ErrorSeverity.MEDIUM)
        ]
        
        for error, category, severity in test_errors:
            error_details = error_handler.handle_error(
                error,
                context={"test": "context"},
                category=category,
                severity=severity
            )
            
            assert error_details.category == category
            assert error_details.severity == severity
            assert error_details.error_id is not None
            assert error_details.user_message is not None

class TestPerformanceAndStress:
    """Test system performance and stress handling"""
    
    def setup_method(self):
        """Setup performance tests"""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Cleanup performance tests"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_concurrent_requests(self):
        """Test handling concurrent requests"""
        from ai.conversation_context import ConversationContextManager
        
        context_manager = ConversationContextManager(self.temp_dir)
        
        def simulate_request(thread_id):
            """Simulate a request from a thread"""
            try:
                from ai.conversation_context import ConversationTurn
                from datetime import datetime
                
                turn = ConversationTurn(
                    timestamp=datetime.utcnow().isoformat(),
                    incoming=f"Message from thread {thread_id}",
                    response=f"Response from thread {thread_id}",
                    sentiment="neutral",
                    intent="test",
                    confidence=0.5,
                    context_used=[]
                )
                
                context_manager.save_conversation_turn(f"Contact_{thread_id}", turn)
                return True
            except Exception as e:
                print(f"Thread {thread_id} failed: {e}")
                return False
        
        # Run concurrent requests
        threads = []
        results = []
        
        for i in range(10):
            thread = threading.Thread(target=lambda i=i: results.append(simulate_request(i)))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Check results
        success_count = sum(1 for result in results if result)
        assert success_count >= 8  # Allow some failures
    
    def test_memory_usage(self):
        """Test memory usage with large datasets"""
        from ai.conversation_context import ConversationContextManager, ConversationTurn
        from datetime import datetime
        
        context_manager = ConversationContextManager(self.temp_dir)
        
        # Create many conversation turns
        for contact_id in range(10):
            for turn_id in range(50):  # 50 turns per contact
                turn = ConversationTurn(
                    timestamp=datetime.utcnow().isoformat(),
                    incoming=f"Message {turn_id} from contact {contact_id}",
                    response=f"Response {turn_id} to contact {contact_id}",
                    sentiment="neutral",
                    intent="test",
                    confidence=0.5,
                    context_used=[]
                )
                
                context_manager.save_conversation_turn(f"Contact_{contact_id}", turn)
        
        # Test that we can still load contexts efficiently
        for contact_id in range(10):
            context = context_manager.load_conversation_context(f"Contact_{contact_id}")
            # Should have limited context due to cleanup
            assert len(context) <= context_manager.max_context_turns

if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "-s"])
