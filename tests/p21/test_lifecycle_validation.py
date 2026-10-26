from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import unittest

from packages.position_management import (
    PositionLifecycleValidationError,
    PositionLifecycleValidationPolicy,
    certify_position_lifecycle,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/position-management/lifecycle-validation-policy.json"


def manifest(workstream: str) -> dict[str, object]:
    return {
        "workstream": workstream,
        "state": "CANONICAL_COMPLETE",
        "closure": {"lock": "RELEASED"},
        "safety": {
            "real_venue_query": False,
            "credential_mode": "NONE",
            "network_mode": "DISABLED",
            "external_order_submission": False,
            "external_order_mutation": False,
            "automatic_oms_mutation": False,
            "live_execution_validated": False,
            "live_execution_authority": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        },
    }


class PositionLifecycleValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = PositionLifecycleValidationPolicy.from_path(POLICY)
        self.manifests = {ws: manifest(ws) for ws in self.policy.required_workstreams}
        self.hashes = {ws: hashlib.sha256(ws.encode()).hexdigest() for ws in self.policy.required_workstreams}

    def test_complete_safe_coverage_passes_deterministically(self) -> None:
        first = certify_position_lifecycle(self.policy, self.manifests, self.hashes)
        second = certify_position_lifecycle(self.policy, self.manifests, self.hashes)
        self.assertEqual(first.state, "P21_POSITION_LIFECYCLE_VALIDATED_PASS")
        self.assertEqual(first.claim_scope, "REFERENCE_POSITION_LIFECYCLE_VALIDATION")
        self.assertEqual(first.certificate_id, second.certificate_id)
        self.assertEqual(first.p22_state, "NOT_STARTED_OWNER_PHASE_AUTHORIZATION_REQUIRED")
        self.assertFalse(first.automatic_p22_activation)
        self.assertFalse(first.live_execution_validated)
        self.assertFalse(first.production_readiness)

    def test_missing_workstream_fails_closed(self) -> None:
        manifests = dict(self.manifests)
        manifests.pop("P21-G")
        with self.assertRaises(PositionLifecycleValidationError):
            certify_position_lifecycle(self.policy, manifests, self.hashes)

    def test_noncanonical_or_unreleased_workstream_fails_closed(self) -> None:
        manifests = copy.deepcopy(self.manifests)
        manifests["P21-F"]["state"] = "IN_PROGRESS"
        with self.assertRaises(PositionLifecycleValidationError):
            certify_position_lifecycle(self.policy, manifests, self.hashes)

        manifests = copy.deepcopy(self.manifests)
        closure = manifests["P21-G"]["closure"]
        assert isinstance(closure, dict)
        closure["lock"] = "ACTIVE"
        with self.assertRaises(PositionLifecycleValidationError):
            certify_position_lifecycle(self.policy, manifests, self.hashes)

    def test_authority_drift_fails_closed(self) -> None:
        manifests = copy.deepcopy(self.manifests)
        safety = manifests["P21-E"]["safety"]
        assert isinstance(safety, dict)
        safety["live_execution_authority"] = True
        with self.assertRaises(PositionLifecycleValidationError):
            certify_position_lifecycle(self.policy, manifests, self.hashes)

    def test_network_or_trading_drift_fails_closed(self) -> None:
        manifests = copy.deepcopy(self.manifests)
        safety = manifests["P21-A"]["safety"]
        assert isinstance(safety, dict)
        safety["network_mode"] = "ENABLED"
        with self.assertRaises(PositionLifecycleValidationError):
            certify_position_lifecycle(self.policy, manifests, self.hashes)


if __name__ == "__main__":
    unittest.main()
