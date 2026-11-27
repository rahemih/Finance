"""Fail-closed version parsing: no child-supplied text in diagnostics."""
import unittest
from unittest.mock import patch
from scripts.dev import doctor
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

    def test_rejects_padded_version_lines(self):
        # run_capture removes the legitimate trailing process newline.
        for tool, valid in (("git", "git version 2.47.1"),
                            ("node", "v24.21.0"),
                            ("pnpm", "11.28.4"),
                            ("uv", "uv 0.12.23")):
            for padded in (" " + valid, valid + " ", "\t" + valid, valid + "\t"):
                with self.subTest(tool=tool, padded=repr(padded)):
                    self.assertEqual(safe_version_output(tool, padded), "INVALID_OUTPUT")

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


class DoctorCollectBoundaryTests(unittest.TestCase):
    def test_collect_does_not_publish_unexpected_child_output(self):
        # Verify the collect() boundary, not just safe_version_output().
        # run_capture strips whitespace upstream; padding is not covered here.
        versions = {"git": "git version 2.47.1", "node": "v24.21.0",
                    "pnpm": "11.28.4", "uv": "uv 0.12.23"}
        for tool in versions:
            with self.subTest(tool=tool):
                def fake_capture(argv):
                    if argv[0] == tool:
                        return "SYNTHETIC_SECRET_MARKER\\n1.2.3"
                    return versions[argv[0]]

                with patch.object(doctor, "run_capture", side_effect=fake_capture), \\
                     patch.object(doctor, "check_command", return_value=True):
                    report = doctor.collect()
                self.assertEqual(report["checks"][tool]["actual"], "INVALID_OUTPUT")
                self.assertFalse(report["checks"][tool]["ok"])
                self.assertNotIn("SYNTHETIC_SECRET_MARKER", str(report))
