import os
import base64
import hmac
import hashlib
import json
import importlib
import unittest
from datetime import datetime, timedelta, timezone


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


class LicenseActivateTests(unittest.TestCase):
    def setUp(self):
        # Ensure clean state
        self.prev_enforce = os.environ.get('LICENSE_ENFORCE')
        self.prev_secret = os.environ.get('LICENSE_ISSUER_SECRET')
        os.environ['LICENSE_ENFORCE'] = '1'
        # Use a temporary secret for test
        self.secret = os.urandom(32)
        os.environ['LICENSE_ISSUER_SECRET'] = base64.b64encode(self.secret).decode()
        # Remove any existing license file
        try:
            os.remove('.dayle_license')
        except FileNotFoundError:
            pass
        # Import/reload server with new env
        import server as srv
        importlib.reload(srv)
        self.srv = srv
        self.client = srv.app.test_client()

    def tearDown(self):
        if self.prev_enforce is not None:
            os.environ['LICENSE_ENFORCE'] = self.prev_enforce
        else:
            os.environ.pop('LICENSE_ENFORCE', None)
        if self.prev_secret is not None:
            os.environ['LICENSE_ISSUER_SECRET'] = self.prev_secret
        else:
            os.environ.pop('LICENSE_ISSUER_SECRET', None)
        try:
            os.remove('.dayle_license')
        except FileNotFoundError:
            pass

    def test_activate_and_reply(self):
        # Build HS256 token with required fields
        header = {"alg": "HS256", "typ": "DAYLE-LIC"}
        payload = {
            "license_id": "LIC-TEST-001",
            "tier": "pro",
            "expires": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
            "hardware_id": "ANY",
            "issued": datetime.now(timezone.utc).isoformat(),
            "features": ["core", "assist"],
            "max_contacts": 10,
            "max_messages_per_day": 100,
            "support_level": "community",
        }
        h_b64 = b64url(json.dumps(header, separators=(",", ":")).encode())
        p_b64 = b64url(json.dumps(payload, separators=(",", ":")).encode())
        signing_input = f"{h_b64}.{p_b64}".encode()
        sig = hmac.new(self.secret, signing_input, hashlib.sha256).digest()
        token = f"{h_b64}.{p_b64}.{b64url(sig)}"

        # Activate
        r = self.client.post('/license/activate', json={"key": token})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json().get('ok'))

        # Status should be valid
        r = self.client.get('/license/status')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json().get('status'), 'valid')

        # With enforcement ON, /reply should now pass (mock LLM)
        with unittest.mock.patch.object(self.srv, 'call_ollama', return_value='Ok.'):
            r = self.client.post('/reply', json={"incoming": "Hi", "contact": "Tester"})
        self.assertEqual(r.status_code, 200)
        self.assertIn('draft', r.get_json())


if __name__ == '__main__':
    unittest.main()

