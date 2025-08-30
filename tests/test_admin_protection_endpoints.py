import os
import importlib
import unittest


class AdminProtectionEndpointsTests(unittest.TestCase):
    def setUp(self):
        self.prev = os.environ.get('ADMIN_TOKEN')
        os.environ['ADMIN_TOKEN'] = 'secret'
        import server as srv
        importlib.reload(srv)
        self.srv = srv
        self.client = srv.app.test_client()

    def tearDown(self):
        if self.prev is not None:
            os.environ['ADMIN_TOKEN'] = self.prev
        else:
            os.environ.pop('ADMIN_TOKEN', None)

    def test_profile_post_requires_admin(self):
        r = self.client.post('/profile', json={"style_rules": "Short."})
        self.assertEqual(r.status_code, 401)
        r = self.client.post('/profile?token=secret', json={"style_rules": "Short."})
        self.assertEqual(r.status_code, 200)

    def test_memory_delete_requires_admin(self):
        r = self.client.delete('/memory?contact=Unit')
        self.assertEqual(r.status_code, 401)
        r = self.client.delete('/memory?contact=Unit&token=secret')
        self.assertEqual(r.status_code, 200)


if __name__ == '__main__':
    unittest.main()

