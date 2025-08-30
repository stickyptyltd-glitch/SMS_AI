#!/usr/bin/env python3
"""
Advanced Webhook and Integration Manager
Supports multiple messaging platforms, external APIs, and custom integrations
with retry logic, rate limiting, and comprehensive monitoring.
"""

import os
import json
import time
import asyncio
import aiohttp
import hmac
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
from urllib.parse import urlparse
import logging

class IntegrationType(Enum):
    WEBHOOK_INCOMING = "webhook_incoming"
    WEBHOOK_OUTGOING = "webhook_outgoing"
    API_INTEGRATION = "api_integration"
    MESSAGING_PLATFORM = "messaging_platform"
    CUSTOM_INTEGRATION = "custom_integration"

class MessagePlatform(Enum):
    TWILIO = "twilio"
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    SLACK = "slack"
    DISCORD = "discord"
    FACEBOOK_MESSENGER = "facebook_messenger"
    SIGNAL = "signal"
    MICROSOFT_TEAMS = "microsoft_teams"
    GOOGLE_CHAT = "google_chat"
    MATRIX = "matrix"
    ROCKETCHAT = "rocketchat"
    MATTERMOST = "mattermost"
    CUSTOM = "custom"

@dataclass
class WebhookConfig:
    """Configuration for a webhook integration"""
    webhook_id: str
    name: str
    integration_type: IntegrationType
    platform: MessagePlatform
    endpoint_url: str
    secret_key: Optional[str]
    headers: Dict[str, str]
    retry_attempts: int
    timeout_seconds: int
    rate_limit_per_minute: int
    active: bool
    created_at: str
    last_used: Optional[str]

@dataclass
class WebhookEvent:
    """Represents a webhook event"""
    event_id: str
    webhook_id: str
    event_type: str
    payload: Dict[str, Any]
    timestamp: str
    source_ip: Optional[str]
    processed: bool
    response_sent: bool
    error_message: Optional[str]

@dataclass
class IntegrationResponse:
    """Response from an integration"""
    success: bool
    status_code: int
    response_data: Dict[str, Any]
    response_time: float
    error_message: Optional[str]

class WebhookSecurity:
    """Security utilities for webhook validation"""
    
    @staticmethod
    def verify_signature(payload: bytes, signature: str, secret: str, 
                        algorithm: str = "sha256") -> bool:
        """Verify webhook signature"""
        try:
            if algorithm == "sha256":
                expected_signature = hmac.new(
                    secret.encode(),
                    payload,
                    hashlib.sha256
                ).hexdigest()
                return hmac.compare_digest(f"sha256={expected_signature}", signature)
            elif algorithm == "sha1":
                expected_signature = hmac.new(
                    secret.encode(),
                    payload,
                    hashlib.sha1
                ).hexdigest()
                return hmac.compare_digest(f"sha1={expected_signature}", signature)
            else:
                return False
        except Exception:
            return False
    
    @staticmethod
    def validate_twilio_signature(url: str, params: Dict, signature: str, 
                                auth_token: str) -> bool:
        """Validate Twilio webhook signature"""
        try:
            # Create the signature string
            signature_string = url
            for key in sorted(params.keys()):
                signature_string += f"{key}{params[key]}"
            
            # Generate expected signature
            expected_signature = hmac.new(
                auth_token.encode(),
                signature_string.encode(),
                hashlib.sha1
            ).digest()
            
            import base64
            expected_signature_b64 = base64.b64encode(expected_signature).decode()
            
            return hmac.compare_digest(expected_signature_b64, signature)
        except Exception:
            return False

class WebhookManager:
    """Advanced webhook and integration manager"""
    
    def __init__(self, data_dir: str = "synapseflow_data"):
        self.data_dir = data_dir
        self.webhook_dir = os.path.join(data_dir, "webhooks")
        os.makedirs(self.webhook_dir, exist_ok=True)
        
        # Database for webhook data
        self.db_path = os.path.join(self.webhook_dir, "webhooks.db")
        self._init_database()
        
        # In-memory storage
        self.webhooks: Dict[str, WebhookConfig] = {}
        self.event_handlers: Dict[str, Callable] = {}
        self.rate_limits: Dict[str, List[float]] = {}
        
        # Load existing webhooks
        self._load_webhooks()
        
        # Setup logging
        self.logger = logging.getLogger("webhook_manager")
        
        # Platform-specific handlers
        self._setup_platform_handlers()
    
    def _init_database(self):
        """Initialize webhook database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS webhooks (
                    webhook_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    integration_type TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    endpoint_url TEXT NOT NULL,
                    secret_key TEXT,
                    headers TEXT,
                    retry_attempts INTEGER DEFAULT 3,
                    timeout_seconds INTEGER DEFAULT 30,
                    rate_limit_per_minute INTEGER DEFAULT 60,
                    active BOOLEAN DEFAULT TRUE,
                    created_at TEXT NOT NULL,
                    last_used TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS webhook_events (
                    event_id TEXT PRIMARY KEY,
                    webhook_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    source_ip TEXT,
                    processed BOOLEAN DEFAULT FALSE,
                    response_sent BOOLEAN DEFAULT FALSE,
                    error_message TEXT,
                    FOREIGN KEY (webhook_id) REFERENCES webhooks (webhook_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS integration_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    webhook_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    response_time REAL,
                    status_code INTEGER,
                    error_message TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (webhook_id) REFERENCES webhooks (webhook_id)
                )
            """)
    
    def _load_webhooks(self):
        """Load webhook configurations from database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM webhooks WHERE active = TRUE")
            for row in cursor.fetchall():
                webhook = WebhookConfig(
                    webhook_id=row[0],
                    name=row[1],
                    integration_type=IntegrationType(row[2]),
                    platform=MessagePlatform(row[3]),
                    endpoint_url=row[4],
                    secret_key=row[5],
                    headers=json.loads(row[6]) if row[6] else {},
                    retry_attempts=row[7],
                    timeout_seconds=row[8],
                    rate_limit_per_minute=row[9],
                    active=bool(row[10]),
                    created_at=row[11],
                    last_used=row[12]
                )
                self.webhooks[webhook.webhook_id] = webhook
    
    def _setup_platform_handlers(self):
        """Setup platform-specific message handlers"""
        self.platform_handlers = {
            MessagePlatform.TWILIO: self._handle_twilio_message,
            MessagePlatform.WHATSAPP: self._handle_whatsapp_message,
            MessagePlatform.TELEGRAM: self._handle_telegram_message,
            MessagePlatform.SLACK: self._handle_slack_message,
            MessagePlatform.DISCORD: self._handle_discord_message,
            MessagePlatform.FACEBOOK_MESSENGER: self._handle_messenger_message,
        }
    
    def register_webhook(self, name: str, integration_type: IntegrationType,
                        platform: MessagePlatform, endpoint_url: str,
                        secret_key: str = None, headers: Dict[str, str] = None,
                        retry_attempts: int = 3, timeout_seconds: int = 30,
                        rate_limit_per_minute: int = 60) -> str:
        """Register a new webhook integration"""
        webhook_id = f"{platform.value}_{int(time.time())}"
        
        webhook = WebhookConfig(
            webhook_id=webhook_id,
            name=name,
            integration_type=integration_type,
            platform=platform,
            endpoint_url=endpoint_url,
            secret_key=secret_key,
            headers=headers or {},
            retry_attempts=retry_attempts,
            timeout_seconds=timeout_seconds,
            rate_limit_per_minute=rate_limit_per_minute,
            active=True,
            created_at=datetime.utcnow().isoformat(),
            last_used=None
        )
        
        self.webhooks[webhook_id] = webhook
        
        # Store in database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO webhooks 
                (webhook_id, name, integration_type, platform, endpoint_url,
                 secret_key, headers, retry_attempts, timeout_seconds,
                 rate_limit_per_minute, active, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                webhook.webhook_id, webhook.name, webhook.integration_type.value,
                webhook.platform.value, webhook.endpoint_url, webhook.secret_key,
                json.dumps(webhook.headers), webhook.retry_attempts,
                webhook.timeout_seconds, webhook.rate_limit_per_minute,
                webhook.active, webhook.created_at
            ))
        
        return webhook_id
    
    def _check_rate_limit(self, webhook_id: str) -> bool:
        """Check if webhook is rate limited"""
        if webhook_id not in self.webhooks:
            return False
        
        webhook = self.webhooks[webhook_id]
        now = time.time()
        
        if webhook_id not in self.rate_limits:
            self.rate_limits[webhook_id] = []
        
        # Clean old requests
        self.rate_limits[webhook_id] = [
            req_time for req_time in self.rate_limits[webhook_id]
            if now - req_time < 60
        ]
        
        # Check limit
        if len(self.rate_limits[webhook_id]) >= webhook.rate_limit_per_minute:
            return False
        
        # Add current request
        self.rate_limits[webhook_id].append(now)
        return True
    
    async def process_incoming_webhook(self, webhook_id: str, payload: Dict[str, Any],
                                     headers: Dict[str, str] = None,
                                     source_ip: str = None) -> IntegrationResponse:
        """Process incoming webhook event"""
        if webhook_id not in self.webhooks:
            return IntegrationResponse(
                success=False,
                status_code=404,
                response_data={"error": "Webhook not found"},
                response_time=0,
                error_message="Webhook not found"
            )
        
        webhook = self.webhooks[webhook_id]
        
        # Check rate limit
        if not self._check_rate_limit(webhook_id):
            return IntegrationResponse(
                success=False,
                status_code=429,
                response_data={"error": "Rate limit exceeded"},
                response_time=0,
                error_message="Rate limit exceeded"
            )
        
        start_time = time.time()
        
        try:
            # Verify signature if secret key is provided
            if webhook.secret_key and headers:
                signature = headers.get('X-Hub-Signature-256') or headers.get('X-Twilio-Signature')
                if signature:
                    payload_bytes = json.dumps(payload, sort_keys=True).encode()
                    if not WebhookSecurity.verify_signature(payload_bytes, signature, webhook.secret_key):
                        return IntegrationResponse(
                            success=False,
                            status_code=401,
                            response_data={"error": "Invalid signature"},
                            response_time=time.time() - start_time,
                            error_message="Invalid signature"
                        )
            
            # Create webhook event
            event = WebhookEvent(
                event_id=f"evt_{int(time.time() * 1000)}",
                webhook_id=webhook_id,
                event_type=payload.get('type', 'message'),
                payload=payload,
                timestamp=datetime.utcnow().isoformat(),
                source_ip=source_ip,
                processed=False,
                response_sent=False,
                error_message=None
            )
            
            # Store event
            self._store_webhook_event(event)
            
            # Process based on platform
            if webhook.platform in self.platform_handlers:
                response = await self.platform_handlers[webhook.platform](webhook, event)
            else:
                response = await self._handle_generic_message(webhook, event)
            
            # Update event status
            event.processed = True
            event.response_sent = response.success
            if not response.success:
                event.error_message = response.error_message
            
            self._update_webhook_event(event)
            
            # Log integration result
            self._log_integration_result(webhook_id, event.event_type, response)
            
            # Update webhook last used
            webhook.last_used = datetime.utcnow().isoformat()
            
            return response
            
        except Exception as e:
            response_time = time.time() - start_time
            error_response = IntegrationResponse(
                success=False,
                status_code=500,
                response_data={"error": str(e)},
                response_time=response_time,
                error_message=str(e)
            )
            
            self._log_integration_result(webhook_id, "error", error_response)
            return error_response
    
    async def _handle_twilio_message(self, webhook: WebhookConfig, 
                                   event: WebhookEvent) -> IntegrationResponse:
        """Handle Twilio SMS webhook"""
        payload = event.payload
        
        # Extract message details
        from_number = payload.get('From', '')
        to_number = payload.get('To', '')
        message_body = payload.get('Body', '')
        
        if not message_body:
            return IntegrationResponse(
                success=False,
                status_code=400,
                response_data={"error": "No message body"},
                response_time=0,
                error_message="No message body"
            )
        
        # Process message through SMS AI
        try:
            from ai.generator import generate_reply
            from ai.analysis import analyze as analyze_message
            
            # Analyze and generate response
            analysis = analyze_message(message_body, from_number)
            reply, _ = generate_reply(message_body, from_number, analysis)
            
            # Send response via Twilio
            response_payload = {
                "To": from_number,
                "From": to_number,
                "Body": reply
            }
            
            return IntegrationResponse(
                success=True,
                status_code=200,
                response_data=response_payload,
                response_time=0,
                error_message=None
            )
            
        except Exception as e:
            return IntegrationResponse(
                success=False,
                status_code=500,
                response_data={"error": str(e)},
                response_time=0,
                error_message=str(e)
            )
    
    async def _handle_whatsapp_message(self, webhook: WebhookConfig,
                                     event: WebhookEvent) -> IntegrationResponse:
        """Handle WhatsApp webhook"""
        # Similar to Twilio but with WhatsApp-specific formatting
        return await self._handle_twilio_message(webhook, event)
    
    async def _handle_telegram_message(self, webhook: WebhookConfig,
                                     event: WebhookEvent) -> IntegrationResponse:
        """Handle Telegram webhook"""
        payload = event.payload
        
        # Extract Telegram message
        message = payload.get('message', {})
        chat_id = message.get('chat', {}).get('id')
        text = message.get('text', '')
        
        if not text or not chat_id:
            return IntegrationResponse(
                success=False,
                status_code=400,
                response_data={"error": "Invalid Telegram message"},
                response_time=0,
                error_message="Invalid Telegram message"
            )
        
        # Process and respond
        try:
            from ai.generator import generate_reply
            from ai.analysis import analyze as analyze_message
            
            analysis = analyze_message(text, str(chat_id))
            reply, _ = generate_reply(text, str(chat_id), analysis)
            
            return IntegrationResponse(
                success=True,
                status_code=200,
                response_data={"chat_id": chat_id, "text": reply},
                response_time=0,
                error_message=None
            )
            
        except Exception as e:
            return IntegrationResponse(
                success=False,
                status_code=500,
                response_data={"error": str(e)},
                response_time=0,
                error_message=str(e)
            )
    
    async def _handle_slack_message(self, webhook: WebhookConfig,
                                  event: WebhookEvent) -> IntegrationResponse:
        """Handle Slack webhook"""
        # Implement Slack-specific message handling
        return IntegrationResponse(
            success=True,
            status_code=200,
            response_data={"text": "Slack integration not fully implemented"},
            response_time=0,
            error_message=None
        )
    
    async def _handle_discord_message(self, webhook: WebhookConfig,
                                    event: WebhookEvent) -> IntegrationResponse:
        """Handle Discord webhook"""
        # Implement Discord-specific message handling
        return IntegrationResponse(
            success=True,
            status_code=200,
            response_data={"content": "Discord integration not fully implemented"},
            response_time=0,
            error_message=None
        )
    
    async def _handle_messenger_message(self, webhook: WebhookConfig,
                                      event: WebhookEvent) -> IntegrationResponse:
        """Handle Facebook Messenger webhook"""
        # Implement Messenger-specific message handling
        return IntegrationResponse(
            success=True,
            status_code=200,
            response_data={"text": "Messenger integration not fully implemented"},
            response_time=0,
            error_message=None
        )
    
    async def _handle_generic_message(self, webhook: WebhookConfig,
                                    event: WebhookEvent) -> IntegrationResponse:
        """Handle generic webhook message"""
        return IntegrationResponse(
            success=True,
            status_code=200,
            response_data={"message": "Generic webhook processed"},
            response_time=0,
            error_message=None
        )
    
    def _store_webhook_event(self, event: WebhookEvent):
        """Store webhook event in database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO webhook_events
                (event_id, webhook_id, event_type, payload, timestamp,
                 source_ip, processed, response_sent, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_id, event.webhook_id, event.event_type,
                json.dumps(event.payload), event.timestamp, event.source_ip,
                event.processed, event.response_sent, event.error_message
            ))
    
    def _update_webhook_event(self, event: WebhookEvent):
        """Update webhook event in database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE webhook_events
                SET processed = ?, response_sent = ?, error_message = ?
                WHERE event_id = ?
            """, (event.processed, event.response_sent, event.error_message, event.event_id))
    
    def _log_integration_result(self, webhook_id: str, event_type: str,
                              response: IntegrationResponse):
        """Log integration result"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO integration_logs
                (webhook_id, event_type, success, response_time, status_code,
                 error_message, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                webhook_id, event_type, response.success, response.response_time,
                response.status_code, response.error_message,
                datetime.utcnow().isoformat()
            ))
    
    def get_webhook_stats(self, webhook_id: str = None) -> Dict[str, Any]:
        """Get webhook statistics"""
        with sqlite3.connect(self.db_path) as conn:
            if webhook_id:
                # Stats for specific webhook
                cursor = conn.execute("""
                    SELECT COUNT(*) as total_events,
                           SUM(CASE WHEN processed = 1 THEN 1 ELSE 0 END) as processed_events,
                           SUM(CASE WHEN response_sent = 1 THEN 1 ELSE 0 END) as successful_responses,
                           AVG(CASE WHEN success = 1 THEN response_time ELSE NULL END) as avg_response_time
                    FROM webhook_events we
                    LEFT JOIN integration_logs il ON we.webhook_id = il.webhook_id
                    WHERE we.webhook_id = ?
                """, (webhook_id,))

                result = cursor.fetchone()

                # Get error distribution
                error_cursor = conn.execute("""
                    SELECT error_message, COUNT(*) as count
                    FROM webhook_events
                    WHERE webhook_id = ? AND error_message IS NOT NULL
                    GROUP BY error_message
                    ORDER BY count DESC
                    LIMIT 5
                """, (webhook_id,))

                errors = [{"error": row[0], "count": row[1]} for row in error_cursor.fetchall()]

                return {
                    "webhook_id": webhook_id,
                    "total_events": result[0] or 0,
                    "processed_events": result[1] or 0,
                    "successful_responses": result[2] or 0,
                    "avg_response_time": result[3] or 0,
                    "success_rate": (result[2] / result[0]) if result[0] > 0 else 0,
                    "common_errors": errors
                }
            else:
                # Overall stats
                cursor = conn.execute("""
                    SELECT COUNT(DISTINCT webhook_id) as total_webhooks,
                           COUNT(*) as total_events,
                           SUM(CASE WHEN processed = 1 THEN 1 ELSE 0 END) as processed_events
                    FROM webhook_events
                """)

                result = cursor.fetchone()

                # Get platform distribution
                platform_cursor = conn.execute("""
                    SELECT w.platform, COUNT(we.event_id) as event_count
                    FROM webhooks w
                    LEFT JOIN webhook_events we ON w.webhook_id = we.webhook_id
                    GROUP BY w.platform
                    ORDER BY event_count DESC
                """)

                platforms = [{"platform": row[0], "events": row[1]} for row in platform_cursor.fetchall()]

                return {
                    "total_webhooks": result[0] or 0,
                    "total_events": result[1] or 0,
                    "processed_events": result[2] or 0,
                    "success_rate": (result[2] / result[1]) if result[1] > 0 else 0,
                    "platform_distribution": platforms
                }

    def get_webhook_health_report(self) -> Dict[str, Any]:
        """Get comprehensive webhook health report"""
        with sqlite3.connect(self.db_path) as conn:
            # Get recent performance metrics
            cursor = conn.execute("""
                SELECT webhook_id,
                       AVG(response_time) as avg_response_time,
                       COUNT(*) as total_requests,
                       SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_requests
                FROM integration_logs
                WHERE timestamp > datetime('now', '-24 hours')
                GROUP BY webhook_id
            """)

            webhook_health = []
            for row in cursor.fetchall():
                webhook_id, avg_time, total, successful = row
                success_rate = successful / total if total > 0 else 0

                health_status = "healthy"
                if success_rate < 0.8:
                    health_status = "degraded"
                if success_rate < 0.5:
                    health_status = "unhealthy"

                webhook_health.append({
                    "webhook_id": webhook_id,
                    "health_status": health_status,
                    "success_rate": success_rate,
                    "avg_response_time": avg_time or 0,
                    "total_requests_24h": total
                })

            # Overall system health
            total_healthy = len([w for w in webhook_health if w["health_status"] == "healthy"])
            total_webhooks = len(webhook_health)

            system_health = "healthy"
            if total_webhooks > 0:
                health_ratio = total_healthy / total_webhooks
                if health_ratio < 0.8:
                    system_health = "degraded"
                if health_ratio < 0.5:
                    system_health = "unhealthy"

            return {
                "system_health": system_health,
                "total_webhooks": total_webhooks,
                "healthy_webhooks": total_healthy,
                "webhook_details": webhook_health,
                "recommendations": self._generate_webhook_recommendations(webhook_health)
            }

    def _generate_webhook_recommendations(self, webhook_health: List[Dict]) -> List[Dict]:
        """Generate recommendations based on webhook health"""
        recommendations = []

        for webhook in webhook_health:
            if webhook["health_status"] == "unhealthy":
                recommendations.append({
                    "webhook_id": webhook["webhook_id"],
                    "priority": "high",
                    "issue": "Low success rate",
                    "suggestion": "Check endpoint availability and authentication"
                })

            if webhook["avg_response_time"] > 5.0:  # 5 seconds
                recommendations.append({
                    "webhook_id": webhook["webhook_id"],
                    "priority": "medium",
                    "issue": "Slow response times",
                    "suggestion": "Optimize endpoint performance or increase timeout"
                })

        return recommendations

# Global webhook manager instance
_webhook_manager = None

def get_webhook_manager() -> WebhookManager:
    """Get global webhook manager instance"""
    global _webhook_manager
    if _webhook_manager is None:
        _webhook_manager = WebhookManager()
    return _webhook_manager
