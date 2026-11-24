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

    def test_node_mismatch_does_not_echo_untrusted_version(self):
        marker = "SYNTHETIC_SECRET_NODE_VERSION"
        self._assert_safe_mismatch({"node": marker}, marker, "Node")

    def test_pnpm_mismatch_does_not_echo_untrusted_version(self):
        marker = "SYNTHETIC_SECRET_PNPM_VERSION"
        self._assert_safe_mismatch(
            {"node": "v24.21.0", "pnpm": marker}, marker, "pnpm"
        )

    def test_uv_mismatch_does_not_echo_untrusted_version(self):
        marker = "SYNTHETIC_SECRET_UV_VERSION"
        self._assert_safe_mismatch(
            {"node": "v24.21.0", "pnpm": "11.28.4", "uv": "uv " + marker},
            marker,
            "uv",
        )


if __name__ == "__main__":
    unittest.main()
