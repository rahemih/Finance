"""Regression coverage: subprocess timeout must not leak command or output."""
from __future__ import annotations

import subprocess
import traceback
import unittest
from unittest.mock import patch

from scripts.dev import common


class SubprocessTimeoutRedactionTests(unittest.TestCase):
    def test_timeout_redacts_command_and_output_for_both_wrappers(self) -> None:
        marker = "SENSITIVE_TIMEOUT_MARKER_DO_NOT_LOG"
        command = ["tool", "--token", marker]
        for wrapper in (common.run_capture, common.run_live):
            with self.subTest(wrapper=wrapper.__name__):
                failure = subprocess.TimeoutExpired(command, 1, output=marker.encode(), stderr=marker.encode())
                with patch.object(common.subprocess, "run", side_effect=failure) as spawn:
                    with self.assertRaises(common.ToolingError) as caught:
                        wrapper(command)
                    spawn.assert_called_once()
                error = caught.exception
                self.assertEqual(str(error), "command failed")
                self.assertIsNone(error.__cause__)
                self.assertTrue(error.__suppress_context__)
                self.assertNotIn(marker, "".join(traceback.format_exception(error)))


if __name__ == "__main__":
    unittest.main()
