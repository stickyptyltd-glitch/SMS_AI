#!/usr/bin/env python3
"""
Configuration Validation System
Validates environment-specific configurations and provides clear error messages.
"""

import os
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum


class Environment(Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class ValidationSeverity(Enum):
    ERROR = "error"      # Must be fixed before startup
    WARNING = "warning"  # Should be addressed but not blocking
    INFO = "info"       # Informational only


@dataclass
class ValidationResult:
    """Result of a single configuration validation check"""
    key: str
    severity: ValidationSeverity
    message: str
    current_value: Optional[str] = None
    suggested_value: Optional[str] = None


class ConfigValidator:
    """Validates application configuration for different environments"""

    def __init__(self, environment: Optional[Environment] = None):
        self.environment = environment or self._detect_environment()
        self.results: List[ValidationResult] = []

    def _detect_environment(self) -> Environment:
        """Auto-detect environment from common environment variables"""
        env_str = os.getenv("ENVIRONMENT", os.getenv("ENV", "development")).lower()

        if env_str in ("prod", "production"):
            return Environment.PRODUCTION
        elif env_str in ("stage", "staging"):
            return Environment.STAGING
        elif env_str in ("test", "testing"):
            return Environment.TESTING
        else:
            return Environment.DEVELOPMENT

    def validate_required_env_var(self, key: str, description: str = "") -> ValidationResult:
        """Validate that a required environment variable is set"""
        value = os.getenv(key)
        if not value:
            return ValidationResult(
                key=key,
                severity=ValidationSeverity.ERROR,
                message=f"Required environment variable {key} is not set. {description}".strip(),
                current_value=None
            )
        return ValidationResult(
            key=key,
            severity=ValidationSeverity.INFO,
            message=f"{key} is configured",
            current_value="***" if "secret" in key.lower() or "key" in key.lower() else value
        )

    def validate_url_format(self, key: str, required: bool = True) -> ValidationResult:
        """Validate that URL environment variable has correct format"""
        value = os.getenv(key)

        if not value:
            if required:
                return ValidationResult(
                    key=key,
                    severity=ValidationSeverity.ERROR,
                    message=f"URL environment variable {key} is required but not set"
                )
            else:
                return ValidationResult(
                    key=key,
                    severity=ValidationSeverity.INFO,
                    message=f"Optional URL {key} is not set"
                )

        # Basic URL validation
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        if not url_pattern.match(value):
            return ValidationResult(
                key=key,
                severity=ValidationSeverity.ERROR,
                message=f"{key} does not appear to be a valid URL: {value}",
                current_value=value,
                suggested_value="http://localhost:PORT or https://domain.com"
            )

        # Production-specific URL validation
        if self.environment == Environment.PRODUCTION and value.startswith("http://"):
            return ValidationResult(
                key=key,
                severity=ValidationSeverity.WARNING,
                message=f"Production environment should use HTTPS: {key}={value}",
                current_value=value,
                suggested_value=value.replace("http://", "https://")
            )

        return ValidationResult(
            key=key,
            severity=ValidationSeverity.INFO,
            message=f"{key} URL format is valid",
            current_value=value
        )

    def validate_boolean_env_var(self, key: str, default: str = "0") -> ValidationResult:
        """Validate boolean environment variables"""
        value = os.getenv(key, default)
        valid_true = ("1", "true", "yes", "on")
        valid_false = ("0", "false", "no", "off")

        if value.lower() not in valid_true + valid_false:
            return ValidationResult(
                key=key,
                severity=ValidationSeverity.WARNING,
                message=f"{key} should be a boolean value (1/0, true/false, yes/no, on/off), got: {value}",
                current_value=value,
                suggested_value="1 or 0"
            )

        return ValidationResult(
            key=key,
            severity=ValidationSeverity.INFO,
            message=f"{key} boolean value is valid",
            current_value=value
        )

    def validate_port_number(self, key: str, default: Optional[str] = None) -> ValidationResult:
        """Validate port number environment variables"""
        value = os.getenv(key, default)

        if not value:
            return ValidationResult(
                key=key,
                severity=ValidationSeverity.ERROR,
                message=f"Port number {key} is required but not set"
            )

        try:
            port = int(value)
            if port < 1 or port > 65535:
                raise ValueError("Port out of range")

            # Check for commonly problematic ports in production
            if self.environment == Environment.PRODUCTION:
                if port < 1024 and port != 80 and port != 443:
                    return ValidationResult(
                        key=key,
                        severity=ValidationSeverity.WARNING,
                        message=f"Port {port} requires root privileges. Consider using port > 1024",
                        current_value=value,
                        suggested_value="8080, 8081, or 3000"
                    )

            return ValidationResult(
                key=key,
                severity=ValidationSeverity.INFO,
                message=f"Port {key} is valid",
                current_value=value
            )

        except ValueError:
            return ValidationResult(
                key=key,
                severity=ValidationSeverity.ERROR,
                message=f"{key} must be a valid port number (1-65535), got: {value}",
                current_value=value,
                suggested_value="8081"
            )

    def validate_ai_configuration(self) -> List[ValidationResult]:
        """Validate AI-related configuration"""
        results = []

        # Check that at least one AI provider is configured
        has_openai = bool(os.getenv("OPENAI_API_KEY"))
        has_ollama = bool(os.getenv("OLLAMA_URL"))

        if not has_openai and not has_ollama:
            results.append(ValidationResult(
                key="AI_PROVIDER",
                severity=ValidationSeverity.ERROR,
                message="No AI provider configured. Set either OPENAI_API_KEY or OLLAMA_URL",
                current_value=None,
                suggested_value="Configure OpenAI or Ollama"
            ))

        # Validate OpenAI configuration
        if has_openai:
            results.append(self.validate_required_env_var("OPENAI_API_KEY", "OpenAI API key"))
            model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
            if not model.startswith(("gpt-", "text-")):
                results.append(ValidationResult(
                    key="OPENAI_MODEL",
                    severity=ValidationSeverity.WARNING,
                    message=f"OPENAI_MODEL '{model}' might not be a valid OpenAI model",
                    current_value=model,
                    suggested_value="gpt-3.5-turbo, gpt-4, or gpt-4-turbo"
                ))

        # Validate Ollama configuration
        if has_ollama:
            results.append(self.validate_url_format("OLLAMA_URL"))

        return results

    def validate_security_configuration(self) -> List[ValidationResult]:
        """Validate security-related configuration"""
        results = []

        # Admin credentials validation
        admin_secret = os.getenv("ADMIN_SECRET")
        if not admin_secret or admin_secret == "dev-secret" or admin_secret == "please-change-this":
            severity = ValidationSeverity.ERROR if self.environment == Environment.PRODUCTION else ValidationSeverity.WARNING
            results.append(ValidationResult(
                key="ADMIN_SECRET",
                severity=severity,
                message="ADMIN_SECRET should be a strong, unique value",
                current_value="***",
                suggested_value="Use a cryptographically secure random string"
            ))

        # License enforcement in production
        if self.environment == Environment.PRODUCTION:
            license_enforce = os.getenv("LICENSE_ENFORCE", "0")
            if license_enforce not in ("1", "true", "yes"):
                results.append(ValidationResult(
                    key="LICENSE_ENFORCE",
                    severity=ValidationSeverity.WARNING,
                    message="LICENSE_ENFORCE should be enabled in production",
                    current_value=license_enforce,
                    suggested_value="1"
                ))

        return results

    def validate_integration_configuration(self) -> List[ValidationResult]:
        """Validate external integration configuration"""
        results = []

        # Twilio configuration (if any Twilio env vars are present)
        twilio_vars = ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM"]
        twilio_configured = any(os.getenv(var) for var in twilio_vars)

        if twilio_configured:
            for var in twilio_vars:
                results.append(self.validate_required_env_var(var, f"Required for Twilio integration"))

        # Facebook configuration (if any FB env vars are present)
        fb_vars = ["FB_PAGE_TOKEN", "FB_VERIFY_TOKEN", "FB_APP_SECRET"]
        fb_configured = any(os.getenv(var) for var in fb_vars)

        if fb_configured:
            for var in fb_vars[:2]:  # PAGE_TOKEN and VERIFY_TOKEN are required
                results.append(self.validate_required_env_var(var, "Required for Facebook integration"))

            # APP_SECRET is recommended for security
            if not os.getenv("FB_APP_SECRET"):
                results.append(ValidationResult(
                    key="FB_APP_SECRET",
                    severity=ValidationSeverity.WARNING,
                    message="FB_APP_SECRET recommended for webhook signature verification",
                    current_value=None
                ))

        return results

    def validate_all(self) -> Tuple[List[ValidationResult], bool]:
        """Run all validation checks and return results"""
        self.results = []

        # Core configuration
        self.results.extend([
            self.validate_port_number("ADMIN_PORT", "5050"),
            self.validate_boolean_env_var("ADMIN_DEBUG", "0"),
            self.validate_boolean_env_var("LICENSE_ENFORCE", "0"),
        ])

        # AI configuration
        self.results.extend(self.validate_ai_configuration())

        # Security configuration
        self.results.extend(self.validate_security_configuration())

        # Integration configuration
        self.results.extend(self.validate_integration_configuration())

        # Check if any critical errors exist
        has_errors = any(r.severity == ValidationSeverity.ERROR for r in self.results)

        return self.results, not has_errors

    def print_results(self) -> None:
        """Print validation results in a formatted way"""
        print(f"\n🔍 Configuration Validation ({self.environment.value} environment)")
        print("=" * 60)

        errors = [r for r in self.results if r.severity == ValidationSeverity.ERROR]
        warnings = [r for r in self.results if r.severity == ValidationSeverity.WARNING]
        info = [r for r in self.results if r.severity == ValidationSeverity.INFO]

        if errors:
            print(f"\n❌ ERRORS ({len(errors)}) - Must be fixed:")
            for result in errors:
                print(f"  • {result.message}")
                if result.suggested_value:
                    print(f"    Suggestion: {result.suggested_value}")

        if warnings:
            print(f"\n⚠️  WARNINGS ({len(warnings)}) - Should be addressed:")
            for result in warnings:
                print(f"  • {result.message}")
                if result.suggested_value:
                    print(f"    Suggestion: {result.suggested_value}")

        if info:
            print(f"\n✅ OK ({len(info)}) - Properly configured:")
            for result in info:
                print(f"  • {result.message}")

        print(f"\n📊 Summary: {len(errors)} errors, {len(warnings)} warnings, {len(info)} OK")

        if errors:
            print("\n🚨 Application startup blocked due to configuration errors!")
            return False
        elif warnings:
            print(f"\n⚡ Application can start but {len(warnings)} issues should be addressed")
        else:
            print("\n🎉 All configuration checks passed!")

        return True


def validate_environment() -> bool:
    """Quick validation function for use in startup scripts"""
    validator = ConfigValidator()
    results, is_valid = validator.validate_all()
    validator.print_results()
    return is_valid


if __name__ == "__main__":
    # Command-line validation
    import sys
    if not validate_environment():
        sys.exit(1)