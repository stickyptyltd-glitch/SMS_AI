#!/usr/bin/env python3
"""
Test suite for configuration validator
"""

import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config_validator import ConfigValidator, validate_environment


class TestConfigValidator:
    """Test cases for ConfigValidator class"""

    def setup_method(self):
        """Setup test environment"""
        self.validator = ConfigValidator()

    def test_validate_url_valid_urls(self):
        """Test URL validation with valid URLs"""
        assert self.validator._validate_url("http://localhost:8080") == True
        assert self.validator._validate_url("https://api.openai.com") == True
        assert self.validator._validate_url("redis://localhost:6379") == True

    def test_validate_url_invalid_urls(self):
        """Test URL validation with invalid URLs"""
        assert self.validator._validate_url("not-a-url") == False
        assert self.validator._validate_url("") == False
        assert self.validator._validate_url("localhost") == False

    def test_validate_port_valid_ports(self):
        """Test port validation with valid ports"""
        assert self.validator._validate_port("8080") == True
        assert self.validator._validate_port("80") == True
        assert self.validator._validate_port("65535") == True

    def test_validate_port_invalid_ports(self):
        """Test port validation with invalid ports"""
        assert self.validator._validate_port("99999") == False
        assert self.validator._validate_port("-1") == False
        assert self.validator._validate_port("abc") == False
        assert self.validator._validate_port("") == False

    def test_validate_boolean_values(self):
        """Test boolean validation"""
        assert self.validator._validate_boolean("1") == True
        assert self.validator._validate_boolean("true") == True
        assert self.validator._validate_boolean("yes") == True
        assert self.validator._validate_boolean("0") == True
        assert self.validator._validate_boolean("false") == True
        assert self.validator._validate_boolean("no") == True
        assert self.validator._validate_boolean("invalid") == False

    @patch.dict(os.environ, {
        'ENVIRONMENT': 'production',
        'SERVER_HOST': '0.0.0.0',
        'SERVER_PORT': '8080',
        'OPENAI_API_KEY': 'sk-test123',
        'ADMIN_PASSWORD': 'secure-password',
        'ADMIN_SECRET': 'secure-secret'
    })
    def test_validate_production_environment(self):
        """Test validation in production environment"""
        result = self.validator.validate_config()
        assert isinstance(result, dict)
        assert 'valid' in result
        assert 'missing_required' in result
        assert 'warnings' in result
        assert 'errors' in result

    @patch.dict(os.environ, {
        'ENVIRONMENT': 'development',
        'SERVER_HOST': '127.0.0.1',
        'SERVER_PORT': '8080'
    })
    def test_validate_development_environment(self):
        """Test validation in development environment"""
        result = self.validator.validate_config()
        assert isinstance(result, dict)
        # Development should be more lenient
        assert len(result['errors']) <= len(result['warnings'])

    def test_ai_configuration_validation(self):
        """Test AI configuration validation"""
        with patch.dict(os.environ, {
            'USE_OPENAI': '1',
            'OPENAI_API_KEY': '',  # Missing key
            'OLLAMA_DISABLE': '0',
            'OLLAMA_URL': 'invalid-url'  # Invalid URL
        }):
            result = self.validator._validate_ai_config()
            assert len(result['errors']) > 0

    def test_security_configuration_validation(self):
        """Test security configuration validation"""
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'production',
            'ADMIN_PASSWORD': 'weak',  # Too short
            'ADMIN_SECRET': 'test',    # Too short
            'DEBUG': '1'               # Debug in production
        }):
            result = self.validator._validate_security_config()
            assert len(result['errors']) > 0

    def test_external_services_validation(self):
        """Test external services validation"""
        with patch.dict(os.environ, {
            'TWILIO_ACCOUNT_SID': 'AC123',
            'TWILIO_AUTH_TOKEN': '',  # Missing token
            'FB_PAGE_TOKEN': 'token',
            'FB_VERIFY_TOKEN': '',    # Missing verify token
        }):
            result = self.validator._validate_external_services()
            assert len(result['warnings']) > 0

    def test_validate_environment_function(self):
        """Test the main validate_environment function"""
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'development',
            'SERVER_PORT': '8080'
        }):
            # Should not raise exception
            result = validate_environment()
            assert isinstance(result, bool)


class TestConfigValidatorIntegration:
    """Integration tests for configuration validator"""

    def test_full_validation_cycle(self):
        """Test complete validation cycle"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test config
            with patch.dict(os.environ, {
                'ENVIRONMENT': 'development',
                'SERVER_HOST': '127.0.0.1',
                'SERVER_PORT': '8080',
                'DATA_DIR': tmpdir
            }):
                validator = ConfigValidator()
                result = validator.validate_config()

                assert 'valid' in result
                assert 'missing_required' in result
                assert 'warnings' in result
                assert 'errors' in result

    def test_strict_validation_mode(self):
        """Test strict validation mode"""
        with patch.dict(os.environ, {
            'CONFIG_VALIDATION_STRICT': '1',
            'ENVIRONMENT': 'production'
        }):
            validator = ConfigValidator()
            result = validator.validate_config()

            # Strict mode should catch more issues
            assert isinstance(result['valid'], bool)

    @patch('utils.config_validator.requests.get')
    def test_external_service_connectivity(self, mock_get):
        """Test external service connectivity checks"""
        # Mock successful response
        mock_get.return_value.status_code = 200

        with patch.dict(os.environ, {
            'OLLAMA_URL': 'http://localhost:11434',
            'OLLAMA_DISABLE': '0'
        }):
            validator = ConfigValidator()
            # This would test connectivity if implemented
            result = validator.validate_config()
            assert isinstance(result, dict)


if __name__ == '__main__':
    pytest.main([__file__])