"""Regression tests for secret-safe developer command wrappers (stdlib only)."""

from __future__ import annotations

import subprocess
import traceback
import unittest
from unittest.mock import patch

from scripts.dev import common


class CommonToolingSafetyTests(unittest.TestCase):
    def test_capture_success_strips_whitespace(self) -> None:
        completed = subprocess.CompletedProcess(["git", "--version"], 0, stdout=" git version 2.0 \n")
        with patch.object(common.subprocess, "run", return_value=completed) as runner:
            self.assertEqual(common.run_capture(["git", "--version"]), "git version 2.0")
            self.assertEqual(runner.call_args.kwargs["cwd"], common.ROOT)
            self.assertTrue(runner.call_args.kwargs["check"])

    def test_capture_uses_argv_not_shell_and_merges_stderr(self) -> None:
        completed = subprocess.CompletedProcess(["tool", "--version"], 0, stdout="ok\n")
        with patch.object(common.subprocess, "run", return_value=completed) as runner:
            self.assertEqual(common.run_capture(["tool", "--version"]), "ok")
        runner.assert_called_once_with(
            ["tool", "--version"],
            cwd=common.ROOT,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

    def test_capture_nonzero_exit_fails_closed_without_command_in_error(self) -> None:
        secret = "SENSITIVE_NONZERO_ARG_MARKER"
        command = ["tool", "--token", secret]
        failure = subprocess.CalledProcessError(127, command, output=secret)
        with patch.object(common.subprocess, "run", side_effect=failure):
            with self.assertRaises(common.ToolingError) as caught:
                common.run_capture(command)
        self.assertEqual(str(caught.exception), "command failed")
        self.assertIsNone(caught.exception.__cause__)
        self.assertNotIn(secret, repr(caught.exception.args))

    def test_capture_failure_does_not_echo_secret_output(self) -> None:
        secret = "SENSITIVE_TEST_MARKER_DO_NOT_LOG"
        failure = subprocess.CalledProcessError(1, ["tool", "--check"], output=secret, stderr=secret)
        with patch.object(common.subprocess, "run", side_effect=failure):
            with self.assertRaises(common.ToolingError) as caught:
                common.run_capture(["tool", "--check"])
        self.assertNotIn(secret, str(caught.exception))
        self.assertIn("command failed", str(caught.exception))

    def test_live_failure_does_not_echo_secret_output(self) -> None:
        secret = "SENSITIVE_TEST_MARKER_DO_NOT_LOG"
        failure = subprocess.CalledProcessError(1, ["tool", "--check"], output=secret, stderr=secret)
        with patch.object(common.subprocess, "run", side_effect=failure):
            with self.assertRaises(common.ToolingError) as caught:
                common.run_live(["tool", "--check"])
        self.assertNotIn(secret, str(caught.exception))

    def test_capture_traceback_redacts_secret_arguments_and_output(self) -> None:
        secret = "SENSITIVE_ARGUMENT_AND_OUTPUT_MARKER"
        command = ["tool", "--token", secret]
        failure = subprocess.CalledProcessError(1, command, output=secret, stderr=secret)
        with patch.object(common.subprocess, "run", side_effect=failure):
            try:
                common.run_capture(command)
            except common.ToolingError as exc:
                rendered = "".join(traceback.format_exception(exc))
                self.assertNotIn(secret, rendered)
                self.assertNotIn("--token", rendered)
                self.assertTrue(exc.__suppress_context__)
            else:
                self.fail("expected ToolingError")

    def test_live_traceback_redacts_secret_arguments(self) -> None:
        secret = "SENSITIVE_LIVE_ARGUMENT_MARKER"
        command = ["tool", "--token", secret]
        failure = subprocess.CalledProcessError(1, command)
        with patch.object(common.subprocess, "run", side_effect=failure):
            try:
                common.run_live(command)
            except common.ToolingError as exc:
                self.assertNotIn(secret, "".join(traceback.format_exception(exc)))
                self.assertTrue(exc.__suppress_context__)
            else:
                self.fail("expected ToolingError")

    def test_capture_oserror_traceback_does_not_disclose_secret(self) -> None:
        secret = "SENSITIVE_OSERROR_MARKER"
        with patch.object(common.subprocess, "run", side_effect=OSError(secret)):
            try:
                common.run_capture(["missing-tool", "--token", secret])
            except common.ToolingError as exc:
                self.assertNotIn(secret, "".join(traceback.format_exception(exc)))
                self.assertTrue(exc.__suppress_context__)
            else:
                self.fail("expected ToolingError")

    def test_live_oserror_traceback_does_not_disclose_secret(self) -> None:
        secret = "SENSITIVE_LIVE_OSERROR_MARKER"
        with patch.object(common.subprocess, "run", side_effect=OSError(secret)):
            try:
                common.run_live(["missing-tool", "--token", secret])
            except common.ToolingError as exc:
                self.assertNotIn(secret, "".join(traceback.format_exception(exc)))
                self.assertTrue(exc.__suppress_context__)
            else:
                self.fail("expected ToolingError")

    def test_live_success_uses_repository_root_and_check(self) -> None:
        with patch.object(common.subprocess, "run") as runner:
            common.run_live(["git", "status"])
        runner.assert_called_once_with(["git", "status"], cwd=common.ROOT, check=True)

    def test_live_missing_binary_fails_closed(self) -> None:
        with patch.object(common.subprocess, "run", side_effect=FileNotFoundError("missing")):
            with self.assertRaises(common.ToolingError) as caught:
                common.run_live(["nonexistent-tool"])
        self.assertIn("command failed", str(caught.exception))

    def test_missing_binary_fails_closed(self) -> None:
        with patch.object(common.subprocess, "run", side_effect=FileNotFoundError("missing")):
            with self.assertRaises(common.ToolingError):
                common.run_capture(["nonexistent-tool"])


if __name__ == "__main__":
    unittest.main()
