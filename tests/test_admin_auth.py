import os
import importlib
import unittest


class AdminAuthTests(unittest.TestCase):
    def setUp(self):
        self.prev = os.environ.get('ADMIN_TOKEN')
        os.environ['ADMIN_TOKEN'] = 'secret'
        import server as srv
        importlib.reload(srv)
        self.client = srv.app.test_client()

    def tearDown(self):
        if self.prev is not None:
            os.environ['ADMIN_TOKEN'] = self.prev
        else:
            os.environ.pop('ADMIN_TOKEN', None)

    def test_admin_requires_token(self):
        r = self.client.get('/admin')
        self.assertEqual(r.status_code, 401)
        r = self.client.get('/admin?token=secret')
        self.assertEqual(r.status_code, 200)


if __name__ == '__main__':
    unittest.main()

