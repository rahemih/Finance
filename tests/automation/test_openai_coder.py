"""Offline, non-network acceptance tests for ChatGPT/OpenAI model runner boundaries."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.automation import openai_coder as oc
from scripts.automation import openai_verify as ov

BASE = "a" * 40
SOURCE = "scripts/dev/common.py"
TEST = "tests/foundation/test_dev_common.py"

def output(files):
    return {"status": "completed", "output": [{"type": "message", "content": [
        {"type": "output_text", "text": json.dumps({"summary": "Fix sanitized failures and tests",
                                                      "files": files})}
    ]}]}

def candidate_report(proposal):
    blob = json.dumps(proposal, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return {"schema": "nq.autocode.candidate.v1", "task_id": oc.TASK_ID,
            "mode": "DEMO_ONLY", "status": "CANDIDATE_UNTESTED",
            "base_sha": BASE, "attempts": 1, "reason": None,
            "files": sorted(item["path"] for item in proposal["files"]),
            "proposal_sha256": hashlib.sha256(blob).hexdigest(),
            "model": "test-model", "tests": "NOT_RUN", "live_enabled": False,
            "code_execution": "NEVER_IN_GENERATOR"}

class GenerateTests(unittest.TestCase):
    def test_successful_response_is_data_not_execution(self):
        reply = output([{"path": SOURCE, "content": "def safe():\n    return True\n"}])
        self.assertEqual(oc.parse_output(reply)["files"][0]["path"], SOURCE)
        changed = oc.verify_candidate(oc.parse_output(reply), {SOURCE: "def safe():\n    return False\n"})
        self.assertIn(SOURCE, changed)

    def test_incomplete_model_response_fails_closed(self):
        with self.assertRaises(oc.RunnerError):
            oc.parse_output({"status": "incomplete", "output": []})

    def test_malformed_json_fails_closed(self):
        with self.assertRaises(oc.RunnerError):
            oc.parse_output({"status": "completed", "output": [{
                "type": "message", "content": [{"type": "output_text", "text": "not json"}]}]})

    def test_unexpected_trading_file_rejected(self):
        proposal = {"summary": "Modify trading tool incorrectly", "files": [
            {"path": ".github/workflows/governance.yml", "content": "on: true"}]}
        with self.assertRaises(oc.RunnerError):
            oc.verify_candidate(proposal, {SOURCE: "x=1\n"})

    def test_secret_configuration_blocks_inference_without_network(self):
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(oc, "get_sha", return_value=BASE), \
             patch.object(oc, "snapshot_files", return_value={SOURCE: "a=1\n"}), \
             patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=True):
            state = oc.generate(Path(temp) / "candidate.json",
                                call=lambda *args: self.fail("must not invoke model"))
        self.assertEqual(state["status"], "BLOCKED")
        self.assertEqual(state["reason"], "OPENAI_API_KEY_NOT_CONFIGURED")
        self.assertFalse(state["live_enabled"])

    def test_successful_mock_model_records_only_candidate(self):
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(oc, "get_sha", return_value=BASE), \
             patch.object(oc, "snapshot_files", return_value={SOURCE: "a=1\n"}), \
             patch.dict("os.environ", {"OPENAI_API_KEY": "placeholder-test-only",
                                       "NQ_OPENAI_MODEL": "test-model"}, clear=True):
            proposal = Path(temp) / "proposal.json"
            state = oc.generate(proposal, call=lambda *args: output([
                {"path": SOURCE, "content": "a=2\n"}]))
            self.assertEqual(state["status"], "CANDIDATE_UNTESTED")
            self.assertEqual(state["tests"], "NOT_RUN")
            self.assertEqual(state["code_execution"], "NEVER_IN_GENERATOR")
            self.assertTrue(proposal.is_file())

    def test_failed_candidate_retries_no_more_than_two(self):
        calls = []
        def bad_model(*args):
            calls.append(1)
            return {"status": "incomplete", "output": []}
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(oc, "get_sha", return_value=BASE), \
             patch.object(oc, "snapshot_files", return_value={SOURCE: "a=1\n"}), \
             patch.dict("os.environ", {"OPENAI_API_KEY": "placeholder-test-only"}, clear=True):
            report = oc.generate(Path(temp) / "proposal.json", call=bad_model)
        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual(len(calls), 2)

    def test_path_traversal_and_invalid_python_are_rejected(self):
        for p, txt in [("../secrets.py", "x=1"),
                       (SOURCE, "def broken(:\n  pass")]:
            with self.subTest(path=p), self.assertRaises(oc.RunnerError):
                oc.verify_candidate({"summary": "Valid summary for test",
                                     "files": [{"path": p, "content": txt}]},
                                    {SOURCE: "a=1\n"})

class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.proposal = self.folder / "proposal.json"
        self.candidate = self.folder / "candidate.json"
        data = {"schema": "nq.autocode.proposal.v1",
                "task_id": oc.TASK_ID, "base_sha": BASE,
                "files": [{"path": SOURCE, "content": "x=2\n"}]}
        self.proposal.write_text(json.dumps(data), encoding="utf-8")
        self.candidate.write_text(json.dumps(candidate_report(data)), encoding="utf-8")

    def test_candidate_digests_and_files_match(self):
        proposal, report = ov.load_proposal(self.proposal, self.candidate, head=BASE)
        self.assertEqual(proposal["files"][0]["path"], SOURCE)
        self.assertEqual(report["status"], "CANDIDATE_UNTESTED")

    def test_sha_mismatch_and_modified_artifacts_fail(self):
        with self.assertRaises(ov.GateError):
            ov.load_proposal(self.proposal, self.candidate, head="b"*40)
        self.proposal.write_text(self.proposal.read_text() + " ", encoding="utf-8")
        # Canonical JSON digest intentionally strips untrusted whitespace;
        # content corruption rather than whitespace must be rejected.
        data = json.loads(self.proposal.read_text())
        data["files"][0]["content"] = "x=3\n"
        self.proposal.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ov.GateError):
            ov.load_proposal(self.proposal, self.candidate, head=BASE)

    def test_cannot_fake_verified_tests(self):
        verified = self.folder / "verified.json"
        ov.finalize(self.proposal, self.candidate, verified, head=BASE)
        data = json.loads(verified.read_text())
        self.assertEqual(data["review"], "NOT_VERIFIED")
        self.assertFalse(data["merge"])
        self.assertTrue(ov.publish_check(self.proposal, self.candidate,
                                         verified, head=BASE)["tests_pass"])
        data["mode"] = "LIVE"
        verified.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ov.GateError):
            ov.publish_check(self.proposal, self.candidate, verified, head=BASE)

if __name__ == "__main__":
    unittest.main()
