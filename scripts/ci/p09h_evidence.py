#!/usr/bin/env python3
"""Build deterministic P09-H integrated validation evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.order_flow_liquidity.p09_validation import (
    P09ValidationEvaluator,
    P09ValidationPolicy,
)

POLICY_PATH = ROOT / "config/order-flow-liquidity/p09-validation-policy.json"


def build(output: Path) -> bool:
    policy = P09ValidationPolicy.from_path(POLICY_PATH)
    documents = {
        item.document: (ROOT / item.document).read_bytes()
        for item in policy.required_workstreams
    }
    report = P09ValidationEvaluator(policy).evaluate(documents)

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P09H_VALIDATION_EVIDENCE",
        "task_id": "FIN-P09-WH-001",
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "outcome": report.outcome,
        "issues": [issue.payload() for issue in report.issues],
        "certified_task_ids": list(report.certified_task_ids),
        "document_sha256s": [
            {"document": document, "sha256": digest}
            for document, digest in report.document_sha256s
        ],
        "validation_fingerprint": report.fingerprint,
        "performance_semantics": report.performance_semantics,
        "validation_scope": {
            "p09_a_through_g_contract_integrity": "CERTIFIED_IF_PASS",
            "profitability": "NOT_CERTIFIED",
            "trade_success_probability": "NOT_CERTIFIED",
            "signal_quality": "NOT_CERTIFIED",
            "production_provider_performance": "NOT_CERTIFIED",
            "production_execution": "NOT_CERTIFIED",
            "production_slippage_or_market_impact": "NOT_CERTIFIED"
        },
        "safety": {
            "country_assumption": report.country_assumption,
            "live_trading": report.live_trading,
            "auto_trading": report.auto_trading,
            "network_required": False,
            "credentials_required": False
        },
        "next_phase": report.next_phase,
        "next_phase_state": report.next_phase_state,
        "p09_canonical_write_deferred_until_p09h_post_merge_and_closure": True
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"P09H_VALIDATION={report.outcome} "
        f"certified={len(report.certified_task_ids)} output={output}"
    )
    return report.outcome == "PASS"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    return 0 if build(parser.parse_args().output) else 1


if __name__ == "__main__":
    raise SystemExit(main())
