"""Fail-closed version parsing: no child-supplied text in diagnostics."""
import unittest
from scripts.dev.doctor import safe_version_output


class DoctorVersionOutputTests(unittest.TestCase):
    def test_expected_formats(self):
        self.assertEqual(safe_version_output("git", "git version 2.47.1"), "2.47.1")
        self.assertEqual(safe_version_output("node", "v24.21.0"), "24.21.0")
        self.assertEqual(safe_version_output("pnpm", "11.28.4"), "11.28.4")
        self.assertEqual(safe_version_output("uv", "uv 0.12.23"), "0.12.23")
        self.assertEqual(safe_version_output("uv", "uv 0.12.23 (x86_64-unknown-linux-gnu)"), "0.12.23")
        self.assertEqual(safe_version_output("uv", "uv 0.12.23 (aarch64-apple-darwin)"), "0.12.23")

    def test_unknown_tool_fails_closed(self):
        for tool in ("unknown", "", "PNPM", "python"):
            with self.subTest(tool=tool):
                self.assertEqual(safe_version_output(tool, "1.2.3"), "INVALID_OUTPUT")

    def test_rejects_multiline_and_unexpected_text(self):
        for tool, valid in (("git", "git version 2.47.1"), ("node", "v24.21.0"),
                            ("pnpm", "11.28.4"), ("uv", "uv 0.12.23")):
            for unsafe in (valid + "\nSYNTHETIC_SECRET_MARKER",
                           valid + " SYNTHETIC_SECRET_MARKER",
                           valid + "\rSYNTHETIC_SECRET_MARKER",
                           "SYNTHETIC_SECRET_MARKER", "x" * 129,
                           valid + " (x86_64-unknown-linux-gnu) SYNTHETIC_SECRET_MARKER",
                           valid + " (SECRET=token)"):
                with self.subTest(tool=tool, unsafe=unsafe[:20]):
                    self.assertEqual(safe_version_output(tool, unsafe), "INVALID_OUTPUT")
