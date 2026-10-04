#!/usr/bin/env python3
"""Validate P04-G developer tooling as a repository contract."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[2]

EXPECTED_SCRIPTS = {
    "doctor": "python scripts/dev/doctor.py",
    "bootstrap": "python scripts/dev/bootstrap.py",
    "check:fast": "python scripts/dev/local_gate.py fast",
    "check:full": "python scripts/dev/local_gate.py full",
    "test:foundation": "python -m unittest discover -s tests/foundation -p \"test_*.py\" -v",
    "hooks:install": "python scripts/dev/install_hooks.py",
}

REQUIRED_DEV_FILES = (
    "scripts/dev/common.py",
    "scripts/dev/doctor.py",
    "scripts/dev/bootstrap.py",
    "scripts/dev/local_gate.py",
    "scripts/dev/install_hooks.py",
    "scripts/dev/hooks/pre-commit",
    "scripts/dev/hooks/pre-push",
)

FORBIDDEN_SECRET_DIAGNOSTIC_TOKENS = (
    "os.environ",
    "os.getenv",
    "environ.items",
    "printenv",
)


def fail(message: str) -> None:
    print(f"DEVELOPER_TOOLING_CONTRACT=FAIL error={message}")
    raise SystemExit(1)


def main() -> int:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    scripts = package.get("scripts", {})
    for name, expected in EXPECTED_SCRIPTS.items():
        actual = scripts.get(name)
        if actual != expected:
            fail(f"package script mismatch name={name} expected={expected!r} actual={actual!r}")

    for relative in REQUIRED_DEV_FILES:
        path = ROOT / relative
        if not path.is_file():
            fail(f"required developer file missing path={relative}")
        if path.suffix == ".py":
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=relative)
            except SyntaxError as exc:
                fail(f"python syntax invalid path={relative} line={exc.lineno}")

    combined = "\n".join(
        (ROOT / relative).read_text(encoding="utf-8")
        for relative in REQUIRED_DEV_FILES
        if relative.endswith(".py")
    )
    for token in FORBIDDEN_SECRET_DIAGNOSTIC_TOKENS:
        if token in combined:
            fail(f"secret-unsafe environment inspection token found token={token}")

    bootstrap = (ROOT / "scripts/dev/bootstrap.py").read_text(encoding="utf-8")
    required_bootstrap = (
        'EXPECTED_PYTHON = "3.14.8"',
        'EXPECTED_NODE = "24.21.0"',
        'EXPECTED_PNPM = "11.28.4"',
        'EXPECTED_UV = "0.12.23"',
        '"--frozen-lockfile"',
        '"--ignore-scripts"',
        '"--locked"',
        '"--no-install-project"',
    )
    for token in required_bootstrap:
        if token not in bootstrap:
            fail(f"bootstrap invariant missing token={token}")

    installer = (ROOT / "scripts/dev/install_hooks.py").read_text(encoding="utf-8")
    for token in ("if not force:", ".nexus-quant.bak", "--force"):
        if token not in installer:
            fail(f"hook overwrite-safety invariant missing token={token}")

    pre_commit = (ROOT / "scripts/dev/hooks/pre-commit").read_text(encoding="utf-8")
    pre_push = (ROOT / "scripts/dev/hooks/pre-push").read_text(encoding="utf-8")
    if "local_gate.py fast" not in pre_commit:
        fail("pre-commit does not invoke fast gate")
    if "local_gate.py full" not in pre_push:
        fail("pre-push does not invoke full gate")

    if re.search(r"https?://", bootstrap):
        fail("bootstrap contains direct remote URL/install path")

    print("DEVELOPER_TOOLING_CONTRACT=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
