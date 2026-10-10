#!/usr/bin/env python3
"""Build deterministic P08-I / G6 technical-validation evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.technical_intelligence.technical_validation_gate import (
    GateOutcome,
    TechnicalValidationGateEvaluator,
    TechnicalValidationGatePolicy,
)

POLICY = (
    ROOT
    / "config/technical-intelligence/technical-validation-gate-policy.json"
)


def build(output: Path) -> bool:
    policy = TechnicalValidationGatePolicy.from_path(POLICY)
    documents = {
        item.document: (ROOT / item.document).read_bytes()
        for item in policy.required_workstreams
    }
    report = TechnicalValidationGateEvaluator(policy).evaluate(documents)

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P08I_TECHNICAL_VALIDATION_GATE_EVIDENCE",
        "gate_id": report.gate_id,
        "policy_version": report.policy_version,
        "policy_sha256": hashlib.sha256(POLICY.read_bytes()).hexdigest(),
        "outcome": report.outcome.value,
        "issues": [issue.payload() for issue in report.issues],
        "certified_task_ids": list(report.certified_task_ids),
        "document_sha256s": [
            {"document": path, "sha256": digest}
            for path, digest in report.document_sha256s
        ],
        "gate_fingerprint": report.fingerprint,
        "technical_validation_scope": {
            "family_evidence_engineering_baseline": "CERTIFIED_IF_PASS",
            "point_in_time_and_trusted_data": "REQUIRED",
            "correlated_transform_double_counting": "CLUSTER_CAPPED",
            "numeric_dependence": "MEASURED_NOT_THRESHOLD_CLASSIFIED",
            "production_fusion_threshold_owner": "P14",
            "calibrated_trade_probability": "NOT_CERTIFIED_BY_G6",
            "profitability": "NOT_CERTIFIED_BY_G6",
            "risk_approval": "NOT_CERTIFIED_BY_G6",
            "strategy_backtest_robustness": "NOT_CERTIFIED_BY_G6",
            "execution": "NOT_AUTHORIZED_BY_G6"
        },
        "safety": {
            "live_trading": report.live_trading,
            "auto_trading": report.auto_trading,
            "country_assumption": report.country_assumption,
            "network_required": False,
            "credentials_required": False
        },
        "next_phase": report.next_phase,
        "next_phase_state": report.next_phase_state,
        "canonical_g6_write_deferred_until_p08i_post_merge": True
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"P08I_GATE={report.outcome.value} "
        f"certified={len(report.certified_task_ids)} output={output}"
    )
    return report.outcome is GateOutcome.PASS


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    return 0 if build(parser.parse_args().output) else 1


if __name__ == "__main__":
    raise SystemExit(main())
