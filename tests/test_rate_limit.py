import os
import importlib
import unittest


class RateLimitTests(unittest.TestCase):
    def setUp(self):
        self.prev = os.environ.get('RATE_LIMIT_PER_MIN')
        os.environ['RATE_LIMIT_PER_MIN'] = '1'
        import server as srv
        importlib.reload(srv)
        self.srv = srv
        self.client = srv.app.test_client()

    def tearDown(self):
        if self.prev is not None:
            os.environ['RATE_LIMIT_PER_MIN'] = self.prev
        else:
            os.environ.pop('RATE_LIMIT_PER_MIN', None)

    def test_assist_rate_limit(self):
        # First request should pass
        r1 = self.client.post('/assist', json={"action": "ask_clarify"})
        self.assertNotEqual(r1.status_code, 429)
        # Second within window should be limited
        r2 = self.client.post('/assist', json={"action": "ask_clarify"})
        self.assertEqual(r2.status_code, 429)
        self.assertIn('Retry-After', r2.headers)


if __name__ == '__main__':
    unittest.main()

