#!/usr/bin/env python3
"""Build deterministic P07-E provenance/confidence evidence offline."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.data_quality import (
    ControlEvidence,
    ControlOutcome,
    ProvenanceConfidenceEvaluator,
    ProvenanceConfidencePolicy,
)

POLICY = ROOT / "config/data-quality/provenance-confidence-policy.json"


def component(control_id: str, confidence: int, char: str, outcome: ControlOutcome = ControlOutcome.PASS):
    return ControlEvidence(
        control_id=control_id,
        outcome=outcome,
        confidence_bps=confidence,
        evidence_sha256=char * 64,
    )


def result_payload(result) -> dict[str, object]:
    return {
        "policy_version": result.policy_version,
        "status": result.status.value,
        "aggregate_confidence_bps": result.aggregate_confidence_bps,
        "components": [item.payload() for item in result.components],
        "missing_controls": list(result.missing_controls),
        "evidence_identity": result.evidence_identity,
        "feature_quality": result.to_feature_quality_eligibility().payload(),
    }


def build(output: Path) -> None:
    policy = ProvenanceConfidencePolicy.from_path(POLICY)
    evaluator = ProvenanceConfidenceEvaluator(policy)

    eligible = evaluator.evaluate(
        (
            component("P07-A", 10000, "a"),
            component("P07-B", 10000, "b"),
            component("P07-C", 9500, "c"),
            component("P07-D", 9500, "d"),
        )
    )
    below_threshold = evaluator.evaluate(
        (
            component("P07-A", 8000, "a"),
            component("P07-B", 8000, "b"),
            component("P07-C", 8000, "c"),
            component("P07-D", 8000, "d"),
        )
    )
    explicit_fail = evaluator.evaluate(
        (
            component("P07-A", 10000, "a"),
            component("P07-B", 10000, "b"),
            component("P07-C", 10000, "c", ControlOutcome.FAIL),
            component("P07-D", 10000, "d"),
        )
    )
    incomplete = evaluator.evaluate(
        (
            component("P07-A", 10000, "a"),
            component("P07-B", 10000, "b"),
            component("P07-C", 10000, "c"),
        )
    )

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P07E_PROVENANCE_CONFIDENCE_EVIDENCE",
        "policy_sha256": hashlib.sha256(POLICY.read_bytes()).hexdigest(),
        "results": [
            result_payload(eligible),
            result_payload(below_threshold),
            result_payload(explicit_fail),
            result_payload(incomplete),
        ],
        "eligible_pass": eligible.status.value == "ELIGIBLE",
        "below_threshold_ineligible": below_threshold.status.value == "INELIGIBLE",
        "explicit_fail_ineligible": explicit_fail.status.value == "INELIGIBLE",
        "incomplete_unknown": incomplete.status.value == "UNKNOWN",
        "feature_adapter_preserves_identity": (
            eligible.to_feature_quality_eligibility().evidence_sha256
            == eligible.evidence_identity
        ),
        "adaptive_weights": False,
        "production_data_quality_vendor": policy.production_data_quality_vendor,
        "safety": {
            "network_required": False,
            "credentials_required": False,
            "country_assumption": "NONE",
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED"
        }
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"P07E_EVIDENCE=PASS output={output}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    build(parser.parse_args().output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
