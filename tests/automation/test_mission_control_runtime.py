"""Bounded operator Start/resume tests; no broker, network or repository mutations."""
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
import time
import unittest
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "automation"))
from mission_control_runtime import ResumeAudit, MAX_RETRIES  # noqa: E402

SHA = "a" * 40

def github_fixture(path):
    if path == "/branches/main":
        return {"commit": {"sha": SHA}}
    if path == "/issues?state=open&per_page=100":
        return [{"number": 530, "title": "P04-F SBOM license blocker"},
                {"number": 535, "title": "PR is mirrored", "pull_request": {}}]
    if path == "/pulls?state=open&per_page=100":
        return [{"number": 535, "title": "Mission Control API"}]
    if path.startswith("/actions/runs?branch=main&head_sha=" + SHA):
        return {"workflow_runs": [{
            "name": "Governance Verify", "status": "completed",
            "conclusion": "success", "head_sha": SHA, "created_at": "2026-11-18T08:00:00Z"
        }]}
    raise AssertionError("Unexpected URL: " + path)

def finish(audit):
    for _ in range(200):
        snapshot = audit.snapshot()
        if snapshot["status"] in ("AUDIT_COMPLETE", "BLOCKED"):
            return snapshot
        time.sleep(.005)
    raise AssertionError("Audit did not reach a terminal status")

class ResumeAuditTests(unittest.TestCase):
    def new(self, fetch=github_fixture, cooldown=300, delay=None):
        self.events = []
        self.published = []
        return ResumeAudit(
            fetch,
            lambda *args: self.events.append(args),
            lambda *args: self.published.append(args),
            cooldown=cooldown,
            delay=delay or (lambda _: None),
        )

    def test_real_read_only_resume_identifies_next_blocker(self):
        paths = []
        def fetch(path):
            paths.append(path)
            return github_fixture(path)
        audit = self.new(fetch)
        code, first = audit.start()
        self.assertEqual(code, 202)
        self.assertEqual(first["mode"], "READ_ONLY_RESUME_AUDIT")
        done = finish(audit)
        self.assertEqual(done["status"], "AUDIT_COMPLETE")
        self.assertEqual(done["main_sha"], SHA)
        self.assertEqual(done["governance_ci"], "PASS_EXACT_MAIN")
        self.assertEqual(done["open_issues"], 1)
        self.assertEqual(done["open_prs"], 1)
        self.assertEqual(done["next_task"]["number"], 530)
        self.assertFalse(done["writes_enabled"])
        self.assertFalse(done["automated_code_changes"])
        self.assertFalse(done["trading_enabled"])
        self.assertTrue(any(x[3]=="TASK_STARTED" for x in self.events))
        self.assertTrue(any(x[3]=="TASK_FINISHED" for x in self.events))
        self.assertEqual(len(paths),4)
        self.assertTrue(all(x.startswith(("/branches/", "/issues?", "/pulls?", "/actions/")) for x in paths))
        self.assertTrue(all(name=="control" for name, _ in self.published))

    def test_fresh_polled_sha_inventory_and_governance_avoids_all_extra_github_requests(self):
        calls = []
        def forbidden_extra(path):
            calls.append(path)
            raise AssertionError("Cached audit must not make duplicate GitHub requests")
        cache = {
            "status": "LIVE", "verified_at": datetime.now(timezone.utc).isoformat(),
            "main_sha": SHA, "governance_ci": "PASS_EXACT_MAIN",
            "issues": [{"number": 530, "title": "P04-F SBOM license blocker"}],
            "prs": [{"number": 535, "title": "Mission Control API"}]
        }
        audit=ResumeAudit(forbidden_extra,lambda *args:None,
                          lambda *args:None,
                          inventory_snapshot=lambda:dict(cache),delay=lambda _:None)
        code,_=audit.start()
        done=finish(audit)
        self.assertEqual(code,202)
        self.assertEqual(calls,[])
        self.assertEqual(done["status"],"AUDIT_COMPLETE")
        self.assertEqual(done["main_sha"],SHA)
        self.assertEqual(done["governance_ci"],"PASS_EXACT_MAIN")
        self.assertEqual(done["next_task"]["number"],530)

    def test_stale_or_unverified_snapshot_never_claims_a_governance_pass(self):
        bad_cache={
            "status":"LIVE",
            "verified_at": (datetime.now(timezone.utc)-timedelta(hours=3)).isoformat(),
            "main_sha": SHA, "governance_ci":"PASS_EXACT_MAIN",
            "issues":[], "prs":[]
        }
        calls=[]
        def fresh_source(path):
            calls.append(path)
            return github_fixture(path)
        audit=ResumeAudit(fresh_source,lambda *args:None,
                          lambda *args:None,
                          inventory_snapshot=lambda:dict(bad_cache),delay=lambda _:None)
        audit.start()
        done=finish(audit)
        self.assertEqual(done["status"],"AUDIT_COMPLETE")
        self.assertEqual(len(calls),4)
        self.assertEqual(done["open_prs"],1)

    def test_cache_without_exact_ci_or_sha_is_discarded(self):
        snapshot={"status":"LIVE","verified_at":datetime.now(timezone.utc).isoformat(),
                  "main_sha":"not-a-sha","governance_ci":"PASS_EXACT_MAIN",
                  "issues":[],"prs":[]}
        a=self.new()
        a.inventory_snapshot=lambda:snapshot
        self.assertIsNone(a._inventory())
        snapshot["main_sha"]=SHA
        snapshot["governance_ci"]="success"
        self.assertIsNone(a._inventory())

    def test_second_start_during_cooldown_is_rate_limited(self):
        audit=self.new()
        audit.start()
        finish(audit)
        code, info=audit.start()
        self.assertEqual(code,429)
        self.assertGreater(info["retry_after_seconds"],0)

    def test_403_never_retries(self):
        calls=[]
        def forbidden(path):
            calls.append(path)
            raise HTTPError(url="https://api.github.com", code=403, msg="blocked", hdrs=None, fp=None)
        audit=self.new(forbidden)
        audit.start()
        done=finish(audit)
        self.assertEqual(done["status"], "BLOCKED")
        self.assertEqual(done["attempt"],1)
        self.assertEqual(len(calls),1)
        self.assertIn("rate limit",done["error"])

    def test_confirmed_rate_limit_is_reported_precisely_and_never_retried(self):
        calls=[]
        def exhausted(path):
            calls.append(path)
            raise HTTPError(url="https://api.github.com", code=403,
                            msg="API rate limit exceeded",
                            hdrs={"X-RateLimit-Remaining":"0"}, fp=None)
        audit=self.new(exhausted)
        audit.start()
        outcome=finish(audit)
        self.assertEqual(outcome["status"],"BLOCKED")
        self.assertIn("hourly read rate limit exhausted",outcome["error"])
        self.assertEqual(len(calls),1)

    def test_invalid_authentication_is_not_credited_as_a_rate_limit(self):
        def unauthorized(path):
            raise HTTPError(url="https://api.github.com", code=401,
                            msg="bad credentials", hdrs={}, fp=None)
        audit=self.new(unauthorized)
        audit.start()
        outcome=finish(audit)
        self.assertEqual(outcome["status"],"BLOCKED")
        self.assertIn("authentication denied",outcome["error"])
        self.assertNotIn("rate limit",outcome["error"])

    def test_infrastructure_errors_retry_at_most_three_times(self):
        count=[]
        def outage(path):
            count.append(path)
            raise TimeoutError("temporary")
        audit=self.new(outage)
        audit.start()
        done=finish(audit)
        self.assertEqual(done["status"],"BLOCKED")
        self.assertEqual(done["attempt"],MAX_RETRIES)
        self.assertEqual(len(count),MAX_RETRIES)

    def test_recover_on_last_retry(self):
        count=[]
        def recovering(path):
            if path=="/branches/main":
                count.append(path)
                if len(count)<3:
                    raise TimeoutError("outage")
            return github_fixture(path)
        audit=self.new(recovering)
        audit.start()
        done=finish(audit)
        self.assertEqual(done["status"],"AUDIT_COMPLETE")
        self.assertEqual(done["attempt"],3)

    def test_fail_closed_when_inventory_saturated(self):
        def many(path):
            if path.startswith("/issues?"):
                return [{"number": n, "title": "Issue"} for n in range(100)]
            return github_fixture(path)
        audit=self.new(many)
        audit.start()
        done=finish(audit)
        self.assertEqual(done["status"],"BLOCKED")
        self.assertEqual(done["open_prs"],None)

    def test_failure_in_emit_does_not_claim_success(self):
        audit=ResumeAudit(github_fixture,lambda *x: (_ for _ in ()).throw(ValueError("storage down")),
                          lambda *x:None,delay=lambda _:None)
        audit.start()
        done=finish(audit)
        self.assertEqual(done["status"],"BLOCKED")
        self.assertNotEqual(done["status"],"AUDIT_COMPLETE")

    def test_missing_ci_never_becomes_pass(self):
        def no_ci(path):
            if path.startswith("/actions/runs?"):
                return {"workflow_runs":[]}
            return github_fixture(path)
        audit=self.new(no_ci)
        audit.start()
        done=finish(audit)
        self.assertEqual(done["governance_ci"],"NOT_VERIFIED")
        self.assertIn("EXACT_MAIN_GOVERNANCE_NOT_VERIFIED",done["blockers"])

    def test_bad_main_sha_blocks(self):
        def bad(path):
            if path=="/branches/main":
                return {"commit":{"sha":"bad"}}
            return github_fixture(path)
        audit=self.new(bad)
        audit.start()
        self.assertEqual(finish(audit)["status"],"BLOCKED")

if __name__=="__main__":
    unittest.main()
