from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Mapping, cast

from packages.position_management import (
    CanonicalPositionEngine,
    CanonicalPositionPolicy,
    EmergencyExitPlanner,
    EmergencyExitPolicy,
    EmergencyExitRequest,
    PositionFillEvent,
    PositionSpec,
)

ROOT = Path(__file__).resolve().parents[2]
POSITION_POLICY = ROOT / "config/position-management/canonical-position-state-policy.json"
EMERGENCY_POLICY = ROOT / "config/position-management/emergency-exit-policy.json"
UPSTREAM = [
    ("P21-A", ROOT / "docs/16-position-management/p21-a-canonical-position-state.json"),
    ("P21-B", ROOT / "docs/16-position-management/p21-b-tp-sl.json"),
    ("P21-C", ROOT / "docs/16-position-management/p21-c-partial-close.json"),
    ("P21-D", ROOT / "docs/16-position-management/p21-d-dynamic-exits.json"),
]


def h(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def load(path: Path) -> Mapping[str, object]:
    value: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise RuntimeError(f"object required: {path}")
    return cast(Mapping[str, object], value)


def require_upstream() -> dict[str, str]:
    result: dict[str, str] = {}
    for label, path in UPSTREAM:
        manifest = load(path)
        if manifest.get("state") != "CANONICAL_COMPLETE":
            raise RuntimeError(f"{label} is not canonical complete")
        closure = manifest.get("closure")
        if not isinstance(closure, Mapping) or closure.get("lock") != "RELEASED":
            raise RuntimeError(f"{label} lock is not released")
        result[label.lower().replace("-", "_") + "_state"] = "CANONICAL_COMPLETE"
    return result


def build_position(position_id: str, market: str, side: str, asset_id: str):
    engine = CanonicalPositionEngine(CanonicalPositionPolicy.from_path(POSITION_POLICY))
    engine.register(PositionSpec(
        position_id=position_id,
        portfolio_id="reference-portfolio",
        strategy_id="reference-strategy",
        asset_id=asset_id,
        market=market,
        side=side,
        quantity_scale=100_000,
        price_scale=100,
        risk_validation_id=h("risk:" + position_id),
        pretrade_firewall_id=h("fw:" + position_id),
    ))
    engine.apply(PositionFillEvent(
        position_id=position_id,
        sequence=1,
        occurred_at_ns=1_000_000_000,
        event_type="OPEN_FILL",
        quantity_scaled=100_000,
        price_scaled=10_000,
        order_id="order-" + position_id,
        client_order_id="client-" + position_id,
        oms_record_id=h("oms:" + position_id),
        reconciliation_report_id=h("recon:" + position_id),
    ))
    return engine.current(position_id)


def request(record, action: str, qty: int, trigger: str, authority: str, reconciliation: str) -> EmergencyExitRequest:
    return EmergencyExitRequest(
        position_record_id=record.record_id,
        position_id=record.position_id,
        action=action,
        requested_quantity_scaled=qty,
        trigger_code=trigger,
        authority_code=authority,
        reconciliation_status=reconciliation,
        emergency_decision_id=h("emergency:" + record.position_id + ":" + action + ":" + trigger),
        authority_decision_id=h("authority:" + record.position_id + ":" + authority),
        source_ref="reference://p21e/" + record.position_id,
    )


def build() -> dict[str, object]:
    upstream = require_upstream()
    planner = EmergencyExitPlanner(EmergencyExitPolicy.from_path(EMERGENCY_POLICY))
    long_position = build_position("p21e-btc-long", "CRYPTO", "LONG", "BTC-USDT")
    short_position = build_position("p21e-eurusd-short", "FOREX", "SHORT", "EUR-USD")

    reduce_plan = planner.plan(
        long_position,
        request(
            long_position,
            "EMERGENCY_REDUCE",
            30_000,
            "RISK_HALT",
            "A5_GOVERNED_REDUCE_ONLY",
            "NOT_REQUIRED",
        ),
    )
    flatten_plan = planner.plan(
        short_position,
        request(
            short_position,
            "EMERGENCY_FLATTEN",
            100_000,
            "SECURITY_INCIDENT",
            "OWNER_EXPLICIT_EMERGENCY_FLATTEN",
            "RESOLVED_NO_CONFLICT",
        ),
    )
    plans = [
        {**reduce_plan.payload(), "plan_id": reduce_plan.plan_id},
        {**flatten_plan.payload(), "plan_id": flatten_plan.plan_id},
    ]
    return {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P21E_EMERGENCY_EXIT_EVIDENCE",
        "task_id": "FIN-P21-WE-001",
        "state": "IN_PROGRESS_REFERENCE_VALIDATED",
        "upstream": upstream,
        "policy_sha256": hashlib.sha256(EMERGENCY_POLICY.read_bytes()).hexdigest(),
        "plans": plans,
        "authority": {
            "p16_trigger_auto_close_authority": False,
            "flatten_authority": "OWNER_EXPLICIT_EMERGENCY_FLATTEN",
            "reduce_only": True,
            "requires_p20_idempotent_execution": True,
            "requires_reconciliation_before_retry": True,
            "blind_reroute_allowed": False,
            "risk_firewall_bypass_authority": False,
            "real_venue_query": False,
            "credential_mode": "NONE",
            "network_mode": "DISABLED",
            "external_order_submission": False,
            "external_order_mutation": False,
            "automatic_oms_mutation": False,
            "canonical_position_mutation": False,
            "live_execution_validated": False,
            "live_execution_authority": False,
            "p21f_started": False,
            "p22_started": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    print(f"P21E_EVIDENCE=PASS sha256={digest} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
