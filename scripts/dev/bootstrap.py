#!/usr/bin/env python3
"""Cross-platform locked developer bootstrap for NEXUS QUANT."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys

if str(Path(__file__).resolve().parents[2]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.dev.common import ToolingError, python_version, require_repo_root, run_capture, run_live


EXPECTED_PYTHON = "3.14.8"
EXPECTED_NODE = "24.21.0"
EXPECTED_PNPM = "11.28.4"
EXPECTED_UV = "0.12.23"


def require_executable(name: str) -> None:
    if shutil.which(name) is None:
        raise ToolingError(f"{name} not found in PATH")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hooks", action="store_true", help="install opt-in Git hooks after bootstrap")
    parser.add_argument("--force-hooks", action="store_true", help="allow safe replacement of existing managed hook targets")
    args = parser.parse_args()

    try:
        require_repo_root()

        if python_version() != EXPECTED_PYTHON:
            raise ToolingError(f"Python {EXPECTED_PYTHON} required; actual={python_version()}")

        require_executable("git")
        require_executable("node")
        require_executable("corepack")

        node = run_capture(["node", "--version"]).lstrip("v")
        if node != EXPECTED_NODE:
            raise ToolingError(f"Node {EXPECTED_NODE} required; actual={node}")

        run_live(["corepack", "enable"])
        run_live(["corepack", "prepare", f"pnpm@{EXPECTED_PNPM}", "--activate"])

        pnpm = run_capture(["pnpm", "--version"]).splitlines()[0].strip()
        if pnpm != EXPECTED_PNPM:
            raise ToolingError(f"pnpm {EXPECTED_PNPM} required after Corepack activation; actual={pnpm}")

        run_live(["pnpm", "install", "--frozen-lockfile", "--ignore-scripts"])

        require_executable("uv")
        uv_line = run_capture(["uv", "--version"]).splitlines()[0].strip()
        parts = uv_line.split()
        uv = parts[1] if len(parts) >= 2 else uv_line
        if uv != EXPECTED_UV:
            raise ToolingError(
                f"uv {EXPECTED_UV} required; actual={uv}. "
                "Install/activate the exact approved uv version explicitly, then rerun bootstrap."
            )

        run_live(["uv", "sync", "--locked", "--no-install-project"])
        run_live([sys.executable, "scripts/dev/doctor.py", "--ci"])
        run_live([sys.executable, "scripts/dev/local_gate.py", "fast"])

        if args.hooks or args.force_hooks:
            command = [sys.executable, "scripts/dev/install_hooks.py"]
            if args.force_hooks:
                command.append("--force")
            run_live(command)

    except ToolingError as exc:
        print(f"DEVELOPER_BOOTSTRAP=FAIL error={exc}")
        return 1

    print("DEVELOPER_BOOTSTRAP=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
