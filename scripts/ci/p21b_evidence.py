from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Mapping, cast

from packages.position_management import (
    CanonicalPositionEngine,
    CanonicalPositionPolicy,
    PositionFillEvent,
    PositionSpec,
    TpSlPlanner,
    TpSlPolicy,
    TpSlRequest,
)

ROOT = Path(__file__).resolve().parents[2]
POSITION_POLICY = ROOT / "config/position-management/canonical-position-state-policy.json"
TPSL_POLICY = ROOT / "config/position-management/tp-sl-policy.json"
P21A_MANIFEST = ROOT / "docs/16-position-management/p21-a-canonical-position-state.json"


def h(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def load(path: Path) -> Mapping[str, object]:
    value: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise RuntimeError(f"object required: {path}")
    return cast(Mapping[str, object], value)


def build_position(position_id: str, market: str, side: str, asset_id: str):
    p_policy = CanonicalPositionPolicy.from_path(POSITION_POLICY)
    engine = CanonicalPositionEngine(p_policy)
    engine.register(PositionSpec(
        position_id=position_id,
        portfolio_id="reference-portfolio",
        strategy_id="reference-strategy",
        asset_id=asset_id,
        market=market,
        side=side,
        quantity_scale=100_000,
        price_scale=100,
        risk_validation_id=h("risk:"+position_id),
        pretrade_firewall_id=h("fw:"+position_id),
    ))
    engine.apply(PositionFillEvent(
        position_id=position_id,
        sequence=1,
        occurred_at_ns=1_000_000_000,
        event_type="OPEN_FILL",
        quantity_scaled=100_000,
        price_scaled=10_000,
        order_id="order-"+position_id,
        client_order_id="client-"+position_id,
        oms_record_id=h("oms:"+position_id),
        reconciliation_report_id=h("recon:"+position_id),
    ))
    return engine.current(position_id)


def request(record, tp: int, sl: int) -> TpSlRequest:
    return TpSlRequest(
        position_record_id=record.record_id,
        position_id=record.position_id,
        side=record.side,
        entry_price_scaled=record.average_entry_price_scaled_floor,
        take_profit_price_scaled=tp,
        stop_loss_price_scaled=sl,
        signal_decision_id=h("signal:"+record.position_id),
        risk_validation_id=h("risk-plan:"+record.position_id),
        source_ref="reference://p21b/"+record.position_id,
    )


def build() -> dict[str, object]:
    p21a = load(P21A_MANIFEST)
    if p21a.get("state") != "CANONICAL_COMPLETE":
        raise RuntimeError("P21-A is not canonical complete")
    closure = p21a.get("closure")
    if not isinstance(closure, Mapping) or closure.get("lock") != "RELEASED":
        raise RuntimeError("P21-A lock is not released")

    policy = TpSlPolicy.from_path(TPSL_POLICY)
    planner = TpSlPlanner(policy)

    long_position = build_position("p21b-btc-long", "CRYPTO", "LONG", "BTC-USDT")
    short_position = build_position("p21b-eurusd-short", "FOREX", "SHORT", "EUR-USD")

    long_plan = planner.plan(long_position, request(long_position, 11_000, 9_000))
    short_plan = planner.plan(short_position, request(short_position, 9_000, 11_000))

    plans = [
        {**long_plan.payload(), "plan_id": long_plan.plan_id},
        {**short_plan.payload(), "plan_id": short_plan.plan_id},
    ]

    return {
        "schema_version":"1.0",
        "kind":"NEXUS_QUANT_P21B_TP_SL_EVIDENCE",
        "task_id":"FIN-P21-WB-001",
        "state":"IN_PROGRESS_REFERENCE_VALIDATED",
        "upstream":{
            "p21a_state":p21a.get("state"),
            "p21a_snapshot_id":closure.get("snapshot_id"),
            "p21a_evidence_sha256":closure.get("evidence_sha256"),
        },
        "policy_sha256":hashlib.sha256(TPSL_POLICY.read_bytes()).hexdigest(),
        "plans":plans,
        "authority":{
            "source_mode":"CALLER_SUPPLIED_LEVELS_VALIDATED_AGAINST_CANONICAL_POSITION",
            "real_venue_query":False,
            "credential_mode":"NONE",
            "network_mode":"DISABLED",
            "external_order_submission":False,
            "external_order_mutation":False,
            "automatic_oms_mutation":False,
            "live_execution_validated":False,
            "live_execution_authority":False,
            "p22_started":False,
            "live_trading":"DISABLED",
            "auto_trading":"DISABLED",
        },
    }


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    payload=build()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    digest=hashlib.sha256(args.output.read_bytes()).hexdigest()
    print(f"P21B_EVIDENCE=PASS sha256={digest} output={args.output}")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
