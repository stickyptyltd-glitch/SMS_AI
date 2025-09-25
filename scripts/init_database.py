#!/usr/bin/env python3
"""
Database Initialization Script
Sets up all databases and data directories for SynapseFlow AI.
"""

import os
import sys
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class DatabaseInitializer:
    """Handles database and storage initialization"""

    def __init__(self, data_dir: str = "synapseflow_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

    def create_directory_structure(self):
        """Create all necessary directories"""
        directories = [
            "analytics",
            "cache",
            "contacts",
            "conversations",
            "learning",
            "personalities",
            "security",
            "users",
            "webhooks",
            "health",
            "backups",
            "logs",
            "metrics"
        ]

        print("📁 Creating directory structure...")
        for dir_name in directories:
            dir_path = self.data_dir / dir_name
            dir_path.mkdir(exist_ok=True)
            print(f"  ✅ {dir_path}")

    def init_webhook_database(self):
        """Initialize webhook management database"""
        db_path = self.data_dir / "webhooks" / "webhooks.db"
        print(f"🔗 Initializing webhook database: {db_path}")

        with sqlite3.connect(db_path) as conn:
            # Webhooks table
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

            # Webhook events table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS webhook_events (
                    event_id TEXT PRIMARY KEY,
                    webhook_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_size INTEGER,
                    response_time REAL,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    attempt_number INTEGER DEFAULT 1,
                    FOREIGN KEY (webhook_id) REFERENCES webhooks (webhook_id)
                )
            """)

            # Create indices
            conn.execute("CREATE INDEX IF NOT EXISTS idx_webhook_events_webhook_id ON webhook_events(webhook_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_webhook_events_created_at ON webhook_events(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_webhook_events_status ON webhook_events(status)")

            conn.commit()
            print("  ✅ Webhook database initialized")

    def init_user_database(self):
        """Initialize user management database"""
        db_path = self.data_dir / "users" / "users.db"
        print(f"👥 Initializing user database: {db_path}")

        with sqlite3.connect(db_path) as conn:
            # Users table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'user',
                    active BOOLEAN DEFAULT TRUE,
                    created_at TEXT NOT NULL,
                    last_login TEXT,
                    login_attempts INTEGER DEFAULT 0,
                    locked_until TEXT
                )
            """)

            # API tokens table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_tokens (
                    token_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    token_hash TEXT NOT NULL,
                    token_preview TEXT NOT NULL,
                    description TEXT,
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    last_used TEXT,
                    usage_count INTEGER DEFAULT 0,
                    active BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)

            # User activity log
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_activity (
                    activity_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    activity_type TEXT NOT NULL,
                    details TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)

            # Create indices
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tokens_user_id ON api_tokens(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tokens_hash ON api_tokens(token_hash)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_activity_user_id ON user_activity(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_activity_created_at ON user_activity(created_at)")

            conn.commit()
            print("  ✅ User database initialized")

    def init_analytics_database(self):
        """Initialize analytics database"""
        db_path = self.data_dir / "analytics" / "analytics.db"
        print(f"📊 Initializing analytics database: {db_path}")

        with sqlite3.connect(db_path) as conn:
            # System metrics table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_metrics (
                    metric_id TEXT PRIMARY KEY,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    metric_type TEXT NOT NULL,
                    tags TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            # API usage table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_usage (
                    usage_id TEXT PRIMARY KEY,
                    endpoint TEXT NOT NULL,
                    method TEXT NOT NULL,
                    user_id TEXT,
                    response_time REAL,
                    status_code INTEGER,
                    error_message TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            # AI model usage table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ai_model_usage (
                    usage_id TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    prompt_tokens INTEGER,
                    completion_tokens INTEGER,
                    total_tokens INTEGER,
                    cost REAL,
                    response_time REAL,
                    success BOOLEAN,
                    error_message TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            # Create indices
            conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_name ON system_metrics(metric_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_metrics_created_at ON system_metrics(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_usage_endpoint ON api_usage(endpoint)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_usage_created_at ON api_usage(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_usage_provider ON ai_model_usage(provider)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_usage_created_at ON ai_model_usage(created_at)")

            conn.commit()
            print("  ✅ Analytics database initialized")

    def init_security_database(self):
        """Initialize security monitoring database"""
        db_path = self.data_dir / "security" / "security.db"
        print(f"🔒 Initializing security database: {db_path}")

        with sqlite3.connect(db_path) as conn:
            # Security events table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS security_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    source_ip TEXT,
                    user_agent TEXT,
                    user_id TEXT,
                    description TEXT,
                    details TEXT,
                    blocked BOOLEAN DEFAULT FALSE,
                    created_at TEXT NOT NULL
                )
            """)

            # Rate limiting events
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rate_limit_events (
                    event_id TEXT PRIMARY KEY,
                    identifier TEXT NOT NULL,
                    limit_type TEXT NOT NULL,
                    current_count INTEGER,
                    limit_threshold INTEGER,
                    window_seconds INTEGER,
                    blocked BOOLEAN DEFAULT FALSE,
                    created_at TEXT NOT NULL
                )
            """)

            # IP blacklist/whitelist
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ip_access_control (
                    ip_address TEXT PRIMARY KEY,
                    access_type TEXT NOT NULL, -- 'whitelist' or 'blacklist'
                    reason TEXT,
                    added_by TEXT,
                    expires_at TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            # Create indices
            conn.execute("CREATE INDEX IF NOT EXISTS idx_security_events_type ON security_events(event_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_security_events_severity ON security_events(severity)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_security_events_created_at ON security_events(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rate_limit_identifier ON rate_limit_events(identifier)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rate_limit_created_at ON rate_limit_events(created_at)")

            conn.commit()
            print("  ✅ Security database initialized")

    def create_default_config_files(self):
        """Create default configuration files"""
        print("📄 Creating default configuration files...")

        # Default profile
        profile_file = self.data_dir / "profile.json"
        if not profile_file.exists():
            default_profile = {
                "style_rules": [
                    "Be concise and helpful",
                    "Use a friendly but professional tone",
                    "Provide accurate information"
                ],
                "preferred_phrases": [
                    "I'd be happy to help",
                    "Let me assist you with that",
                    "Is there anything else I can help you with?"
                ],
                "banned_words": [
                    "hate", "stupid", "idiot"
                ],
                "created_at": datetime.utcnow().isoformat(),
                "version": "1.0"
            }
            with open(profile_file, 'w') as f:
                json.dump(default_profile, f, indent=2)
            print(f"  ✅ Created {profile_file}")

        # Default policy
        policy_file = self.data_dir / "policy.json"
        if not policy_file.exists():
            default_policy = {
                "version": "1.0",
                "created_at": datetime.utcnow().isoformat(),
                "response_policies": {}
            }
            with open(policy_file, 'w') as f:
                json.dump(default_policy, f, indent=2)
            print(f"  ✅ Created {policy_file}")

        # Default templates
        templates_file = self.data_dir / "templates.json"
        if not templates_file.exists():
            default_templates = {
                "greeting": [
                    "Hello! How can I help you today?",
                    "Hi there! What can I do for you?",
                    "Welcome! How may I assist you?"
                ],
                "acknowledgment": [
                    "I understand.",
                    "Got it, thanks for letting me know.",
                    "Thanks for the information."
                ],
                "farewell": [
                    "Have a great day!",
                    "Take care!",
                    "Goodbye, and feel free to reach out anytime!"
                ],
                "error": [
                    "I'm sorry, I'm having trouble processing that request.",
                    "Something went wrong. Please try again.",
                    "I apologize for the inconvenience. Let me try to help another way."
                ]
            }
            with open(templates_file, 'w') as f:
                json.dump(default_templates, f, indent=2)
            print(f"  ✅ Created {templates_file}")

    def create_health_check_files(self):
        """Create health check configuration"""
        print("🏥 Setting up health check configuration...")

        health_dir = self.data_dir / "health"

        # Health check history will be created automatically by the health checker
        # Just ensure the directory exists
        print(f"  ✅ Health directory: {health_dir}")

    def create_log_structure(self):
        """Create logging directory structure"""
        print("📝 Setting up logging structure...")

        logs_dir = self.data_dir / "logs"
        log_subdirs = ["app", "security", "webhook", "health", "performance"]

        for subdir in log_subdirs:
            log_path = logs_dir / subdir
            log_path.mkdir(exist_ok=True)
            print(f"  ✅ {log_path}")

    def run_initialization(self):
        """Run complete initialization"""
        print("🚀 Starting SynapseFlow AI Database Initialization")
        print("=" * 55)

        try:
            # Create directory structure
            self.create_directory_structure()

            # Initialize databases
            self.init_webhook_database()
            self.init_user_database()
            self.init_analytics_database()
            self.init_security_database()

            # Create configuration files
            self.create_default_config_files()
            self.create_health_check_files()
            self.create_log_structure()

            print("\n🎉 Database initialization completed successfully!")
            print(f"📁 Data directory: {self.data_dir.absolute()}")
            print("\n📋 Next steps:")
            print("1. Configure your .env file with appropriate settings")
            print("2. Run configuration validation: python -m utils.config_validator")
            print("3. Start the application: python server.py")

        except Exception as e:
            print(f"\n❌ Initialization failed: {e}")
            import traceback
            traceback.print_exc()
            return False

        return True


def main():
    """Main entry point"""
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "synapseflow_data"

    print(f"Initializing with data directory: {data_dir}")

    initializer = DatabaseInitializer(data_dir)
    success = initializer.run_initialization()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()