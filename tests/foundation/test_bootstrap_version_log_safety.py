"""Regression: untrusted CLI version output must not reach bootstrap failure logs."""

from __future__ import annotations

import contextlib
import io
import unittest
from unittest.mock import patch

from scripts.dev import bootstrap


class BootstrapVersionLogSafetyTests(unittest.TestCase):
    def _run_with_version(self, versions: dict[str, str]) -> str:
        output = io.StringIO()

        def capture(argv):
            return versions.get(argv[0], "24.21.0")

        with (
            patch.object(bootstrap, "require_repo_root"),
            patch.object(bootstrap, "python_version", return_value=bootstrap.EXPECTED_PYTHON),
            patch.object(bootstrap, "require_executable"),
            patch.object(bootstrap, "run_capture", side_effect=capture),
            patch.object(bootstrap, "run_live"),
            patch("sys.argv", ["bootstrap.py"]),
            contextlib.redirect_stdout(output),
        ):
            self.assertEqual(bootstrap.main(), 1)
        return output.getvalue()

    def _assert_safe_mismatch(self, versions: dict[str, str], marker: str, tool: str) -> None:
        output = self._run_with_version(versions)
        self.assertNotIn(marker, output)
        self.assertIn("DEVELOPER_BOOTSTRAP=FAIL", output)
        self.assertIn(f"{tool} ", output)
        self.assertIn("detected version withheld from logs", output)
        self.assertNotIn("DEVELOPER_BOOTSTRAP=PASS", output)

    def test_python_mismatch_does_not_echo_untrusted_version(self):
        marker = "SYNTHETIC_SECRET_PYTHON_VERSION"
        output = io.StringIO()
        with (
            patch.object(bootstrap, "require_repo_root"),
            patch.object(bootstrap, "python_version", return_value=marker),
            patch("sys.argv", ["bootstrap.py"]),
            contextlib.redirect_stdout(output),
        ):
            self.assertEqual(bootstrap.main(), 1)
        rendered = output.getvalue()
        self.assertNotIn(marker, rendered)
        self.assertIn("DEVELOPER_BOOTSTRAP=FAIL", rendered)
        self.assertIn("Python ", rendered)
        self.assertIn("detected version withheld from logs", rendered)
        self.assertNotIn("DEVELOPER_BOOTSTRAP=PASS", rendered)

    def test_node_mismatch_does_not_echo_untrusted_version(self):
        marker = "SYNTHETIC_SECRET_NODE_VERSION"
        self._assert_safe_mismatch({"node": marker}, marker, "Node")

    def test_repeated_node_version_prefix_is_rejected(self):
        output = self._run_with_version({"node": "vv24.21.0"})
        self.assertIn("DEVELOPER_BOOTSTRAP=FAIL", output)
        self.assertIn("Node ", output)
        self.assertNotIn("DEVELOPER_BOOTSTRAP=PASS", output)

    def test_pnpm_mismatch_does_not_echo_untrusted_version(self):
        marker = "SYNTHETIC_SECRET_PNPM_VERSION"
        self._assert_safe_mismatch(
            {"node": "v24.21.0", "pnpm": marker}, marker, "pnpm"
        )

    def test_empty_pnpm_version_fails_without_traceback(self):
        output = self._run_with_version({"node": "v24.21.0", "pnpm": ""})
        self.assertIn("DEVELOPER_BOOTSTRAP=FAIL", output)
        self.assertIn("pnpm ", output)
        self.assertNotIn("Traceback", output)

    def test_empty_uv_version_fails_without_traceback(self):
        output = self._run_with_version(
            {"node": "v24.21.0", "pnpm": "11.28.4", "uv": ""}
        )
        self.assertIn("DEVELOPER_BOOTSTRAP=FAIL", output)
        self.assertIn("uv ", output)
        self.assertNotIn("Traceback", output)

    def test_uv_mismatch_does_not_echo_untrusted_version(self):
        marker = "SYNTHETIC_SECRET_UV_VERSION"
        self._assert_safe_mismatch(
            {"node": "v24.21.0", "pnpm": "11.28.4", "uv": "uv " + marker},
            marker,
            "uv",
        )


if __name__ == "__main__":
    unittest.main()
