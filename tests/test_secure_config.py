#!/usr/bin/env python3
"""
Test suite for secure configuration manager
"""

import pytest
import os
import tempfile
import json
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.secure_config import SecureConfigManager, get_config_manager


class TestSecureConfigManager:
    """Test cases for SecureConfigManager class"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'test_config.enc')
        self.key_file = os.path.join(self.temp_dir, 'test_key.key')
        self.manager = SecureConfigManager(
            config_file_path=self.config_file,
            key_file_path=self.key_file
        )

    def teardown_method(self):
        """Cleanup test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_manager_initialization(self):
        """Test secure config manager initialization"""
        assert self.manager.config_file_path == self.config_file
        assert self.manager.key_file_path == self.key_file
        assert self.manager._encryption_key is not None
        assert self.manager._fernet is not None

    def test_set_and_get_config(self):
        """Test setting and getting configuration values"""
        self.manager.set_config('test_key', 'test_value')
        assert self.manager.get_config('test_key') == 'test_value'

    def test_get_config_with_default(self):
        """Test getting config with default value"""
        assert self.manager.get_config('nonexistent', 'default') == 'default'
        assert self.manager.get_config('nonexistent') is None

    def test_config_persistence(self):
        """Test that configuration persists across instances"""
        self.manager.set_config('persist_key', 'persist_value')

        # Create new manager instance with same files
        new_manager = SecureConfigManager(
            config_file_path=self.config_file,
            key_file_path=self.key_file
        )

        assert new_manager.get_config('persist_key') == 'persist_value'

    def test_encryption_key_generation(self):
        """Test encryption key generation and reuse"""
        key1 = self.manager._encryption_key

        # Create new manager with same key file
        new_manager = SecureConfigManager(
            config_file_path=self.config_file + '.new',
            key_file_path=self.key_file
        )

        key2 = new_manager._encryption_key
        assert key1 == key2

    def test_delete_config(self):
        """Test deleting configuration values"""
        self.manager.set_config('delete_me', 'value')
        assert self.manager.get_config('delete_me') == 'value'

        self.manager.delete_config('delete_me')
        assert self.manager.get_config('delete_me') is None

    def test_list_configs(self):
        """Test listing configuration keys"""
        self.manager.set_config('key1', 'value1')
        self.manager.set_config('key2', 'value2')

        keys = self.manager.list_configs()
        assert 'key1' in keys
        assert 'key2' in keys

    def test_clear_all_configs(self):
        """Test clearing all configurations"""
        self.manager.set_config('key1', 'value1')
        self.manager.set_config('key2', 'value2')

        self.manager.clear_all_configs()

        assert len(self.manager.list_configs()) == 0

    def test_export_to_env_file_without_secrets(self):
        """Test exporting to env file without secrets"""
        self.manager.set_config('PUBLIC_KEY', 'public_value')
        self.manager.set_config('OPENAI_API_KEY', 'secret_value')

        env_file = os.path.join(self.temp_dir, 'test.env')
        self.manager.export_to_env_file(env_file, include_secrets=False)

        with open(env_file, 'r') as f:
            content = f.read()

        assert 'PUBLIC_KEY=public_value' in content
        assert 'OPENAI_API_KEY' not in content

    def test_export_to_env_file_with_secrets(self):
        """Test exporting to env file with secrets"""
        self.manager.set_config('PUBLIC_KEY', 'public_value')
        self.manager.set_config('OPENAI_API_KEY', 'secret_value')

        env_file = os.path.join(self.temp_dir, 'test.env')
        self.manager.export_to_env_file(env_file, include_secrets=True)

        with open(env_file, 'r') as f:
            content = f.read()

        assert 'PUBLIC_KEY=public_value' in content
        assert 'OPENAI_API_KEY=secret_value' in content

    def test_import_from_env(self):
        """Test importing from environment variables"""
        with patch.dict(os.environ, {
            'TEST_KEY_1': 'value1',
            'TEST_KEY_2': 'value2',
            'PATH': '/usr/bin'  # Should be filtered out
        }):
            count = self.manager.import_from_env()

            assert count >= 2  # At least our test keys
            assert self.manager.get_config('TEST_KEY_1') == 'value1'
            assert self.manager.get_config('TEST_KEY_2') == 'value2'
            assert self.manager.get_config('PATH') is None  # Should be filtered

    def test_validate_config(self):
        """Test configuration validation"""
        # Set some required configs
        self.manager.set_config('SERVER_HOST', '0.0.0.0')
        self.manager.set_config('SERVER_PORT', '8080')

        result = self.manager.validate_config()

        assert 'valid' in result
        assert 'missing_required' in result
        assert 'warnings' in result
        assert 'errors' in result

    def test_backup_and_restore_config(self):
        """Test config backup and restore"""
        self.manager.set_config('backup_key', 'backup_value')

        backup_file = os.path.join(self.temp_dir, 'backup.enc')
        self.manager.backup_config(backup_file)

        # Clear and restore
        self.manager.clear_all_configs()
        assert self.manager.get_config('backup_key') is None

        self.manager.restore_config(backup_file)
        assert self.manager.get_config('backup_key') == 'backup_value'

    def test_rotate_encryption_key(self):
        """Test encryption key rotation"""
        self.manager.set_config('rotate_key', 'rotate_value')
        old_key = self.manager._encryption_key

        self.manager.rotate_encryption_key()
        new_key = self.manager._encryption_key

        assert old_key != new_key
        # Value should still be accessible
        assert self.manager.get_config('rotate_key') == 'rotate_value'

    def test_config_schema_validation(self):
        """Test configuration schema validation"""
        # Test valid port
        self.manager.set_config('SERVER_PORT', '8080')
        result = self.manager._validate_value('SERVER_PORT', '8080')
        assert result == (True, None)

        # Test invalid port
        result = self.manager._validate_value('SERVER_PORT', '99999')
        assert result == (False, "Port must be between 1 and 65535")

    def test_error_handling_corrupted_file(self):
        """Test error handling with corrupted config file"""
        # Write invalid content to config file
        with open(self.config_file, 'w') as f:
            f.write('corrupted data')

        # Should handle gracefully and create new config
        new_manager = SecureConfigManager(
            config_file_path=self.config_file,
            key_file_path=self.key_file
        )

        # Should be able to set new values
        new_manager.set_config('test', 'value')
        assert new_manager.get_config('test') == 'value'

    def test_file_permissions(self):
        """Test that config files have correct permissions"""
        self.manager.set_config('test', 'value')

        # Check config file permissions (should be 600)
        config_stat = os.stat(self.config_file)
        assert oct(config_stat.st_mode)[-3:] == '600'

        # Check key file permissions (should be 600)
        key_stat = os.stat(self.key_file)
        assert oct(key_stat.st_mode)[-3:] == '600'


class TestSecureConfigManagerIntegration:
    """Integration tests for secure config manager"""

    def test_get_config_manager_singleton(self):
        """Test that get_config_manager returns singleton"""
        manager1 = get_config_manager()
        manager2 = get_config_manager()

        assert manager1 is manager2

    def test_environment_integration(self):
        """Test integration with environment variables"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = os.path.join(tmpdir, 'config.enc')
            key_file = os.path.join(tmpdir, 'key.key')

            with patch.dict(os.environ, {
                'SECURE_CONFIG_FILE': config_file,
                'SECURE_KEY_FILE': key_file
            }):
                manager = get_config_manager()
                assert manager.config_file_path == config_file
                assert manager.key_file_path == key_file

    def test_concurrent_access(self):
        """Test concurrent access to config manager"""
        import threading
        import time

        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = os.path.join(tmpdir, 'concurrent.enc')
            key_file = os.path.join(tmpdir, 'concurrent.key')

            manager = SecureConfigManager(config_file, key_file)
            results = []

            def worker(worker_id):
                for i in range(10):
                    key = f'worker_{worker_id}_key_{i}'
                    value = f'worker_{worker_id}_value_{i}'
                    manager.set_config(key, value)
                    retrieved = manager.get_config(key)
                    results.append(retrieved == value)
                    time.sleep(0.001)  # Small delay

            threads = []
            for i in range(3):
                thread = threading.Thread(target=worker, args=(i,))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            # All operations should have succeeded
            assert all(results)

    def test_migration_from_plain_config(self):
        """Test migration from plain text configuration"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create plain config file
            plain_config = os.path.join(tmpdir, 'plain.json')
            config_data = {
                'OPENAI_API_KEY': 'sk-test123',
                'SERVER_PORT': '8080'
            }

            with open(plain_config, 'w') as f:
                json.dump(config_data, f)

            # Migrate to secure config
            secure_config = os.path.join(tmpdir, 'secure.enc')
            key_file = os.path.join(tmpdir, 'secure.key')

            manager = SecureConfigManager(secure_config, key_file)

            # Import from plain file
            with open(plain_config, 'r') as f:
                plain_data = json.load(f)

            for key, value in plain_data.items():
                manager.set_config(key, value)

            # Verify migration
            assert manager.get_config('OPENAI_API_KEY') == 'sk-test123'
            assert manager.get_config('SERVER_PORT') == '8080'


if __name__ == '__main__':
    pytest.main([__file__])