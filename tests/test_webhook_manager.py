#!/usr/bin/env python3
"""
Test suite for enhanced webhook manager
"""

import pytest
import os
import json
import hmac
import hashlib
from unittest.mock import patch, MagicMock, AsyncMock
import sys
from pathlib import Path
import tempfile
import sqlite3

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from integrations.webhook_manager import WebhookManager


class TestWebhookManager:
    """Test cases for WebhookManager class"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test_webhooks.db')
        self.webhook_manager = WebhookManager(db_path=self.db_path)

    def teardown_method(self):
        """Cleanup test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_webhook_manager_initialization(self):
        """Test webhook manager initialization"""
        assert self.webhook_manager.db_path == self.db_path
        assert os.path.exists(self.db_path)

        # Check if tables were created
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            assert 'webhooks' in tables
            assert 'webhook_events' in tables

    def test_register_webhook(self):
        """Test webhook registration"""
        webhook_config = {
            'name': 'test_webhook',
            'integration_type': 'sms',
            'platform': 'twilio',
            'endpoint_url': 'https://example.com/webhook',
            'secret_key': 'secret123',
            'headers': {'Content-Type': 'application/json'},
            'retry_attempts': 3,
            'timeout_seconds': 30,
            'rate_limit_per_minute': 60
        }

        webhook_id = self.webhook_manager.register_webhook(webhook_config)

        assert webhook_id is not None
        assert len(webhook_id) > 0

        # Verify webhook was stored
        webhook = self.webhook_manager.get_webhook(webhook_id)
        assert webhook is not None
        assert webhook['name'] == 'test_webhook'
        assert webhook['endpoint_url'] == 'https://example.com/webhook'

    def test_get_webhook_nonexistent(self):
        """Test getting non-existent webhook"""
        webhook = self.webhook_manager.get_webhook('nonexistent')
        assert webhook is None

    def test_update_webhook(self):
        """Test webhook update"""
        # Register webhook first
        webhook_config = {
            'name': 'update_test',
            'integration_type': 'sms',
            'platform': 'twilio',
            'endpoint_url': 'https://example.com/webhook'
        }

        webhook_id = self.webhook_manager.register_webhook(webhook_config)

        # Update webhook
        updates = {
            'name': 'updated_webhook',
            'timeout_seconds': 60
        }

        success = self.webhook_manager.update_webhook(webhook_id, updates)
        assert success is True

        # Verify updates
        webhook = self.webhook_manager.get_webhook(webhook_id)
        assert webhook['name'] == 'updated_webhook'
        assert webhook['timeout_seconds'] == 60

    def test_delete_webhook(self):
        """Test webhook deletion"""
        webhook_config = {
            'name': 'delete_test',
            'integration_type': 'sms',
            'platform': 'twilio',
            'endpoint_url': 'https://example.com/webhook'
        }

        webhook_id = self.webhook_manager.register_webhook(webhook_config)

        # Delete webhook
        success = self.webhook_manager.delete_webhook(webhook_id)
        assert success is True

        # Verify deletion
        webhook = self.webhook_manager.get_webhook(webhook_id)
        assert webhook is None

    def test_list_webhooks(self):
        """Test listing webhooks"""
        # Register multiple webhooks
        for i in range(3):
            webhook_config = {
                'name': f'webhook_{i}',
                'integration_type': 'sms',
                'platform': 'twilio',
                'endpoint_url': f'https://example.com/webhook/{i}'
            }
            self.webhook_manager.register_webhook(webhook_config)

        webhooks = self.webhook_manager.list_webhooks()
        assert len(webhooks) == 3

        # Test filtering by platform
        twilio_webhooks = self.webhook_manager.list_webhooks(platform='twilio')
        assert len(twilio_webhooks) == 3

        slack_webhooks = self.webhook_manager.list_webhooks(platform='slack')
        assert len(slack_webhooks) == 0

    @pytest.mark.asyncio
    async def test_send_outgoing_webhook_success(self):
        """Test successful outgoing webhook delivery"""
        webhook_config = {
            'name': 'outgoing_test',
            'integration_type': 'sms',
            'platform': 'twilio',
            'endpoint_url': 'https://example.com/webhook',
            'secret_key': 'secret123'
        }

        webhook_id = self.webhook_manager.register_webhook(webhook_config)

        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value='success')
            mock_post.return_value.__aenter__.return_value = mock_response

            payload = {'message': 'test message', 'from': '+1234567890'}
            success = await self.webhook_manager.send_outgoing_webhook(webhook_id, payload)

            assert success is True
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_outgoing_webhook_with_hmac(self):
        """Test outgoing webhook with HMAC signature"""
        webhook_config = {
            'name': 'hmac_test',
            'integration_type': 'sms',
            'platform': 'twilio',
            'endpoint_url': 'https://example.com/webhook',
            'secret_key': 'secret123'
        }

        webhook_id = self.webhook_manager.register_webhook(webhook_config)

        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_response

            payload = {'message': 'test'}
            await self.webhook_manager.send_outgoing_webhook(webhook_id, payload)

            # Verify HMAC header was added
            call_args = mock_post.call_args
            headers = call_args[1]['headers']
            assert 'X-Webhook-Signature' in headers

            # Verify HMAC signature is correct
            expected_signature = hmac.new(
                'secret123'.encode('utf-8'),
                json.dumps(payload).encode('utf-8'),
                hashlib.sha256
            ).hexdigest()

            assert headers['X-Webhook-Signature'] == f'sha256={expected_signature}'

    @pytest.mark.asyncio
    async def test_send_outgoing_webhook_retry(self):
        """Test webhook retry mechanism"""
        webhook_config = {
            'name': 'retry_test',
            'integration_type': 'sms',
            'platform': 'twilio',
            'endpoint_url': 'https://example.com/webhook',
            'retry_attempts': 2,
            'timeout_seconds': 1
        }

        webhook_id = self.webhook_manager.register_webhook(webhook_config)

        with patch('aiohttp.ClientSession.post') as mock_post:
            # First call fails, second succeeds
            mock_response_fail = AsyncMock()
            mock_response_fail.status = 500
            mock_response_success = AsyncMock()
            mock_response_success.status = 200

            mock_post.return_value.__aenter__.side_effect = [
                mock_response_fail,
                mock_response_success
            ]

            payload = {'message': 'test'}
            success = await self.webhook_manager.send_outgoing_webhook(webhook_id, payload)

            assert success is True
            assert mock_post.call_count == 2

    @pytest.mark.asyncio
    async def test_broadcast_webhook(self):
        """Test broadcasting to multiple webhooks"""
        # Register multiple webhooks
        webhook_ids = []
        for i in range(3):
            webhook_config = {
                'name': f'broadcast_{i}',
                'integration_type': 'sms',
                'platform': 'twilio',
                'endpoint_url': f'https://example.com/webhook/{i}'
            }
            webhook_id = self.webhook_manager.register_webhook(webhook_config)
            webhook_ids.append(webhook_id)

        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_response

            payload = {'message': 'broadcast test'}
            results = await self.webhook_manager.broadcast_webhook(payload, platform='twilio')

            assert len(results) == 3
            assert all(result['success'] for result in results)
            assert mock_post.call_count == 3

    def test_verify_incoming_webhook_signature(self):
        """Test incoming webhook signature verification"""
        secret = 'webhook_secret'
        payload = '{"message": "test"}'

        # Create valid signature
        signature = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        # Test valid signature
        is_valid = self.webhook_manager.verify_incoming_signature(
            payload, f'sha256={signature}', secret
        )
        assert is_valid is True

        # Test invalid signature
        is_valid = self.webhook_manager.verify_incoming_signature(
            payload, 'sha256=invalid', secret
        )
        assert is_valid is False

    def test_get_webhook_statistics(self):
        """Test webhook statistics retrieval"""
        webhook_config = {
            'name': 'stats_test',
            'integration_type': 'sms',
            'platform': 'twilio',
            'endpoint_url': 'https://example.com/webhook'
        }

        webhook_id = self.webhook_manager.register_webhook(webhook_config)

        # Log some events
        self.webhook_manager._log_event(webhook_id, 'outgoing', 256, 150, 'success')
        self.webhook_manager._log_event(webhook_id, 'outgoing', 512, 300, 'success')
        self.webhook_manager._log_event(webhook_id, 'outgoing', 128, None, 'failed', 'Timeout')

        stats = self.webhook_manager.get_webhook_statistics(webhook_id)

        assert stats['total_events'] == 3
        assert stats['successful_events'] == 2
        assert stats['failed_events'] == 1
        assert stats['average_response_time'] == 225.0  # (150 + 300) / 2

    def test_get_recent_events(self):
        """Test retrieving recent webhook events"""
        webhook_config = {
            'name': 'events_test',
            'integration_type': 'sms',
            'platform': 'twilio',
            'endpoint_url': 'https://example.com/webhook'
        }

        webhook_id = self.webhook_manager.register_webhook(webhook_config)

        # Log some events
        for i in range(5):
            self.webhook_manager._log_event(
                webhook_id, 'outgoing', 256, 150, 'success'
            )

        events = self.webhook_manager.get_recent_events(webhook_id, limit=3)
        assert len(events) == 3

        # All events should be for our webhook
        for event in events:
            assert event['webhook_id'] == webhook_id

    def test_cleanup_old_events(self):
        """Test cleanup of old webhook events"""
        webhook_config = {
            'name': 'cleanup_test',
            'integration_type': 'sms',
            'platform': 'twilio',
            'endpoint_url': 'https://example.com/webhook'
        }

        webhook_id = self.webhook_manager.register_webhook(webhook_config)

        # Log some events
        for i in range(10):
            self.webhook_manager._log_event(
                webhook_id, 'outgoing', 256, 150, 'success'
            )

        # Clean up old events (keep only 5 most recent)
        cleaned = self.webhook_manager.cleanup_old_events(webhook_id, keep_count=5)

        assert cleaned == 5  # Should have cleaned 5 events

        # Verify only 5 events remain
        events = self.webhook_manager.get_recent_events(webhook_id, limit=100)
        assert len(events) == 5

    def test_webhook_rate_limiting_check(self):
        """Test webhook rate limiting"""
        webhook_config = {
            'name': 'rate_limit_test',
            'integration_type': 'sms',
            'platform': 'twilio',
            'endpoint_url': 'https://example.com/webhook',
            'rate_limit_per_minute': 2
        }

        webhook_id = self.webhook_manager.register_webhook(webhook_config)

        # Check rate limit - should allow first request
        allowed = self.webhook_manager.check_rate_limit(webhook_id)
        assert allowed is True

        # Log an event to increment counter
        self.webhook_manager._log_event(webhook_id, 'outgoing', 256, 150, 'success')

        # Should still allow second request
        allowed = self.webhook_manager.check_rate_limit(webhook_id)
        assert allowed is True

        # Log another event
        self.webhook_manager._log_event(webhook_id, 'outgoing', 256, 150, 'success')

        # Third request should be rate limited
        allowed = self.webhook_manager.check_rate_limit(webhook_id)
        assert allowed is False


if __name__ == '__main__':
    pytest.main([__file__])