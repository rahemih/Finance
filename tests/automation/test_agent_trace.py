"""Tests for bounded, tamper-evident, no-trading journal."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[2] / "scripts" / "automation" / "agent_trace.py"
spec = importlib.util.spec_from_file_location("agent_trace", SOURCE)
assert spec and spec.loader
trace = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trace)

TASK = "FIN-P24-WZ-002"
AT = "2026-11-17T12:00:00Z"

class AgentTraceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "trace.jsonl"

    def record(self, **kwargs):
        params = dict(agent_id="A1", task_id=TASK, run_id="run-test-1",
                      event_type="TEST_STARTED", message="offline unit test",
                      target="tests/automation/test_agent_trace.py", at=AT)
        params.update(kwargs)
        return trace.append(self.path, **params)

    def test_append_chain_and_export(self):
        a = self.record()
        b = self.record(event_type="TEST_PASSED")
        self.assertEqual(b["seq"], 2)
        self.assertEqual(b["prev_hash"], a["event_hash"])
        self.assertEqual(len(trace.export_json(self.path)["events"]), 2)
        self.assertFalse(trace.export_json(self.path)["authenticated_agent_identity"])

    def test_modifying_message_is_detected(self):
        self.record()
        self.path.write_text(self.path.read_text().replace("offline unit test", "not real"))
        with self.assertRaises(trace.TraceError):
            trace.load(self.path)

    def test_deleted_first_event_is_detected(self):
        self.record()
        self.record()
        self.path.write_text(self.path.read_text().splitlines(True)[1])
        with self.assertRaises(trace.TraceError):
            trace.load(self.path)

    def test_rejects_live_mode_in_journal(self):
        self.record()
        text = self.path.read_text().replace("DEMO_ONLY", "LIVE")
        self.path.write_text(text)
        with self.assertRaises(trace.TraceError):
            trace.load(self.path)

    def test_rejects_secret_content(self):
        with self.assertRaises(trace.TraceError):
            self.record(message="api_key=abcdef123456")
        self.assertFalse(self.path.exists())

    def test_rejects_sensitive_target(self):
        with self.assertRaises(trace.TraceError):
            self.record(target="secrets/production.json")

    def test_rejects_traversal(self):
        with self.assertRaises(trace.TraceError):
            self.record(target="../config.yaml")

    def test_rejects_unknown_agent(self):
        with self.assertRaises(trace.TraceError):
            self.record(agent_id="A99")

    def test_rejects_unknown_action(self):
        with self.assertRaises(trace.TraceError):
            self.record(event_type="ENABLE_LIVE")

    def test_rejects_invalid_task(self):
        with self.assertRaises(trace.TraceError):
            self.record(task_id="P24")

    def test_rejects_extra_fields(self):
        e = self.record()
        import json
        e["token"] = "abc"
        self.path.write_text(json.dumps(e) + "\n")
        with self.assertRaises(trace.TraceError):
            trace.load(self.path)

    def test_rejects_repeat_seq(self):
        self.record()
        self.path.write_text(self.path.read_text() * 2)
        with self.assertRaises(trace.TraceError):
            trace.load(self.path)

    def test_rejects_local_time(self):
        with self.assertRaises(trace.TraceError):
            self.record(at="2026-11-17T12:00:00")

    def test_empty_export_not_completion(self):
        r = trace.export_json(self.path)
        self.assertEqual(r["events"], [])
        self.assertFalse(r["authenticated_agent_identity"])

if __name__ == "__main__":
    unittest.main()
