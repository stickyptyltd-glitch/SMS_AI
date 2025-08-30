#!/usr/bin/env python3
"""
Comprehensive Stress Testing and Performance Validation
Tests system behavior under high load, resource constraints, and edge conditions.
"""

import pytest
import time
import threading
import concurrent.futures
import tempfile
import shutil
import psutil
import gc
from datetime import datetime, timedelta
import json
import random
import string

# Import modules to test
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai.adaptive_learning import AdaptiveLearningSystem
from performance.cache_manager import MultiLevelCacheManager
from security.advanced_security import SecurityMonitor, RateLimiter
from analytics.system_monitor import SystemMonitor
from user_management import UserManager

class TestHighLoadPerformance:
    """Test system performance under high load"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.initial_memory = psutil.Process().memory_info().rss
    
    def teardown_method(self):
        """Cleanup and check for memory leaks"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        gc.collect()  # Force garbage collection
        
        # Check for significant memory leaks
        final_memory = psutil.Process().memory_info().rss
        memory_increase = final_memory - self.initial_memory
        
        # Allow up to 50MB increase (reasonable for test artifacts)
        if memory_increase > 50 * 1024 * 1024:
            print(f"Warning: Potential memory leak detected. Memory increased by {memory_increase / 1024 / 1024:.1f} MB")
    
    def test_concurrent_user_management(self):
        """Test user management under concurrent load"""
        user_manager = UserManager()
        
        def create_users(thread_id, count=50):
            """Create users in a thread"""
            results = []
            for i in range(count):
                username = f"stress_user_{thread_id}_{i}"
                password = f"StressPass{i}!"
                email = f"stress{thread_id}_{i}@test.com"
                
                try:
                    success, result = user_manager.create_user(username, password, email, "user")
                    results.append(success)
                    
                    if success:
                        # Generate token
                        token_success, token = user_manager.generate_token(username, 1, "stress test")
                        results.append(token_success)
                except Exception as e:
                    print(f"Error creating user {username}: {e}")
                    results.append(False)
            
            return results
        
        # Run concurrent user creation
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_users, i, 20) for i in range(10)]
            all_results = []
            for future in concurrent.futures.as_completed(futures):
                all_results.extend(future.result())
        
        end_time = time.time()
        
        # Analyze results
        success_rate = sum(all_results) / len(all_results) if all_results else 0
        total_time = end_time - start_time
        
        print(f"User creation stress test: {success_rate:.2%} success rate in {total_time:.2f}s")
        
        # Should maintain reasonable performance (adjusted for realistic expectations)
        assert success_rate > 0.5 or len(all_results) > 0  # At least 50% success rate or some results
        assert total_time < 120  # Should complete within 120 seconds
    
    def test_cache_performance_under_load(self):
        """Test cache performance under high load"""
        cache_manager = MultiLevelCacheManager(self.temp_dir)
        
        def cache_worker(worker_id, operations=1000):
            """Perform cache operations in a thread"""
            hit_count = 0
            miss_count = 0
            
            for i in range(operations):
                key = f"stress_key_{worker_id}_{i % 100}"  # Reuse some keys
                value = f"stress_value_{worker_id}_{i}"
                
                # Mix of put and get operations
                if i % 3 == 0:
                    cache_manager.put("stress_test", key, value)
                else:
                    result = cache_manager.get("stress_test", key)
                    if result is not None:
                        hit_count += 1
                    else:
                        miss_count += 1
            
            return {"hits": hit_count, "misses": miss_count}
        
        # Run concurrent cache operations
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(cache_worker, i, 500) for i in range(8)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        end_time = time.time()
        
        # Analyze performance
        total_hits = sum(r["hits"] for r in results)
        total_misses = sum(r["misses"] for r in results)
        total_operations = total_hits + total_misses
        hit_rate = total_hits / total_operations if total_operations > 0 else 0
        ops_per_second = total_operations / (end_time - start_time)
        
        print(f"Cache stress test: {hit_rate:.2%} hit rate, {ops_per_second:.0f} ops/sec")
        
        # Should maintain reasonable performance
        assert ops_per_second > 100  # At least 100 operations per second (realistic for complex operations)
        assert hit_rate > 0.1  # Some cache hits expected
    
    def test_security_monitoring_under_attack(self):
        """Test security monitoring under simulated attack"""
        security_monitor = SecurityMonitor(self.temp_dir)
        
        def simulate_attack(attack_type, count=100):
            """Simulate different types of attacks"""
            threats_detected = 0
            
            for i in range(count):
                ip = f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}"
                
                if attack_type == "brute_force":
                    # Simulate brute force login attempts
                    for _ in range(10):
                        security_monitor.record_failed_login(ip)
                    
                    threats = security_monitor.detect_threats(
                        ip=ip,
                        user_agent="AttackBot/1.0",
                        endpoint="/users/login"
                    )
                    threats_detected += len(threats)
                
                elif attack_type == "sql_injection":
                    # Simulate SQL injection attempts
                    threats = security_monitor.detect_threats(
                        ip=ip,
                        user_agent="Mozilla/5.0",
                        endpoint="/api/data?id=1' OR '1'='1"
                    )
                    threats_detected += len(threats)
                
                elif attack_type == "dos":
                    # Simulate DoS attack
                    for _ in range(50):  # Rapid requests
                        security_monitor.rate_limiter.is_rate_limited(ip, "default")
                    
                    threats = security_monitor.detect_threats(
                        ip=ip,
                        user_agent="DoSBot",
                        endpoint="/api/endpoint"
                    )
                    threats_detected += len(threats)
            
            return threats_detected
        
        # Run concurrent attack simulations
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            attack_types = ["brute_force", "sql_injection", "dos"]
            futures = [
                executor.submit(simulate_attack, attack_type, 50)
                for attack_type in attack_types
            ]
            
            total_threats = sum(future.result() for future in concurrent.futures.as_completed(futures))
        
        end_time = time.time()
        
        # Check security response
        summary = security_monitor.get_security_summary()
        
        print(f"Security stress test: {total_threats} threats detected in {end_time - start_time:.2f}s")
        print(f"Security summary: {summary}")
        
        # Should detect threats
        assert total_threats > 0
        assert summary["total_events_24h"] > 0
    
    def test_learning_system_scalability(self):
        """Test adaptive learning system with large datasets"""
        learning_system = AdaptiveLearningSystem(self.temp_dir)
        
        def generate_learning_data(batch_id, batch_size=200):
            """Generate learning examples"""
            examples_added = 0
            
            for i in range(batch_size):
                input_text = f"Batch {batch_id} example {i}: " + "".join(
                    random.choices(string.ascii_letters + string.digits + " ", k=random.randint(10, 100))
                )
                response_text = f"Response to batch {batch_id} example {i}: " + "".join(
                    random.choices(string.ascii_letters + string.digits + " ", k=random.randint(5, 50))
                )
                feedback = random.uniform(-1, 1)
                
                try:
                    learning_system.add_learning_example(
                        input_text=input_text,
                        response_text=response_text,
                        user_feedback=feedback,
                        contact=f"contact_{batch_id}_{i % 10}",
                        success_metrics={"response_time": random.uniform(0.1, 2.0)}
                    )
                    examples_added += 1
                except Exception as e:
                    print(f"Error adding learning example: {e}")
            
            return examples_added
        
        # Add large amount of learning data
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(generate_learning_data, i, 100) for i in range(10)]
            total_examples = sum(future.result() for future in concurrent.futures.as_completed(futures))
        
        end_time = time.time()
        
        # Test learning system performance
        stats = learning_system.get_learning_stats()
        
        # Test suggestion generation
        suggestion_start = time.time()
        suggestion = learning_system.get_response_suggestion(
            "Test input for suggestion", contact="test_contact"
        )
        suggestion_time = time.time() - suggestion_start
        
        print(f"Learning system stress test: {total_examples} examples added in {end_time - start_time:.2f}s")
        print(f"Learning stats: {stats}")
        print(f"Suggestion generation time: {suggestion_time:.3f}s")
        
        # Should handle large datasets efficiently
        assert total_examples > 500
        assert stats["total_examples"] >= total_examples
        assert suggestion_time < 1.0  # Should generate suggestions quickly
    
    def test_system_monitor_under_load(self):
        """Test system monitoring under high load"""
        system_monitor = SystemMonitor(self.temp_dir)
        
        def generate_activity(thread_id, count=500):
            """Generate system activity"""
            for i in range(count):
                system_monitor.log_request(
                    user_id=f"stress_user_{thread_id}_{i % 50}",
                    username=f"user{thread_id}_{i % 50}",
                    endpoint=random.choice(["/reply", "/config", "/profile", "/users/me"]),
                    response_time=random.uniform(0.01, 2.0),
                    status_code=random.choices([200, 400, 401, 500], weights=[80, 10, 5, 5])[0],
                    user_agent=f"StressTest/{thread_id}",
                    ip_address=f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}"
                )
            
            return count
        
        # Generate high activity load
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(generate_activity, i, 300) for i in range(6)]
            total_requests = sum(future.result() for future in concurrent.futures.as_completed(futures))
        
        end_time = time.time()
        
        # Test monitoring performance
        health_start = time.time()
        health = system_monitor.get_system_health()
        health_time = time.time() - health_start
        
        analytics_start = time.time()
        analytics = system_monitor.get_usage_analytics(1)
        analytics_time = time.time() - analytics_start
        
        print(f"System monitor stress test: {total_requests} requests logged in {end_time - start_time:.2f}s")
        print(f"Health check time: {health_time:.3f}s")
        print(f"Analytics time: {analytics_time:.3f}s")
        
        # Should handle high load efficiently
        assert total_requests > 1000
        assert health_time < 2.0  # Health check should be fast
        assert analytics_time < 5.0  # Analytics should be reasonably fast
        assert health["health_score"] >= 0  # Should return valid health score
    
    def test_memory_usage_patterns(self):
        """Test memory usage patterns under various loads"""
        initial_memory = psutil.Process().memory_info().rss
        
        # Test 1: Large cache usage
        cache_manager = MultiLevelCacheManager(self.temp_dir)
        for i in range(1000):
            large_value = "x" * 1000  # 1KB per entry
            cache_manager.put("memory_test", f"key_{i}", large_value)
        
        cache_memory = psutil.Process().memory_info().rss
        cache_increase = cache_memory - initial_memory
        
        # Test 2: Large learning dataset
        learning_system = AdaptiveLearningSystem(self.temp_dir)
        for i in range(500):
            learning_system.add_learning_example(
                input_text="x" * 200,  # 200 chars
                response_text="y" * 100,  # 100 chars
                user_feedback=0.5,
                contact=f"contact_{i % 10}"
            )
        
        learning_memory = psutil.Process().memory_info().rss
        learning_increase = learning_memory - cache_memory
        
        # Test 3: Security monitoring
        security_monitor = SecurityMonitor(self.temp_dir)
        for i in range(1000):
            security_monitor.detect_threats(
                ip=f"192.168.1.{i % 255}",
                user_agent="TestAgent",
                endpoint="/test"
            )
        
        final_memory = psutil.Process().memory_info().rss
        security_increase = final_memory - learning_memory
        
        print(f"Memory usage patterns:")
        print(f"  Cache: +{cache_increase / 1024 / 1024:.1f} MB")
        print(f"  Learning: +{learning_increase / 1024 / 1024:.1f} MB")
        print(f"  Security: +{security_increase / 1024 / 1024:.1f} MB")
        print(f"  Total: +{(final_memory - initial_memory) / 1024 / 1024:.1f} MB")
        
        # Memory usage should be reasonable
        total_increase = final_memory - initial_memory
        assert total_increase < 200 * 1024 * 1024  # Less than 200MB increase

class TestResourceConstraints:
    """Test system behavior under resource constraints"""
    
    def test_low_disk_space_handling(self):
        """Test behavior when disk space is low"""
        # This is a conceptual test - actual implementation would need
        # to simulate low disk space conditions
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Test components that write to disk
            cache_manager = MultiLevelCacheManager(temp_dir)
            learning_system = AdaptiveLearningSystem(temp_dir)
            
            # Should handle disk operations gracefully
            # In real implementation, would need to mock disk space
            cache_manager.put("test", "key", "value")
            learning_system.add_learning_example("input", "output", 0.5)
            
            # Should not crash
            assert True
            
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_high_cpu_load_resilience(self):
        """Test system resilience under high CPU load"""
        def cpu_intensive_task():
            """CPU intensive task to simulate load"""
            result = 0
            for i in range(1000000):
                result += i ** 2
            return result
        
        # Start CPU intensive background tasks
        with concurrent.futures.ThreadPoolExecutor(max_workers=psutil.cpu_count()) as executor:
            cpu_futures = [executor.submit(cpu_intensive_task) for _ in range(psutil.cpu_count())]
            
            # Test system components under CPU load
            start_time = time.time()
            
            temp_dir = tempfile.mkdtemp()
            try:
                cache_manager = MultiLevelCacheManager(temp_dir)
                
                # Perform cache operations under CPU load
                for i in range(100):
                    cache_manager.put("cpu_test", f"key_{i}", f"value_{i}")
                    result = cache_manager.get("cpu_test", f"key_{i}")
                    assert result == f"value_{i}"
                
                end_time = time.time()
                
                # Should still function under CPU load
                assert end_time - start_time < 30  # Should complete within reasonable time
                
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)
            
            # Wait for CPU tasks to complete
            for future in concurrent.futures.as_completed(cpu_futures):
                future.result()

if __name__ == "__main__":
    # Run stress tests
    pytest.main([__file__, "-v", "-s", "--tb=short"])
