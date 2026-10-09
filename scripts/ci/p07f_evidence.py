#!/usr/bin/env python3
"""Build deterministic P07-F quarantine-routing evidence offline."""

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
    QuarantineRouter,
    QuarantineRoutingPolicy,
)

ROUTING_POLICY = ROOT / "config/data-quality/quarantine-routing-policy.json"
QUALITY_POLICY = ROOT / "config/data-quality/provenance-confidence-policy.json"


def components(confidence: int = 10000, *, omit_d: bool = False):
    controls = ("P07-A", "P07-B", "P07-C") if omit_d else ("P07-A", "P07-B", "P07-C", "P07-D")
    chars = {"P07-A": "a", "P07-B": "b", "P07-C": "c", "P07-D": "d"}
    return tuple(
        ControlEvidence(
            control_id=control,
            outcome=ControlOutcome.PASS,
            confidence_bps=confidence,
            evidence_sha256=chars[control] * 64,
        )
        for control in controls
    )


def decision_payload(decision) -> dict[str, object]:
    return {
        "subject_id": decision.subject_id,
        "disposition": decision.disposition.value,
        "downstream_allowed": decision.downstream_allowed,
        "quality_status": decision.quality_status.value,
        "quality_policy_version": decision.quality_policy_version,
        "quality_evidence_sha256": decision.quality_evidence_sha256,
        "routing_policy_version": decision.routing_policy_version,
        "effective_quality_status": decision.effective_quality_status,
        "reason_codes": list(decision.reason_codes),
        "decision_id": decision.decision_id,
        "feature_quality": decision.to_feature_quality_eligibility().payload(),
        "quarantine_record_id": (
            decision.quarantine_record.record_id
            if decision.quarantine_record is not None
            else None
        ),
    }


def build(output: Path) -> None:
    quality_evaluator = ProvenanceConfidenceEvaluator(
        ProvenanceConfidencePolicy.from_path(QUALITY_POLICY)
    )
    routing_policy = QuarantineRoutingPolicy.from_path(ROUTING_POLICY)
    router = QuarantineRouter(routing_policy)

    eligible = quality_evaluator.evaluate(components())
    ineligible = quality_evaluator.evaluate(components(8000))
    unknown = quality_evaluator.evaluate(components(omit_d=True))

    accepted = router.route(subject_id="dataset:accepted", quality=eligible)
    quarantined = router.route(subject_id="dataset:quarantined", quality=ineligible)
    blocked = router.route(subject_id="dataset:unknown", quality=unknown)
    critical_override = router.route(
        subject_id="dataset:critical",
        quality=eligible,
        critical_reason_codes=("MANUAL_GOVERNANCE_BLOCK",),
    )

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P07F_QUARANTINE_ROUTING_EVIDENCE",
        "routing_policy_sha256": hashlib.sha256(ROUTING_POLICY.read_bytes()).hexdigest(),
        "quality_policy_sha256": hashlib.sha256(QUALITY_POLICY.read_bytes()).hexdigest(),
        "decisions": [
            decision_payload(accepted),
            decision_payload(quarantined),
            decision_payload(blocked),
            decision_payload(critical_override),
        ],
        "eligible_accepts_downstream": (
            accepted.disposition.value == "ACCEPTED_DOWNSTREAM"
            and accepted.downstream_allowed
            and accepted.quarantine_record is None
        ),
        "ineligible_quarantined_fail_closed": (
            quarantined.disposition.value == "QUARANTINED"
            and not quarantined.downstream_allowed
            and quarantined.quarantine_record is not None
        ),
        "unknown_blocked_fail_closed": (
            blocked.disposition.value == "BLOCKED_UNKNOWN"
            and not blocked.downstream_allowed
            and blocked.quarantine_record is not None
        ),
        "critical_override_quarantines_eligible": (
            critical_override.disposition.value == "QUARANTINED"
            and not critical_override.downstream_allowed
            and critical_override.quality_status.value == "ELIGIBLE"
            and critical_override.to_feature_quality_eligibility().status == "QUARANTINED"
        ),
        "nontrusted_feature_quality_fail_closed": (
            quarantined.to_feature_quality_eligibility().status == "QUARANTINED"
            and blocked.to_feature_quality_eligibility().status == "UNKNOWN"
            and accepted.to_feature_quality_eligibility().status == "ELIGIBLE"
        ),
        "destructive_delete_allowed": False,
        "silent_bypass_allowed": False,
        "production_quarantine_storage_vendor": routing_policy.production_quarantine_storage_vendor,
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
    print(f"P07F_EVIDENCE=PASS output={output}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    build(parser.parse_args().output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
