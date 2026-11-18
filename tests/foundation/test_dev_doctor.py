"""Regression tests for developer doctor fail-closed, secret-safe diagnostics."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.dev import doctor
from scripts.dev.common import ToolingError


class VersionOutputTests(unittest.TestCase):
    def test_missing_command_does_not_execute(self) -> None:
        with patch.object(doctor, "check_command", return_value=False), \
             patch.object(doctor, "run_capture") as capture:
            self.assertEqual(doctor.read_version_output("node", ["node", "--version"]), "NOT_FOUND")
            capture.assert_not_called()

    def test_execution_failure_is_sanitized(self) -> None:
        with patch.object(doctor, "check_command", return_value=True), \
             patch.object(doctor, "run_capture", side_effect=ToolingError("SECRET_DO_NOT_LOG")):
            value = doctor.read_version_output("uv", ["uv", "--version"])
        self.assertEqual(value, "EXECUTION_FAILED")
        self.assertNotIn("SECRET_DO_NOT_LOG", value)

    def test_empty_command_output_is_safe(self) -> None:
        with patch.object(doctor, "check_command", return_value=True), \
             patch.object(doctor, "run_capture", return_value="\n \n"):
            self.assertEqual(doctor.read_version_output("pnpm", ["pnpm", "--version"]), "EMPTY_OUTPUT")

    def test_multiline_output_is_handled(self) -> None:
        with patch.object(doctor, "check_command", return_value=True), \
             patch.object(doctor, "run_capture", return_value="git version 2.45.1\nOther info"):
            self.assertEqual(doctor.read_version_output("git", ["git", "--version"]),
                             "git version 2.45.1\nOther info")


class RepositoryPrivacyTests(unittest.TestCase):
    def test_repository_root_failure_does_not_expose_sensitive_exception(self) -> None:
        # An invalid repo-root check must fail closed without leaking raw paths,
        # command output or credentials in JSON/text diagnostics.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".node-version").write_text(doctor.EXPECTED["node"], encoding="utf-8")
            (root / ".python-version").write_text(doctor.EXPECTED["python"], encoding="utf-8")
            (root / "package.json").write_text(json.dumps({
                "engines": {"node": doctor.EXPECTED["node"]},
                "packageManager": "pnpm@" + doctor.EXPECTED["pnpm"],
            }), encoding="utf-8")
            with patch.object(doctor, "ROOT", root), \
                 patch.object(doctor, "require_repo_root",
                              side_effect=ToolingError("TOKEN_SECRET_DO_NOT_PRINT /private/path")), \
                 patch.object(doctor, "python_version", return_value=doctor.EXPECTED["python"]), \
                 patch.object(doctor, "check_command", return_value=False):
                report = doctor.collect()
        self.assertFalse(report["ok"])
        self.assertEqual(report["checks"]["repository"],
                         {"ok": False, "value": "REPOSITORY_CHECK_FAILED"})
        self.assertNotIn("TOKEN_SECRET_DO_NOT_PRINT", json.dumps(report))
        self.assertNotIn("/private/path", json.dumps(report))
        self.assertIn("package:pnpm", report["checks"])


class FullReportTests(unittest.TestCase):
    def test_failed_git_does_not_hide_other_dependency_results(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".node-version").write_text(doctor.EXPECTED["node"] + "\n", encoding="utf-8")
            (root / ".python-version").write_text(doctor.EXPECTED["python"] + "\n", encoding="utf-8")
            (root / "package.json").write_text(json.dumps({
                "engines": {"node": doctor.EXPECTED["node"]},
                "packageManager": "pnpm@" + doctor.EXPECTED["pnpm"],
            }), encoding="utf-8")

            def command_output(args: list[str]) -> str:
                if args[0] == "git":
                    raise ToolingError("secret-value-from-stdout")
                return {
                    "node": "v" + doctor.EXPECTED["node"],
                    "pnpm": doctor.EXPECTED["pnpm"],
                    "uv": "uv " + doctor.EXPECTED["uv"],
                }[args[0]]

            with patch.object(doctor, "ROOT", root), \
                 patch.object(doctor, "require_repo_root"), \
                 patch.object(doctor, "python_version", return_value=doctor.EXPECTED["python"]), \
                 patch.object(doctor, "check_command", return_value=True), \
                 patch.object(doctor, "run_capture", side_effect=command_output):
                report = doctor.collect()

        self.assertFalse(report["ok"])
        self.assertFalse(report["checks"]["git"]["ok"])
        self.assertEqual(report["checks"]["git"]["actual"], "EXECUTION_FAILED")
        for name in ("node", "pnpm", "uv", "package:node", "package:pnpm",
                     "file:.node-version", "file:.python-version"):
            with self.subTest(name=name):
                self.assertTrue(report["checks"][name]["ok"])
        self.assertNotIn("secret-value-from-stdout", json.dumps(report))

    def test_empty_version_output_is_reported_not_crashed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".node-version").write_text(doctor.EXPECTED["node"], encoding="utf-8")
            (root / ".python-version").write_text(doctor.EXPECTED["python"], encoding="utf-8")
            (root / "package.json").write_text(json.dumps({
                "engines": {"node": doctor.EXPECTED["node"]},
                "packageManager": "pnpm@" + doctor.EXPECTED["pnpm"],
            }), encoding="utf-8")
            with patch.object(doctor, "ROOT", root), \
                 patch.object(doctor, "require_repo_root"), \
                 patch.object(doctor, "python_version", return_value=doctor.EXPECTED["python"]), \
                 patch.object(doctor, "check_command", return_value=True), \
                 patch.object(doctor, "run_capture", return_value=""):
                report = doctor.collect()
        self.assertFalse(report["ok"])
        for name in ("git", "node", "pnpm", "uv"):
            self.assertEqual(report["checks"][name]["actual"], "EMPTY_OUTPUT")


if __name__ == "__main__":
    unittest.main()
