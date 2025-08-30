import unittest
from unittest import mock

import server as srv
from ai.analysis import parse_json_safely
from ai.generator import postprocess_reply
from server import infer_goal, append_memory, load_memory
from server import choose_variant, update_policy, load_policy, fill_template, propose_times


class AnalysisTests(unittest.TestCase):
    def test_parse_json_safely(self):
        self.assertEqual(parse_json_safely('{"a":1}')["a"], 1)
        self.assertIsNone(parse_json_safely('not json'))
        self.assertEqual(parse_json_safely('x {"a":2} y')["a"], 2)

    def test_postprocess(self):
        prof = {"banned_words": ["never"], "max_reply_len": 10}
        self.assertEqual(postprocess_reply("This will never happen", prof), "This will…")

    def test_reply_flow_with_mock_llm(self):
        app = srv.app
        client = app.test_client()

        # Mock call_ollama in server module
        with mock.patch.object(srv, 'call_ollama') as co:
            # First call: analysis returns JSON
            co.side_effect = [
                '{"sentiment":"neutral","intent":"clarify","toxicity":0,"urgent":0}',
                'Ok. Let\'s keep it simple.'
            ]
            res = client.post('/reply', json={"incoming": "Can we talk?", "contact": "Courtney"})
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertIn('draft', data)
            self.assertIn('analysis', data)

    def test_goal_selection(self):
        self.assertEqual(infer_goal({"toxicity": 1}), "de-escalate+boundary")
        self.assertEqual(infer_goal({"intent": "setup_call"}), "move_to_call")
        self.assertEqual(infer_goal({"intent": "make_plan"}), "propose_time/place")
        self.assertEqual(infer_goal({"intent": "clarify"}), "ask_concise_question")
        self.assertEqual(infer_goal({"urgent": 1}), "acknowledge_then_brief_action")
        self.assertEqual(infer_goal({}), "acknowledge_and_close")

    def test_bandit_and_templates(self):
        v = choose_variant("acknowledge_and_close", "Tester", ["Ok.", "Noted."])
        self.assertIn(v, ["Ok.", "Noted."])
        update_policy("acknowledge_and_close", "Tester", v, 1.0)
        p = load_policy()
        self.assertIn("acknowledge_and_close::tester", p)
        t = fill_template("Free at {time1}", {"time1": "Mon 06:00PM"})
        self.assertIn("06:00PM", t)
        times = propose_times()
        self.assertIn("time1", times)

    def test_memory_append_and_load(self):
        contact = "Unit Test"
        append_memory(contact, {"incoming": "hi", "draft": "ok"})
        mem = load_memory(contact, limit=1)
        self.assertTrue(len(mem) >= 1)


if __name__ == '__main__':
    unittest.main()
