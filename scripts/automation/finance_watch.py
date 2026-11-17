"""Fail-closed, read-only GitHub evidence watcher for NEXUS QUANT.

A9/A10 monitoring support only; NOT a model runtime or authorization engine.
Never places orders, modifies GitHub/Linear or declares final completion.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPOSITORY = "rahemih/Finance"
API = f"https://api.github.com/repos/{REPOSITORY}"
MAX_ITEMS = 100
REQUIRED_GATE = "Governance Verify"


class EvidenceError(Exception):
    """Incomplete or untrusted evidence cannot be promoted."""


def _get_json(path: str, token: str) -> object:
    # Approved paths are generated in code, never from retrieved GitHub text.
    req = Request(
        f"{API}{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "nexus-quant-governed-readonly-watch/1.0",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
        method="GET",
    )
    try:
        with urlopen(req, timeout=18) as response:
            return json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        # Do not log auth headers or credentials.
        raise EvidenceError(f"GitHub evidence fetch failed for {path.split('?')[0]}") from exc


def collect(token: str) -> dict:
    branch = _get_json("/branches/main", token)
    if not isinstance(branch, dict) or not isinstance(branch.get("commit"), dict):
        raise EvidenceError("Main branch unverified")
    sha = branch["commit"].get("sha")
    if not isinstance(sha, str) or len(sha) != 40 or any(c not in "0123456789abcdef" for c in sha):
        raise EvidenceError("Invalid main SHA")
    issues = _get_json("/issues?state=open&per_page=100", token)
    prs = _get_json("/pulls?state=open&per_page=100", token)
    runs = _get_json(f"/actions/runs?branch=main&head_sha={sha}&per_page=100", token)
    return {"branch": branch, "issues": issues, "prs": prs, "runs": runs}


def _bounded_list(value: object, name: str) -> list[dict]:
    if not isinstance(value, list):
        raise EvidenceError(f"{name} is not a list")
    if len(value) >= MAX_ITEMS:
        raise EvidenceError(f"{name} reached pagination limit")
    if not all(isinstance(x, dict) for x in value):
        raise EvidenceError(f"{name} contains malformed entries")
    return value


def _item(x: dict) -> dict:
    n = x.get("number")
    title = x.get("title")
    if type(n) is not int or not isinstance(title, str):
        raise EvidenceError("Malformed issue/PR metadata")
    return {
        "number": n,
        "title": title[:240],
        "url": f"https://github.com/{REPOSITORY}/{'pull' if x.get('pull_request') else 'issues'}/{n}",
    }


def summarize(payload: dict, as_of: str) -> dict:
    if not isinstance(payload, dict):
        raise EvidenceError("Invalid evidence structure")
    branch = payload.get("branch")
    if not isinstance(branch, dict) or not isinstance(branch.get("commit"), dict):
        raise EvidenceError("Main branch SHA unverified")
    sha = branch["commit"].get("sha")
    if not isinstance(sha, str) or len(sha) != 40 or any(c not in "0123456789abcdef" for c in sha):
        raise EvidenceError("Invalid main commit SHA")
    issues_all = _bounded_list(payload.get("issues"), "issues")
    prs_all = _bounded_list(payload.get("prs"), "prs")
    open_issues = [_item(x) for x in issues_all if not x.get("pull_request")]
    open_prs = [_item({**x, "pull_request": True}) for x in prs_all]
    if len({x["number"] for x in open_issues}) != len(open_issues):
        raise EvidenceError("Duplicate issues")
    if len({x["number"] for x in open_prs}) != len(open_prs):
        raise EvidenceError("Duplicate pull requests")
    runs_obj = payload.get("runs")
    if not isinstance(runs_obj, dict):
        raise EvidenceError("Missing workflow run envelope")
    runs = _bounded_list(runs_obj.get("workflow_runs"), "workflow_runs")
    exact = [r for r in runs if r.get("head_sha") == sha and r.get("name") == REQUIRED_GATE]
    exact.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
    latest = exact[0] if exact else None
    ci_state = (
        "SUCCESS_EXACT_MAIN" if latest and latest.get("status") == "completed" and latest.get("conclusion") == "success"
        else "FAILED_EXACT_MAIN" if latest and latest.get("status") == "completed" and latest.get("conclusion") == "failure"
        else "NOT_VERIFIED"
    )
    blockers = []
    for issue in open_issues:
        title = issue["title"].lower()
        if any(word in title for word in ("license", "sbom", "blocked", "prerequisite", "live", "demo", "hygiene")):
            blockers.append(issue)
    for pr in open_prs:
        title = pr["title"].lower()
        if any(word in title for word in ("blocked", "review pending", "license", "security")):
            blockers.append(pr)
    report = {
        "schema_version": "1.0",
        "workflow_id": "FIN-P24-WZ-001",
        "mode": "READ_ONLY_GOVERNED_MONITOR",
        "as_of_utc": as_of,
        "source": {"repository": REPOSITORY, "main_sha": sha},
        "open_issue_count": len(open_issues),
        "open_pr_count": len(open_prs),
        "open_issues": sorted(open_issues, key=lambda x: x["number"]),
        "open_prs": sorted(open_prs, key=lambda x: x["number"]),
        "potential_blockers": sorted(blockers, key=lambda x: x["number"]),
        "exact_main_governance": {
            "status": ci_state,
            "run_id": latest.get("id") if latest else None,
            "run_url": f"https://github.com/{REPOSITORY}/actions/runs/{latest['id']}" if latest and type(latest.get("id")) is int else None,
        },
        "live_trading": "NOT_AUTHORIZED",
        "auto_trading": "NOT_AUTHORIZED",
        "final_completion": "NOT_VERIFIED",
        "next_action": "REVIEW_BLOCKERS_AND_TASK_CONTRACTS; NO_AUTOMATIC_APPROVAL",
        "evidence_limitations": [
            "GitHub listings are single-page; 100 entries means count unknown.",
            "Watcher cannot certify A5/A8/A10, Linear parity, UI, security, Demo, or final acceptance.",
            "Issue/PR state and one CI run do not prove roadmap completion.",
        ],
    }
    digest = hashlib.sha256(json.dumps(report, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    report["report_sha256"] = digest
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, help="Offline JSON evidence fixture")
    parser.add_argument("--as-of", help="UTC timestamp for reproducible offline tests")
    parser.add_argument("--output", type=Path, default=Path("build/finance-agent-watch/report.json"))
    args = parser.parse_args()
    stamp = args.as_of or datetime.now(timezone.utc).isoformat()
    try:
        payload = json.loads(args.fixture.read_text(encoding="utf-8")) if args.fixture else collect(os.environ.get("GITHUB_TOKEN", ""))
        report = summarize(payload, stamp)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        print(f"FINANCE_AGENT_WATCH=PASS mode=READ_ONLY main={report['source']['main_sha'][:12]} issues={report['open_issue_count']} prs={report['open_pr_count']} completion=NOT_VERIFIED")
        print(f"REPORT_SHA256={report['report_sha256']}")
        return 0
    except (EvidenceError, OSError, ValueError, TypeError):
        print("FINANCE_AGENT_WATCH=BLOCKED evidence_fetch_or_validation_failed", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
