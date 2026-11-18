"""Credential-free end-to-end simulation: model proposal → real code test → verified publish.

No external OpenAI calls, credentials, GitHub writes, or live trading.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts.automation import openai_coder as oc
from scripts.automation import openai_verify as ov

TEST_COMMON = """def run_capture(command):
    try:
        raise ValueError("secret-argument")
    except Exception:
        raise RuntimeError("sanitized command failure") from None
"""
TEST_REGRESSION = """import unittest
from scripts.dev.common import run_capture

class CommonTests(unittest.TestCase):
    def test_does_not_expose_secret_argument(self):
        try:
            run_capture(["tool", "secret-argument"])
        except RuntimeError as exc:
            self.assertEqual(str(exc), "sanitized command failure")
        else:
            self.fail("Expected diagnostic exception")
"""

def call_command(root: Path, args: list[str]):
    result=subprocess.run(args,cwd=root,capture_output=True,text=True,timeout=25)
    if result.returncode:
        raise AssertionError(result.stdout[-1200:] + "\n" + result.stderr[-1200:])
    return result.stdout

class EndToEndSimulation(unittest.TestCase):
    def test_proposed_code_runs_only_in_tokenless_validation_and_can_be_published(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            source=root/"scripts/dev/common.py"
            source.parent.mkdir(parents=True)
            source.write_text("def run_capture(command):\n    raise ValueError('raw secret')\n",encoding="utf-8")
            (root/".gitignore").write_text("build/\n__pycache__/\n*.pyc\n",encoding="utf-8")
            call_command(root,["git","init","-q"])
            call_command(root,["git","config","user.name","Test Actor"])
            call_command(root,["git","config","user.email","test@example.invalid"])
            call_command(root,["git","add","scripts/dev/common.py",".gitignore"])
            call_command(root,["git","commit","-qm","fixture initial"])
            sha=call_command(root,["git","rev-parse","HEAD"]).strip()
            proposal_file=root/"build/proposal.json"
            report_file=root/"build/generation.json"
            verified_file=root/"build/verified.json"

            def mocked_model(*args):
                return {"status":"completed","output":[{"type":"message","content":[{
                    "type":"output_text","text":json.dumps({
                        "summary":"Sanitize tool errors with deterministic unit test",
                        "files":[{"path":"scripts/dev/common.py","content":TEST_COMMON},
                                 {"path":"tests/foundation/test_dev_common.py","content":TEST_REGRESSION}]
                    })
                }]}]}

            with patch.object(oc,"get_sha",return_value=sha), \
                 patch.object(oc,"snapshot_files",return_value={
                     "scripts/dev/common.py":source.read_text()}), \
                 patch.dict(os.environ,{"OPENAI_API_KEY":"test-synthetic-only",
                                        "NQ_OPENAI_MODEL":"test-model"}):
                report=oc.generate(proposal_file,call=mocked_model)
            self.assertEqual(report["status"],"CANDIDATE_UNTESTED")
            self.assertEqual(report["tests"],"NOT_RUN")
            self.assertTrue(proposal_file.exists())
            report_file.parent.mkdir(parents=True,exist_ok=True)
            report_file.write_text(json.dumps(report),encoding="utf-8")

            with patch.object(ov,"ROOT",root):
                ov.apply_proposal(proposal_file,report_file,head=sha)
            self.assertTrue((root/"tests/foundation/test_dev_common.py").exists())

            # Actual generated Python is executed here, in a different stage
            # than the mocked model secret-bearing generation call.
            call_command(root,[sys.executable,"-m","unittest","discover",
                               "-s","tests/foundation","-p","test_*.py","-v"])

            with patch.object(ov,"ROOT",root):
                verified=ov.finalize(proposal_file,report_file,verified_file,head=sha)
            self.assertTrue(verified["tests_pass"])
            self.assertFalse(verified["merge"])

            # New publisher job gets fresh main checkout with NO changed files.
            call_command(root,["git","reset","--hard","HEAD"])
            (root/"tests/foundation/test_dev_common.py").unlink()
            with patch.object(ov,"ROOT",root):
                publish=ov.publish_check(proposal_file,report_file,verified_file,head=sha)
                ov.apply_proposal(proposal_file,report_file,head=sha)
            self.assertEqual(publish["review"],"NOT_VERIFIED")
            status=call_command(root,["git","status","--short","--untracked-files=all"])
            self.assertIn("scripts/dev/common.py",status)
            self.assertIn("tests/foundation/test_dev_common.py",status)
            self.assertNotIn("credentials",status)

if __name__ == "__main__":
    unittest.main()
