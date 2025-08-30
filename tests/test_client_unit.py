import os
import hmac
import hashlib
import unittest
from unittest import mock

import test_client as tc


class ValidationTests(unittest.TestCase):
    def test_validate_phone_ok(self):
        tc._validate_phone("+15551234567")

    def test_validate_phone_bad(self):
        with self.assertRaises(SystemExit) as cm:
            tc._validate_phone("1234")
        self.assertEqual(cm.exception.code, 2)

    def test_validate_text_ok(self):
        tc._validate_text("hello")

    def test_validate_text_bad(self):
        with self.assertRaises(SystemExit) as cm:
            tc._validate_text("   ")
        self.assertEqual(cm.exception.code, 2)

    def test_xml_escape(self):
        s = '<&"\'>'
        esc = tc._xml_escape(s)
        self.assertIn("&lt;", esc)
        self.assertIn("&amp;", esc)
        self.assertIn("&quot;", esc)
        self.assertIn("&apos;", esc)


class FbSigTests(unittest.TestCase):
    def test_fb_sig_ok(self):
        secret = "shh"
        payload = b"body"
        digest = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        header = f"sha256={digest}"
        self.assertTrue(tc._verify_fb_sig(secret, payload, header))

    def test_fb_sig_bad(self):
        self.assertFalse(tc._verify_fb_sig("shh", b"body", "sha256=deadbeef"))


class FlaskWebhookTests(unittest.TestCase):
    def test_twilio_sms_twiML(self):
        app = tc.create_twilio_app(from_number=None, auto=False)
        client = app.test_client()
        resp = client.post("/sms", data={"From": "+15551230001", "Body": "hi"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"<Response>", resp.data)

    def test_messenger_verify(self):
        app = tc.create_messenger_app(verify_token="verify", app_secret=None, page_token=None, auto=False)
        client = app.test_client()
        resp = client.get("/webhook?hub.mode=subscribe&hub.verify_token=verify&hub.challenge=123")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data, b"123")

    def test_messenger_invalid_sig(self):
        app = tc.create_messenger_app(verify_token="verify", app_secret="shh", page_token=None, auto=False)
        client = app.test_client()
        resp = client.post("/webhook", data=b"{}", headers={"X-Hub-Signature-256": "sha256=deadbeef"})
        self.assertEqual(resp.status_code, 403)

    def test_messenger_receive_draft(self):
        app = tc.create_messenger_app(verify_token="verify", app_secret=None, page_token=None, auto=False)
        client = app.test_client()
        with mock.patch.object(tc, "api_reply", return_value={"draft": "ok"}):
            resp = client.post(
                "/webhook",
                json={
                    "entry": [
                        {
                            "messaging": [
                                {"sender": {"id": "psid"}, "message": {"text": "hi"}}
                            ]
                        }
                    ]
                },
            )
        self.assertEqual(resp.status_code, 200)


class LocalClientTests(unittest.TestCase):
    def test_local_reply_ok(self):
        with mock.patch("requests.post") as p:
            m = mock.Mock(); m.json.return_value = {"draft": "hey"}; m.raise_for_status.return_value = None
            p.return_value = m
            res = tc.LOCAL.reply("hi", "Tester")
            self.assertEqual(res["draft"], "hey")

    def test_local_reply_error(self):
        with mock.patch("requests.post", side_effect=Exception("boom")):
            with self.assertRaises(tc.ClientError):
                tc.LOCAL.reply("hi", "Tester")


if __name__ == "__main__":
    unittest.main()

