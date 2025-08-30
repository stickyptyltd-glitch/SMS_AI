import os
import unittest
from unittest import mock

import server as srv


class ReplyFallbackTests(unittest.TestCase):
    def setUp(self):
        os.environ['LICENSE_ENFORCE'] = '0'
        self.client = srv.app.test_client()

    def test_reply_fallback_on_llm_error(self):
        # Force call_ollama to raise and ensure we still get 200 with a draft
        with mock.patch.object(srv, 'call_ollama', side_effect=RuntimeError('LLM down')):
            r = self.client.post('/reply', json={"incoming": "Can we talk?", "contact": "Courtney"})
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIn('draft', data)
        self.assertTrue(data.get('analysis', {}).get('llm_failed'))


if __name__ == '__main__':
    unittest.main()

