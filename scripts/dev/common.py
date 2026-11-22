"""Shared helpers for NEXUS QUANT developer tooling."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
from typing import Sequence


ROOT = Path(__file__).resolve().parents[2]


class ToolingError(RuntimeError):
    pass


def run_capture(command: Sequence[str]) -> str:
    try:
        result = subprocess.run(
            list(command),
            cwd=ROOT,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    except (OSError, ValueError, IndexError, UnicodeError, subprocess.SubprocessError):
        # Do not expose command arguments or subprocess output via exception chaining.
        raise ToolingError("command failed") from None
    return result.stdout.strip()


def run_live(command: Sequence[str]) -> None:
    try:
        subprocess.run(list(command), cwd=ROOT, check=True)
    except (OSError, ValueError, IndexError, UnicodeError, subprocess.SubprocessError):
        # Do not expose command arguments or subprocess output via exception chaining.
        raise ToolingError("command failed") from None


def require_repo_root() -> None:
    required = (
        ROOT / "package.json",
        ROOT / "pyproject.toml",
        ROOT / "docs/01-roadmap/MASTER-ROADMAP-v2.0.md",
        ROOT / "scripts/verify_governance.py",
    )
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        raise ToolingError(f"repository root validation failed; missing={missing}")


def python_version() -> str:
    return ".".join(str(x) for x in sys.version_info[:3])
