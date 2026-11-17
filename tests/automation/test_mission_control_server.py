"""Offline security and API tests for FIN-P24-WZ-003; no broker or network."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import threading
from urllib.error import HTTPError
from urllib.request import urlopen
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

    def test_unlisted_path_rejected(self):
        with self.assertRaises(HTTPError) as err:
            urlopen("http://127.0.0.1:%d/scripts/automation/agent_trace.py"%self.srv.server_port,timeout=4)
        self.assertEqual(err.exception.code,404)

if __name__=="__main__":
    unittest.main()
