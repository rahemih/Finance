"""Subprocess-boundary regression for inherited run_live output (synthetic markers only)."""

from __future__ import annotations

import subprocess
import sys
import unittest


_CHILD = """
from scripts.dev.common import ToolingError, run_live
import sys
try:
    run_live([sys.executable, "-c",
              "import sys;sys.stdout.write('OUT_BOUNDARY_MARKER\\\\n');"
              "sys.stderr.write('ERR_BOUNDARY_MARKER\\\\n');"
              "sys.exit(int(sys.argv[1]))", sys.argv[1]])
except ToolingError as exc:
    sys.stderr.write("WRAPPER_ERROR:" + str(exc) + "\\n")
    sys.exit(23)
"""


class LiveOutputBoundaryTests(unittest.TestCase):
    def test_inherited_streams_are_not_redacted(self) -> None:
        for exit_code in (0, 7):
            with self.subTest(exit_code=exit_code):
                result = subprocess.run(
                    [sys.executable, "-c", _CHILD, str(exit_code)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0 if exit_code == 0 else 23)
                self.assertIn("OUT_BOUNDARY_MARKER", result.stdout)
                self.assertIn("ERR_BOUNDARY_MARKER", result.stderr)
                self.assertEqual(
                    "WRAPPER_ERROR:command failed" in result.stderr,
                    exit_code != 0,
                )
                # Sanitized wrapper errors must not append traceback details
                # or expose the child command; inherited child output remains visible.
                self.assertNotIn("Traceback (most recent call last)", result.stderr)
                self.assertNotIn("CalledProcessError", result.stderr)
                self.assertNotIn("subprocess.run(", result.stderr)


if __name__ == "__main__":
    unittest.main()
