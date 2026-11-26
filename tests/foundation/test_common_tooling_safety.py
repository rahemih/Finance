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

    def test_capture_success_without_text_fails_closed(self) -> None:
        # Defensive boundary: a missing/binary payload must not escape as a
        # raw AttributeError or TypeError from the wrapper.
        for payload in (None, b"SENSITIVE_BINARY_OUTPUT_MARKER"):
            with self.subTest(payload_type=type(payload).__name__):
                completed = subprocess.CompletedProcess(["tool"], 0, stdout=payload)
                with patch.object(common.subprocess, "run", return_value=completed):
                    with self.assertRaisesRegex(common.ToolingError, "^command failed$") as caught:
                        common.run_capture(["tool"])
                self.assertIsNone(caught.exception.__cause__)

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

    def test_live_output_is_inherited_not_redacted(self) -> None:
        with patch.object(common.subprocess, "run") as runner:
            common.run_live(["safe-tool", "--version"])
        self.assertNotIn("stdout", runner.call_args.kwargs)
        self.assertNotIn("stderr", runner.call_args.kwargs)
        self.assertIn("NOT redacted", common.run_live.__doc__)

    def test_live_missing_binary_fails_closed(self) -> None:
        with patch.object(common.subprocess, "run", side_effect=FileNotFoundError("missing")):
            with self.assertRaises(common.ToolingError) as caught:
                common.run_live(["nonexistent-tool"])
        self.assertIn("command failed", str(caught.exception))

    def test_empty_argv_fails_closed(self) -> None:
        for runner in (common.run_capture, common.run_live):
            with self.subTest(runner=runner.__name__):
                with patch.object(common.subprocess, "run", side_effect=IndexError("empty argv")):
                    with self.assertRaisesRegex(common.ToolingError, "^command failed$") as caught:
                        runner([])
                self.assertIsNone(caught.exception.__cause__)

    def test_scalar_string_or_bytes_command_never_invokes_subprocess(self) -> None:
        # Scalar str/bytes are not argv even though str implements Sequence.
        for command in ("git --version", b"git --version"):
            for runner in (common.run_capture, common.run_live):
                with self.subTest(command=type(command).__name__, runner=runner.__name__):
                    with patch.object(common.subprocess, "run") as subprocess_runner:
                        with self.assertRaisesRegex(common.ToolingError, "^command failed$"):
                            runner(command)
                    subprocess_runner.assert_not_called()

    def test_empty_executable_never_invokes_subprocess(self) -> None:
        # Empty argv[0] must fail before any child process is started.
        for runner in (common.run_capture, common.run_live):
            with self.subTest(runner=runner.__name__):
                with patch.object(common.subprocess, "run") as process:
                    with self.assertRaisesRegex(common.ToolingError, "^command failed$"):
                        runner(["", "--version"])
                process.assert_not_called()

    def test_whitespace_only_executable_never_invokes_subprocess(self) -> None:
        for executable in (" ", "\t", "\n", " \t "):

            for runner in (common.run_capture, common.run_live):
                with self.subTest(executable=repr(executable), runner=runner.__name__):
                    with patch.object(common.subprocess, "run") as process:
                        with self.assertRaisesRegex(common.ToolingError, "^command failed$"):
                            runner([executable, "--version"])
                    process.assert_not_called()

    def test_empty_argv_never_invokes_subprocess(self) -> None:
        for runner in (common.run_capture, common.run_live):
            with self.subTest(runner=runner.__name__):
                with patch.object(common.subprocess, "run") as subprocess_runner:
                    with self.assertRaisesRegex(common.ToolingError, "^command failed$"):
                        runner([])
                subprocess_runner.assert_not_called()

    def test_typeerror_from_invalid_argv_is_sanitized(self) -> None:
        secret = "SENSITIVE_TYPEERROR_MARKER"
        for runner in (common.run_capture, common.run_live):
            with self.subTest(runner=runner.__name__):
                with patch.object(common.subprocess, "run", side_effect=TypeError(secret)):
                    try:
                        runner(["tool", "--token", secret])
                    except common.ToolingError as exc:
                        self.assertEqual(str(exc), "command failed")
                        self.assertNotIn(secret, "".join(traceback.format_exception(exc)))
                        self.assertTrue(exc.__suppress_context__)
                    else:
                        self.fail("expected ToolingError")

    def test_invalid_argv_fails_closed(self) -> None:
        for runner in (common.run_capture, common.run_live):
            with self.subTest(runner=runner.__name__):
                with patch.object(common.subprocess, "run", side_effect=ValueError("sensitive invalid argv")):
                    with self.assertRaisesRegex(common.ToolingError, "^command failed$") as caught:
                        runner(["tool"])
                self.assertIsNone(caught.exception.__cause__)

    def test_capture_decode_failure_redacts_secret(self) -> None:
        secret = "SENSITIVE_DECODE_MARKER"
        failure = UnicodeDecodeError("utf-8", secret.encode(), 0, 1, secret)
        with patch.object(common.subprocess, "run", side_effect=failure):
            try:
                common.run_capture(["tool", "--token", secret])
            except common.ToolingError as exc:
                self.assertEqual(str(exc), "command failed")
                self.assertNotIn(secret, "".join(traceback.format_exception(exc)))
                self.assertTrue(exc.__suppress_context__)
            else:
                self.fail("expected ToolingError")

    def test_live_decode_failure_redacts_secret(self) -> None:
        secret = "SENSITIVE_LIVE_DECODE_MARKER"
        failure = UnicodeDecodeError("utf-8", secret.encode(), 0, 1, secret)
        with patch.object(common.subprocess, "run", side_effect=failure):
            try:
                common.run_live(["tool", "--token", secret])
            except common.ToolingError as exc:
                self.assertEqual(str(exc), "command failed")
                self.assertNotIn(secret, "".join(traceback.format_exception(exc)))
                self.assertTrue(exc.__suppress_context__)
            else:
                self.fail("expected ToolingError")

    def test_malformed_argv_elements_never_start_process(self) -> None:
        # Reject non-string elements and embedded NUL before invoking subprocess.
        for command in (["tool", None], ["tool", b"arg"], ["tool", "bad\x00arg"]):
            for runner in (common.run_capture, common.run_live):
                with self.subTest(command=repr(command), runner=runner.__name__):
                    with patch.object(common.subprocess, "run") as subprocess_runner:
                        with self.assertRaisesRegex(common.ToolingError, "^command failed$"):
                            runner(command)
                    subprocess_runner.assert_not_called()

    def test_hostile_truthiness_is_not_evaluated_before_materialization(self) -> None:
        secret = "SENSITIVE_BOOL_FAILURE_MARKER"

        class HostileTruthiness:
            def __bool__(self):
                raise RuntimeError(secret)

            def __iter__(self):
                return iter(["tool", "--version"])

        for runner in (common.run_capture, common.run_live):
            with self.subTest(runner=runner.__name__):
                completed = subprocess.CompletedProcess(["tool", "--version"], 0, stdout="ok")
                with patch.object(common.subprocess, "run", return_value=completed) as subprocess_runner:
                    runner(HostileTruthiness())
                subprocess_runner.assert_called_once()

    def test_hostile_string_subclass_never_invokes_process(self) -> None:
        secret = "SENSITIVE_STR_SUBCLASS_MARKER"

        class HostileString(str):
            def strip(self, *args, **kwargs):
                raise RuntimeError(secret)

            def __str__(self):
                raise RuntimeError(secret)

        for command in ([HostileString("tool"), "--version"], ["tool", HostileString("--version")]):
            for runner in (common.run_capture, common.run_live):
                with self.subTest(runner=runner.__name__):
                    with patch.object(common.subprocess, "run") as process:
                        try:
                            runner(command)
                        except common.ToolingError as exc:
                            self.assertEqual(str(exc), "command failed")
                            self.assertNotIn(secret, "".join(traceback.format_exception(exc)))
                            self.assertTrue(exc.__suppress_context__)
                        else:
                            self.fail("expected ToolingError")
                    process.assert_not_called()

    def test_generator_argv_is_materialized_and_validated(self) -> None:
        for runner in (common.run_capture, common.run_live):
            with self.subTest(runner=runner.__name__):
                with patch.object(common.subprocess, "run") as subprocess_runner:
                    with self.assertRaisesRegex(common.ToolingError, "^command failed$"):
                        runner(item for item in ("tool", None))
                subprocess_runner.assert_not_called()

    def test_generator_materialization_failure_redacts_exception_and_never_spawns(self) -> None:
        secret = "SENSITIVE_ITERATOR_FAILURE_MARKER"

        def broken_argv():
            yield "tool"
            raise RuntimeError(secret)

        for runner in (common.run_capture, common.run_live):
            with self.subTest(runner=runner.__name__):
                with patch.object(common.subprocess, "run") as subprocess_runner:
                    try:
                        runner(broken_argv())
                    except common.ToolingError as exc:
                        self.assertEqual(str(exc), "command failed")
                        self.assertNotIn(secret, "".join(traceback.format_exception(exc)))
                        self.assertTrue(exc.__suppress_context__)
                    else:
                        self.fail("expected ToolingError")
                subprocess_runner.assert_not_called()

    def test_iterator_overflow_fails_closed_without_spawning(self) -> None:
        secret = "SENSITIVE_OVERFLOW_MARKER"

        class OverflowingArgv:
            def __iter__(self):
                raise OverflowError(secret)

        for runner in (common.run_capture, common.run_live):
            with self.subTest(runner=runner.__name__):
                with patch.object(common.subprocess, "run") as process:
                    try:
                        runner(OverflowingArgv())
                    except common.ToolingError as exc:
                        self.assertEqual(str(exc), "command failed")
                        self.assertNotIn(secret, "".join(traceback.format_exception(exc)))
                    else:
                        self.fail("expected ToolingError")
                process.assert_not_called()

    def test_custom_iterator_exception_fails_closed_without_spawning(self) -> None:
        secret = "SENSITIVE_CUSTOM_ITERATOR_MARKER"

        class HostileArgv:
            def __iter__(self):
                raise LookupError(secret)

        for runner in (common.run_capture, common.run_live):
            with self.subTest(runner=runner.__name__):
                with patch.object(common.subprocess, "run") as process:
                    try:
                        runner(HostileArgv())
                    except common.ToolingError as exc:
                        self.assertEqual(str(exc), "command failed")
                        self.assertNotIn(secret, "".join(traceback.format_exception(exc)))
                        self.assertTrue(exc.__suppress_context__)
                    else:
                        self.fail("expected ToolingError")
                process.assert_not_called()

    def test_missing_binary_fails_closed(self) -> None:
        with patch.object(common.subprocess, "run", side_effect=FileNotFoundError("missing")):
            with self.assertRaises(common.ToolingError):
                common.run_capture(["nonexistent-tool"])


if __name__ == "__main__":
    unittest.main()
