"""Trusted publisher gate: validate untrusted AI patch; NEVER execute it.

Runs in a GitHub Actions job separate from model credentials. This module
only applies a narrow patch to two explicitly approved Python files.
GitHub API writes and PR creation happen in the workflow after this gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

from governed_coder import read_task, MAX_PATCH_BYTES, MAX_FILE_BYTES

ROOT = Path(__file__).resolve().parents[2]
SHA = re.compile(r"^[0-9a-f]{40}$")
HEX = re.compile(r"^[0-9a-f]{64}$")

class PublishError(Exception):
    pass

def verify(report: dict, patch: bytes, main_sha: str, allowed: list[str]) -> list[str]:
    if (not isinstance(report, dict) or
            report.get("schema_version") != "fin.coder.run.v1" or
            report.get("task_id") != "FIN-P24-WZ-005" or
            report.get("status") != "READY_FOR_PR_REVIEW" or
            report.get("tests_pass") is not True or
            report.get("financial_mode") != "DEMO_ONLY" or
            report.get("live_enabled") is not False or
            report.get("merged") is not False or
            report.get("independent_review") != "NOT_VERIFIED" or
            not isinstance(report.get("iterations"), int) or
            not 1 <= report["iterations"] <= 2 or
            not SHA.fullmatch(str(main_sha)) or report.get("base_sha") != main_sha):
        raise PublishError("Run evidence / main SHA mismatch")
    if (not isinstance(patch, bytes) or not 0 < len(patch) <= MAX_PATCH_BYTES or
            not HEX.fullmatch(str(report.get("patch_sha256"))) or
            hashlib.sha256(patch).hexdigest() != report["patch_sha256"]):
        raise PublishError("Patch digest or size invalid")
    if b"\0" in patch or b"GIT binary patch" in patch or b"literal " in patch:
        raise PublishError("Binary patch rejected")
    try:
        text = patch.decode("utf-8")
    except UnicodeError as exc:
        raise PublishError("Non-UTF8 patch rejected") from exc
    # Only one trusted diff header per changed path, no confusing git quoting.
    names = []
    for line in text.splitlines():
        if line.startswith("diff --git "):
            match = re.fullmatch(r"diff --git a/([a-z0-9_./-]+) b/([a-z0-9_./-]+)", line)
            if not match or match[1] != match[2]:
                raise PublishError("Unsafe patch header")
            names.append(match[1])
        if line.startswith(("rename from ", "rename to ", "delete mode ",
                            "old mode ", "new mode ", "copy from ", "copy to ")):
            raise PublishError("Rename, deletion or chmod rejected")
    if not names or len(set(names)) != len(names) or any(n not in allowed for n in names):
        raise PublishError("Patch contains non-allowlisted files")
    if names != sorted(names) and len(names) > 1:
        # Avoid ambiguous multi-diff structures.
        raise PublishError("Patch headers not deterministically ordered")
    if set(report.get("changed_files", [])) != set(names):
        raise PublishError("Patch path list does not match evidence")
    return names

def execute(report_path: Path, patch_path: Path, main_sha: str) -> list[str]:
    task = read_task()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    patch = patch_path.read_bytes()
    paths = verify(report, patch, main_sha, task["allowed_files"])
    # Never run any generated code in this privileged publisher process.
    check = subprocess.run(["git", "apply", "--check", "--whitespace=error", "-"],
                           cwd=ROOT, input=patch, capture_output=True)
    if check.returncode:
        raise PublishError("Patch cannot be safely applied to exact main")
    applied = subprocess.run(["git", "apply", "--whitespace=error", "-"],
                             cwd=ROOT, input=patch, capture_output=True)
    if applied.returncode:
        raise PublishError("Patch application failed")
    for path in paths:
        full = ROOT / path
        if (not full.is_file() or full.is_symlink() or
                not full.resolve().is_relative_to(ROOT) or
                full.stat().st_size > MAX_FILE_BYTES):
            raise PublishError("Patch applied unsafe file")
    # Double-check against the actual repo worktree, not patch claims.
    changes = subprocess.run(["git", "status", "--porcelain", "-z", "--untracked-files=all"],
                             cwd=ROOT, capture_output=True)
    if changes.returncode:
        raise PublishError("Cannot enumerate post-apply changes")
    for item in changes.stdout.decode().split("\0"):
        if not item:
            continue
        if len(item) < 4 or item[3:] not in paths or item[:2] not in (" M", "??"):
            raise PublishError("Post-apply scope violation")
    return paths

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--patch", type=Path, required=True)
    parser.add_argument("--main-sha", required=True)
    args = parser.parse_args()
    try:
        paths = execute(args.report, args.patch, args.main_sha)
        print("PUBLISH_GUARD=PASS allowed_files=" + str(len(paths)))
        return 0
    except (PublishError, OSError, json.JSONDecodeError, ValueError) as exc:
        print("PUBLISH_GUARD=BLOCKED reason=" + type(exc).__name__, file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
