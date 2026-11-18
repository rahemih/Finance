#!/usr/bin/env python3
"""Strict, secret-safe developer environment diagnostics."""

from __future__ import annotations

import argparse
import json
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
    return shutil.which(name) is not None


def read_version_output(name: str, command: list[str]) -> str:
    """Return a safe diagnostic marker when an available tool cannot execute."""
    if not check_command(name):
        return "NOT_FOUND"
    try:
        return run_capture(command).strip() or "EMPTY_OUTPUT"
    except ToolingError:
        # Never expose subprocess stderr, command arguments, or credentials.
        return "EXECUTION_FAILED"


def collect() -> dict:
    checks: dict[str, dict[str, object]] = {}

    try:
        require_repo_root()
        checks["repository"] = {"ok": True, "value": str(ROOT)}
    except ToolingError as exc:
        checks["repository"] = {"ok": False, "value": str(exc)}

    actual_python = python_version()
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
        actual = path.read_text(encoding="utf-8").strip() if path.is_file() else "NOT_FOUND"
        checks[f"file:{relative}"] = {"ok": actual == expected, "expected": expected, "actual": actual}

    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    checks["package:node"] = {
        "ok": package.get("engines", {}).get("node") == EXPECTED["node"],
        "expected": EXPECTED["node"],
        "actual": package.get("engines", {}).get("node"),
    }
    checks["package:pnpm"] = {
        "ok": package.get("packageManager") == f"pnpm@{EXPECTED['pnpm']}",
        "expected": f"pnpm@{EXPECTED['pnpm']}",
        "actual": package.get("packageManager"),
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
