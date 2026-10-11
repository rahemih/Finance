#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.fundamental_intelligence.p10_validation import P10ValidationEvaluator, P10ValidationPolicy

POLICY_PATH = ROOT / "config/fundamental-intelligence/p10-validation-policy.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    policy = P10ValidationPolicy.from_path(POLICY_PATH)
    documents = {x.document: (ROOT / x.document).read_bytes() for x in policy.required_workstreams}
    report = P10ValidationEvaluator(policy).evaluate(documents)
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P10H_VALIDATION_EVIDENCE",
        "task_id": "FIN-P10-WH-001",
        "policy_sha256": hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest(),
        "outcome": report.outcome,
        "issues": [x.payload() for x in report.issues],
        "certified_task_ids": list(report.certified_task_ids),
        "document_sha256s": [{"document": p, "sha256": d} for p, d in report.document_sha256s],
        "validation_fingerprint": report.fingerprint,
        "performance_semantics": report.performance_semantics,
        "validation_scope": {
            "p10_a_through_g_contract_integrity": "CERTIFIED_IF_PASS",
            "profitability": "NOT_CERTIFIED",
            "trade_success_probability": "NOT_CERTIFIED",
            "production_provider_performance": "NOT_CERTIFIED",
            "production_execution": "NOT_CERTIFIED",
            "production_latency_slo": "NOT_CERTIFIED"
        },
        "safety": {
            "country_assumption": policy.required_country_assumption,
            "live_trading": policy.required_live_trading,
            "auto_trading": policy.required_auto_trading,
            "network_required": False,
            "credentials_required": False
        },
        "next_phase": report.next_phase,
        "next_phase_state": report.next_phase_state,
        "p10_canonical_write_deferred_until_p10h_post_merge_and_closure": True
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"P10H_VALIDATION={report.outcome} certified={len(report.certified_task_ids)} output={args.output}")
    return 0 if report.outcome == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
