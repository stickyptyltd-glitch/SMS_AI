import os
import importlib
import unittest


class LicenseEnforcementTests(unittest.TestCase):
    def setUp(self):
        # Enable license enforcement before importing server
        os.environ['LICENSE_ENFORCE'] = '1'
        # Ensure no existing license file
        try:
            import server as srv_existing
            importlib.reload(srv_existing)
        except Exception:
            pass
        import server as srv
        self.srv = srv
        self.client = srv.app.test_client()

    def test_reply_forbidden_without_license(self):
        r = self.client.post('/reply', json={"incoming": "hi", "contact": "X"})
        # When enforcement is on and license is missing, expect 403
        self.assertEqual(r.status_code, 403)
        data = r.get_json()
        self.assertEqual(data.get('error'), 'license')


if __name__ == '__main__':
    unittest.main()

