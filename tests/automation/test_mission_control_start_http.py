"""HTTP acceptance tests for read-only Start and protected event ingestion."""
import json
from unittest.mock import patch
from pathlib import Path
import sys
import threading
import tempfile
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"/"automation"))
from mission_control_runtime import ResumeAudit
from mission_control_server import Server, Journal, State

SHA="b"*40

def fake_github(path):
    if path=="/branches/main":return {"commit":{"sha":SHA}}
    if path.startswith("/issues?"):return [{"number":530,"title":"SBOM license issue"}]
    if path.startswith("/pulls?"):return []
    if path.startswith("/actions/"):return {"workflow_runs":[]}
    raise RuntimeError("unknown fixture path")

class StartHttpTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        journal=Journal(Path(tmp.name)/"journal.db")
        app=type("App",(),{})()
        app.host="127.0.0.1";app.public_origin="";app.ingest_token="z"*40
        app.lock=threading.RLock();app.subscribers=set();app.journal=journal
        app.audit=ResumeAudit(fake_github,lambda *x:None,lambda *x:None,cooldown=60,delay=lambda _:None)
        app.snapshot=lambda:{"schema_version":"nq.mission.v3","github":{"status":"WAITING","runs":[],"prs":[],"issues":[]},"trace":journal.export(),"control":app.audit.snapshot()}
        self.app=app
        self.srv=Server(("127.0.0.1",0),app)
        thread=threading.Thread(target=self.srv.serve_forever,daemon=True)
        thread.start()
        self.addCleanup(self.srv.server_close)
        self.addCleanup(self.srv.shutdown)
        self.base="http://127.0.0.1:"+str(self.srv.server_port)

    def request(self,body,*,origin=None,content_type="application/json"):
        hdr={"Content-Type":content_type}
        if origin is not None:hdr["Origin"]=origin
        return Request(self.base+"/api/start",data=json.dumps(body).encode(),headers=hdr,method="POST")

    def test_one_click_start_enqueues_real_bounded_audit(self):
        with urlopen(self.request({"action":"resume_audit"}),timeout=4) as res:
            self.assertEqual(res.status,202)
            payload=json.load(res)
            self.assertEqual(payload["mode"],"READ_ONLY_RESUME_AUDIT")
            self.assertFalse(payload["writes_enabled"])
        for _ in range(100):
            if self.app.audit.snapshot()["status"] in ("AUDIT_COMPLETE","BLOCKED"):break
            time.sleep(.01)
        with urlopen(self.base+"/api/control",timeout=4) as res:
            result=json.load(res)
            self.assertEqual(result["status"],"AUDIT_COMPLETE")
            self.assertEqual(result["main_sha"],SHA)

    def test_public_start_cannot_accept_arbitrary_command(self):
        with self.assertRaises(HTTPError) as err:
            urlopen(self.request({"action":"execute","cmd":"rm -rf"}),timeout=4)
        self.assertEqual(err.exception.code,422)

    def test_cross_origin_action_is_rejected(self):
        self.app.public_origin="https://nq.example.com"
        with self.assertRaises(HTTPError) as err:
            urlopen(self.request({"action":"resume_audit"},origin="https://evil.example"),timeout=4)
        self.assertEqual(err.exception.code,403)
        self.assertEqual(self.app.audit.snapshot()["status"],"IDLE")

    def test_remote_mode_rejects_missing_origin(self):
        # A public Start is an audit request, never a cross-site command.
        self.app.public_origin="https://nq.example.com"
        with self.assertRaises(HTTPError) as err:
            urlopen(self.request({"action":"resume_audit"}),timeout=4)
        self.assertEqual(err.exception.code,403)
        self.assertEqual(self.app.audit.snapshot()["status"],"IDLE")

    def test_cross_site_fetch_metadata_is_rejected(self):
        req=self.request({"action":"resume_audit"})
        req.add_header("Sec-Fetch-Site","cross-site")
        with self.assertRaises(HTTPError) as err:
            urlopen(req,timeout=4)
        self.assertEqual(err.exception.code,403)
        self.assertEqual(self.app.audit.snapshot()["status"],"IDLE")

    def test_remote_same_origin_start_is_accepted(self):
        # A legitimate browser request from the configured HTTPS origin must work.
        self.app.public_origin="https://nq.example.com"
        req=self.request({"action":"resume_audit"},origin="https://nq.example.com")
        req.add_header("Sec-Fetch-Site","same-origin")
        with urlopen(req,timeout=4) as res:
            self.assertEqual(res.status,202)
            self.assertFalse(json.load(res)["writes_enabled"])

    def test_remote_same_origin_rejects_cross_site_metadata(self):
        # A matching Origin alone cannot override contradictory browser metadata.
        self.app.public_origin="https://nq.example.com"
        req=self.request({"action":"resume_audit"},origin="https://nq.example.com")
        req.add_header("Sec-Fetch-Site","cross-site")
        with self.assertRaises(HTTPError) as err:
            urlopen(req,timeout=4)
        self.assertEqual(err.exception.code,403)
        self.assertEqual(self.app.audit.snapshot()["status"],"IDLE")

    def test_remote_origin_prefix_spoof_is_rejected(self):
        # A hostile hostname containing the trusted origin as a prefix must
        # not satisfy the exact-origin check or start an audit.
        self.app.public_origin="https://nq.example.com"
        req=self.request({"action":"resume_audit"},origin="https://nq.example.com.evil.example")
        req.add_header("Sec-Fetch-Site","same-origin")
        with self.assertRaises(HTTPError) as err:
            urlopen(req,timeout=4)
        self.assertEqual(err.exception.code,403)
        self.assertEqual(self.app.audit.snapshot()["status"],"IDLE")

    def test_remote_state_requires_https_public_origin(self):
        # A remotely bound server must never start with an absent or insecure
        # public origin, otherwise the Start Origin check could be disabled.
        with tempfile.TemporaryDirectory() as tmp:
            env = {
                "NQ_HOST": "0.0.0.0",
                "NQ_PUBLIC_ORIGIN": "",
                "RENDER_EXTERNAL_URL": "",
                "NQ_DATA_PATH": str(Path(tmp) / "journal.db"),
                "NQ_INGEST_TOKEN": "",
            }
            with patch.dict("os.environ", env):
                with self.assertRaisesRegex(RuntimeError, "Remote mode requires HTTPS public origin"):
                    State()

    def test_remote_state_rejects_plain_http_origin(self):
        # A remote listener must not accept an HTTP origin for Start requests.
        with tempfile.TemporaryDirectory() as tmp:
            env = {
                "NQ_HOST": "0.0.0.0",
                "NQ_PUBLIC_ORIGIN": "http://nq.example.com",
                "RENDER_EXTERNAL_URL": "",
                "NQ_DATA_PATH": str(Path(tmp) / "journal.db"),
                "NQ_INGEST_TOKEN": "",
            }
            with patch.dict("os.environ", env):
                with self.assertRaisesRegex(RuntimeError, "Remote mode requires HTTPS public origin"):
                    State()

    def test_public_start_does_not_authorize_event_ingestion(self):
        req=Request(self.base+"/api/events",
            data=json.dumps({"agent_id":"A1"}).encode(),
            headers={"Content-Type":"application/json"},method="POST")
        with self.assertRaises(HTTPError) as err:
            urlopen(req,timeout=4)
        self.assertEqual(err.exception.code,401)
        self.assertEqual(self.app.journal.validate(),[])

    def test_rate_limit_rejects_repeat_start(self):
        with urlopen(self.request({"action":"resume_audit"}),timeout=4):pass
        # Existing in-flight request returns the active status (202); completed
        # requests are limited to 1 per cooldown.
        for _ in range(100):
            if self.app.audit.snapshot()["status"]=="AUDIT_COMPLETE":break
            time.sleep(.01)
        with self.assertRaises(HTTPError) as err:
            urlopen(self.request({"action":"resume_audit"}),timeout=4)
        self.assertEqual(err.exception.code,429)

if __name__=="__main__":unittest.main()
