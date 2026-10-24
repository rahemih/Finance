from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Mapping, cast

from packages.position_management import CanonicalPositionEngine, CanonicalPositionPolicy, PositionFillEvent, PositionSpec

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/position-management/canonical-position-state-policy.json"
P20 = ROOT / "docs/15-execution/p20-phase-closure.json"


def h(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def load(path: Path) -> Mapping[str, object]:
    value: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise RuntimeError(f"object required: {path}")
    return cast(Mapping[str, object], value)


def spec(position_id: str, market: str, side: str, asset_id: str) -> PositionSpec:
    return PositionSpec(
        position_id, "reference-portfolio", "reference-strategy", asset_id,
        market, side, 100_000, 100, h("risk:"+position_id), h("firewall:"+position_id)
    )


def event(position_id: str, seq: int, kind: str, qty: int, price: int) -> PositionFillEvent:
    token = f"{position_id}:{seq}:{kind}"
    return PositionFillEvent(
        position_id, seq, 1_000_000_000 + seq * 100_000_000, kind, qty, price,
        "order-"+token, "client-"+token, h("oms:"+token), h("recon:"+token),
        "reference://p21a/"+token,
    )


def build() -> dict[str, object]:
    upstream = load(P20)
    if upstream.get("state") != "CANONICAL_COMPLETE":
        raise RuntimeError("P20 not canonical complete")
    if upstream.get("roadmap_exit_gate") != "G11_EXECUTION_VALIDATED" or upstream.get("gate_state") != "PASS":
        raise RuntimeError("G11 upstream gate not PASS")
    if upstream.get("gate_claim_scope") != "REFERENCE_SIMULATION_EXECUTION_VALIDATION":
        raise RuntimeError("G11 scope mismatch")

    policy = CanonicalPositionPolicy.from_path(POLICY)
    engine = CanonicalPositionEngine(policy)
    engine.register(spec("btc-long", "CRYPTO", "LONG", "BTC-USDT"))
    engine.register(spec("eurusd-short", "FOREX", "SHORT", "EUR-USD"))

    engine.apply(event("btc-long", 1, "OPEN_FILL", 100_000, 10_000))
    engine.apply(event("btc-long", 2, "ADD_FILL", 50_000, 11_000))
    engine.apply(event("btc-long", 3, "REDUCE_FILL", 25_000, 12_000))
    engine.apply(event("eurusd-short", 1, "OPEN_FILL", 200_000, 108_500))
    engine.apply(event("eurusd-short", 2, "REDUCE_FILL", 200_000, 107_900))

    return {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P21A_CANONICAL_POSITION_EVIDENCE",
        "task_id": "FIN-P21-WA-001",
        "state": "IN_PROGRESS_REFERENCE_VALIDATED",
        "upstream": {
            "p20_state": upstream.get("state"),
            "gate": upstream.get("roadmap_exit_gate"),
            "gate_state": upstream.get("gate_state"),
            "gate_id": upstream.get("gate_id"),
            "gate_scope": upstream.get("gate_claim_scope"),
        },
        "policy_sha256": hashlib.sha256(POLICY.read_bytes()).hexdigest(),
        "snapshot": engine.snapshot(),
        "authority": {
            "real_venue_query": False,
            "credential_mode": "NONE",
            "network_mode": "DISABLED",
            "external_order_submission": False,
            "external_order_mutation": False,
            "automatic_oms_mutation": False,
            "live_execution_validated": False,
            "live_execution_authority": False,
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
    snapshot = payload["snapshot"]
    assert isinstance(snapshot, dict)
    print(f"P21A_EVIDENCE=PASS snapshot_id={snapshot['snapshot_id']} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
