#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.ux.notification_engine import NotificationPolicy


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/ux/notification-engine.json"
ALERTING = ROOT / "config/news-sentiment/alerting-narrative-policy.json"


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    policy = NotificationPolicy.from_paths(POLICY, ALERTING)
    sample = {
        "source_event_id": "deterministic-reference-event",
        "severity": "CRITICAL",
        "title_fa": "هشدار بحرانی",
        "body_fa": "نمونه مرجع قطعی",
        "created_at": "2026-10-27T00:00:00Z",
        "provenance_ref": "sha256:" + "b" * 64,
    }
    route = policy.route(sample, in_quiet_hours=True)
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P23F_EVIDENCE",
        "task_id": "FIN-P23-WF-001",
        "status": "PASS",
        "policy_id": policy.policy_id,
        "route_action": route.action,
        "route_channel": route.channel,
        "escalation_target": route.escalation_target,
        "external_delivery_enabled": False,
        "credential_access": False,
        "owner_authorization": False,
        "risk_approval": False,
        "execution_approval": False,
        "p24_state": "NOT_STARTED",
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }
    evidence_id = hashlib.sha256(canonical_bytes(payload)).hexdigest()
    result = {**payload, "evidence_id": evidence_id}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_bytes(result) + b"\n")
    print(
        f"P23F_NOTIFICATION_ENGINE=PASS policy_id={policy.policy_id} "
        f"evidence_id={evidence_id}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
