"""NEXUS QUANT governed, read-only Mission Control streaming API.

Not a trading engine. No approval escalation, order routing or arbitrary code execution.
"""
from __future__ import annotations

from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from queue import Empty, Full, Queue
from contextlib import contextmanager
import hashlib
import hmac
import json
import os
import re
import sqlite3
import threading
import time
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

import agent_trace as trace
from mission_control_runtime import ResumeAudit

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "apps" / "agent-mission-control"
API = "https://api.github.com/repos/rahemih/Finance"
RUN_PATH = re.compile(r"^/api/github/actions/runs/([0-9]{1,16})/jobs$")
PR_PATH = re.compile(r"^/api/github/pulls/([0-9]{1,12})/files$")
ASSETS = {"/": "index.html", "/index.html": "index.html", "/app.js": "app.js",
          "/trace-ui.js": "trace-ui.js", "/live.js": "live.js", "/font-control.js": "font-control.js", "/styles.css": "styles.css"}
SOURCE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{5,95}$")


def now():
    return datetime.now(timezone.utc).isoformat()


class Journal:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        with self.db() as db:
            db.execute("CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY, source_id TEXT UNIQUE NOT NULL, payload TEXT NOT NULL)")
        self.validate()

    @contextmanager
    def db(self):
        con = sqlite3.connect(str(self.path), timeout=10)
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def validate(self):
        with self.lock, self.db() as db:
            rows = db.execute("SELECT seq,payload FROM events ORDER BY seq").fetchall()
            events = trace.verify([row[1] for row in rows])
            if any(row[0] != event["seq"] for row, event in zip(rows, events)):
                raise trace.TraceError("Journal index mismatch")
            return events

    def append(self, incoming, source_id):
        if not isinstance(source_id, str) or not SOURCE_ID.fullmatch(source_id):
            raise trace.TraceError("Invalid idempotency key")
        if not isinstance(incoming, dict) or set(incoming) != {
            "agent_id", "task_id", "run_id", "event_type", "message", "target"
        }:
            raise trace.TraceError("Unexpected input fields")
        e = trace._event_data(incoming["agent_id"], incoming["task_id"], incoming["run_id"],
                              incoming["event_type"], incoming["message"], incoming["target"], now())
        with self.lock, self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute("SELECT payload FROM events WHERE source_id=?", (source_id,)).fetchone()
            if old:
                prev = json.loads(old[0])
                if any(prev.get(k) != incoming[k] for k in incoming):
                    raise trace.TraceError("Reused idempotency key with changed event")
                return prev, False
            tail = db.execute("SELECT payload FROM events ORDER BY seq DESC LIMIT 1").fetchone()
            last = json.loads(tail[0]) if tail else None
            e["seq"] = last["seq"] + 1 if last else 1
            e["prev_hash"] = last["event_hash"] if last else "0" * 64
            e["event_hash"] = hashlib.sha256(trace.canonical(e)).hexdigest()
            db.execute("INSERT INTO events (seq,source_id,payload) VALUES (?,?,?)",
                       (e["seq"], source_id, trace.canonical(e).decode()))
        return e, True

    def export(self):
        events = self.validate()
        # Capped to avoid oversized SSE and to keep UI responsive.
        tail = events[-400:]
        return {
            "schema_version": trace.SCHEMA,
            "source": "AUTHENTICATED_RUNNER_EVENT_API",
            "verified_local_chain": True,
            "authenticated_agent_identity": False,
            "financial_mode": "DEMO_ONLY",
            "base_seq": tail[0]["seq"] if tail else 1,
            "previous_hash": tail[0]["prev_hash"] if tail else "0" * 64,
            "last_hash": tail[-1]["event_hash"] if tail else None,
            "events": tail,
        }


class State:
    def __init__(self):
        self.lock = threading.RLock()
        self.journal = Journal(os.getenv("NQ_DATA_PATH", "/tmp/nq-events.sqlite3"))
        self.ingest_token = os.getenv("NQ_INGEST_TOKEN", "")
        self.public_origin = os.getenv("NQ_PUBLIC_ORIGIN", "") or os.getenv("RENDER_EXTERNAL_URL", "")
        self.github_token = os.getenv("NQ_GITHUB_TOKEN", "")
        self.github_interval = max(60, int(os.getenv("NQ_GITHUB_POLL_SECONDS", "300")))
        self.github = {"status": "WAITING", "verified_at": None, "runs": [],
                       "prs": [], "issues": [], "error": "No successful GitHub fetch"}
        self.subscribers = set()
        self.audit_event_lock = threading.Lock()
        self.audit_event_seq = 0
        self.audit = ResumeAudit(self.gh, self._audit_emit, self.publish)
        host = os.getenv("NQ_HOST", "127.0.0.1")
        self.host = host
        if host not in ("127.0.0.1", "localhost", "::1") and not self.public_origin.startswith("https://"):
            raise RuntimeError("Remote mode requires HTTPS public origin")
        if self.ingest_token and len(self.ingest_token) < 32:
            raise RuntimeError("Ingest token too short")
        threading.Thread(target=self._poll_loop, daemon=True).start()

    def gh(self, path):
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "NQ-Mission-Control/3.0",
                   "X-GitHub-Api-Version": "2022-11-28"}
        if self.github_token:
            headers["Authorization"] = "Bearer " + self.github_token
        with urlopen(Request(API + path, headers=headers), timeout=14) as r:
            return json.load(r)

    def _poll_loop(self):
        while True:
            try:
                runs = self.gh("/actions/runs?per_page=25")["workflow_runs"]
                prs = self.gh("/pulls?state=open&per_page=50")
                issues = self.gh("/issues?state=open&per_page=50")
                if not all(isinstance(x, list) for x in [runs, prs, issues]):
                    raise ValueError("Malformed API response")
                # Workflow dashboard intentionally shows the newest 25 runs,
                # not the complete lifetime history; a full first page is valid.
                # PR/issue inventories still fail closed if they hit their page cap.
                if len(prs) == 50 or len(issues) == 50:
                    raise ValueError("PR/issue pagination limit")
                # Public view: only expose GitHub fields required by the monitor.
                # Never forward arbitrary API fields (identities, permissions, tokens).
                runs = [{key: item.get(key) for key in (
                    "id", "name", "event", "status", "conclusion", "head_sha", "created_at"
                )} for item in runs]
                prs = [{key: item.get(key) for key in (
                    "number", "title", "draft", "updated_at"
                )} for item in prs]
                issues = [{key: item.get(key) for key in (
                    "number", "title", "updated_at"
                )} for item in issues if "pull_request" not in item]
                fresh = {"status": "LIVE", "verified_at": now(), "runs": runs,
                         "prs": prs, "issues": issues,
                         "error": None}
            except (Exception,):
                with self.lock:
                    fresh = {**self.github, "status": "DEGRADED",
                             "error": "GitHub unavailable; last successful data may be stale"}
            with self.lock:
                self.github = fresh
            self.publish("github", fresh)
            time.sleep(self.github_interval)

    def publish(self, name, value):
        packet = (name, json.dumps(value, ensure_ascii=False, separators=(",", ":")))
        with self.lock:
            for q in list(self.subscribers):
                try:
                    q.put_nowait(packet)
                except Full:
                    try: q.get_nowait()
                    except Empty: pass
                    try: q.put_nowait(("resync", "{}"))
                    except Full: pass

    def _audit_emit(self, agent_id, task_id, run_id, event_type, message, target):
        # One source event per actual step; no API/runner impersonation.
        with self.audit_event_lock:
            self.audit_event_seq += 1
            key = f"{run_id}-{self.audit_event_seq}"
        event, is_new = self.journal.append({
            "agent_id": agent_id, "task_id": task_id, "run_id": run_id,
            "event_type": event_type, "message": message, "target": target,
        }, key)
        if is_new:
            self.publish("trace", event)

    def snapshot(self):
        with self.lock:
            gh = json.loads(json.dumps(self.github))
        return {"schema_version": "nq.mission.v3", "server_time": now(),
                "github": gh, "trace": self.journal.export(),
                "control": self.audit.snapshot(),
                "api": {"connected": True, "stream": "SSE",
                        "ingestion_enabled": bool(self.ingest_token),
                        "live_trading": "DISABLED", "auto_trading": "DISABLED",
                        "agent_runtime": "NOT_CONNECTED_UNTIL_RUNNER_EMITS"}}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, format, *args):
        if not self.path.startswith("/api/events"):
            super().log_message(format, *args)

    @property
    def app(self):
        return self.server.app

    def send(self, code, data):
        body = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode()
        self.send_response(code)
        self._out_headers("application/json; charset=utf-8", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _out_headers(self, typ, size=None):
        self.send_header("Content-Type", typ)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; font-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
        if size is not None:
            self.send_header("Content-Length", str(size))

    def do_GET(self):
        # Separate path from browser-added query strings (e.g. ?utm_source=chatgpt.com).
        # Only allowlisted, read-only GET paths are public; ingestion still requires the runner token.
        path = urlsplit(self.path).path
        if path in ASSETS:
            target = WEB / ASSETS[path]
            try: data = target.read_bytes()
            except OSError:
                return self.send(404, {"error": "not_found"})
            typ = ("text/html; charset=utf-8" if target.suffix == ".html" else
                   "text/css; charset=utf-8" if target.suffix == ".css" else
                   "application/javascript; charset=utf-8")
            self.send_response(200); self._out_headers(typ, len(data)); self.end_headers()
            self.wfile.write(data)
            return
        if path == "/api/health":
            return self.send(200, {"status": "UP", "mode": "DEMO_ONLY"})
        if path == "/api/state":
            return self.send(200, self.app.snapshot())
        if path == "/api/control":
            return self.send(200, self.app.audit.snapshot())
        if path == "/api/stream":
            return self._stream()
        match = RUN_PATH.fullmatch(path)
        if match:
            return self.proxy("/actions/runs/" + match[1] + "/jobs?per_page=100")
        match = PR_PATH.fullmatch(path)
        if match:
            return self.proxy("/pulls/" + match[1] + "/files?per_page=100", files=True)
        return self.send(404, {"error": "not_found"})

    def proxy(self, path, files=False):
        try:
            data = self.app.gh(path)
            if files:
                if not isinstance(data, list) or len(data) >= 100:
                    return self.send(502, {"error": "incomplete_files"})
                safe_files = [{key: item.get(key) for key in (
                    "filename", "status", "additions", "deletions"
                )} for item in data if isinstance(item, dict)]
                return self.send(200, {"files": safe_files})
            jobs = data.get("jobs") if isinstance(data, dict) else None
            if not isinstance(jobs, list) or len(jobs) >= 100:
                return self.send(502, {"error": "incomplete_jobs"})
            safe_jobs = [{
                "id": item.get("id"), "name": item.get("name"),
                "status": item.get("status"), "conclusion": item.get("conclusion"),
                "steps": [{
                    key: step.get(key) for key in ("name", "status", "conclusion", "started_at")
                } for step in item.get("steps", []) if isinstance(step, dict)]
            } for item in jobs if isinstance(item, dict)]
            return self.send(200, {"jobs": safe_jobs})
        except Exception:
            return self.send(502, {"error": "github_unavailable"})

    def _stream(self):
        q = Queue(maxsize=64)
        with self.app.lock:
            if len(self.app.subscribers) >= 24:
                return self.send(503, {"error": "too_many_viewers"})
            self.app.subscribers.add(q)
        self.send_response(200)
        self._out_headers("text/event-stream; charset=utf-8")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        try:
            payload = json.dumps(self.app.snapshot(), ensure_ascii=False, separators=(",", ":"))
            self.wfile.write(("event: snapshot\ndata: " + payload + "\n\n").encode())
            self.wfile.flush()
            while True:
                try:
                    name, value = q.get(timeout=14)
                    self.wfile.write(("event: " + name + "\ndata: " + value + "\n\n").encode())
                except Empty:
                    self.wfile.write(b": heartbeat\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            with self.app.lock: self.app.subscribers.discard(q)
            self.close_connection = True

    def do_POST(self):
        length = self.headers.get("Content-Length", "")
        try: size = int(length)
        except ValueError: size = -1
        if not 0 < size <= 2048:
            return self.send(413, {"error": "invalid_size"})
        if self.path == "/api/start":
            # Public control is intentionally limited to one read-only, bounded
            # fixed-target audit, never code execution or external mutations.
            if size > 128:
                return self.send(413, {"error": "invalid_size"})
            origin = self.headers.get("Origin")
            if self.app.public_origin and origin != self.app.public_origin:
                return self.send(403, {"error": "origin_rejected"})
            if self.headers.get("Sec-Fetch-Site", "same-origin") != "same-origin":
                return self.send(403, {"error": "cross_site_rejected"})
            if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
                return self.send(415, {"error": "json_only"})
            try:
                value = json.loads(self.rfile.read(size))
                if value != {"action": "resume_audit"}:
                    return self.send(422, {"error": "invalid_action"})
            except (UnicodeError, ValueError, TypeError):
                return self.send(422, {"error": "invalid_action"})
            code, report = self.app.audit.start()
            return self.send(code, report)
        if self.path != "/api/events":
            return self.send(404, {"error": "not_found"})
        token = self.app.ingest_token
        if not token:
            return self.send(503, {"error": "ingestion_not_configured"})
        if not hmac.compare_digest(self.headers.get("Authorization", ""), "Bearer " + token):
            return self.send(401, {"error": "unauthorized"})
        origin = self.headers.get("Origin")
        if origin and (not self.app.public_origin or origin != self.app.public_origin):
            return self.send(403, {"error": "origin_rejected"})
        if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
            return self.send(415, {"error": "json_only"})
        try:
            event, is_new = self.app.journal.append(
                json.loads(self.rfile.read(size)), self.headers.get("Idempotency-Key", ""))
        except (ValueError, TypeError, sqlite3.Error, UnicodeError):
            return self.send(422, {"error": "invalid_event"})
        if is_new:
            self.app.publish("trace", event)
        return self.send(201 if is_new else 200, {"accepted": True, "new": is_new,
                                                 "seq": event["seq"], "mode": "DEMO_ONLY"})


class Server(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, addr, app):
        self.app = app
        super().__init__(addr, Handler)


def main():
    app = State()
    server = Server((app.host, int(os.getenv("PORT", "10000"))), app)
    print("MISSION_CONTROL_START mode=DEMO_ONLY no_trading=True", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
