"""Subprocess-boundary regression for inherited run_live output (synthetic markers only)."""

from __future__ import annotations

import subprocess
import sys
import unittest
from unittest.mock import patch

from scripts.dev.common import ToolingError, run_capture, run_live


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

    def test_capture_success_returns_sensitive_output_without_printing(self) -> None:
        """Captured output remains caller-sensitive and is not emitted by the wrapper."""
        import contextlib
        import io

        marker = "SYNTHETIC_CAPTURE_ONLY_MARKER"
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch(
            "scripts.dev.common.subprocess.run",
            return_value=subprocess.CompletedProcess(["tool"], 0, stdout=marker + "\n"),
        ) as spawn:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                captured = run_capture(["tool"])
        self.assertEqual(captured, marker)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(stderr.getvalue(), "")
        spawn.assert_called_once()
        self.assertEqual(spawn.call_args.kwargs["stderr"], subprocess.STDOUT)
        self.assertEqual(spawn.call_args.kwargs["stdout"], subprocess.PIPE)

    def test_invalid_argv_never_spawns_child(self) -> None:
        class CustomStr(str):
            pass

        invalid_commands = (
            "echo unsafe",
            b"echo unsafe",
            [],
            [CustomStr("echo"), "unsafe"],
            ["echo", CustomStr("unsafe")],
            ["echo", b"SYNTHETIC_ARG_MARKER"],
            ["echo", 123],
            ["echo", "bad" + chr(0) + "argument"],
            ["   ", "unsafe"],
        )
        for runner in (run_capture, run_live):
            with self.subTest(runner=runner.__name__):
                with patch("scripts.dev.common.subprocess.run") as spawn:
                    for command in invalid_commands:
                        with self.subTest(command_type=type(command).__name__):
                            with self.assertRaisesRegex(ToolingError, "^command failed$") as caught:
                                runner(command)
                            self.assertIsNone(caught.exception.__cause__)
                            # Direct validation failures have no chained exception;
                            # suppress_context is only required for caught exceptions.
                            if not isinstance(command, (str, bytes)):
                                self.assertTrue(caught.exception.__suppress_context__)
                    spawn.assert_not_called()


    def test_iterator_failure_never_spawns_child(self) -> None:
        class HostileIterator:
            def __iter__(self):
                raise RuntimeError("SENSITIVE_ITERATOR_MARKER")

        for runner in (run_capture, run_live):
            with self.subTest(runner=runner.__name__):
                with patch("scripts.dev.common.subprocess.run") as spawn:
                    with self.assertRaisesRegex(ToolingError, "^command failed$") as caught:
                        runner(HostileIterator())
                    self.assertIsNone(caught.exception.__cause__)
                    self.assertTrue(caught.exception.__suppress_context__)
                    spawn.assert_not_called()

    def test_partial_iteration_failure_never_spawns_child(self) -> None:
        class PartialIterator:
            def __iter__(self):
                yield "tool"
                raise RuntimeError("SENSITIVE_PARTIAL_ITERATION_MARKER")

        for runner in (run_capture, run_live):
            with self.subTest(runner=runner.__name__):
                with patch("scripts.dev.common.subprocess.run") as spawn:
                    with self.assertRaisesRegex(ToolingError, "^command failed$") as caught:
                        runner(PartialIterator())
                    self.assertIsNone(caught.exception.__cause__)
                    self.assertTrue(caught.exception.__suppress_context__)
                    spawn.assert_not_called()

    def test_length_hint_failure_never_spawns_child(self) -> None:
        class HostileLengthHint:
            def __iter__(self):
                return iter(["tool", "--version"])

            def __len__(self):
                raise RuntimeError("SENSITIVE_LENGTH_HINT_MARKER")

        for runner in (run_capture, run_live):
            with self.subTest(runner=runner.__name__):
                with patch("scripts.dev.common.subprocess.run") as spawn:
                    with self.assertRaisesRegex(ToolingError, "^command failed$") as caught:
                        runner(HostileLengthHint())
                    self.assertIsNone(caught.exception.__cause__)
                    self.assertTrue(caught.exception.__suppress_context__)
                    spawn.assert_not_called()

if __name__ == "__main__":
    unittest.main()
