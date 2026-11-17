"""NEXUS QUANT safe agent observability event journal (non-trading).

No credential capture, command execution, agent activation, trading or remote writes.
Signed proof of independent review is deliberately outside this local hash chain.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys

SCHEMA = "fin.agent.event.v1"
AGENTS = frozenset(f"A{i}" for i in range(11))
EVENT_TYPES = frozenset({
    "TASK_STARTED", "AGENT_STARTED", "HEARTBEAT", "TOOL_STARTED", "TOOL_FINISHED",
    "FILE_CHANGED", "TEST_STARTED", "TEST_PASSED", "TEST_FAILED",
    "BUG_DETECTED", "BUG_FIX_STARTED", "BUG_FIXED", "HANDOFF", "VETO",
    "BLOCKED", "AGENT_FINISHED", "TASK_FINISHED", "ERROR",
})
TASK_RE = re.compile(r"^FIN-P\d\d-W[A-Z]-\d{3}(?:-R\d\d)?$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,99}$")
HEX = re.compile(r"^[a-f0-9]{64}$")
# Sensitive fields must never be retained. This rejects suspicious values rather than
# silently keeping secret fragments in an "audit" artifact.
SENSITIVE = re.compile(r"(?i)(?:\b(?:token|password|passwd|secret|api[_ -]?key|authorization|bearer|private[_ -]?key)\b\s*[:=]|gh[pousr]_[A-Za-z0-9]{12,}|sk-[A-Za-z0-9_-]{16,}|-----BEGIN .*PRIVATE KEY-----)")


class TraceError(ValueError):
    """Malformed or unsafe trace information."""


def canonical(record: dict) -> bytes:
    return json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _validate_text(value: str, label: str, max_length: int) -> str:
    if not isinstance(value, str) or not value or len(value) > max_length or any(ord(c) < 32 for c in value):
        raise TraceError(f"Invalid {label}")
    if SENSITIVE.search(value):
        raise TraceError(f"Sensitive data prohibited in {label}")
    return value


def _validate_target(value: str) -> str:
    if not value:
        return "-"
    _validate_text(value, "target", 240)
    p = value.replace("\\", "/")
    if p.startswith("/") or "://" in p or ":" in p or any(x in ("..", "") for x in p.split("/")):
        raise TraceError("Unsafe target path")
    forbidden = (".env", "secrets/", "credentials/", "private/", ".ssh/", ".git/")
    if any(x in p.lower() for x in forbidden):
        raise TraceError("Sensitive target path prohibited")
    return p


def _event_data(agent_id: str, task_id: str, run_id: str, event_type: str,
                message: str, target: str, at: str) -> dict:
    if agent_id not in AGENTS:
        raise TraceError("Unknown agent")
    if not TASK_RE.fullmatch(task_id):
        raise TraceError("Unknown task ID format")
    if not ID_RE.fullmatch(run_id):
        raise TraceError("Invalid run ID")
    if event_type not in EVENT_TYPES:
        raise TraceError("Unknown event type")
    _validate_text(message, "message", 180)
    target = _validate_target(target)
    try:
        t = datetime.fromisoformat(at.replace("Z", "+00:00"))
        if t.tzinfo is None or t.utcoffset() != timezone.utc.utcoffset(t):
            raise ValueError("Expected UTC")
    except (ValueError, TypeError) as exc:
        raise TraceError("Invalid UTC timestamp") from exc
    return {"schema_version": SCHEMA, "agent_id": agent_id, "task_id": task_id,
            "run_id": run_id, "event_type": event_type, "message": message,
            "target": target, "at_utc": at, "financial_mode": "DEMO_ONLY"}


def verify(lines: list[str]) -> list[dict]:
    prev = "0" * 64
    events: list[dict] = []
    for line in lines:
        if not line.strip():
            raise TraceError("Unexpected blank line")
        if len(line) > 4096:
            raise TraceError("Oversized event")
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise TraceError("Invalid JSON") from exc
        if not isinstance(event, dict):
            raise TraceError("Event must be a dictionary")
        allowed = {"schema_version", "agent_id", "task_id", "run_id", "event_type", "message", "target", "at_utc", "financial_mode", "seq", "prev_hash", "event_hash"}
        if set(event) != allowed:
            raise TraceError("Event schema mismatch")
        _event_data(event["agent_id"], event["task_id"], event["run_id"],
                    event["event_type"], event["message"], event["target"], event["at_utc"])
        if event["schema_version"] != SCHEMA or event["financial_mode"] != "DEMO_ONLY":
            raise TraceError("Unsafe financial mode or event version")
        if type(event["seq"]) is not int or event["seq"] != len(events) + 1 or event["prev_hash"] != prev:
            raise TraceError("Sequence or hash chain invalid")
        digest = hashlib.sha256(canonical({k: v for k, v in event.items() if k != "event_hash"})).hexdigest()
        if event["event_hash"] != digest or not HEX.fullmatch(digest):
            raise TraceError("Tampered event")
        events.append(event)
        prev = digest
    return events


def load(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    if path.stat().st_size > 10_000_000:
        raise TraceError("Journal too large: rotate before further writes")
    return verify(path.read_text(encoding="utf-8").splitlines())


@contextmanager
def exclusive_lock(lockfile: Path):
    """Cross-process lock (Linux CI and Windows 10), independent of the data file."""
    lockfile.parent.mkdir(parents=True, exist_ok=True)
    with lockfile.open("a+b") as handle:
        if os.name == "nt":
            import msvcrt
            handle.seek(0)
            handle.write(b"0")
            handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)


def append(path: Path, *, agent_id: str, task_id: str, run_id: str,
           event_type: str, message: str, target: str = "-", at: str | None = None) -> dict:
    at = at or datetime.now(timezone.utc).isoformat()
    data = _event_data(agent_id, task_id, run_id, event_type, message, target, at)
    path.parent.mkdir(parents=True, exist_ok=True)
    with exclusive_lock(Path(str(path) + ".lock")):
        previous = load(path)
        data["seq"] = len(previous) + 1
        data["prev_hash"] = previous[-1]["event_hash"] if previous else "0" * 64
        data["event_hash"] = hashlib.sha256(canonical(data)).hexdigest()
        with path.open("a", encoding="utf-8", newline="\n") as out:
            out.write(canonical(data).decode("utf-8") + "\n")
            out.flush()
            os.fsync(out.fileno())
    return data


def export_json(path: Path) -> dict:
    events = load(path)
    return {"schema_version": SCHEMA, "source": "LOCAL_AGENT_EVENT_JOURNAL",
            "verified_local_chain": True, "authenticated_agent_identity": False,
            "financial_mode": "DEMO_ONLY", "last_hash": events[-1]["event_hash"] if events else None,
            "events": events}


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded non-trading agent event journal")
    sub = parser.add_subparsers(dest="command", required=True)
    emit = sub.add_parser("emit")
    emit.add_argument("--journal", type=Path, required=True)
    emit.add_argument("--agent", choices=sorted(AGENTS), required=True)
    emit.add_argument("--task", required=True)
    emit.add_argument("--run", required=True)
    emit.add_argument("--type", choices=sorted(EVENT_TYPES), required=True)
    emit.add_argument("--message", required=True)
    emit.add_argument("--target", default="-")
    view = sub.add_parser("export")
    view.add_argument("--journal", type=Path, required=True)
    view.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "emit":
            event = append(args.journal, agent_id=args.agent, task_id=args.task,
                           run_id=args.run, event_type=args.type,
                           message=args.message, target=args.target)
            print(f"TRACE_EMITTED seq={event['seq']} hash={event['event_hash'][:12]} mode=DEMO_ONLY")
        else:
            report = export_json(args.journal)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"TRACE_EXPORT=PASS events={len(report['events'])} mode=DEMO_ONLY")
        return 0
    except (TraceError, OSError, UnicodeError) as exc:
        # Avoid printing rejected content.
        print(f"TRACE_BLOCKED={type(exc).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
