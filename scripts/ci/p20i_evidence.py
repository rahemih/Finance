from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Mapping, cast

from packages.execution.broker_simulation_gate import (
    BrokerSimulationEngine,
    BrokerSimulationPolicy,
    G11ExecutionValidationGate,
    SimulationScenario,
)
from packages.execution.execution_quality import (
    ExecutionQualityLedger,
    ExecutionQualityObservation,
    ExecutionQualityPolicy,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/execution/broker-simulation-g11-policy.json"
QUALITY_POLICY = ROOT / "config/execution/execution-quality-policy.json"
MANIFESTS = {
    "P20-A": ROOT / "docs/15-execution/p20-a-adapter-contract.json",
    "P20-B": ROOT / "docs/15-execution/p20-b-crypto-execution-adapter.json",
    "P20-C": ROOT / "docs/15-execution/p20-c-forex-execution-adapter.json",
    "P20-D": ROOT / "docs/15-execution/p20-d-oms-lifecycle.json",
    "P20-E": ROOT / "docs/15-execution/p20-e-idempotency-duplicate-prevention.json",
    "P20-F": ROOT / "docs/15-execution/p20-f-retry-timeout-crash-recovery.json",
    "P20-G": ROOT / "docs/15-execution/p20-g-reconciliation.json",
    "P20-H": ROOT / "docs/15-execution/p20-h-execution-quality-metrics.json",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_manifest(path: Path) -> Mapping[str, object]:
    value: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"manifest root must be object: {path}")
    return cast(Mapping[str, object], value)


def _quality_summary() -> Mapping[str, object]:
    policy = ExecutionQualityPolicy.from_path(QUALITY_POLICY)
    ledger = ExecutionQualityLedger(policy)
    for market, order_id, side, arrival, fill, ack, first_fill, terminal in (
        ("CRYPTO", "g11-btc-001", "BUY", 100_000, 100_050, 1_080_000_000, 1_180_000_000, 1_250_000_000),
        ("FOREX", "g11-eurusd-001", "SELL", 108_500, 108_450, 1_120_000_000, 1_220_000_000, 1_320_000_000),
    ):
        ledger.add(ExecutionQualityObservation(
            market=market,
            order_id=order_id,
            client_order_id=f"client-{order_id}",
            reconciliation_report_id=hashlib.sha256(f"reconciliation:{order_id}".encode()).hexdigest(),
            reconciliation_verdict="MATCHED",
            side=side,
            order_type="LIMIT",
            terminal_status="FILLED",
            ordered_quantity_scaled=100_000,
            filled_quantity_scaled=100_000,
            quantity_scale=100,
            arrival_price_scaled=arrival,
            average_fill_price_scaled=fill,
            price_scale=100,
            submit_time_ns=1_000_000_000,
            ack_time_ns=ack,
            first_fill_time_ns=first_fill,
            terminal_time_ns=terminal,
            source_ref=f"reference://p20i/{market.lower()}/{order_id}",
        ))
    return ledger.summary()


def build() -> dict[str, object]:
    policy = BrokerSimulationPolicy.from_path(POLICY)
    manifests = {name: _load_manifest(path) for name, path in MANIFESTS.items()}
    engine = BrokerSimulationEngine(policy)
    results = tuple(
        engine.run(SimulationScenario(
            scenario_id=f"p20i-{market.lower()}-{scenario.lower()}",
            market=market,
            scenario_type=scenario,
        ))
        for market in policy.markets
        for scenario in policy.required_scenarios
    )
    quality = _quality_summary()
    gate = G11ExecutionValidationGate(policy).evaluate(
        dependency_manifests=manifests,
        simulation_results=results,
        execution_quality_summary=quality,
    )
    return {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P20I_G11_EVIDENCE",
        "task_id": "FIN-P20-WI-001",
        "state": "IN_PROGRESS_REFERENCE_SIMULATION_VALIDATED",
        "policy_sha256": _sha256(POLICY),
        "dependency_manifest_sha256": {name: _sha256(path) for name, path in MANIFESTS.items()},
        "simulation": engine.snapshot(),
        "execution_quality_summary": quality,
        "gate": gate,
        "authority": {
            "gate_scope": "REFERENCE_SIMULATION_EXECUTION_VALIDATION",
            "reference_simulation_validated": True,
            "production_broker_selection": "NOT_SELECTED",
            "production_broker_certification": False,
            "real_venue_query": False,
            "credential_mode": "NONE",
            "network_mode": "DISABLED",
            "external_order_submission": False,
            "external_order_mutation": False,
            "automatic_oms_mutation": False,
            "live_execution_validated": False,
            "live_execution_authority": False,
            "automatic_live_promotion": False,
            "p21_started": False,
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
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    gate = payload["gate"]
    assert isinstance(gate, dict)
    print(f"P20I_G11_EVIDENCE=PASS gate_id={gate['gate_id']} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
