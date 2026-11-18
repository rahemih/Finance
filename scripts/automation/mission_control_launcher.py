"""Owner-authorized, fixed-target GitHub Actions dispatch; public viewing is read-only."""
from __future__ import annotations

import hmac
import json
from threading import Lock
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API = ("https://api.github.com/repos/rahemih/Finance/actions/workflows/"
       "finance-openai-builder.yml/dispatches")
RUN_URL = "https://github.com/rahemih/Finance/actions/workflows/finance-openai-builder.yml"

class Launcher:
    """No arbitrary commands, model parameters, workflows or repository IDs."""
    def __init__(self, *, origin: str, owner_token: str, dispatch_token: str,
                 dispatch=None, cooldown: int = 1800):
        self.origin = origin.rstrip("/")
        self.owner_token = owner_token
        self.dispatch_token = dispatch_token
        self.dispatch = dispatch or self._github_dispatch
        self.cooldown = cooldown
        self.lock = Lock()
        self.last_started = 0.0
        self.last = {"status": "IDLE", "task_id": "FIN-P24-WZ-008",
                     "workflow": RUN_URL, "at": None, "error": None}

    @property
    def configured(self):
        return (self.origin.startswith("https://") and
                len(self.owner_token) >= 32 and len(self.dispatch_token) >= 32)

    def state(self):
        with self.lock:
            snap = dict(self.last)
        snap["configured"] = self.configured
        snap["mode"] = "OWNER_AUTHENTICATED_GITHUB_DISPATCH"
        snap["financial_mode"] = "DEMO_ONLY"
        snap["scope"] = "FIXED_GOVERNED_TASK_ONLY"
        if not self.configured:
            snap["status"] = "BLOCKED_CONFIGURATION"
        return snap

    def _github_dispatch(self):
        body = json.dumps({"ref": "main"}).encode("utf-8")
        request = Request(API, data=body, method="POST",
                          headers={
                              "Authorization": "Bearer " + self.dispatch_token,
                              "Accept": "application/vnd.github+json",
                              "X-GitHub-Api-Version": "2022-11-28",
                              "Content-Type": "application/json",
                              "User-Agent": "nexus-quant-owner-launch/1.0"
                          })
        with urlopen(request, timeout=18) as response:
            return response.status == 204

    def launch(self, *, authorization: str, origin: str, fetch_site: str, payload: object):
        if not self.configured:
            return 503, {"status": "BLOCKED_CONFIGURATION",
                         "error": "OWNER_OR_GITHUB_DISPATCH_TOKEN_MISSING"}
        if origin != self.origin or fetch_site != "same-origin":
            return 403, {"status": "BLOCKED_ORIGIN"}
        if not hmac.compare_digest(authorization, "Bearer " + self.owner_token):
            return 401, {"status": "OWNER_AUTH_REQUIRED"}
        if payload != {"action": "run_fixed_governed_task"}:
            return 422, {"status": "INVALID_FIXED_ACTION"}
        with self.lock:
            clock = time.monotonic()
            if clock - self.last_started < self.cooldown:
                return 429, {"status": "COOLDOWN", "retry_after_seconds":
                             max(1, int(self.cooldown - (clock - self.last_started)))}
            self.last_started = clock
            self.last = {"status": "REQUESTING_GITHUB", "task_id": "FIN-P24-WZ-008",
                         "workflow": RUN_URL, "at": None, "error": None}
            # Keep the lock during dispatch so concurrent triggers cannot fork spending.
            try:
                accepted = self.dispatch()
            except (HTTPError, URLError, TimeoutError, OSError):
                self.last["status"] = "BLOCKED_GITHUB_DISPATCH"
                self.last["error"] = "WORKFLOW_UNAVAILABLE_OR_NO_DISPATCH_PERMISSION"
                # A timeout may mean GitHub accepted the request; never blindly retry.
                return 502, dict(self.last)
            if not accepted:
                self.last["status"] = "BLOCKED_UNVERIFIED_DISPATCH"
                self.last["error"] = "GITHUB_DID_NOT_CONFIRM_DISPATCH"
                return 502, dict(self.last)
            self.last["status"] = "DISPATCH_ACCEPTED"
            self.last["at"] = time.time()
            return 202, dict(self.last)
