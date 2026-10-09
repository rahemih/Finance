#!/usr/bin/env python3
"""Build deterministic P07-G quality dashboard/SLO evidence offline."""

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
    QualityRouteObservation,
    QualitySloEvaluator,
    QualitySloPolicy,
    RouteDisposition,
)

POLICY = ROOT / "config/data-quality/quality-slo-policy.json"


def obs(index: int, disposition: RouteDisposition) -> QualityRouteObservation:
    seed = hashlib.sha256(f"decision-{index}-{disposition.value}".encode("utf-8")).hexdigest()
    return QualityRouteObservation(
        subject_id=f"subject-{index:03d}",
        disposition=disposition,
        decision_evidence_sha256=seed,
    )


def snapshot_payload(snapshot) -> dict[str, object]:
    return {
        "policy_version": snapshot.policy_version,
        "total_count": snapshot.total_count,
        "accepted_count": snapshot.accepted_count,
        "quarantined_count": snapshot.quarantined_count,
        "blocked_unknown_count": snapshot.blocked_unknown_count,
        "trusted_route_bps": snapshot.trusted_route_bps,
        "quarantine_rate_bps": snapshot.quarantine_rate_bps,
        "unknown_block_rate_bps": snapshot.unknown_block_rate_bps,
        "evaluations": [item.payload() for item in snapshot.evaluations],
        "highest_severity": snapshot.highest_severity.value,
        "blocking": snapshot.blocking,
        "decision_evidence_sha256s": list(snapshot.decision_evidence_sha256s),
        "fingerprint": snapshot.fingerprint,
    }


def build(output: Path) -> None:
    policy = QualitySloPolicy.from_path(POLICY)
    evaluator = QualitySloEvaluator(policy)

    healthy = evaluator.evaluate(
        tuple(obs(i, RouteDisposition.ACCEPTED_DOWNSTREAM) for i in range(20))
    )
    warning = evaluator.evaluate(
        tuple(
            [obs(i, RouteDisposition.ACCEPTED_DOWNSTREAM) for i in range(18)]
            + [obs(18, RouteDisposition.QUARANTINED), obs(19, RouteDisposition.QUARANTINED)]
        )
    )
    critical = evaluator.evaluate(
        tuple(
            [obs(i, RouteDisposition.ACCEPTED_DOWNSTREAM) for i in range(18)]
            + [
                obs(18, RouteDisposition.BLOCKED_UNKNOWN),
                obs(19, RouteDisposition.BLOCKED_UNKNOWN),
            ]
        )
    )
    no_data = evaluator.evaluate(())

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P07G_QUALITY_SLO_EVIDENCE",
        "policy_sha256": hashlib.sha256(POLICY.read_bytes()).hexdigest(),
        "snapshots": {
            "healthy": snapshot_payload(healthy),
            "warning": snapshot_payload(warning),
            "critical": snapshot_payload(critical),
            "no_data": snapshot_payload(no_data),
        },
        "healthy_non_blocking": not healthy.blocking,
        "warning_non_blocking": not warning.blocking,
        "critical_blocking": critical.blocking,
        "no_data_blocking": no_data.blocking,
        "production_observability_vendor": policy.production_observability_vendor,
        "safety": {
            "network_required": False,
            "credentials_required": False,
            "country_assumption": "NONE",
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"P07G_EVIDENCE=PASS output={output}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    build(parser.parse_args().output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
