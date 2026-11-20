#!/usr/bin/env python3
"""Strict, secret-safe developer environment diagnostics."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
import shutil
import sys

if str(Path(__file__).resolve().parents[2]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.dev.common import ROOT, ToolingError, python_version, require_repo_root, run_capture


EXPECTED = {
    "python": "3.14.8",
    "node": "24.21.0",
    "pnpm": "11.28.4",
    "uv": "0.12.23",
}


def check_command(name: str) -> bool:
    # PATH resolution itself can fail (invalid environment or inaccessible path).
    # Treat this as an unavailable tool without exposing local path details.
    try:
        return shutil.which(name) is not None
    except (OSError, ValueError):
        return False


def read_version_output(name: str, command: list[str]) -> str:
    """Return a safe diagnostic marker when an available tool cannot execute."""
    if not check_command(name):
        return "NOT_FOUND"
    try:
        raw = run_capture(command).strip()
        if not raw:
            return "EMPTY_OUTPUT"
        # Do not echo arbitrary stdout from an executable found on PATH.
        # A replaced binary may print tokens, paths or control sequences.
        patterns = {
            "git": r"git version [0-9]+\.[0-9]+(?:\.[0-9]+)?(?:\.[A-Za-z0-9._-]+)?",
            "node": r"v[0-9]+\.[0-9]+\.[0-9]+",
            "pnpm": r"[0-9]+\.[0-9]+\.[0-9]+",
            "uv": r"uv [0-9]+\.[0-9]+\.[0-9]+(?:\+[A-Za-z0-9._-]+)?(?: \([A-Za-z0-9_-]+\))?",
        }
        pattern = patterns.get(name)
        if pattern is None or re.fullmatch(pattern, raw) is None:
            return "UNEXPECTED_OUTPUT"
        return raw
    except (ToolingError, OSError):
        # Executables may disappear or become unreadable after PATH lookup.
        # Never expose subprocess stderr, command arguments, or credentials.
        return "EXECUTION_FAILED"


def collect() -> dict:
    checks: dict[str, dict[str, object]] = {}

    try:
        require_repo_root()
        # A successful root check must not disclose local usernames or paths.
        checks["repository"] = {"ok": True, "value": "REPOSITORY_ROOT_OK"}
    except ToolingError:
        # Repository checks can contain local paths, subprocess output or secrets.
        # Expose only a fixed diagnostic marker, never the raw exception text.
        checks["repository"] = {"ok": False, "value": "REPOSITORY_CHECK_FAILED"}

    # Python version helpers may return arbitrary local output on failure.
    # Report only a strictly recognized version, never raw diagnostic text.
    try:
        python_raw = python_version()
        actual_python = python_raw if isinstance(python_raw, str) and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", python_raw) else "UNEXPECTED_OUTPUT"
    except (ToolingError, OSError):
        actual_python = "EXECUTION_FAILED"
    checks["python"] = {
        "ok": actual_python == EXPECTED["python"],
        "expected": EXPECTED["python"],
        "actual": actual_python,
    }

    actual_git = read_version_output("git", ["git", "--version"]).splitlines()[0]
    checks["git"] = {"ok": actual_git.startswith("git version "), "actual": actual_git}

    actual_node_line = read_version_output("node", ["node", "--version"]).splitlines()[0]
    actual_node = actual_node_line.removeprefix("v")
    checks["node"] = {
        "ok": actual_node == EXPECTED["node"],
        "expected": EXPECTED["node"],
        "actual": actual_node,
    }

    actual_pnpm = read_version_output("pnpm", ["pnpm", "--version"]).splitlines()[0]
    checks["pnpm"] = {
        "ok": actual_pnpm == EXPECTED["pnpm"],
        "expected": EXPECTED["pnpm"],
        "actual": actual_pnpm,
    }

    actual_uv_line = read_version_output("uv", ["uv", "--version"]).splitlines()[0]
    uv_parts = actual_uv_line.split()
    actual_uv = uv_parts[1] if len(uv_parts) >= 2 and uv_parts[0] == "uv" else actual_uv_line
    checks["uv"] = {
        "ok": actual_uv == EXPECTED["uv"],
        "expected": EXPECTED["uv"],
        "actual": actual_uv,
    }

    canonical = {
        ".node-version": EXPECTED["node"],
        ".python-version": EXPECTED["python"],
    }
    for relative, expected in canonical.items():
        path = ROOT / relative
        try:
            actual = path.read_text(encoding="utf-8").strip() if path.is_file() else "NOT_FOUND"
        except (OSError, UnicodeError):
            # Permission errors and invalid encoding must not abort the full report.
            actual = "UNREADABLE_CONTENT"
        checks[f"file:{relative}"] = {"ok": actual == expected, "expected": expected, "actual": actual if actual in (expected, "NOT_FOUND", "UNREADABLE_CONTENT") else "UNEXPECTED_CONTENT"}

    # Malformed or unreadable manifests are ordinary failed checks, not crashes.
    # Never echo parser errors or manifest contents: they may contain secrets.
    try:
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        if not isinstance(package, dict):
            package = {}
    except (OSError, UnicodeError, ValueError):
        package = {}
    engines = package.get("engines")
    package_node = engines.get("node") if isinstance(engines, dict) else None
    package_pnpm = package.get("packageManager")
    checks["package:node"] = {
        "ok": package_node == EXPECTED["node"],
        "expected": EXPECTED["node"],
        "actual": package_node if package_node == EXPECTED["node"] else "UNEXPECTED_CONTENT",
    }
    checks["package:pnpm"] = {
        "ok": package_pnpm == f"pnpm@{EXPECTED['pnpm']}",
        "expected": f"pnpm@{EXPECTED['pnpm']}",
        "actual": package_pnpm if package_pnpm == f"pnpm@{EXPECTED['pnpm']}" else "UNEXPECTED_CONTENT",
    }

    ok = all(bool(item.get("ok")) for item in checks.values())
    return {"ok": ok, "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--ci", action="store_true")
    args = parser.parse_args()

    try:
        report = collect()
    except Exception as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": type(exc).__name__}, sort_keys=True))
        else:
            print(f"DEVELOPER_DOCTOR=FAIL error={type(exc).__name__}")
        return 1

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for name, detail in report["checks"].items():
            state = "PASS" if detail.get("ok") else "FAIL"
            expected = detail.get("expected")
            actual = detail.get("actual", detail.get("value"))
            suffix = f" expected={expected}" if expected is not None else ""
            print(f"{state} {name} actual={actual}{suffix}")
        print(f"DEVELOPER_DOCTOR={'PASS' if report['ok'] else 'FAIL'}")

    if args.ci and not report["ok"]:
        return 1
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
