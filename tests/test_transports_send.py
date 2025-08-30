import unittest
from unittest import mock

import test_client as tc


class TwilioSendTests(unittest.TestCase):
    def test_twilio_send_sms(self):
        fake_msg = type("Msg", (), {"sid": "SM123", "status": "queued"})
        fake_client = type("Client", (), {"messages": type("M", (), {"create": lambda self, **k: fake_msg})()})
        with mock.patch.object(tc, "_twilio_client", return_value=fake_client):
            res = tc.TwilioTransport("+15550000000").send_sms("+15551112222", "Hi")
            self.assertEqual(res["sid"], "SM123")


class MessengerSendTests(unittest.TestCase):
    def test_fb_send_ok(self):
        class R:
            def raise_for_status(self):
                return None
            def json(self):
                return {"message_id": "mid.123"}
        with mock.patch("requests.post", return_value=R()):
            res = tc._fb_send("PSID", "Hello", page_token="TOKEN")
            self.assertIn("message_id", res)


if __name__ == '__main__':
    unittest.main()

