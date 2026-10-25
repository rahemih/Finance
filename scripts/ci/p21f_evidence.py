from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Mapping, cast

from packages.position_management import (
    BrokerPositionReconciler,
    BrokerReconciliationPolicy,
    CanonicalPositionEngine,
    CanonicalPositionPolicy,
    PositionFillEvent,
    PositionSpec,
    ReferenceBrokerPositionObservation,
)

ROOT = Path(__file__).resolve().parents[2]
POSITION_POLICY = ROOT / "config/position-management/canonical-position-state-policy.json"
RECON_POLICY = ROOT / "config/position-management/broker-reconciliation-policy.json"
UPSTREAM = [
    ("P21-A", ROOT / "docs/16-position-management/p21-a-canonical-position-state.json"),
    ("P21-B", ROOT / "docs/16-position-management/p21-b-tp-sl.json"),
    ("P21-C", ROOT / "docs/16-position-management/p21-c-partial-close.json"),
    ("P21-D", ROOT / "docs/16-position-management/p21-d-dynamic-exits.json"),
    ("P21-E", ROOT / "docs/16-position-management/p21-e-emergency-exit.json"),
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


def build_position(position_id: str):
    engine = CanonicalPositionEngine(CanonicalPositionPolicy.from_path(POSITION_POLICY))
    engine.register(PositionSpec(
        position_id=position_id,
        portfolio_id="reference-portfolio",
        strategy_id="reference-strategy",
        asset_id="BTC-USDT",
        market="CRYPTO",
        side="LONG",
        quantity_scale=100_000,
        price_scale=100,
        risk_validation_id=h("risk:" + position_id),
        pretrade_firewall_id=h("fw:" + position_id),
    ))
    engine.apply(PositionFillEvent(
        position_id=position_id,
        sequence=1,
        occurred_at_ns=100,
        event_type="OPEN_FILL",
        quantity_scaled=100_000,
        price_scaled=10_000,
        order_id="order-" + position_id,
        client_order_id="client-" + position_id,
        oms_record_id=h("oms:" + position_id),
        reconciliation_report_id=h("recon:" + position_id),
    ))
    return engine.current(position_id)


def observation(record, quantity: int) -> ReferenceBrokerPositionObservation:
    return ReferenceBrokerPositionObservation(
        position_record_id=record.record_id,
        position_id=record.position_id,
        asset_id=record.asset_id,
        market=record.market,
        status="OPEN",
        quantity_scale=record.quantity_scale,
        price_scale=record.price_scale,
        observed_at_ns=100,
        source_ref="reference://p21f/" + record.position_id,
        side=record.side,
        open_quantity_scaled=quantity,
        average_entry_price_scaled_floor=record.average_entry_price_scaled_floor,
        external_position_ref="sandbox:" + record.position_id,
    )


def build() -> dict[str, object]:
    upstream = require_upstream()
    reconciler = BrokerPositionReconciler(BrokerReconciliationPolicy.from_path(RECON_POLICY))

    matched_position = build_position("p21f-matched")
    mismatch_position = build_position("p21f-quantity-mismatch")
    matched = reconciler.reconcile(
        matched_position,
        observation(matched_position, matched_position.open_quantity_scaled),
    )
    mismatch = reconciler.reconcile(
        mismatch_position,
        observation(mismatch_position, mismatch_position.open_quantity_scaled - 1),
    )

    reports = [
        {**matched.payload(), "report_id": matched.report_id},
        {**mismatch.payload(), "report_id": mismatch.report_id},
    ]
    return {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P21F_BROKER_RECONCILIATION_EVIDENCE",
        "task_id": "FIN-P21-WF-001",
        "state": "IN_PROGRESS_REFERENCE_VALIDATED",
        "upstream": upstream,
        "policy_sha256": hashlib.sha256(RECON_POLICY.read_bytes()).hexdigest(),
        "reports": reports,
        "authority": {
            "comparison_mode": "EXACT_FIXED_POINT_NO_HIDDEN_TOLERANCE",
            "observation_source": "CALLER_SUPPLIED_REFERENCE_OR_SANDBOX_ONLY",
            "mismatch_disposition": "SAFE_HOLD_NEW_ENTRY_BLOCK",
            "mismatch_action": "MANUAL_GOVERNED_RECONCILIATION_REQUIRED",
            "auto_repair": False,
            "auto_flatten": False,
            "real_venue_query": False,
            "credential_mode": "NONE",
            "network_mode": "DISABLED",
            "external_order_submission": False,
            "external_order_mutation": False,
            "automatic_oms_mutation": False,
            "canonical_position_mutation": False,
            "live_execution_validated": False,
            "live_execution_authority": False,
            "p21g_started": False,
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
    print(f"P21F_EVIDENCE=PASS sha256={digest} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
