from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from quant.backtesting.capacity_testing import evaluate_liquidity_capacity
from quant.backtesting.execution_realism import (
    ExecutionRealismPolicy,
    HistoricalDepthLevel,
    HistoricalExecutionContext,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/quant/liquidity-capacity-test-policy.json"


def _context(sequence: int) -> HistoricalExecutionContext:
    return HistoricalExecutionContext(
        sequence=sequence,
        event_time_ns=1000 + sequence,
        available_at_ns=1000 + sequence,
        asset_id="BTC-USD",
        price_scale=1,
        bids=(HistoricalDepthLevel(99, "100"), HistoricalDepthLevel(98, "100")),
        asks=(HistoricalDepthLevel(101, "100"), HistoricalDepthLevel(102, "100")),
        source_evidence_sha256=f"{sequence + 1:064x}",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = evaluate_liquidity_capacity(
        robustness_certificate_id="a" * 64,
        execution_policy=ExecutionRealismPolicy(
            policy_version="p17f-ci-v1",
            taker_fee_bps=5,
            decision_latency_ns=0,
            max_displayed_depth_participation_bps=5000,
        ),
        side="BUY",
        baseline_quantity="50",
        contexts=(_context(0), _context(1)),
        scale_bps=(10_000, 20_000, 30_000),
    )
    payload = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P17F_LIQUIDITY_CAPACITY_EVIDENCE",
        "task_id": "FIN-P17-WF-001",
        "fixture_only": True,
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "certificate_id": result.certificate_id,
        "status": result.status,
        "asset_id": result.asset_id,
        "side": result.side,
        "max_full_fill_scale_bps": result.max_full_fill_scale_bps,
        "scale_summaries": [item.payload() for item in result.scale_summaries],
        "hidden_liquidity_inference": False,
        "market_impact_claim": False,
        "profitability_claim_authority": False,
        "g9_authority": False,
        "execution_authority": False,
        "order_routing_authority": False,
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"P17F_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
