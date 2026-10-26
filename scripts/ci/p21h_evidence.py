from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Mapping, cast

from packages.position_management import (
    PositionLifecycleValidationPolicy,
    certify_position_lifecycle,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/position-management/lifecycle-validation-policy.json"
MANIFESTS = {
    "P21-A": ROOT / "docs/16-position-management/p21-a-canonical-position-state.json",
    "P21-B": ROOT / "docs/16-position-management/p21-b-tp-sl.json",
    "P21-C": ROOT / "docs/16-position-management/p21-c-partial-close.json",
    "P21-D": ROOT / "docs/16-position-management/p21-d-dynamic-exits.json",
    "P21-E": ROOT / "docs/16-position-management/p21-e-emergency-exit.json",
    "P21-F": ROOT / "docs/16-position-management/p21-f-broker-reconciliation.json",
    "P21-G": ROOT / "docs/16-position-management/p21-g-restart-recovery.json",
}


def load(path: Path) -> Mapping[str, object]:
    value: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise RuntimeError(f"object required: {path}")
    return cast(Mapping[str, object], value)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict[str, object]:
    policy = PositionLifecycleValidationPolicy.from_path(POLICY)
    manifests = {workstream: load(path) for workstream, path in MANIFESTS.items()}
    hashes = {workstream: sha256(path) for workstream, path in MANIFESTS.items()}
    certificate = certify_position_lifecycle(policy, manifests, hashes)
    return {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P21H_POSITION_LIFECYCLE_VALIDATION_EVIDENCE",
        "task_id": "FIN-P21-WH-001",
        "phase": "P21",
        "workstream": "P21-H",
        "state": "IN_PROGRESS_REFERENCE_VALIDATED",
        "policy_sha256": sha256(POLICY),
        "certificate": {**certificate.payload(), "certificate_id": certificate.certificate_id},
        "authority": {
            "claim_scope": "REFERENCE_POSITION_LIFECYCLE_VALIDATION",
            "all_p21_contract_tests_required": True,
            "real_venue_query": False,
            "credential_mode": "NONE",
            "network_mode": "DISABLED",
            "external_order_submission": False,
            "external_order_mutation": False,
            "automatic_oms_mutation": False,
            "automatic_position_mutation": False,
            "live_execution_validated": False,
            "live_execution_authority": False,
            "production_readiness": False,
            "automatic_p22_activation": False,
            "p22_state": "NOT_STARTED_OWNER_PHASE_AUTHORIZATION_REQUIRED",
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
    certificate = payload["certificate"]
    assert isinstance(certificate, dict)
    print(
        "P21H_LIFECYCLE_VALIDATION=PASS "
        f"certificate_id={certificate['certificate_id']} output={args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
