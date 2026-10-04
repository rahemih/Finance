#!/usr/bin/env python3
"""Install safe opt-in Git hooks for NEXUS QUANT."""

from __future__ import annotations

import argparse
from pathlib import Path
import os
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "scripts/dev/hooks"


class HookError(RuntimeError):
    pass


def hooks_dir() -> Path:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-path", "hooks"],
            cwd=ROOT,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise HookError("not inside a usable Git worktree") from exc
    path = Path(result.stdout.strip())
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


def install_one(name: str, force: bool) -> None:
    source = TEMPLATES / name
    if not source.is_file():
        raise HookError(f"hook template missing: {source.relative_to(ROOT)}")

    destination_dir = hooks_dir()
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / name
    backup = destination_dir / f"{name}.nexus-quant.bak"

    if destination.exists():
        if not force:
            raise HookError(
                f"{name} already exists; refusing overwrite. "
                "Use --force only after reviewing the existing hook."
            )
        if backup.exists():
            raise HookError(
                f"backup already exists at {backup}; move/remove it manually before --force"
            )
        destination.replace(backup)

    destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    try:
        mode = destination.stat().st_mode
        destination.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except OSError:
        # Git for Windows can still execute the shebang wrapper via its shell layer.
        pass
    print(f"HOOK_INSTALLED name={name} path={destination}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    try:
        install_one("pre-commit", args.force)
        install_one("pre-push", args.force)
    except HookError as exc:
        print(f"HOOK_INSTALL=FAIL error={exc}")
        return 1

    print("HOOK_INSTALL=PASS")
    print("NOTE=Git hooks are local convenience only; protected CI remains authoritative.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
