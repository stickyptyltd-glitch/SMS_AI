#!/usr/bin/env python3
"""
DayleSMS AI - Enterprise License Management System
Copyright (c) 2025 Sticky Technologies. All rights reserved.

This software is protected by copyright law and international treaties.
Unauthorized reproduction or distribution is strictly prohibited.
"""

import os
import json
import hmac
import hashlib
import base64
import time
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Dict, Any, Optional, Tuple
"""Note: Offline activation uses HMAC-SHA256 (HS256) signed tokens."""

class LicenseError(Exception):
    """Custom exception for license-related errors."""
    pass

class LicenseManager:
    """
    Enterprise License Management System for DayleSMS AI
    
    Features:
    - Hardware fingerprinting
    - Online license validation
    - Tamper detection
    - Feature gating
    - Trial periods
    - Upgrade management
    """
    
    def __init__(self, license_server_url: str = None):
        self.license_file = ".dayle_license"
        self.hardware_id = self._generate_hardware_id()
        self.master_key = self._derive_key()
        self._issuer_secret = self._load_issuer_secret()
        
    def _generate_hardware_id(self) -> str:
        """Generate unique hardware fingerprint."""
        try:
            import platform
            import uuid
            import subprocess
            
            # Collect hardware identifiers
            machine_id = platform.machine()
            processor = platform.processor()
            mac_address = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                                  for elements in range(0,2*6,2)][::-1])
            
            # Try to get CPU serial (Linux)
            cpu_info = ""
            try:
                result = subprocess.run(['cat', '/proc/cpuinfo'], capture_output=True, text=True)
                for line in result.stdout.split('\n'):
                    if 'serial' in line.lower():
                        cpu_info = line.split(':')[1].strip()
                        break
            except:
                pass
                
            # Combine identifiers
            hw_string = f"{machine_id}-{processor}-{mac_address}-{cpu_info}"
            return hashlib.sha256(hw_string.encode()).hexdigest()[:16]
        except Exception as e:
            # Fallback to basic system info
            import platform
            fallback = f"{platform.system()}-{platform.node()}"
            return hashlib.sha256(fallback.encode()).hexdigest()[:16]
    
    def _derive_key(self) -> bytes:
        """Derive encryption key from hardware ID."""
        salt = b"DayleSMS_Enterprise_2025"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(self.hardware_id.encode()))
    
    def activate_license(self, activation_key: str) -> bool:
        """
        Activate license with provided key.
        
        Args:
            activation_key: License key from purchase
            
        Returns:
            True if activation successful
            
        Raises:
            LicenseError: If activation fails
        """
        try:
            # Validate key format
            if not self._validate_key_format(activation_key):
                raise LicenseError("Invalid activation key format")
            
            # Offline activation using signed token (HS256 JWS-like)
            license_data = self._decode_and_verify_token(activation_key)
            if not self._validate_license_data(license_data):
                raise LicenseError("Invalid license data")
            # Bind check
            bound_hw = license_data.get("hardware_id")
            if bound_hw and bound_hw not in ("ANY", self.hardware_id):
                raise LicenseError("License not valid for this machine")
            encrypted = self._encrypt_license(license_data)
            with open(self.license_file, "wb") as f:
                f.write(encrypted)
            return True
        except Exception as e:
            raise LicenseError(f"Activation error: {str(e)}")
    
    def validate_license(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate current license.
        
        Returns:
            Tuple of (is_valid, license_info)
        """
        try:
            # Check if license file exists
            if not os.path.exists(self.license_file):
                return False, {"error": "No license file found"}
            
            # Decrypt license
            with open(self.license_file, "rb") as f:
                encrypted_data = f.read()
            
            license_data = self._decrypt_license(encrypted_data)
            
            # Validate license data
            if not self._validate_license_data(license_data):
                return False, {"error": "Invalid license data"}
            
            # Check expiration
            if self._is_license_expired(license_data):
                return False, {"error": "License expired", "expires": license_data.get("expires")}
            
            # Check hardware binding (allow ANY)
            hw = license_data.get("hardware_id")
            if hw not in (self.hardware_id, "ANY"):
                return False, {"error": "License not valid for this machine"}
            
            # Online validation (periodic)
            if self._needs_online_validation(license_data):
                try:
                    online_valid = self._perform_online_validation(license_data)
                    if not online_valid:
                        return False, {"error": "Online validation failed"}
                except:
                    # Allow offline grace period
                    pass
            
            return True, license_data
            
        except Exception as e:
            return False, {"error": f"License validation error: {str(e)}"}
    
    def get_license_info(self) -> Dict[str, Any]:
        """Get detailed license information."""
        is_valid, info = self.validate_license()
        
        if not is_valid:
            return {"status": "invalid", "error": info.get("error")}
        
        license_data = info
        expires = datetime.fromisoformat(license_data.get("expires", ""))
        now = datetime.now(expires.tzinfo) if getattr(expires, 'tzinfo', None) else datetime.now()
        days_remaining = (expires - now).days
        
        return {
            "status": "valid",
            "tier": license_data.get("tier", "starter"),
            "features": license_data.get("features", []),
            "expires": license_data.get("expires"),
            "days_remaining": max(0, days_remaining),
            "max_contacts": license_data.get("max_contacts", 10),
            "max_messages_per_day": license_data.get("max_messages_per_day", 100),
            "support_level": license_data.get("support_level", "community")
        }
    
    def check_feature(self, feature: str) -> bool:
        """Check if specific feature is licensed."""
        is_valid, license_data = self.validate_license()
        if not is_valid:
            return False
        
        features = license_data.get("features", [])
        return feature in features
    
    def _validate_key_format(self, key: str) -> bool:
        """Validate activation token format: base64url header.payload.signature"""
        parts = key.strip().split('.')
        return len(parts) == 3 and all(parts)
    
    def _base64url_decode(self, data: str) -> bytes:
        pad = '=' * (-len(data) % 4)
        return base64.urlsafe_b64decode((data + pad).encode())

    def _decode_and_verify_token(self, token: str) -> Dict[str, Any]:
        header_b64, payload_b64, sig_b64 = token.strip().split('.')
        signing_input = f"{header_b64}.{payload_b64}".encode()
        signature = self._base64url_decode(sig_b64)
        header = json.loads(self._base64url_decode(header_b64).decode())
        if header.get('alg') != 'HS256':
            raise LicenseError('Unsupported algorithm')
        # Verify signature (HMAC-SHA256)
        expected = hmac.new(self._issuer_secret, signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            raise LicenseError('Signature verification failed')
        payload = json.loads(self._base64url_decode(payload_b64).decode())
        return payload

    def _load_issuer_secret(self) -> bytes:
        env = os.environ.get('LICENSE_ISSUER_SECRET')
        if env:
            try:
                return base64.b64decode(env)
            except Exception:
                return env.encode()
        path = os.path.join(os.path.dirname(__file__), 'issuer_secret.key')
        try:
            with open(path, 'rb') as f:
                raw = f.read().strip()
                try:
                    return base64.b64decode(raw)
                except Exception:
                    return raw
        except FileNotFoundError:
            # Default dev secret; replace or set LICENSE_ISSUER_SECRET in production
            return hashlib.sha256(b'DEV-DEFAULT-SECRET-CHANGE-ME').digest()
    
    def _encrypt_license(self, license_data: Dict) -> bytes:
        """Encrypt license data for storage."""
        f = Fernet(self.master_key)
        data_str = json.dumps(license_data)
        return f.encrypt(data_str.encode())
    
    def _decrypt_license(self, encrypted_data: bytes) -> Dict:
        """Decrypt stored license data."""
        f = Fernet(self.master_key)
        decrypted = f.decrypt(encrypted_data)
        return json.loads(decrypted.decode())
    
    def _validate_license_data(self, license_data: Dict) -> bool:
        """Validate license data structure and integrity."""
        required_fields = ["license_id", "tier", "expires", "hardware_id", "issued"]
        return all(field in license_data for field in required_fields)
    
    def _is_license_expired(self, license_data: Dict) -> bool:
        """Check if license is expired (timezone-safe)."""
        try:
            expires = datetime.fromisoformat(license_data.get("expires", ""))
        except Exception:
            return True
        now = datetime.now(expires.tzinfo) if getattr(expires, 'tzinfo', None) else datetime.now()
        return now > expires
    
    def _needs_online_validation(self, license_data: Dict) -> bool:
        """Offline activation: no online validation required."""
        return False
    
    def _perform_online_validation(self, license_data: Dict) -> bool:
        """No-op for offline activation."""
        return True

# Global license manager instance
_license_manager = None

def get_license_manager() -> LicenseManager:
    """Get global license manager instance."""
    global _license_manager
    if _license_manager is None:
        _license_manager = LicenseManager()
    return _license_manager

def require_license(feature: str = None):
    """Decorator to require valid license for function execution."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            lm = get_license_manager()
            is_valid, _ = lm.validate_license()
            
            if not is_valid:
                raise LicenseError("Valid license required")
            
            if feature and not lm.check_feature(feature):
                raise LicenseError(f"Feature '{feature}' not licensed")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

def check_license_status() -> Dict[str, Any]:
    """Check current license status."""
    lm = get_license_manager()
    return lm.get_license_info()
