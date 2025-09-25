#!/usr/bin/env python3
"""
Test suite for health checker
"""

import pytest
import asyncio
import os
from unittest.mock import patch, MagicMock, AsyncMock
import sys
from pathlib import Path
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.health_checker import HealthChecker, get_system_health


class TestHealthChecker:
    """Test cases for HealthChecker class"""

    def setup_method(self):
        """Setup test environment"""
        self.health_checker = HealthChecker()

    @pytest.mark.asyncio
    async def test_check_openai_service_healthy(self):
        """Test OpenAI service health check - healthy"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "data": [{"id": "gpt-3.5-turbo"}]
            })
            mock_get.return_value.__aenter__.return_value = mock_response

            result = await self.health_checker.check_openai()

            assert result['status'] == 'healthy'
            assert result['service'] == 'openai'
            assert 'response_time' in result
            assert result['details']['models_available'] > 0

    @pytest.mark.asyncio
    async def test_check_openai_service_unhealthy(self):
        """Test OpenAI service health check - unhealthy"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = Exception("Connection failed")

            result = await self.health_checker.check_openai()

            assert result['status'] == 'unhealthy'
            assert result['service'] == 'openai'
            assert 'error' in result
            assert 'Connection failed' in result['error']

    @pytest.mark.asyncio
    async def test_check_ollama_service_healthy(self):
        """Test Ollama service health check - healthy"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "models": [{"name": "llama3"}]
            })
            mock_get.return_value.__aenter__.return_value = mock_response

            with patch.dict(os.environ, {'OLLAMA_URL': 'http://localhost:11434'}):
                result = await self.health_checker.check_ollama()

                assert result['status'] == 'healthy'
                assert result['service'] == 'ollama'
                assert result['details']['models_available'] == 1

    @pytest.mark.asyncio
    async def test_check_ollama_service_disabled(self):
        """Test Ollama service health check - disabled"""
        with patch.dict(os.environ, {'OLLAMA_DISABLE': '1'}):
            result = await self.health_checker.check_ollama()

            assert result['status'] == 'disabled'
            assert result['service'] == 'ollama'

    @pytest.mark.asyncio
    async def test_check_redis_service_healthy(self):
        """Test Redis service health check - healthy"""
        with patch('redis.asyncio.from_url') as mock_redis:
            mock_client = AsyncMock()
            mock_client.ping.return_value = True
            mock_client.info.return_value = {'redis_version': '7.0.0'}
            mock_redis.return_value = mock_client

            with patch.dict(os.environ, {'REDIS_URL': 'redis://localhost:6379'}):
                result = await self.health_checker.check_redis()

                assert result['status'] == 'healthy'
                assert result['service'] == 'redis'
                assert result['details']['version'] == '7.0.0'

    @pytest.mark.asyncio
    async def test_check_twilio_service_healthy(self):
        """Test Twilio service health check - healthy"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "account_sid": "AC123",
                "status": "active"
            })
            mock_get.return_value.__aenter__.return_value = mock_response

            with patch.dict(os.environ, {
                'TWILIO_ACCOUNT_SID': 'AC123',
                'TWILIO_AUTH_TOKEN': 'token123'
            }):
                result = await self.health_checker.check_twilio()

                assert result['status'] == 'healthy'
                assert result['service'] == 'twilio'

    @pytest.mark.asyncio
    async def test_check_facebook_service_healthy(self):
        """Test Facebook service health check - healthy"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "id": "page123",
                "name": "Test Page"
            })
            mock_get.return_value.__aenter__.return_value = mock_response

            with patch.dict(os.environ, {
                'FB_PAGE_TOKEN': 'token123'
            }):
                result = await self.health_checker.check_facebook()

                assert result['status'] == 'healthy'
                assert result['service'] == 'facebook'

    @pytest.mark.asyncio
    async def test_check_all_services(self):
        """Test checking all services at once"""
        with patch.object(self.health_checker, 'check_openai') as mock_openai, \
             patch.object(self.health_checker, 'check_ollama') as mock_ollama, \
             patch.object(self.health_checker, 'check_redis') as mock_redis, \
             patch.object(self.health_checker, 'check_twilio') as mock_twilio, \
             patch.object(self.health_checker, 'check_facebook') as mock_facebook:

            mock_openai.return_value = {'status': 'healthy', 'service': 'openai'}
            mock_ollama.return_value = {'status': 'healthy', 'service': 'ollama'}
            mock_redis.return_value = {'status': 'healthy', 'service': 'redis'}
            mock_twilio.return_value = {'status': 'healthy', 'service': 'twilio'}
            mock_facebook.return_value = {'status': 'healthy', 'service': 'facebook'}

            results = await self.health_checker.check_all_services()

            assert len(results) == 5
            assert all(result['status'] == 'healthy' for result in results)

    def test_get_overall_status_all_healthy(self):
        """Test overall status calculation - all healthy"""
        results = [
            {'status': 'healthy', 'service': 'openai'},
            {'status': 'healthy', 'service': 'ollama'},
            {'status': 'disabled', 'service': 'redis'}  # disabled counts as ok
        ]

        status = self.health_checker.get_overall_status(results)
        assert status == 'healthy'

    def test_get_overall_status_some_unhealthy(self):
        """Test overall status calculation - some unhealthy"""
        results = [
            {'status': 'healthy', 'service': 'openai'},
            {'status': 'unhealthy', 'service': 'ollama'},
            {'status': 'healthy', 'service': 'redis'}
        ]

        status = self.health_checker.get_overall_status(results)
        assert status == 'degraded'

    def test_get_overall_status_all_unhealthy(self):
        """Test overall status calculation - all unhealthy"""
        results = [
            {'status': 'unhealthy', 'service': 'openai'},
            {'status': 'unhealthy', 'service': 'ollama'}
        ]

        status = self.health_checker.get_overall_status(results)
        assert status == 'unhealthy'

    @pytest.mark.asyncio
    async def test_health_check_with_timeout(self):
        """Test health check with timeout"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            # Simulate timeout
            mock_get.side_effect = asyncio.TimeoutError()

            result = await self.health_checker.check_openai()

            assert result['status'] == 'unhealthy'
            assert 'timeout' in result['error'].lower()

    @pytest.mark.asyncio
    async def test_service_not_configured(self):
        """Test health check for unconfigured service"""
        with patch.dict(os.environ, {}, clear=True):
            result = await self.health_checker.check_twilio()

            assert result['status'] == 'not_configured'
            assert result['service'] == 'twilio'


class TestHealthCheckerIntegration:
    """Integration tests for health checker"""

    @pytest.mark.asyncio
    async def test_get_system_health_function(self):
        """Test the main get_system_health function"""
        with patch('utils.health_checker.HealthChecker.check_all_services') as mock_check:
            mock_check.return_value = [
                {'status': 'healthy', 'service': 'openai', 'response_time': 150}
            ]

            result = await get_system_health()

            assert 'overall_status' in result
            assert 'services' in result
            assert 'timestamp' in result
            assert 'system_info' in result

    @pytest.mark.asyncio
    async def test_health_check_error_handling(self):
        """Test health check error handling"""
        health_checker = HealthChecker()

        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = Exception("Unexpected error")

            result = await health_checker.check_openai()

            assert result['status'] == 'unhealthy'
            assert 'Unexpected error' in result['error']

    def test_health_checker_initialization(self):
        """Test health checker initialization"""
        checker = HealthChecker()
        assert checker.timeout == 10  # Default timeout

        checker_custom = HealthChecker(timeout=30)
        assert checker_custom.timeout == 30


if __name__ == '__main__':
    pytest.main([__file__])