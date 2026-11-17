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
import secrets
import sqlite3
import threading
import time
from urllib.request import Request, urlopen

import agent_trace as trace

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "apps" / "agent-mission-control"
API = "https://api.github.com/repos/rahemih/Finance"
RUN_PATH = re.compile(r"^/api/github/actions/runs/([0-9]{1,16})/jobs$")
PR_PATH = re.compile(r"^/api/github/pulls/([0-9]{1,12})/files$")
ASSETS = {"/": "index.html", "/index.html": "index.html", "/app.js": "app.js",
          "/trace-ui.js": "trace-ui.js", "/live.js": "live.js", "/styles.css": "styles.css"}
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
        self.view_password = os.getenv("NQ_VIEW_PASSWORD", "")
        self.session_secret = os.getenv("NQ_SESSION_SECRET", "")
        self.ingest_token = os.getenv("NQ_INGEST_TOKEN", "")
        self.public_origin = os.getenv("NQ_PUBLIC_ORIGIN", "")
        self.github_token = os.getenv("NQ_GITHUB_TOKEN", "")
        self.github_interval = max(60, int(os.getenv("NQ_GITHUB_POLL_SECONDS", "300")))
        self.github = {"status": "WAITING", "verified_at": None, "runs": [],
                       "prs": [], "issues": [], "error": "No successful GitHub fetch"}
        self.subscribers = set()
        self.attempts = {}
        host = os.getenv("NQ_HOST", "127.0.0.1")
        self.host = host
        if host not in ("127.0.0.1", "localhost", "::1"):
            if not (self.public_origin.startswith("https://") and
                    len(self.view_password) >= 20 and len(self.session_secret) >= 32):
                raise RuntimeError("Remote mode requires HTTPS public origin, viewer secret and HMAC secret")
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
                if len(runs) == 25 or len(prs) == 50 or len(issues) == 50:
                    raise ValueError("Pagination limit")
                fresh = {"status": "LIVE", "verified_at": now(), "runs": runs,
                         "prs": prs, "issues": [x for x in issues if "pull_request" not in x],
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

    def snapshot(self):
        with self.lock:
            gh = json.loads(json.dumps(self.github))
        return {"schema_version": "nq.mission.v3", "server_time": now(),
                "github": gh, "trace": self.journal.export(),
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

    def allowed(self):
        if not self.app.view_password and self.app.host in ("127.0.0.1", "::1", "localhost"):
            return True
        for pair in self.headers.get("Cookie", "").split(";"):
            if pair.strip().startswith("nq_view="):
                try:
                    expiry, signature = pair.strip().split("=", 1)[1].split(".", 1)
                    if not expiry.isdigit() or not (time.time() < int(expiry) < time.time() + 29000):
                        return False
                    expected = hmac.new(self.app.session_secret.encode(), expiry.encode(), hashlib.sha256).hexdigest()
                    return hmac.compare_digest(expected, signature)
                except (ValueError, IndexError):
                    return False
        return False

    def do_GET(self):
        path = self.path
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
        if not self.allowed():
            return self.send(401, {"error": "login_required"})
        if path == "/api/state":
            return self.send(200, self.app.snapshot())
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
            return self.send(200, {"files": data} if files else data)
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
        if self.path == "/api/login":
            ip = self.client_address[0]
            with self.app.lock:
                times = [t for t in self.app.attempts.get(ip, [])
                         if time.monotonic() - t < 300]
                if len(times) >= 5:
                    return self.send(429, {"error": "too_many_attempts"})
                self.app.attempts[ip] = times
            try:
                obj = json.loads(self.rfile.read(size))
                valid = (isinstance(obj, dict) and set(obj) == {"password"}
                         and isinstance(obj["password"], str)
                         and self.app.view_password
                         and hmac.compare_digest(obj["password"], self.app.view_password))
            except (ValueError, TypeError, UnicodeError):
                valid = False
            if not valid:
                with self.app.lock: self.app.attempts[ip].append(time.monotonic())
                return self.send(401, {"error": "incorrect_password"})
            expiry = str(int(time.time() + 28800))
            signature = hmac.new(self.app.session_secret.encode(), expiry.encode(), hashlib.sha256).hexdigest()
            body = b'{"authenticated":true}'
            self.send_response(200)
            self._out_headers("application/json; charset=utf-8", len(body))
            self.send_header("Set-Cookie", f"nq_view={expiry}.{signature}; HttpOnly; SameSite=Strict; Secure; Path=/")
            self.end_headers()
            self.wfile.write(body)
            return
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
