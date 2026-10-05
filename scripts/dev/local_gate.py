#!/usr/bin/env python3
"""Fast/full local gates aligned with canonical CI without replacing CI authority."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import sys

if str(Path(__file__).resolve().parents[2]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.dev.common import ROOT, ToolingError, run_capture, run_live


BRANCH_RE = re.compile(
    r"^(feat|fix|docs|chore|research|security|perf|test|refactor|bootstrap)/"
    r"FIN-P\d{2}-W[A-Z]-\d{3}(?:-R\d{2})?-[a-z0-9][a-z0-9-]{0,79}$"
)


def validate_local_branch() -> None:
    try:
        branch = run_capture(["git", "branch", "--show-current"]).strip()
    except ToolingError:
        return
    if not branch or branch == "main" or branch.startswith("dependabot/"):
        return
    if BRANCH_RE.fullmatch(branch) is None:
        raise ToolingError(f"branch name is not governance-compatible: {branch}")
    print(f"LOCAL_BRANCH_NAME=PASS branch={branch}")


def fast_gate() -> None:
    validate_local_branch()
    commands = [
        [sys.executable, "scripts/verify_governance.py"],
        [sys.executable, "scripts/ci/foundation_ci.py", "lint"],
        [sys.executable, "scripts/ci/foundation_ci.py", "typecheck"],
        [sys.executable, "scripts/ci/foundation_ci.py", "unit"],
        [sys.executable, "scripts/ci/foundation_ci.py", "contract"],
        [sys.executable, "scripts/ci/config_contract.py"],
        [sys.executable, "-m", "unittest", "discover", "-s", "tests/foundation", "-p", "test_*.py", "-v"],
        [sys.executable, "-m", "unittest", "discover", "-s", "tests/p05", "-p", "test_*.py", "-v"],
        [sys.executable, "scripts/ci/supply_chain_policy.py", "manifest"],
        [sys.executable, "scripts/ci/developer_tooling_contract.py"],
        [sys.executable, "scripts/ci/foundation_ci.py", "security"],
        [sys.executable, "scripts/ci/foundation_ci.py", "promotion"],
    ]
    for command in commands:
        run_live(command)


def full_gate() -> None:
    run_live([sys.executable, "scripts/dev/doctor.py", "--ci"])
    run_live(["pnpm", "install", "--frozen-lockfile", "--ignore-scripts"])
    run_live(["uv", "sync", "--locked", "--no-install-project"])
    fast_gate()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("fast", "full"))
    args = parser.parse_args()

    try:
        if args.mode == "fast":
            fast_gate()
        else:
            full_gate()
    except (ToolingError, subprocess.CalledProcessError) as exc:
        print(f"LOCAL_GATE=FAIL mode={args.mode} error={exc}")
        return 1

    print(f"LOCAL_GATE=PASS mode={args.mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
