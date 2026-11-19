"""Offline security and API tests for FIN-P24-WZ-003; no broker or network."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "automation"))
from mission_control_server import Journal, Handler, Server, trace

EVENT = {"agent_id":"A1","task_id":"FIN-P24-WZ-003","run_id":"test-run-123",
         "event_type":"TEST_STARTED","message":"Unit test started",
         "target":"tests/automation/test_mission_control_server.py"}

class JournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.j=Journal(Path(self.tmp.name)/"events.sqlite3")

    def test_idempotency(self):
        x,new=self.j.append(EVENT,"test-unique-001")
        y,duplicate=self.j.append(EVENT,"test-unique-001")
        self.assertTrue(new)
        self.assertFalse(duplicate)
        self.assertEqual(x,y)
        self.assertEqual(len(self.j.validate()),1)

    def test_hash_chain(self):
        a,_=self.j.append(EVENT,"test-unique-001")
        b,_=self.j.append({**EVENT,"event_type":"TEST_PASSED"},"test-unique-002")
        self.assertEqual(b["prev_hash"],a["event_hash"])
        self.assertEqual(b["seq"],2)
        self.assertEqual(self.j.export()["events"][-1]["event_hash"],b["event_hash"])

    def test_changed_idempotency_value_fails(self):
        self.j.append(EVENT,"test-unique-001")
        with self.assertRaises(trace.TraceError):
            self.j.append({**EVENT,"message":"modified"},"test-unique-001")

    def test_no_live_event(self):
        with self.assertRaises(trace.TraceError):
            self.j.append({**EVENT,"event_type":"ENABLE_LIVE"},"test-unique-001")

    def test_no_sensitive_text(self):
        with self.assertRaises(trace.TraceError):
            self.j.append({**EVENT,"message":"api_key=some-secret-string"},"test-unique-001")

    def test_reject_extra_fields(self):
        with self.assertRaises(trace.TraceError):
            self.j.append({**EVENT,"secret":"foo"},"test-unique-001")

    def test_reject_invalid_agent(self):
        with self.assertRaises(trace.TraceError):
            self.j.append({**EVENT,"agent_id":"A99"},"test-unique-001")

    def test_tampering_detected(self):
        self.j.append(EVENT,"test-unique-001")
        with self.j.db() as db:
            row=db.execute("SELECT payload FROM events LIMIT 1").fetchone()[0]
            db.execute("UPDATE events SET payload=? WHERE seq=1",(row.replace("Unit test","Fake test"),))
        with self.assertRaises(trace.TraceError):
            self.j.validate()

class PollingTests(unittest.TestCase):
    def test_recent_workflow_page_is_a_valid_bounded_window(self):
        from mission_control_server import State
        import inspect
        source = inspect.getsource(State._poll_loop)
        self.assertNotIn("len(runs) == 25", source)
        self.assertIn("len(prs) == 50 or len(issues) == 50", source)


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.j=Journal(Path(self.tmp.name)/"events.sqlite3")
        class FakeState:
            host="127.0.0.1";view_password="";session_secret="";ingest_token=""
            public_origin="";github={"status":"WAITING","verified_at":None,"runs":[],"prs":[],"issues":[],"error":"not ready"}
            def __init__(self,j):self.journal=j;self.lock=threading.RLock();self.subscribers=set()
            def snapshot(self):
                return {"schema_version":"nq.mission.v3","github":self.github,"trace":self.journal.export(),"api":{"live_trading":"DISABLED"}}
        self.srv=Server(("127.0.0.1",0),FakeState(self.j))
        self.t=threading.Thread(target=self.srv.serve_forever,daemon=True)
        self.t.start()
        self.addCleanup(self.srv.server_close)
        self.addCleanup(self.srv.shutdown)

    def test_health(self):
        with urlopen("http://127.0.0.1:%d/api/health"%self.srv.server_port,timeout=4) as r:
            self.assertEqual(json.load(r)["status"],"UP")

    def test_initial_state_no_fake_events(self):
        with urlopen("http://127.0.0.1:%d/api/state"%self.srv.server_port,timeout=4) as r:
            state=json.load(r)
            self.assertEqual(state["github"]["status"],"WAITING")
            self.assertEqual(state["trace"]["events"],[])

    def test_homepage_with_external_tracking_query(self):
        # A ChatGPT link can add ?utm_source=chatgpt.com; the homepage must remain public.
        url = "http://127.0.0.1:%d/?utm_source=chatgpt.com" % self.srv.server_port
        with urlopen(url, timeout=4) as response:
            self.assertEqual(response.status, 200)
            self.assertIn("text/html", response.headers.get("Content-Type", ""))
            self.assertIn(b"<!doctype html>", response.read(256).lower())

    def test_allowlisted_assets_with_queries(self):
        base = "http://127.0.0.1:%d" % self.srv.server_port
        for path, expected in (
            ("/index.html?utm_source=chatgpt.com", "text/html"),
            ("/styles.css?v=2", "text/css"),
            ("/font-control.js?v=2", "application/javascript"),
        ):
            with self.subTest(path=path), urlopen(base + path, timeout=4) as response:
                self.assertEqual(response.status, 200)
                self.assertIn(expected, response.headers.get("Content-Type", ""))

    def test_read_only_state_is_public_even_with_tracking_query(self):
        url = "http://127.0.0.1:%d/api/state?utm_source=chatgpt.com" % self.srv.server_port
        with urlopen(url, timeout=4) as response:
            self.assertEqual(response.status, 200)
            state = json.load(response)
            self.assertEqual(state["github"]["status"], "WAITING")
            self.assertEqual(state["trace"]["events"], [])

    def test_sse_stream_is_public(self):
        url = "http://127.0.0.1:%d/api/stream" % self.srv.server_port
        with urlopen(url, timeout=4) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers["Content-Type"], "text/event-stream; charset=utf-8")
            self.assertEqual(response.readline().strip(), b"event: snapshot")

    def test_paid_model_launch_is_not_exposed(self):
        base = "http://127.0.0.1:%d" % self.srv.server_port
        with self.assertRaises(HTTPError) as get_error:
            urlopen(base + "/api/launcher", timeout=4)
        self.assertEqual(get_error.exception.code, 404)
        for path in ("/api/launch", "/api/model/run"):
            with self.subTest(path=path):
                request = Request(base + path, method="POST",
                                  data=b'{"action":"run_fixed_governed_task"}',
                                  headers={"Content-Type":"application/json"})
                with self.assertRaises(HTTPError) as err:
                    urlopen(request, timeout=4)
                self.assertEqual(err.exception.code, 404)

    def test_public_home_describes_accurate_free_mode(self):
        base = "http://127.0.0.1:%d" % self.srv.server_port
        with urlopen(base + "/", timeout=4) as response:
            html = response.read().decode("utf-8")
        self.assertIn("بررسی فوری وضعیت پروژه", html)
        self.assertNotIn('id="operator-launch"', html)
        self.assertNotIn('src="launch.js"', html)
        self.assertNotIn("OPENAI BUILDER", html)

    def test_login_endpoint_removed(self):
        request = Request(
            "http://127.0.0.1:%d/api/login" % self.srv.server_port,
            data=b'{"password":"sample"}',
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(HTTPError) as err:
            urlopen(request, timeout=4)
        self.assertEqual(err.exception.code, 404)

    def test_event_ingestion_not_public_without_runner_token(self):
        self.srv.app.ingest_token = "a" * 48
        request = Request(
            "http://127.0.0.1:%d/api/events" % self.srv.server_port,
            data=json.dumps(EVENT).encode(),
            headers={"Content-Type": "application/json", "Idempotency-Key": "secure-run-123"},
            method="POST",
        )
        with self.assertRaises(HTTPError) as err:
            urlopen(request, timeout=4)
        self.assertEqual(err.exception.code, 401)
        self.assertEqual(self.j.validate(), [])

    def test_public_proxy_strips_unknown_github_fields(self):
        self.srv.app.gh = lambda path: (
            {"jobs": [{"id": 3, "name": "test", "status": "completed", "conclusion": "success",
                       "secret_field": "should-not-leak",
                       "steps": [{"name": "run", "status": "completed", "conclusion": "success",
                                  "started_at": "2026-01-01T00:00:00Z", "hidden": "no"}]}]}
            if "/jobs?" in path else
            [{"filename": "README.md", "status": "modified", "additions": 1, "deletions": 0,
              "hidden": "should-not-leak"}]
        )
        base = "http://127.0.0.1:%d" % self.srv.server_port
        with urlopen(base + "/api/github/actions/runs/123/jobs", timeout=4) as response:
            data = json.load(response)
            self.assertNotIn("secret_field", data["jobs"][0])
            self.assertNotIn("hidden", data["jobs"][0]["steps"][0])
        with urlopen(base + "/api/github/pulls/123/files", timeout=4) as response:
            data = json.load(response)
            self.assertNotIn("hidden", data["files"][0])

    def test_unknown_route_with_query_remains_not_found(self):
        url = "http://127.0.0.1:%d/not-an-asset?utm_source=chatgpt.com" % self.srv.server_port
        with self.assertRaises(HTTPError) as err:
            urlopen(url, timeout=4)
        self.assertEqual(err.exception.code, 404)

    def test_unlisted_path_rejected(self):
        with self.assertRaises(HTTPError) as err:
            urlopen("http://127.0.0.1:%d/scripts/automation/agent_trace.py"%self.srv.server_port,timeout=4)
        self.assertEqual(err.exception.code,404)

if __name__=="__main__":
    unittest.main()
