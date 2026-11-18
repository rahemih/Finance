"""Validate model-generated file contents without granting model or tests write credentials.

Actions jobs:
- validate: apply proposal, run actual tests without OPENAI_API_KEY / write token;
  then finalize verified evidence.
- publish: validate evidence and apply the same patch, but NEVER run generated code.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.automation.openai_coder import ALLOWED, MAX_FILE_SIZE, TASK_ID, digest, manifest

SHA_RE = re.compile(r"^[a-f0-9]{40}$")
HEX_RE = re.compile(r"^[a-f0-9]{64}$")

class GateError(Exception):
    pass

def sha_head() -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                            text=True, timeout=10, check=True)
    return result.stdout.strip()

def load_proposal(path: Path, candidate: Path, *, head: str) -> tuple[dict, dict]:
    task = manifest()
    if not SHA_RE.fullmatch(head):
        raise GateError("Invalid current checkout SHA")
    if path.stat().st_size > 90_000 or candidate.stat().st_size > 4_000:
        raise GateError("Artifact exceeds size limits")
    proposal = json.loads(path.read_text(encoding="utf-8"))
    report = json.loads(candidate.read_text(encoding="utf-8"))
    if (not isinstance(proposal, dict) or set(proposal) !=
            {"schema", "task_id", "base_sha", "files"} or
            proposal["schema"] != "nq.autocode.proposal.v1" or
            proposal["task_id"] != TASK_ID or proposal["base_sha"] != head):
        raise GateError("Untrusted proposal schema or SHA mismatch")
    if (not isinstance(report, dict) or report.get("schema") != "nq.autocode.candidate.v1"
            or report.get("task_id") != TASK_ID or report.get("base_sha") != head
            or report.get("status") != "CANDIDATE_UNTESTED"
            or report.get("tests") != "NOT_RUN"
            or report.get("live_enabled") is not False
            or report.get("code_execution") != "NEVER_IN_GENERATOR"
            or not 1 <= report.get("attempts", 0) <= task["max_attempts"]):
        raise GateError("Candidate metadata not trusted")
    b = json.dumps(proposal, sort_keys=True, ensure_ascii=False,
                   separators=(",", ":")).encode("utf-8")
    if not HEX_RE.fullmatch(str(report.get("proposal_sha256"))) or digest(b) != report["proposal_sha256"]:
        raise GateError("Model artifact integrity failure")
    entries = proposal["files"]
    if not isinstance(entries, list) or not 1 <= len(entries) <= 2:
        raise GateError("Invalid changed file count")
    found = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"path", "content"}:
            raise GateError("Model-controlled metadata")
        path_value, content = entry["path"], entry["content"]
        if path_value not in ALLOWED or path_value in found or not isinstance(content, str):
            raise GateError("Model requested unauthorized file path")
        if not 1 <= len(content.encode("utf-8")) <= MAX_FILE_SIZE or "\x00" in content:
            raise GateError("File content invalid")
        try:
            compile(content, path_value, "exec", dont_inherit=True)
        except (SyntaxError, ValueError) as exc:
            raise GateError("Invalid proposed Python syntax") from exc
        found.append(path_value)
    if found != sorted(found) or found != report.get("files"):
        raise GateError("File inventory inconsistent")
    return proposal, report

def apply_proposal(path: Path, candidate: Path, *, head: str) -> dict:
    proposal, report = load_proposal(path, candidate, head=head)
    for entry in proposal["files"]:
        file = ROOT / entry["path"]
        if file.is_symlink() or not file.resolve().is_relative_to(ROOT):
            raise GateError("Target path is not safe")
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(entry["content"], encoding="utf-8")
    status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"],
                            cwd=ROOT, capture_output=True, text=True, timeout=10, check=True)
    for row in status.stdout.splitlines():
        # build/ artifacts are untracked and are excluded by .gitignore.
        if len(row) < 4 or row[3:] not in ALLOWED:
            raise GateError("Unsafe change detected after materialization")
    if not status.stdout.strip():
        raise GateError("No modified sources to validate")
    return report

def finalize(path: Path, candidate: Path, output: Path, *, head: str) -> dict:
    # Call only AFTER a separate Actions step executed the full fixed test command.
    proposal, report = load_proposal(path, candidate, head=head)
    verified = {
        "schema": "nq.autocode.verified.v1", "task_id": TASK_ID,
        "base_sha": head, "proposal_sha256": report["proposal_sha256"],
        "files": report["files"], "tests_pass": True,
        "test_source": "CREDENTIAL_FREE_GITHUB_ACTIONS_VALIDATE_JOB",
        "mode": "DEMO_ONLY", "review": "NOT_VERIFIED", "merge": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(verified, sort_keys=True, indent=2) + "\n",
                      encoding="utf-8")
    return verified

def publish_check(path: Path, candidate: Path, verified_path: Path,
                  *, head: str) -> dict:
    proposal, report = load_proposal(path, candidate, head=head)
    verified = json.loads(verified_path.read_text(encoding="utf-8"))
    if (not isinstance(verified, dict) or set(verified) != {
            "schema", "task_id", "base_sha", "proposal_sha256", "files",
            "tests_pass", "test_source", "mode", "review", "merge"} or
            verified.get("schema") != "nq.autocode.verified.v1" or
            verified.get("task_id") != TASK_ID or verified.get("base_sha") != head or
            verified.get("proposal_sha256") != report["proposal_sha256"] or
            verified.get("files") != report["files"] or
            verified.get("tests_pass") is not True or
            verified.get("test_source") != "CREDENTIAL_FREE_GITHUB_ACTIONS_VALIDATE_JOB" or
            verified.get("mode") != "DEMO_ONLY" or
            verified.get("review") != "NOT_VERIFIED" or verified.get("merge") is not False):
        raise GateError("Independently verified evidence missing")
    return verified

def main() -> int:
    cli = argparse.ArgumentParser()
    cli.add_argument("phase", choices=("apply", "finalize", "publish"))
    cli.add_argument("--proposal", type=Path, required=True)
    cli.add_argument("--candidate", type=Path, required=True)
    cli.add_argument("--verified", type=Path)
    cli.add_argument("--sha", required=True)
    args = cli.parse_args()
    try:
        if sha_head() != args.sha:
            raise GateError("Stale base, abort")
        if args.phase == "apply":
            apply_proposal(args.proposal, args.candidate, head=args.sha)
        elif args.phase == "finalize":
            if args.verified is None:
                raise GateError("Verified artifact path missing")
            finalize(args.proposal, args.candidate, args.verified, head=args.sha)
        else:
            if args.verified is None:
                raise GateError("Verified artifact path missing")
            publish_check(args.proposal, args.candidate, args.verified, head=args.sha)
            apply_proposal(args.proposal, args.candidate, head=args.sha)
        print("FIN_AUTOCODE_" + args.phase.upper() + "=PASS")
        return 0
    except (GateError, OSError, ValueError, subprocess.SubprocessError,
            json.JSONDecodeError, KeyError, TypeError) as exc:
        print("FIN_AUTOCODE_" + args.phase.upper() + "=BLOCKED type="
              + type(exc).__name__, file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
