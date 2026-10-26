from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Mapping, cast

from packages.operations.operations_validation import (
    OperationsValidationPolicy,
    certify_operations_validation,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/operations/operations-validation-g12-policy.json"
MANIFESTS = {
    "P22-A": ROOT / "docs/17-operations/p22-a-metrics-logs-traces.json",
    "P22-B": ROOT / "docs/17-operations/p22-b-system-state-machine.json",
    "P22-C": ROOT / "docs/17-operations/p22-c-auto-diagnostics.json",
    "P22-D": ROOT / "docs/17-operations/p22-d-constrained-self-healing.json",
    "P22-E": ROOT / "docs/17-operations/p22-e-backup.json",
    "P22-F": ROOT / "docs/17-operations/p22-f-restore-drills.json",
    "P22-G": ROOT / "docs/17-operations/p22-g-disaster-recovery.json",
    "P22-H": ROOT / "docs/17-operations/p22-h-incident-postmortem.json",
    "P22-I": ROOT / "docs/17-operations/p22-i-slo-capacity-cost-monitoring.json",
}


def _load(path: Path) -> Mapping[str, object]:
    value: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise RuntimeError(f"manifest root must be object: {path}")
    return cast(Mapping[str, object], value)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict[str, object]:
    policy = OperationsValidationPolicy.from_path(POLICY)
    manifests = {name: _load(path) for name, path in MANIFESTS.items()}
    hashes = {name: _sha256(path) for name, path in MANIFESTS.items()}
    certificate = certify_operations_validation(policy, manifests, hashes)
    return {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P22J_G12_OPERATIONS_VALIDATION_EVIDENCE",
        "task_id": "FIN-P22-WJ-001",
        "phase": "P22",
        "workstream": "P22-J",
        "state": "IN_PROGRESS_REFERENCE_OPERATIONS_VALIDATED",
        "policy_sha256": _sha256(POLICY),
        "certificate": {
            **certificate.payload(),
            "certificate_id": certificate.certificate_id,
        },
        "authority": {
            "gate_scope": "REFERENCE_OPERATIONS_VALIDATION",
            "all_p22_contract_tests_required": True,
            "production_readiness": False,
            "automatic_p23_activation": False,
            "network_mode": "DISABLED",
            "credential_mode": "NONE",
            "external_order_authority": False,
            "runtime_state_mutation": False,
            "live_execution_authority": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
            "p23_state": "NOT_STARTED_OWNER_PHASE_AUTHORIZATION_REQUIRED",
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
        "P22J_G12_OPERATIONS_VALIDATION=PASS "
        f"certificate_id={certificate['certificate_id']} output={args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
