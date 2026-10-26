from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import unittest

from packages.operations.operations_validation import (
    OperationsValidationError,
    OperationsValidationPolicy,
    certify_operations_validation,
)


POLICY = Path("config/operations/operations-validation-g12-policy.json")
MANIFESTS = {
    "P22-A": Path("docs/17-operations/p22-a-metrics-logs-traces.json"),
    "P22-B": Path("docs/17-operations/p22-b-system-state-machine.json"),
    "P22-C": Path("docs/17-operations/p22-c-auto-diagnostics.json"),
    "P22-D": Path("docs/17-operations/p22-d-constrained-self-healing.json"),
    "P22-E": Path("docs/17-operations/p22-e-backup.json"),
    "P22-F": Path("docs/17-operations/p22-f-restore-drills.json"),
    "P22-G": Path("docs/17-operations/p22-g-disaster-recovery.json"),
    "P22-H": Path("docs/17-operations/p22-h-incident-postmortem.json"),
    "P22-I": Path("docs/17-operations/p22-i-slo-capacity-cost-monitoring.json"),
}


def load_manifest(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def hashes() -> dict[str, str]:
    return {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in MANIFESTS.items()}


class OperationsValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = OperationsValidationPolicy.from_path(POLICY)
        self.manifests = {name: load_manifest(path) for name, path in MANIFESTS.items()}
        self.hashes = hashes()

    def certify(self):
        return certify_operations_validation(self.policy, self.manifests, self.hashes)

    def test_canonical_p22_a_through_i_pass_g12_reference_validation(self) -> None:
        certificate = self.certify()
        self.assertEqual(certificate.gate_name, "G12_OPERATIONS_VALIDATED")
        self.assertEqual(certificate.result, "PASS")
        self.assertEqual(certificate.claim_scope, "REFERENCE_OPERATIONS_VALIDATION")
        self.assertEqual(tuple(name for name, _ in certificate.manifest_sha256), tuple(MANIFESTS))
        self.assertEqual(len(certificate.certificate_id), 64)

    def test_missing_manifest_fails_closed(self) -> None:
        self.manifests.pop("P22-I")
        self.hashes.pop("P22-I")
        with self.assertRaises(OperationsValidationError):
            self.certify()

    def test_manifest_order_mismatch_fails_closed(self) -> None:
        reversed_items = list(self.manifests.items())[::-1]
        self.manifests = dict(reversed_items)
        with self.assertRaises(OperationsValidationError):
            self.certify()

    def test_noncanonical_manifest_fails_closed(self) -> None:
        changed = copy.deepcopy(self.manifests["P22-C"])
        changed["state"] = "IN_PROGRESS"
        self.manifests["P22-C"] = changed
        with self.assertRaises(OperationsValidationError):
            self.certify()

    def test_unreleased_lock_fails_closed(self) -> None:
        changed = copy.deepcopy(self.manifests["P22-D"])
        closure = changed["closure"]
        assert isinstance(closure, dict)
        closure["lock"] = "ACQUIRED"
        self.manifests["P22-D"] = changed
        with self.assertRaises(OperationsValidationError):
            self.certify()

    def test_governance_failure_fails_closed(self) -> None:
        changed = copy.deepcopy(self.manifests["P22-H"])
        closure = changed["closure"]
        assert isinstance(closure, dict)
        post = closure["post_merge_governance"]
        assert isinstance(post, dict)
        post["status"] = "FAILURE"
        self.manifests["P22-H"] = changed
        with self.assertRaises(OperationsValidationError):
            self.certify()

    def test_live_authority_drift_fails_closed(self) -> None:
        changed = copy.deepcopy(self.manifests["P22-G"])
        safety = changed["safety"]
        assert isinstance(safety, dict)
        safety["live_execution_authority"] = True
        self.manifests["P22-G"] = changed
        with self.assertRaises(OperationsValidationError):
            self.certify()

    def test_network_or_credential_drift_fails_closed(self) -> None:
        changed = copy.deepcopy(self.manifests["P22-A"])
        safety = changed["safety"]
        assert isinstance(safety, dict)
        safety["network_mode"] = "ENABLED"
        self.manifests["P22-A"] = changed
        with self.assertRaises(OperationsValidationError):
            self.certify()

        self.manifests = {name: load_manifest(path) for name, path in MANIFESTS.items()}
        changed = copy.deepcopy(self.manifests["P22-I"])
        safety = changed["safety"]
        assert isinstance(safety, dict)
        safety["credential_mode"] = "PRESENT"
        self.manifests["P22-I"] = changed
        with self.assertRaises(OperationsValidationError):
            self.certify()

    def test_forbidden_runtime_authority_fails_closed(self) -> None:
        changed = copy.deepcopy(self.manifests["P22-D"])
        safety = changed["safety"]
        assert isinstance(safety, dict)
        safety["execution_authority"] = True
        self.manifests["P22-D"] = changed
        with self.assertRaises(OperationsValidationError):
            self.certify()

    def test_invalid_manifest_hash_fails_closed(self) -> None:
        self.hashes["P22-E"] = "bad"
        with self.assertRaises(OperationsValidationError):
            self.certify()

    def test_certificate_is_deterministic(self) -> None:
        first = self.certify()
        second = self.certify()
        self.assertEqual(first.certificate_id, second.certificate_id)
        self.assertEqual(first.payload(), second.payload())

    def test_gate_never_grants_p23_or_production_authority(self) -> None:
        certificate = self.certify()
        self.assertFalse(certificate.automatic_p23_activation)
        self.assertFalse(certificate.production_readiness)
        self.assertEqual(certificate.network_mode, "DISABLED")
        self.assertEqual(certificate.credential_mode, "NONE")
        self.assertFalse(certificate.external_order_authority)
        self.assertFalse(certificate.runtime_state_mutation)
        self.assertFalse(certificate.live_execution_authority)
        self.assertEqual(certificate.live_trading, "DISABLED")
        self.assertEqual(certificate.auto_trading, "DISABLED")


if __name__ == "__main__":
    unittest.main()
