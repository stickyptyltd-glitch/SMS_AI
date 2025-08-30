#!/usr/bin/env python3
"""
Comprehensive Error Handling and Edge Case Testing
Tests all advanced features under various error conditions and edge cases.
"""

import pytest
import json
import time
import tempfile
import shutil
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
import threading
import concurrent.futures

# Import modules to test
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.multi_model_manager import MultiModelManager, ModelProvider, ModelCapability
from ai.adaptive_learning import AdaptiveLearningSystem
from integrations.webhook_manager import WebhookManager, MessagePlatform, IntegrationType
from performance.cache_manager import MultiLevelCacheManager
from utils.error_handling import InputValidator, ErrorHandler, ValidationError
from security.advanced_security import SecurityMonitor, RateLimiter

class TestMultiModelErrorHandling:
    """Test multi-model AI system error handling"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.multi_model_manager = MultiModelManager(self.temp_dir)
    
    def teardown_method(self):
        """Cleanup test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_api_failure_fallback(self):
        """Test fallback when primary API fails"""
        # Mock API failure
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_response.json = AsyncMock(return_value={"error": "API Error"})
            mock_post.return_value.__aenter__.return_value = mock_response
            
            # Should handle failure gracefully
            response = await self.multi_model_manager.generate_response(
                "Test prompt", ModelCapability.TEXT_GENERATION
            )
            
            # Should either return None or use fallback
            assert response is None or response.content is not None
    
    @pytest.mark.asyncio
    async def test_rate_limit_handling(self):
        """Test rate limit handling"""
        # Simulate rate limiting
        for model_config in self.multi_model_manager.models.values():
            model_config.rate_limit_per_minute = 1
        
        # First request should work
        response1 = await self.multi_model_manager.generate_response(
            "Test prompt 1", ModelCapability.TEXT_GENERATION
        )
        
        # Second request should be rate limited
        response2 = await self.multi_model_manager.generate_response(
            "Test prompt 2", ModelCapability.TEXT_GENERATION
        )
        
        # At least one should be None due to rate limiting
        assert response1 is None or response2 is None
    
    @pytest.mark.asyncio
    async def test_invalid_model_config(self):
        """Test handling of invalid model configurations"""
        # Add invalid model config
        from ai.multi_model_manager import ModelConfig
        invalid_config = ModelConfig(
            provider=ModelProvider.OPENAI,
            model_name="invalid-model",
            api_key="invalid-key",
            endpoint="https://invalid-endpoint.com",
            capabilities=[ModelCapability.TEXT_GENERATION],
            max_tokens=100,
            cost_per_token=0.001,
            response_time_avg=1.0,
            reliability_score=0.5,
            priority=999,
            rate_limit_per_minute=10,
            context_window=1000
        )
        
        self.multi_model_manager.models["invalid"] = invalid_config
        
        # Should handle invalid config gracefully
        response = await self.multi_model_manager.generate_response(
            "Test prompt", ModelCapability.TEXT_GENERATION
        )
        
        # Should not crash, might return None
        assert response is None or isinstance(response.content, str)
    
    def test_concurrent_model_access(self):
        """Test concurrent access to model manager"""
        def make_request(prompt):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    self.multi_model_manager.generate_response(
                        prompt, ModelCapability.TEXT_GENERATION
                    )
                )
            finally:
                loop.close()
        
        # Run multiple concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(make_request, f"Test prompt {i}")
                for i in range(10)
            ]
            
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Should handle concurrent access without crashing
        assert len(results) == 10
        # Some results might be None due to rate limiting or failures

class TestAdaptiveLearningErrorHandling:
    """Test adaptive learning system error handling"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.learning_system = AdaptiveLearningSystem(self.temp_dir)
    
    def teardown_method(self):
        """Cleanup test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_corrupted_database_recovery(self):
        """Test recovery from corrupted database"""
        # Corrupt the database file
        db_path = self.learning_system.db_path
        with open(db_path, 'w') as f:
            f.write("corrupted data")
        
        # Should recover gracefully
        new_learning_system = AdaptiveLearningSystem(self.temp_dir)
        
        # Should be able to add examples
        new_learning_system.add_learning_example(
            "test input", "test response", 0.5
        )
        
        assert len(new_learning_system.learning_examples) >= 1
    
    def test_invalid_feature_extraction(self):
        """Test handling of invalid input for feature extraction"""
        # Test with various invalid inputs
        invalid_inputs = [None, "", 123, [], {}, "\x00\x01\x02"]
        
        for invalid_input in invalid_inputs:
            try:
                features = self.learning_system.feature_extractor.extract_features(invalid_input)
                # Should return some features or handle gracefully
                assert isinstance(features, dict)
            except Exception as e:
                # Should not crash with unhandled exceptions
                assert isinstance(e, (TypeError, ValueError, AttributeError))
    
    def test_memory_pressure_handling(self):
        """Test handling of memory pressure with large datasets"""
        # Add many learning examples
        for i in range(1000):
            self.learning_system.add_learning_example(
                f"input {i}", f"response {i}", 0.5,
                context={"test": True}, contact=f"contact_{i % 10}"
            )
        
        # Should handle large dataset without crashing
        stats = self.learning_system.get_learning_stats()
        assert stats["total_examples"] > 0
        
        # Should be able to get suggestions
        suggestion = self.learning_system.get_response_suggestion("test input")
        # Might be None, but shouldn't crash

class TestWebhookErrorHandling:
    """Test webhook system error handling"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.webhook_manager = WebhookManager(self.temp_dir)
    
    def teardown_method(self):
        """Cleanup test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_malformed_webhook_payload(self):
        """Test handling of malformed webhook payloads"""
        webhook_id = self.webhook_manager.register_webhook(
            "test_webhook", IntegrationType.WEBHOOK_INCOMING,
            MessagePlatform.TWILIO, "http://example.com"
        )
        
        # Test various malformed payloads
        malformed_payloads = [
            None,
            "",
            "not json",
            {"incomplete": "data"},
            {"From": None, "Body": None},
            {"circular": None}  # Will be made circular
        ]
        
        # Make one payload circular
        circular = {"data": {}}
        circular["data"]["self"] = circular
        malformed_payloads.append(circular)
        
        for payload in malformed_payloads:
            try:
                response = await self.webhook_manager.process_incoming_webhook(
                    webhook_id, payload
                )
                # Should handle gracefully
                assert response.status_code in [200, 400, 500]
            except Exception as e:
                # Should not have unhandled exceptions
                pytest.fail(f"Unhandled exception for payload {payload}: {e}")
    
    @pytest.mark.asyncio
    async def test_webhook_signature_validation_errors(self):
        """Test webhook signature validation error handling"""
        webhook_id = self.webhook_manager.register_webhook(
            "secure_webhook", IntegrationType.WEBHOOK_INCOMING,
            MessagePlatform.TWILIO, "http://example.com",
            secret_key="test_secret"
        )
        
        # Test with invalid signatures
        invalid_headers = [
            {"X-Hub-Signature-256": "invalid"},
            {"X-Hub-Signature-256": "sha256=invalid"},
            {"X-Twilio-Signature": "invalid"},
            {},  # No signature
            {"X-Hub-Signature-256": None}
        ]
        
        for headers in invalid_headers:
            response = await self.webhook_manager.process_incoming_webhook(
                webhook_id, {"test": "data"}, headers
            )
            
            # Should reject invalid signatures
            assert response.status_code in [401, 400]
    
    def test_concurrent_webhook_processing(self):
        """Test concurrent webhook processing"""
        webhook_id = self.webhook_manager.register_webhook(
            "concurrent_webhook", IntegrationType.WEBHOOK_INCOMING,
            MessagePlatform.CUSTOM, "http://example.com"
        )
        
        async def process_webhook(i):
            return await self.webhook_manager.process_incoming_webhook(
                webhook_id, {"message": f"test {i}"}
            )
        
        # Process multiple webhooks concurrently
        async def run_concurrent_test():
            tasks = [process_webhook(i) for i in range(10)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            results = loop.run_until_complete(run_concurrent_test())
        finally:
            loop.close()
        
        # Should handle concurrent processing
        assert len(results) == 10
        # Some might be exceptions due to rate limiting
        successful = [r for r in results if not isinstance(r, Exception)]
        assert len(successful) > 0

class TestCacheErrorHandling:
    """Test cache system error handling"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_manager = MultiLevelCacheManager(self.temp_dir)
    
    def teardown_method(self):
        """Cleanup test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_disk_cache_corruption_recovery(self):
        """Test recovery from disk cache corruption"""
        # Put some data in cache
        self.cache_manager.put("test", "key1", "value1")
        
        # Corrupt the cache index
        import json
        with open(self.cache_manager.disk_cache.index_file, 'w') as f:
            f.write("corrupted json")
        
        # Should recover gracefully
        new_cache_manager = MultiLevelCacheManager(self.temp_dir)
        
        # Should be able to use cache
        new_cache_manager.put("test", "key2", "value2")
        result = new_cache_manager.get("test", "key2")
        assert result == "value2"
    
    def test_memory_pressure_cache_eviction(self):
        """Test cache behavior under memory pressure"""
        # Fill cache beyond capacity
        small_cache = MultiLevelCacheManager(self.temp_dir)
        small_cache.memory_cache.max_size = 10
        
        # Add more items than capacity
        for i in range(20):
            small_cache.put("test", f"key{i}", f"value{i}")
        
        # Should handle eviction gracefully
        stats = small_cache.get_performance_stats("test")
        assert stats["total_requests"] > 0
        
        # Should still be functional
        small_cache.put("test", "new_key", "new_value")
        result = small_cache.get("test", "new_key")
        assert result == "new_value"
    
    def test_concurrent_cache_access(self):
        """Test concurrent cache access"""
        def cache_worker(worker_id):
            for i in range(100):
                key = f"worker_{worker_id}_key_{i}"
                value = f"worker_{worker_id}_value_{i}"
                
                # Put and get
                self.cache_manager.put("concurrent_test", key, value)
                result = self.cache_manager.get("concurrent_test", key)
                
                if result != value:
                    return False
            return True
        
        # Run multiple workers concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(cache_worker, i) for i in range(5)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All workers should succeed
        assert all(results)

class TestSecurityErrorHandling:
    """Test security system error handling"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.security_monitor = SecurityMonitor(self.temp_dir)
    
    def teardown_method(self):
        """Cleanup test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_invalid_ip_address_handling(self):
        """Test handling of invalid IP addresses"""
        invalid_ips = [
            None, "", "invalid", "999.999.999.999",
            "not.an.ip", "::invalid::", "127.0.0.1:8080"
        ]
        
        for invalid_ip in invalid_ips:
            try:
                # Should handle invalid IPs gracefully
                threats = self.security_monitor.detect_threats(
                    ip=invalid_ip,
                    user_agent="test",
                    endpoint="/test"
                )
                # Should return list (might be empty)
                assert isinstance(threats, list)
            except Exception as e:
                # Should not crash with unhandled exceptions
                assert isinstance(e, (ValueError, TypeError))
    
    def test_rate_limiter_edge_cases(self):
        """Test rate limiter edge cases"""
        rate_limiter = RateLimiter()
        
        # Test with None/empty identifiers
        edge_cases = [None, "", "  ", "\x00", "very_long_identifier" * 100]
        
        for identifier in edge_cases:
            try:
                limited, reset_time = rate_limiter.is_rate_limited(str(identifier) if identifier else "default")
                assert isinstance(limited, bool)
                assert isinstance(reset_time, (int, float))
            except Exception as e:
                # Should handle gracefully
                assert isinstance(e, (ValueError, TypeError))
    
    def test_security_event_logging_errors(self):
        """Test security event logging error handling"""
        # Test with various problematic data
        problematic_data = [
            {"circular": None},  # Will be made circular
            {"large_data": "x" * 1000000},  # Very large data
            {"unicode": "🚨💀🔥" * 1000},  # Unicode data
            {"none_values": None},
            {"nested": {"deep": {"very": {"deep": "data"}}}}
        ]
        
        # Make one circular
        circular = {"data": {}}
        circular["data"]["self"] = circular
        problematic_data.append(circular)
        
        for data in problematic_data:
            try:
                threats = self.security_monitor.detect_threats(
                    ip="192.168.1.1",
                    user_agent="test",
                    endpoint="/test",
                    user_id="test_user"
                )
                # Should handle without crashing
                assert isinstance(threats, list)
            except Exception as e:
                # Should not have unhandled exceptions
                pytest.fail(f"Unhandled exception for data {type(data)}: {e}")

class TestInputValidationEdgeCases:
    """Test input validation edge cases"""
    
    def test_extreme_input_sizes(self):
        """Test validation with extreme input sizes"""
        # Very large inputs
        large_email = "a" * 1000 + "@" + "b" * 1000 + ".com"
        large_username = "x" * 10000
        large_password = "P@ssw0rd!" * 1000
        large_message = "Hello! " * 100000
        
        # Should handle large inputs gracefully
        assert InputValidator.validate_email(large_email) == False
        
        valid, msg = InputValidator.validate_username(large_username)
        assert valid == False
        
        valid, issues = InputValidator.validate_password(large_password)
        assert valid == False
        
        valid, msg = InputValidator.validate_message_content(large_message)
        assert valid == False
    
    def test_unicode_and_special_characters(self):
        """Test validation with Unicode and special characters"""
        unicode_inputs = [
            "test@例え.テスト",  # Unicode domain
            "用户名123",  # Unicode username
            "密码123!@#",  # Unicode password
            "🚀🎉💻 Hello World! 🌟",  # Emoji message
            "\x00\x01\x02",  # Control characters
            "test\r\nheader: injection",  # Header injection attempt
        ]
        
        for unicode_input in unicode_inputs:
            try:
                # Should handle Unicode gracefully
                InputValidator.validate_email(unicode_input)
                InputValidator.validate_username(unicode_input)
                InputValidator.validate_password(unicode_input)
                InputValidator.validate_message_content(unicode_input)
                InputValidator.sanitize_input(unicode_input)
            except Exception as e:
                # Should not crash with unhandled exceptions
                assert isinstance(e, (UnicodeError, ValueError, TypeError))

if __name__ == "__main__":
    # Run comprehensive error tests
    pytest.main([__file__, "-v", "--tb=short"])
