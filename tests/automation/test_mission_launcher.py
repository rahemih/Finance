"""End-to-end local HTTP tests for secure owner-only workflow dispatch."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"/"automation"))
from mission_control_launcher import Launcher
from mission_control_server import Server

ORIGIN="https://nq-agent-mission-preview-zeqg.onrender.com"
OWNER="o"*48
GITHUB="g"*48

class LauncherTests(unittest.TestCase):
    def new(self, dispatch=None):
        self.calls=[]
        return Launcher(origin=ORIGIN,owner_token=OWNER,dispatch_token=GITHUB,
                        dispatch=dispatch or (lambda:self.calls.append(1) or True),
                        cooldown=1800)

    def test_default_is_blocked_without_secrets(self):
        l=Launcher(origin=ORIGIN,owner_token="",dispatch_token="")
        self.assertFalse(l.state()["configured"])
        code,body=l.launch(authorization="",origin=ORIGIN,fetch_site="same-origin",
                            payload={"action":"run_fixed_governed_task"})
        self.assertEqual(code,503)
        self.assertEqual(body["error"],"OWNER_OR_GITHUB_DISPATCH_TOKEN_MISSING")

    def test_one_exact_owner_action_dispatches_once(self):
        l=self.new()
        code,info=l.launch(authorization="Bearer "+OWNER,origin=ORIGIN,
                           fetch_site="same-origin",payload={"action":"run_fixed_governed_task"})
        self.assertEqual(code,202)
        self.assertEqual(info["status"],"DISPATCH_ACCEPTED")
        self.assertEqual(len(self.calls),1)
        self.assertEqual(l.state()["mode"],"OWNER_AUTHENTICATED_GITHUB_DISPATCH")
        self.assertNotIn(OWNER,json.dumps(l.state()))
        self.assertNotIn(GITHUB,json.dumps(l.state()))
        second,data=l.launch(authorization="Bearer "+OWNER,origin=ORIGIN,
                           fetch_site="same-origin",payload={"action":"run_fixed_governed_task"})
        self.assertEqual(second,429)
        self.assertGreater(data["retry_after_seconds"],0)
        self.assertEqual(len(self.calls),1)

    def test_wrong_owner_and_cross_site_never_dispatch(self):
        l=self.new()
        for token,origin,fetch_site,expected in (
            ("Bearer "+("x"*48),ORIGIN,"same-origin",401),
            ("Bearer "+OWNER,"https://evil.example","same-origin",403),
            ("Bearer "+OWNER,ORIGIN,"cross-site",403),
        ):
            with self.subTest(expected=expected):
                status,_=l.launch(authorization=token,origin=origin,fetch_site=fetch_site,
                                  payload={"action":"run_fixed_governed_task"})
                self.assertEqual(status,expected)
        self.assertEqual(self.calls,[])

    def test_cannot_submit_arbitrary_task_or_workflow(self):
        l=self.new()
        for value in ({"action":"run","task":"rm-rf"},
                      {"action":"run_fixed_governed_task","ref":"unreviewed"},
                      {"action":"run_fixed_governed_task","model":"unlimited"}):
            status,_=l.launch(authorization="Bearer "+OWNER,origin=ORIGIN,
                              fetch_site="same-origin",payload=value)
            self.assertEqual(status,422)
        self.assertEqual(self.calls,[])

    def test_unconfirmed_dispatch_is_not_reported_as_started(self):
        l=self.new(dispatch=lambda:False)
        status,result=l.launch(authorization="Bearer "+OWNER,origin=ORIGIN,
                             fetch_site="same-origin",payload={"action":"run_fixed_governed_task"})
        self.assertEqual(status,502)
        self.assertEqual(result["status"],"BLOCKED_UNVERIFIED_DISPATCH")

    def test_unknown_response_is_not_blindly_retried(self):
        from urllib.error import URLError
        calls=[]
        def outage():
            calls.append(1)
            raise URLError("GitHub timeout")
        l=self.new(dispatch=outage)
        status,_=l.launch(authorization="Bearer "+OWNER,origin=ORIGIN,
                          fetch_site="same-origin",payload={"action":"run_fixed_governed_task"})
        self.assertEqual(status,502)
        self.assertEqual(len(calls),1)

class HttpLauncherTests(unittest.TestCase):
    def setUp(self):
        app=type("StubApp",(),{})()
        app.launcher=Launcher(origin=ORIGIN,owner_token=OWNER,dispatch_token=GITHUB,
                             dispatch=lambda:True,cooldown=1000)
        self.published=[]
        app.publish=lambda *event:self.published.append(event)
        self.server=Server(("127.0.0.1",0),app)
        self.base="http://127.0.0.1:"+str(self.server.server_port)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def start_request(self,token,body=None,origin=ORIGIN):
        payload=json.dumps(body or {"action":"run_fixed_governed_task"}).encode()
        return Request(self.base+"/api/launch",data=payload,method="POST",
            headers={"Content-Type":"application/json","Origin":origin,
                     "Sec-Fetch-Site":"same-origin","Authorization":"Bearer "+token})

    def test_http_public_status_contains_no_keys(self):
        with urlopen(self.base+"/api/launcher",timeout=4) as response:
            self.assertEqual(response.status,200)
            info=json.load(response)
        self.assertTrue(info["configured"])
        self.assertNotIn(OWNER,json.dumps(info))
        self.assertNotIn(GITHUB,json.dumps(info))

    def test_http_bad_secret_rejected_before_dispatch(self):
        with self.assertRaises(HTTPError) as err:
            urlopen(self.start_request("wrong"),timeout=4)
        self.assertEqual(err.exception.code,401)
        self.assertEqual(self.published,[])

    def test_http_start_returns_actual_github_acceptance(self):
        with urlopen(self.start_request(OWNER),timeout=4) as response:
            self.assertEqual(response.status,202)
            self.assertEqual(json.load(response)["status"],"DISPATCH_ACCEPTED")
        self.assertEqual(self.published[0][0],"launch")

    def test_http_unknown_command_does_not_dispatch(self):
        with self.assertRaises(HTTPError) as err:
            urlopen(self.start_request(OWNER,{"action":"execute_shell"}),timeout=4)
        self.assertEqual(err.exception.code,422)

if __name__=="__main__":
    unittest.main()
