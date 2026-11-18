"""Bounded, evidence-based Finance resume audit for Mission Control.

This is *not* a coding/LLM agent and has no repository write or trading tools.
It makes fixed read-only GitHub requests, resumes from current canonical main,
issues and PRs, and sends authentic audit events to the SSE journal.
No user-provided paths, commands, URLs or task identities are executed.
"""
from __future__ import annotations

from datetime import datetime, timezone
from http.client import HTTPException
from threading import Lock, Thread
from urllib.error import HTTPError, URLError
import re
import time
import uuid

TASK_ID = "FIN-P24-WZ-004"
SOURCE = "rahemih/Finance"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
MAX_RETRIES = 3
COOLDOWN_SECONDS = 300

def utc_now():
    return datetime.now(timezone.utc).isoformat()

class AuditError(Exception):
    pass

class ResumeAudit:
    """One in-process bounded public read-only run; no remote mutations."""
    def __init__(self, github_get, event_emit, publish, *, cooldown=COOLDOWN_SECONDS, delay=None,
                 inventory_snapshot=None, cache_age_seconds=1800):
        self.github_get = github_get
        self.event_emit = event_emit
        self.publish = publish
        self.cooldown = cooldown
        self.delay = delay or time.sleep
        # Reuse a recently fetched server-owned GitHub snapshot when available.
        # The audit still checks canonical main SHA and exact-main CI live.
        self.inventory_snapshot = inventory_snapshot
        self.cache_age_seconds = cache_age_seconds
        self.lock = Lock()
        self.last_start = 0.0
        self.state = {
            "mode": "READ_ONLY_RESUME_AUDIT", "status": "IDLE", "run_id": None,
            "started_at": None, "finished_at": None, "attempt": 0,
            "max_attempts": MAX_RETRIES, "main_sha": None, "next_task": None,
            "open_issues": None, "open_prs": None, "governance_ci": "NOT_VERIFIED",
            "blockers": [], "error": None, "writes_enabled": False,
            "trading_enabled": False, "automated_code_changes": False,
        }

    def snapshot(self):
        with self.lock:
            return dict(self.state)

    def _emit(self, agent, kind, message, target="-"):
        # The Journal validates event identity and sensitive data and emits to SSE.
        try:
            self.event_emit(agent, TASK_ID, self.state["run_id"], kind, message, target)
        except Exception:
            # Do not turn a telemetry failure into a fabricated success.
            raise AuditError("Event journal unavailable")

    def _progress(self, **fields):
        with self.lock:
            self.state.update(fields)
            visible = dict(self.state)
        self.publish("control", visible)

    def start(self):
        with self.lock:
            now = time.monotonic()
            if self.state["status"] in ("RUNNING", "RETRYING"):
                return 202, dict(self.state)
            if self.last_start and now - self.last_start < self.cooldown:
                wait = max(1, int(self.cooldown - (now - self.last_start)))
                return 429, {**self.state, "retry_after_seconds": wait}
            self.last_start = now
            run_id = "audit-" + uuid.uuid4().hex[:20]
            self.state = {
                **self.state, "run_id": run_id, "status": "RUNNING",
                "started_at": utc_now(), "finished_at": None, "attempt": 0,
                "main_sha": None, "next_task": None, "open_issues": None,
                "open_prs": None, "governance_ci": "NOT_VERIFIED",
                "blockers": [], "error": None,
            }
            visible = dict(self.state)
        self.publish("control", visible)
        Thread(target=self._run, daemon=True, name="nq-readonly-resume-audit").start()
        return 202, visible

    def _get(self, path):
        try:
            return self.github_get(path)
        except HTTPError as exc:
            # Do not retry rejected requests. Distinguish a confirmed rate
            # limit from a 403 whose cause cannot be reliably established.
            headers = exc.headers
            remaining = headers.get("X-RateLimit-Remaining") if headers else None
            if exc.code == 429 or (exc.code == 403 and remaining == "0"):
                raise AuditError("GitHub anonymous hourly read rate limit exhausted") from exc
            if exc.code == 401:
                raise AuditError("GitHub authentication denied; audit cannot verify data") from exc
            if exc.code == 403:
                raise AuditError("GitHub permission or rate limit blocked audit (cause unverified)") from exc
            if exc.code in (404, 422):
                raise AuditError("Required GitHub evidence endpoint was rejected") from exc
            raise
        except (URLError, TimeoutError, OSError, HTTPException):
            raise

    @staticmethod
    def _list(value, kind):
        if not isinstance(value, list):
            raise AuditError("Unverified GitHub " + kind + " listing")
        if len(value) >= 100:
            raise AuditError("GitHub " + kind + " listing saturated at 100; cannot certify complete")
        if not all(isinstance(item, dict) for item in value):
            raise AuditError("Malformed GitHub " + kind + " listing")
        return value

    def _inventory(self):
        """Prefer fresh authenticated server-poll results over repeat anonymous API calls.

        Return None if the source is stale, partial, malformed or saturated.
        Never use a cached record to claim an exact main SHA or Governance pass.
        """
        if self.inventory_snapshot is None:
            return None
        try:
            record = self.inventory_snapshot()
            if not isinstance(record, dict) or record.get("status") != "LIVE":
                return None
            stamp = record.get("verified_at")
            if not isinstance(stamp, str):
                return None
            parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                return None
            age = (datetime.now(timezone.utc) - parsed).total_seconds()
            if not 0 <= age <= self.cache_age_seconds:
                return None
            issues = self._list(record.get("issues"), "issues")
            prs = self._list(record.get("prs"), "PRs")
            if len(prs) >= 50 or len(issues) >= 50:
                return None
            sha = record.get("main_sha")
            ci = record.get("governance_ci")
            if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
                return None
            if ci not in ("PASS_EXACT_MAIN", "FAIL_EXACT_MAIN", "NOT_VERIFIED"):
                return None
            # These are the allowlisted server-poll fields; CI and SHA were
            # verified from the exact main branch in that same poll cycle.
            return sha, issues, prs, ci
        except (ValueError, TypeError, KeyError, AttributeError, AuditError):
            return None

    @staticmethod
    def _next_task(issues, prs):
        # Priority is an *audit suggestion*, not an authority to execute.
        ranks = (
            ("SECURITY_OR_SUPPLY_CHAIN", ("sbom", "license", "security", "vulnerability")),
            ("DEMO_ACCEPTANCE", ("demo", "broker", "provider")),
            ("WEB_IMPLEMENTATION", ("web-p0", "frontend", "ui", "next.js")),
            ("GOVERNANCE_RECONCILIATION", ("linear", "governance", "review", "lock")),
        )
        candidates = []
        for item in issues:
            n = item.get("number")
            title = item.get("title", "")
            if type(n) is int and isinstance(title, str):
                candidates.append({"number": n, "title": title[:160],
                                   "kind": "issue", "url": f"https://github.com/{SOURCE}/issues/{n}"})
        for item in prs:
            n = item.get("number")
            title = item.get("title", "")
            if type(n) is int and isinstance(title, str):
                candidates.append({"number": n, "title": title[:160],
                                   "kind": "pr", "url": f"https://github.com/{SOURCE}/pull/{n}"})
        def priority(item):
            title = item["title"].lower()
            for i, (_, keys) in enumerate(ranks):
                if any(word in title for word in keys):
                    return i, item["number"]
            return len(ranks), item["number"]
        candidates.sort(key=priority)
        if not candidates:
            return {"category": "FINAL_INDEPENDENT_AUDIT_REQUIRED",
                    "url": f"https://github.com/{SOURCE}",
                    "kind": "checkpoint", "number": None,
                    "title": "Open issue inventory empty; verify all roadmap gates independently"}
        chosen = candidates[0]
        chosen["category"] = next(
            (name for name, words in ranks if any(word in chosen["title"].lower() for word in words)),
            "REVIEW_CURRENT_OPEN_WORK")
        return chosen

    def _inspect(self):
        self._emit("A0", "TOOL_STARTED", "Retrieving canonical main branch", "main")
        cached = self._inventory()
        if cached is None:
            branch = self._get("/branches/main")
            sha = branch.get("commit", {}).get("sha") if isinstance(branch, dict) else None
            if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
                raise AuditError("Main branch SHA not verified")
        else:
            sha, issues, prs, conclusion = cached
        self._progress(main_sha=sha)
        self._emit("A9", "TEST_PASSED", "Main SHA verified against GitHub", "main")
        self._emit("A0", "TOOL_STARTED", "Reading open issues and pull requests", "backlog")
        if cached is None:
            issues_raw = self._list(self._get("/issues?state=open&per_page=100"), "issues")
            prs = self._list(self._get("/pulls?state=open&per_page=100"), "PRs")
            issues = [item for item in issues_raw if "pull_request" not in item]
        self._progress(open_issues=len(issues), open_prs=len(prs))
        self._emit("A9", "TEST_PASSED", "Current open work inventory retrieved", "backlog")
        self._emit("A0", "TEST_STARTED", "Checking exact-main governance CI", "governance")
        if cached is None:
            runs = self._get(f"/actions/runs?branch=main&head_sha={sha}&per_page=50")
            workflow_runs = runs.get("workflow_runs") if isinstance(runs, dict) else None
            if not isinstance(workflow_runs, list) or not all(isinstance(r, dict) for r in workflow_runs):
                raise AuditError("Governance CI evidence unavailable")
            ci = [r for r in workflow_runs if r.get("name") == "Governance Verify" and r.get("head_sha") == sha]
            ci.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
            latest = ci[0] if ci else None
            conclusion = (
                "PASS_EXACT_MAIN" if latest and latest.get("status") == "completed" and latest.get("conclusion") == "success"
                else "FAIL_EXACT_MAIN" if latest and latest.get("status") == "completed" and latest.get("conclusion") == "failure"
                else "NOT_VERIFIED"
            )
        self._progress(governance_ci=conclusion)
        self._emit("A9", "TEST_PASSED" if conclusion == "PASS_EXACT_MAIN" else "BLOCKED",
                   "Exact-main CI verified" if conclusion == "PASS_EXACT_MAIN" else "Exact-main CI not confirmed",
                   "governance")
        next_task = self._next_task(issues, prs)
        blockers = []
        if conclusion != "PASS_EXACT_MAIN":
            blockers.append("EXACT_MAIN_GOVERNANCE_NOT_VERIFIED")
        if next_task["category"] == "FINAL_INDEPENDENT_AUDIT_REQUIRED":
            blockers.append("FULL_ROADMAP_ACCEPTANCE_NOT_VERIFIED")
        if issues or prs:
            blockers.append("OPEN_REPOSITORY_WORK_NOT_RESOLVED")
        blockers.append("AUTONOMOUS_CODE_RUNNER_NOT_CONNECTED")
        self._progress(next_task=next_task, blockers=blockers)
        self._emit("A0", "HANDOFF", f"Next audit candidate: {next_task['category']}", "backlog")
        self._emit("A0", "BLOCKED",
                   "Automated fixes require separately authorized code runner; read-only audit completed",
                   "governance")

    def _run(self):
        try:
            self._emit("A0", "TASK_STARTED", "Started bounded read-only Finance resume inspection", "backlog")
        except AuditError:
            self._progress(status="BLOCKED", error="Event journal unavailable",
                           blockers=["EVENT_JOURNAL_UNAVAILABLE"], finished_at=utc_now())
            return
        for attempt in range(1, MAX_RETRIES + 1):
            self._progress(status="RUNNING" if attempt == 1 else "RETRYING", attempt=attempt)
            try:
                self._inspect()
                self._emit("A0", "TASK_FINISHED", "Resume inspection complete; next work needs governed runner", "backlog")
                self._progress(status="AUDIT_COMPLETE", finished_at=utc_now())
                return
            except AuditError as exc:
                # Fail closed. Authorization, validation, event integrity and saturation errors never auto-retry.
                self._progress(status="BLOCKED", error=str(exc),
                               blockers=["GITHUB_OR_EVENT_EVIDENCE_UNAVAILABLE"],
                               finished_at=utc_now())
                try:
                    self._emit("A0", "BLOCKED", "Insufficient verified evidence for safe resume", "backlog")
                except Exception:
                    pass
                return
            except Exception:
                # Infrastructure failures get a finite bounded retry, with no leaked error details.
                if attempt < MAX_RETRIES:
                    self._progress(status="RETRYING", error="Transient read-only API error")
                    try:
                        self._emit("A9", "ERROR", "Transient evidence request failed; retrying", "backlog")
                    except Exception:
                        pass
                    self.delay(min(2 ** (attempt - 1), 4))
                else:
                    self._progress(status="BLOCKED", error="API unavailable after bounded retries",
                                   blockers=["GITHUB_API_UNREACHABLE"], finished_at=utc_now())
                    try:
                        self._emit("A0", "BLOCKED", "GitHub unavailable after three bounded attempts", "backlog")
                    except Exception:
                        pass
                    return
