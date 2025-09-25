#!/usr/bin/env python3
"""
Secure Configuration Management System
Encrypts and manages sensitive configuration data with proper key management.
"""

import os
import json
import secrets
import hashlib
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, asdict
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import logging
from datetime import datetime


@dataclass
class ConfigSchema:
    """Schema for configuration validation"""
    key: str
    required: bool = True
    encrypted: bool = False
    default_value: Optional[Any] = None
    validation_pattern: Optional[str] = None
    description: Optional[str] = None


class SecureConfigManager:
    """Secure configuration manager with encryption support"""

    def __init__(self, config_file: str = "synapseflow_data/secure_config.enc"):
        self.config_file = config_file
        self.config_dir = os.path.dirname(config_file)
        self.key_file = os.path.join(self.config_dir, ".config_key")

        # Ensure directory exists
        os.makedirs(self.config_dir, exist_ok=True)

        # Initialize encryption
        self._fernet = None
        self._config_cache = {}
        self._last_loaded = 0

        # Configuration schema
        self.schema = self._define_schema()

        # Load or generate encryption key
        self._setup_encryption()

    def _define_schema(self) -> Dict[str, ConfigSchema]:
        """Define the configuration schema with validation rules"""
        return {
            # API Keys (encrypted)
            "OPENAI_API_KEY": ConfigSchema(
                key="OPENAI_API_KEY",
                encrypted=True,
                description="OpenAI API key for ChatGPT integration"
            ),
            "TWILIO_AUTH_TOKEN": ConfigSchema(
                key="TWILIO_AUTH_TOKEN",
                encrypted=True,
                description="Twilio authentication token"
            ),
            "FB_APP_SECRET": ConfigSchema(
                key="FB_APP_SECRET",
                encrypted=True,
                description="Facebook app secret for webhook verification"
            ),
            "ADMIN_SECRET": ConfigSchema(
                key="ADMIN_SECRET",
                encrypted=True,
                description="Secret key for admin authentication"
            ),
            "LICENSE_ISSUER_SECRET": ConfigSchema(
                key="LICENSE_ISSUER_SECRET",
                encrypted=True,
                description="Secret key for license generation"
            ),

            # Configuration (non-encrypted but validated)
            "OPENAI_MODEL": ConfigSchema(
                key="OPENAI_MODEL",
                required=False,
                default_value="gpt-3.5-turbo",
                description="OpenAI model to use"
            ),
            "OLLAMA_MODEL": ConfigSchema(
                key="OLLAMA_MODEL",
                required=False,
                default_value="llama2-uncensored:7b",
                description="Ollama model name"
            ),
            "RATE_LIMIT_PER_MIN": ConfigSchema(
                key="RATE_LIMIT_PER_MIN",
                required=False,
                default_value="120",
                description="Rate limit requests per minute"
            ),
            "ADMIN_HOST": ConfigSchema(
                key="ADMIN_HOST",
                required=False,
                default_value="127.0.0.1",
                description="Admin interface host binding"
            ),
            "ADMIN_PORT": ConfigSchema(
                key="ADMIN_PORT",
                required=False,
                default_value="5050",
                description="Admin interface port"
            ),

            # Service URLs
            "OLLAMA_URL": ConfigSchema(
                key="OLLAMA_URL",
                required=False,
                default_value="http://127.0.0.1:11434",
                description="Ollama service URL"
            ),
            "REDIS_URL": ConfigSchema(
                key="REDIS_URL",
                required=False,
                description="Redis connection URL"
            ),

            # Integration credentials
            "TWILIO_ACCOUNT_SID": ConfigSchema(
                key="TWILIO_ACCOUNT_SID",
                required=False,
                description="Twilio account SID"
            ),
            "TWILIO_FROM": ConfigSchema(
                key="TWILIO_FROM",
                required=False,
                description="Twilio sender phone number"
            ),
            "FB_PAGE_TOKEN": ConfigSchema(
                key="FB_PAGE_TOKEN",
                encrypted=True,
                required=False,
                description="Facebook page access token"
            ),
            "FB_VERIFY_TOKEN": ConfigSchema(
                key="FB_VERIFY_TOKEN",
                required=False,
                description="Facebook webhook verification token"
            ),
        }

    def _setup_encryption(self):
        """Setup encryption key and Fernet cipher"""
        try:
            # Try to load existing key
            if os.path.exists(self.key_file):
                with open(self.key_file, 'rb') as f:
                    key = f.read()
            else:
                # Generate new key
                key = Fernet.generate_key()

                # Save key with secure permissions
                with open(self.key_file, 'wb') as f:
                    f.write(key)
                os.chmod(self.key_file, 0o600)  # Read/write for owner only

                logging.info(f"Generated new encryption key: {self.key_file}")

            self._fernet = Fernet(key)

        except Exception as e:
            logging.error(f"Failed to setup encryption: {e}")
            raise

    def _encrypt_value(self, value: str) -> str:
        """Encrypt a configuration value"""
        if not self._fernet:
            raise RuntimeError("Encryption not initialized")

        encrypted_bytes = self._fernet.encrypt(value.encode('utf-8'))
        return base64.b64encode(encrypted_bytes).decode('ascii')

    def _decrypt_value(self, encrypted_value: str) -> str:
        """Decrypt a configuration value"""
        if not self._fernet:
            raise RuntimeError("Encryption not initialized")

        try:
            encrypted_bytes = base64.b64decode(encrypted_value.encode('ascii'))
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            logging.error(f"Failed to decrypt configuration value: {e}")
            raise

    def _load_config_file(self) -> Dict[str, Any]:
        """Load configuration from encrypted file"""
        if not os.path.exists(self.config_file):
            return {}

        try:
            with open(self.config_file, 'r') as f:
                encrypted_config = json.load(f)

            config = {}
            for key, value in encrypted_config.items():
                if key.endswith('_encrypted') and isinstance(value, str):
                    # This is an encrypted value
                    original_key = key[:-10]  # Remove '_encrypted' suffix
                    try:
                        config[original_key] = self._decrypt_value(value)
                    except Exception as e:
                        logging.warning(f"Failed to decrypt {original_key}: {e}")
                        # Skip corrupted encrypted values
                        continue
                else:
                    # Non-encrypted value
                    config[key] = value

            return config

        except Exception as e:
            logging.error(f"Failed to load config file: {e}")
            return {}

    def _save_config_file(self, config: Dict[str, Any]):
        """Save configuration to encrypted file"""
        try:
            encrypted_config = {}

            for key, value in config.items():
                schema = self.schema.get(key)

                if schema and schema.encrypted and value is not None:
                    # Encrypt sensitive values
                    encrypted_config[f"{key}_encrypted"] = self._encrypt_value(str(value))
                else:
                    # Store non-sensitive values in plain text
                    encrypted_config[key] = value

            # Add metadata
            encrypted_config['_metadata'] = {
                'version': '1.0',
                'created': datetime.utcnow().isoformat(),
                'schema_version': '1.0'
            }

            # Write to temp file first, then rename (atomic write)
            temp_file = self.config_file + '.tmp'
            with open(temp_file, 'w') as f:
                json.dump(encrypted_config, f, indent=2)

            os.rename(temp_file, self.config_file)
            os.chmod(self.config_file, 0o600)  # Secure permissions

            logging.info(f"Saved secure configuration to {self.config_file}")

        except Exception as e:
            logging.error(f"Failed to save config file: {e}")
            raise

    def get_config(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        """Get a configuration value"""
        # Check cache first
        current_time = os.path.getmtime(self.config_file) if os.path.exists(self.config_file) else 0
        if current_time > self._last_loaded:
            self._config_cache = self._load_config_file()
            self._last_loaded = current_time

        # Get from cache or environment
        value = self._config_cache.get(key)
        if value is None:
            value = os.getenv(key, default)

        # Apply schema defaults
        if value is None:
            schema = self.schema.get(key)
            if schema and schema.default_value is not None:
                value = schema.default_value

        return value

    def set_config(self, key: str, value: Any, save_immediately: bool = True):
        """Set a configuration value"""
        # Validate against schema
        schema = self.schema.get(key)
        if schema:
            if schema.validation_pattern:
                import re
                if not re.match(schema.validation_pattern, str(value)):
                    raise ValueError(f"Value for {key} does not match required pattern")

        # Update cache
        if not self._config_cache:
            self._config_cache = self._load_config_file()

        self._config_cache[key] = value

        # Save if requested
        if save_immediately:
            self._save_config_file(self._config_cache)

        # Also set environment variable for compatibility
        os.environ[key] = str(value)

    def get_all_config(self, include_secrets: bool = False) -> Dict[str, Any]:
        """Get all configuration values"""
        config = self._load_config_file()

        # Merge with environment variables
        for key in self.schema.keys():
            env_value = os.getenv(key)
            if env_value and key not in config:
                config[key] = env_value

        # Filter secrets if requested
        if not include_secrets:
            filtered_config = {}
            for key, value in config.items():
                schema = self.schema.get(key)
                if schema and schema.encrypted:
                    filtered_config[key] = "***REDACTED***" if value else None
                else:
                    filtered_config[key] = value
            return filtered_config

        return config

    def validate_config(self) -> Dict[str, Any]:
        """Validate current configuration against schema"""
        config = self._load_config_file()
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'missing_required': [],
            'status': 'valid'
        }

        # Check required fields
        for key, schema in self.schema.items():
            if schema.required:
                value = config.get(key) or os.getenv(key)
                if not value:
                    validation_results['missing_required'].append({
                        'key': key,
                        'description': schema.description
                    })
                    validation_results['valid'] = False

        # Set overall status
        if validation_results['missing_required']:
            validation_results['status'] = 'missing_required'
        elif validation_results['errors']:
            validation_results['status'] = 'errors'
        elif validation_results['warnings']:
            validation_results['status'] = 'warnings'

        return validation_results

    def import_from_env(self) -> int:
        """Import configuration from environment variables"""
        imported_count = 0

        for key in self.schema.keys():
            env_value = os.getenv(key)
            if env_value:
                self.set_config(key, env_value, save_immediately=False)
                imported_count += 1

        if imported_count > 0:
            self._save_config_file(self._config_cache)
            logging.info(f"Imported {imported_count} configuration values from environment")

        return imported_count

    def export_to_env_file(self, file_path: str, include_secrets: bool = False):
        """Export configuration to .env file format"""
        config = self.get_all_config(include_secrets=include_secrets)

        with open(file_path, 'w') as f:
            f.write(f"# Configuration exported on {datetime.utcnow().isoformat()}\n")
            f.write("# DO NOT COMMIT THIS FILE TO VERSION CONTROL\n\n")

            for key, value in sorted(config.items()):
                if key.startswith('_'):  # Skip metadata
                    continue

                schema = self.schema.get(key)
                if schema and schema.description:
                    f.write(f"# {schema.description}\n")

                if value is None:
                    f.write(f"#{key}=\n")
                else:
                    f.write(f"{key}={value}\n")
                f.write("\n")

    def rotate_encryption_key(self):
        """Rotate the encryption key (re-encrypt all data with new key)"""
        logging.info("Starting encryption key rotation...")

        # Load current config with old key
        old_config = self._load_config_file()

        # Generate new key
        old_key_file = self.key_file + '.old'
        os.rename(self.key_file, old_key_file)

        new_key = Fernet.generate_key()
        with open(self.key_file, 'wb') as f:
            f.write(new_key)
        os.chmod(self.key_file, 0o600)

        # Re-initialize with new key
        self._fernet = Fernet(new_key)

        # Save config with new key
        self._save_config_file(old_config)

        logging.info("Encryption key rotation completed")


# Global config manager instance
_config_manager = None

def get_config_manager() -> SecureConfigManager:
    """Get the global secure config manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = SecureConfigManager()
    return _config_manager


def get_secure_config(key: str, default: Optional[Any] = None) -> Optional[Any]:
    """Convenience function to get configuration value"""
    return get_config_manager().get_config(key, default)


def set_secure_config(key: str, value: Any):
    """Convenience function to set configuration value"""
    return get_config_manager().set_config(key, value)


if __name__ == "__main__":
    # Command-line interface for config management
    import sys

    if len(sys.argv) < 2:
        print("Usage: python secure_config.py <command> [args...]")
        print("Commands:")
        print("  validate              - Validate current configuration")
        print("  import-env            - Import from environment variables")
        print("  export <file>         - Export to .env file")
        print("  get <key>             - Get configuration value")
        print("  set <key> <value>     - Set configuration value")
        print("  list                  - List all configuration")
        print("  rotate-key            - Rotate encryption key")
        sys.exit(1)

    manager = get_config_manager()
    command = sys.argv[1].lower()

    if command == "validate":
        result = manager.validate_config()
        print(f"Configuration status: {result['status']}")
        if result['missing_required']:
            print("Missing required configuration:")
            for item in result['missing_required']:
                print(f"  - {item['key']}: {item['description']}")

    elif command == "import-env":
        count = manager.import_from_env()
        print(f"Imported {count} configuration values")

    elif command == "export":
        if len(sys.argv) < 3:
            print("Usage: export <file>")
            sys.exit(1)
        manager.export_to_env_file(sys.argv[2], include_secrets=True)
        print(f"Configuration exported to {sys.argv[2]}")

    elif command == "get":
        if len(sys.argv) < 3:
            print("Usage: get <key>")
            sys.exit(1)
        value = manager.get_config(sys.argv[2])
        print(f"{sys.argv[2]}={value}")

    elif command == "set":
        if len(sys.argv) < 4:
            print("Usage: set <key> <value>")
            sys.exit(1)
        manager.set_config(sys.argv[2], sys.argv[3])
        print(f"Set {sys.argv[2]}")

    elif command == "list":
        config = manager.get_all_config(include_secrets=False)
        for key, value in sorted(config.items()):
            if not key.startswith('_'):
                print(f"{key}={value}")

    elif command == "rotate-key":
        manager.rotate_encryption_key()
        print("Encryption key rotated successfully")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)