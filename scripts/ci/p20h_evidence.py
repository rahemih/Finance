from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from packages.execution.execution_quality import (
    ExecutionQualityLedger,
    ExecutionQualityObservation,
    ExecutionQualityPolicy,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/execution/execution-quality-policy.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def obs(*, market: str, order_id: str, side: str, arrival: int, fill: int, ack_delta: int, fill_delta: int, terminal_delta: int) -> ExecutionQualityObservation:
    submit = 1_000_000_000
    return ExecutionQualityObservation(
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
        submit_time_ns=submit,
        ack_time_ns=submit + ack_delta,
        first_fill_time_ns=submit + fill_delta,
        terminal_time_ns=submit + terminal_delta,
        source_ref=f"reference://p20h/{market.lower()}/{order_id}",
    )


def build() -> dict[str, object]:
    policy = ExecutionQualityPolicy.from_path(POLICY)
    ledger = ExecutionQualityLedger(policy)
    ledger.add(obs(market="CRYPTO", order_id="btc-001", side="BUY", arrival=100_000, fill=100_050, ack_delta=80_000_000, fill_delta=180_000_000, terminal_delta=250_000_000))
    ledger.add(obs(market="FOREX", order_id="eurusd-001", side="SELL", arrival=108_500, fill=108_450, ack_delta=120_000_000, fill_delta=220_000_000, terminal_delta=320_000_000))
    summary = ledger.summary()
    return {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P20H_EXECUTION_QUALITY_EVIDENCE",
        "task_id": "FIN-P20-WH-001",
        "state": "IN_PROGRESS_REFERENCE_VALIDATED",
        "policy_sha256": _sha256(POLICY),
        "policy_id": policy.policy_id,
        "summary": summary,
        "authority": {
            "reference_only": True,
            "real_venue_query": False,
            "production_execution_certification": False,
            "broker_certification": False,
            "credential_mode": "NONE",
            "network_mode": "DISABLED",
            "external_order_submission": False,
            "external_order_mutation": False,
            "live_execution_authority": False,
            "g11_execution_validated": False,
            "p20_i_started": False,
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
    print(f"P20H_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
