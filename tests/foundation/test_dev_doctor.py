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

    def test_multiline_output_is_sanitized(self) -> None:
        with patch.object(doctor, "check_command", return_value=True), \
             patch.object(doctor, "run_capture", return_value="git version 2.45.1\nSECRET_DO_NOT_LOG"):
            self.assertEqual(doctor.read_version_output("git", ["git", "--version"]),
                             "UNEXPECTED_OUTPUT")

    def test_malicious_stdout_is_not_reflected(self) -> None:
        for tool, stdout in (
            ("node", "v24.21.0 TOKEN_SECRET"),
            ("pnpm", "11.28.4\\x1b[31m"),
            ("uv", "uv 0.12.23\n/private/credential"),
            ("git", "git version 2.45.1\rPRIVATE"),
        ):
            with self.subTest(tool=tool), \
                 patch.object(doctor, "check_command", return_value=True), \
                 patch.object(doctor, "run_capture", return_value=stdout):
                self.assertEqual(doctor.read_version_output(tool, [tool, "--version"]),
                                 "UNEXPECTED_OUTPUT")

    def test_uv_platform_suffix_is_accepted_without_leaking_extra_output(self) -> None:
        for stdout, expected in (
            ("uv 0.12.23 (x86_64-unknown-linux-gnu)", "uv 0.12.23 (x86_64-unknown-linux-gnu)"),
            ("uv 0.12.23 (aarch64-apple-darwin)", "uv 0.12.23 (aarch64-apple-darwin)"),
            ("uv 0.12.23 (x86_64-unknown-linux-gnu) SECRET", "UNEXPECTED_OUTPUT"),
            ("uv 0.12.23 (x86_64-unknown-linux-gnu)\\nTOKEN", "UNEXPECTED_OUTPUT"),
            ("uv 0.12.23 (../../private)", "UNEXPECTED_OUTPUT"),
        ):
            with self.subTest(stdout=stdout), \
                 patch.object(doctor, "check_command", return_value=True), \
                 patch.object(doctor, "run_capture", return_value=stdout):
                self.assertEqual(doctor.read_version_output("uv", ["uv", "--version"]), expected)

    def test_valid_versions_remain_usable(self) -> None:
        for tool, stdout in (
            ("node", "v24.21.0"),
            ("pnpm", "11.28.4"),
            ("uv", "uv 0.12.23"),
            ("git", "git version 2.45.1"),
        ):
            with self.subTest(tool=tool), \
                 patch.object(doctor, "check_command", return_value=True), \
                 patch.object(doctor, "run_capture", return_value=stdout):
                self.assertEqual(doctor.read_version_output(tool, [tool, "--version"]), stdout)


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


    def test_successful_repository_root_does_not_disclose_local_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="TOKEN_SECRET_REPO_") as directory:
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
                 patch.object(doctor, "check_command", return_value=False):
                report = doctor.collect()
            self.assertEqual(report["checks"]["repository"],
                             {"ok": True, "value": "REPOSITORY_ROOT_OK"})
            self.assertNotIn(str(root), json.dumps(report))
            self.assertNotIn("TOKEN_SECRET_REPO_", json.dumps(report))


class FullReportTests(unittest.TestCase):
    def test_manifest_secrets_are_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".node-version").write_text("TOKEN_SECRET_NODE", encoding="utf-8")
            (root / ".python-version").write_text(doctor.EXPECTED["python"], encoding="utf-8")
            (root / "package.json").write_text(json.dumps({
                "engines": {"node": "TOKEN_SECRET_ENGINE"},
                "packageManager": "TOKEN_SECRET_PACKAGE",
            }), encoding="utf-8")
            with patch.object(doctor, "ROOT", root), \
                 patch.object(doctor, "require_repo_root"), \
                 patch.object(doctor, "python_version", return_value=doctor.EXPECTED["python"]), \
                 patch.object(doctor, "check_command", return_value=False):
                report = doctor.collect()
        output = json.dumps(report)
        self.assertNotIn("TOKEN_SECRET", output)
        for name in ("file:.node-version", "package:node", "package:pnpm"):
            self.assertEqual(report["checks"][name]["actual"], "UNEXPECTED_CONTENT")

    def test_malformed_package_manifest_fails_closed_without_leaking(self) -> None:
        for manifest in ("{TOKEN_SECRET_BAD_JSON", "[]", '{"engines": "TOKEN_SECRET_ENGINE"}'):
            with self.subTest(manifest=manifest), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / ".node-version").write_text(doctor.EXPECTED["node"], encoding="utf-8")
                (root / ".python-version").write_text(doctor.EXPECTED["python"], encoding="utf-8")
                (root / "package.json").write_text(manifest, encoding="utf-8")
                with patch.object(doctor, "ROOT", root), \
                     patch.object(doctor, "require_repo_root"), \
                     patch.object(doctor, "python_version", return_value=doctor.EXPECTED["python"]), \
                     patch.object(doctor, "check_command", return_value=False):
                    report = doctor.collect()
                self.assertFalse(report["ok"])
                self.assertEqual(report["checks"]["package:node"]["actual"], "UNEXPECTED_CONTENT")
                self.assertEqual(report["checks"]["package:pnpm"]["actual"], "UNEXPECTED_CONTENT")
                self.assertNotIn("TOKEN_SECRET", json.dumps(report))

    def test_unreadable_runtime_pin_fails_closed_without_aborting(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".node-version").write_text(doctor.EXPECTED["node"], encoding="utf-8")
            (root / ".python-version").write_text(doctor.EXPECTED["python"], encoding="utf-8")
            (root / "package.json").write_text(json.dumps({
                "engines": {"node": doctor.EXPECTED["node"]},
                "packageManager": "pnpm@" + doctor.EXPECTED["pnpm"],
            }), encoding="utf-8")
            original_read_text = Path.read_text

            def read_with_failure(path: Path, *args: object, **kwargs: object) -> str:
                if path.name == ".node-version":
                    raise PermissionError("TOKEN_SECRET_PRIVATE_PATH")
                return original_read_text(path, *args, **kwargs)

            with patch.object(doctor, "ROOT", root), \
                 patch.object(doctor, "require_repo_root"), \
                 patch.object(doctor, "python_version", return_value=doctor.EXPECTED["python"]), \
                 patch.object(doctor, "check_command", return_value=False), \
                 patch.object(Path, "read_text", read_with_failure):
                report = doctor.collect()
        self.assertFalse(report["ok"])
        self.assertEqual(report["checks"]["file:.node-version"]["actual"], "UNREADABLE_CONTENT")
        self.assertIn("package:pnpm", report["checks"])
        self.assertNotIn("TOKEN_SECRET", json.dumps(report))

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
