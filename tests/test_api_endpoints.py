import os
import unittest
from unittest import mock

import server as srv


class ApiEndpointTests(unittest.TestCase):
    def setUp(self):
        os.environ['LICENSE_ENFORCE'] = '0'
        self.app = srv.app
        self.client = self.app.test_client()

    def test_health_and_privacy(self):
        r = self.client.get('/health')
        self.assertEqual(r.status_code, 200)
        r = self.client.get('/privacy')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'Privacy Policy', r.data)

    def test_profile_get_post(self):
        # Get default
        r = self.client.get('/profile')
        self.assertEqual(r.status_code, 200)
        prof = r.get_json()
        self.assertIn('style_rules', prof)
        # Update preferred phrases
        new_pref = ["Ok.", "Noted."]
        r = self.client.post('/profile', json={"preferred_phrases": new_pref})
        self.assertEqual(r.status_code, 200)
        r = self.client.get('/profile')
        self.assertEqual(r.get_json().get('preferred_phrases'), new_pref)

    def test_assist_endpoint(self):
        with mock.patch.object(srv, 'choose_variant', return_value='Let\'s call at {time1}'):
            r = self.client.post('/assist', json={"action": "move_to_call", "incoming": "call?", "contact": "Tester"})
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIn('text', data)
        self.assertEqual(data.get('goal'), 'move_to_call')

    def test_memory_endpoints_and_goals(self):
        contact = 'API Test'
        # Create a reply to store memory (mock model)
        with mock.patch.object(srv, 'call_ollama', return_value='Ok.'):
            r = self.client.post('/reply', json={"incoming": "Hello", "contact": contact})
        self.assertEqual(r.status_code, 200)
        r = self.client.get(f'/memory?contact={contact}&limit=5')
        self.assertEqual(r.status_code, 200)
        items = r.get_json().get('items') or []
        self.assertTrue(len(items) >= 1)
        # Goals endpoint
        r = self.client.get(f'/goals?contact={contact}&limit=5')
        self.assertEqual(r.status_code, 200)
        self.assertIn('goals', r.get_json())
        # Delete memory
        r = self.client.delete(f'/memory?contact={contact}')
        self.assertEqual(r.status_code, 200)

    def test_metrics_increments(self):
        # Snapshot before
        m1 = self.client.get('/metrics').data.decode()
        with mock.patch.object(srv, 'call_ollama', return_value='Ok.'):
            self.client.post('/reply', json={"incoming": "Hi", "contact": "M"})
        self.client.post('/assist', json={"action": "ask_clarify"})
        m2 = self.client.get('/metrics').data.decode()
        self.assertNotEqual(m1, m2)


if __name__ == '__main__':
    unittest.main()

