from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Mapping, cast

from packages.position_management import (
    CanonicalPositionEngine,
    CanonicalPositionPolicy,
    DynamicExitPlanner,
    DynamicExitPolicy,
    DynamicExitRequest,
    PositionFillEvent,
    PositionSpec,
    TpSlPlanner,
    TpSlPolicy,
    TpSlRequest,
)

ROOT = Path(__file__).resolve().parents[2]
POSITION_POLICY = ROOT / "config/position-management/canonical-position-state-policy.json"
TPSL_POLICY = ROOT / "config/position-management/tp-sl-policy.json"
DYNAMIC_POLICY = ROOT / "config/position-management/dynamic-exit-policy.json"
P21A_MANIFEST = ROOT / "docs/16-position-management/p21-a-canonical-position-state.json"
P21B_MANIFEST = ROOT / "docs/16-position-management/p21-b-tp-sl.json"
P21C_MANIFEST = ROOT / "docs/16-position-management/p21-c-partial-close.json"


def h(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def load(path: Path) -> Mapping[str, object]:
    value: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise RuntimeError(f"object required: {path}")
    return cast(Mapping[str, object], value)


def require_canonical(path: Path, label: str) -> Mapping[str, object]:
    manifest = load(path)
    if manifest.get("state") != "CANONICAL_COMPLETE":
        raise RuntimeError(f"{label} is not canonical complete")
    closure = manifest.get("closure")
    if not isinstance(closure, Mapping) or closure.get("lock") != "RELEASED":
        raise RuntimeError(f"{label} lock is not released")
    return manifest


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


def build_protection(record):
    planner = TpSlPlanner(TpSlPolicy.from_path(TPSL_POLICY))
    tp, sl = (12_000, 9_000) if record.side == "LONG" else (8_000, 11_000)
    return planner.plan(record, TpSlRequest(
        position_record_id=record.record_id,
        position_id=record.position_id,
        side=record.side,
        entry_price_scaled=record.average_entry_price_scaled_floor,
        take_profit_price_scaled=tp,
        stop_loss_price_scaled=sl,
        signal_decision_id=h("signal:" + record.position_id),
        risk_validation_id=h("risk-plan:" + record.position_id),
        source_ref="reference://p21d/protection/" + record.position_id,
    ))


def request(record, mode: str, reference: int, stop: int) -> DynamicExitRequest:
    return DynamicExitRequest(
        position_record_id=record.record_id,
        position_id=record.position_id,
        mode=mode,
        reference_price_scaled=reference,
        requested_stop_price_scaled=stop,
        exit_decision_id=h("exit:" + record.position_id + ":" + mode + ":" + str(reference) + ":" + str(stop)),
        source_ref="reference://p21d/" + record.position_id,
    )


def build() -> dict[str, object]:
    p21a = require_canonical(P21A_MANIFEST, "P21-A")
    p21b = require_canonical(P21B_MANIFEST, "P21-B")
    p21c = require_canonical(P21C_MANIFEST, "P21-C")

    planner = DynamicExitPlanner(DynamicExitPolicy.from_path(DYNAMIC_POLICY))
    long_position = build_position("p21d-btc-long", "CRYPTO", "LONG", "BTC-USDT")
    short_position = build_position("p21d-eurusd-short", "FOREX", "SHORT", "EUR-USD")
    long_plan = planner.plan(
        long_position,
        build_protection(long_position),
        request(long_position, "BREAK_EVEN", 10_500, 10_000),
    )
    short_plan = planner.plan(
        short_position,
        build_protection(short_position),
        request(short_position, "TRAILING", 8_800, 9_300),
    )
    plans = [
        {**long_plan.payload(), "plan_id": long_plan.plan_id},
        {**short_plan.payload(), "plan_id": short_plan.plan_id},
    ]

    return {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P21D_DYNAMIC_EXIT_EVIDENCE",
        "task_id": "FIN-P21-WD-001",
        "state": "IN_PROGRESS_REFERENCE_VALIDATED",
        "upstream": {
            "p21a_state": p21a.get("state"),
            "p21b_state": p21b.get("state"),
            "p21c_state": p21c.get("state"),
        },
        "policy_sha256": hashlib.sha256(DYNAMIC_POLICY.read_bytes()).hexdigest(),
        "plans": plans,
        "authority": {
            "reference_price_source": "CALLER_SUPPLIED_NO_VENUE_QUERY",
            "stop_source": "CALLER_SUPPLIED_NO_UNIVERSAL_TRAIL_DISTANCE",
            "stop_ratchet": "MONOTONIC_TIGHTEN_ONLY",
            "take_profit_change": "P21B_TAKE_PROFIT_PRESERVED",
            "real_venue_query": False,
            "credential_mode": "NONE",
            "network_mode": "DISABLED",
            "external_order_submission": False,
            "external_order_mutation": False,
            "automatic_oms_mutation": False,
            "canonical_position_mutation": False,
            "live_execution_validated": False,
            "live_execution_authority": False,
            "p21e_started": False,
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
    print(f"P21D_EVIDENCE=PASS sha256={digest} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
