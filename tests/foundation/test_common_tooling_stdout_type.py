"""Regression for hostile captured stdout subclasses (stdlib only)."""

import subprocess
import unittest
from unittest.mock import patch

from scripts.dev import common


class CapturedStdoutTypeTests(unittest.TestCase):
    def test_str_subclass_strip_is_never_called(self):
        class HostileStdout(str):
            def strip(self, *args, **kwargs):
                raise RuntimeError("SENSITIVE_HOSTILE_STDOUT_MARKER")

        result = subprocess.CompletedProcess(["tool"], 0, stdout=HostileStdout("secret"))
        with patch.object(common.subprocess, "run", return_value=result):
            with self.assertRaisesRegex(common.ToolingError, "^command failed$") as caught:
                common.run_capture(["tool"])
        self.assertIsNone(caught.exception.__cause__)
        self.assertTrue(caught.exception.__suppress_context__)

    def test_missing_or_binary_stdout_fails_closed(self):
        for stdout in (None, b"UNSAFE_BINARY_OUTPUT_MARKER"):
            with self.subTest(stdout_type=type(stdout).__name__):
                result = subprocess.CompletedProcess(["tool"], 0, stdout=stdout)
                with patch.object(common.subprocess, "run", return_value=result):
                    with self.assertRaisesRegex(common.ToolingError, "^command failed$") as caught:
                        common.run_capture(["tool"])
                self.assertIsNone(caught.exception.__cause__)
                self.assertTrue(caught.exception.__suppress_context__)

    def test_plain_str_still_strips(self):
        result = subprocess.CompletedProcess(["tool"], 0, stdout=" ok \n")
        with patch.object(common.subprocess, "run", return_value=result):
            self.assertEqual(common.run_capture(["tool"]), "ok")


if __name__ == "__main__":
    unittest.main()
