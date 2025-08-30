import os
import json
import unittest

import server as srv


class LicenseApiTests(unittest.TestCase):
    def setUp(self):
        os.environ['LICENSE_ENFORCE'] = '0'
        self.client = srv.app.test_client()

    def test_hwid(self):
        r = self.client.get('/license/hwid')
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIn('hardware_id', data)

    def test_status_unlicensed(self):
        r = self.client.get('/license/status')
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIn('status', data)

    def test_activate_missing_key(self):
        r = self.client.post('/license/activate', json={})
        self.assertEqual(r.status_code, 400)
        data = r.get_json()
        self.assertFalse(data['ok'])


class MetricsTests(unittest.TestCase):
    def setUp(self):
        self.client = srv.app.test_client()

    def test_metrics_format(self):
        r = self.client.get('/metrics')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'smsai_uptime_seconds', r.data)


if __name__ == '__main__':
    unittest.main()

