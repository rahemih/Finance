from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
from typing import cast
import unittest

from packages.ux.p23_e2e_validation import (
    EXPECTED_MANIFESTS,
    P23E2EValidation,
    P23E2EValidationError,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/ux/p23-e2e-validation.json"


class P23E2EValidationTests(unittest.TestCase):
    def _policy_raw(self) -> dict[str, object]:
        value = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertIsInstance(value, dict)
        return cast(dict[str, object], value)

    def _copy_root(self, target: Path) -> None:
        for _, _, relative in EXPECTED_MANIFESTS:
            source = ROOT / relative
            dest = target / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
        ia_source = ROOT / "config/ux/information-architecture.json"
        ia_dest = target / "config/ux/information-architecture.json"
        ia_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ia_source, ia_dest)

    def _load_with_policy(self, raw: dict[str, object]) -> P23E2EValidation:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._copy_root(root)
            policy_path = root / "policy.json"
            policy_path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
            return P23E2EValidation.from_root(policy_path, root)

    def _load_with_manifest_mutation(
        self, workstream: str, mutate: object
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._copy_root(root)
            policy_path = root / "policy.json"
            policy_path.write_bytes(POLICY.read_bytes())
            relative = next(path for ws, _, path in EXPECTED_MANIFESTS if ws == workstream)
            path = root / relative
            raw = cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))
            if not callable(mutate):
                self.fail("mutation helper must be callable")
            mutate(raw)
            path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
            P23E2EValidation.from_root(policy_path, root)

    def test_canonical_validation_passes(self) -> None:
        validation = P23E2EValidation.from_root(POLICY, ROOT)
        self.assertEqual(len(validation.upstream), 8)
        self.assertEqual(len(validation.canonical_surfaces), 11)
        self.assertEqual(len(validation.journeys), 5)
        self.assertEqual(validation.safety["p24_state"], "NOT_STARTED")

    def test_validation_id_is_deterministic(self) -> None:
        first = P23E2EValidation.from_root(POLICY, ROOT)
        second = P23E2EValidation.from_root(POLICY, ROOT)
        self.assertEqual(first.validation_id, second.validation_id)

    def test_upstream_manifest_order_drift_fails_closed(self) -> None:
        raw = self._policy_raw()
        manifests = cast(list[object], raw["upstream_manifests"])
        manifests[0], manifests[1] = manifests[1], manifests[0]
        with self.assertRaisesRegex(P23E2EValidationError, "upstream manifest order"):
            self._load_with_policy(raw)

    def test_noncanonical_upstream_state_fails_closed(self) -> None:
        def mutate(raw: dict[str, object]) -> None:
            raw["state"] = "IN_PROGRESS"

        with self.assertRaisesRegex(P23E2EValidationError, "not CANONICAL_COMPLETE"):
            self._load_with_manifest_mutation("P23-C", mutate)

    def test_unreleased_upstream_lock_fails_closed(self) -> None:
        def mutate(raw: dict[str, object]) -> None:
            raw["lock_state"] = "ACQUIRED"

        with self.assertRaisesRegex(P23E2EValidationError, "lock is not RELEASED"):
            self._load_with_manifest_mutation("P23-F", mutate)

    def test_missing_closure_lineage_fails_closed(self) -> None:
        def mutate(raw: dict[str, object]) -> None:
            closure = cast(dict[str, object], raw["closure"])
            closure.pop("post_merge_governance_run", None)

        with self.assertRaisesRegex(P23E2EValidationError, "post_merge_governance_run"):
            self._load_with_manifest_mutation("P23-G", mutate)

    def test_live_authority_drift_fails_closed(self) -> None:
        def mutate(raw: dict[str, object]) -> None:
            safety = cast(dict[str, object], raw["safety"])
            safety["live_trading"] = "ENABLED"

        with self.assertRaisesRegex(P23E2EValidationError, "Live Trading drift"):
            self._load_with_manifest_mutation("P23-H", mutate)

    def test_production_activation_drift_fails_closed(self) -> None:
        def mutate(raw: dict[str, object]) -> None:
            safety = cast(dict[str, object], raw["safety"])
            safety["production_activation"] = True

        with self.assertRaisesRegex(P23E2EValidationError, "forbidden authority drift"):
            self._load_with_manifest_mutation("P23-D", mutate)

    def test_noncanonical_journey_surface_fails_closed(self) -> None:
        raw = self._policy_raw()
        journeys = cast(list[dict[str, object]], raw["reference_journeys"])
        surfaces = cast(list[str], journeys[0]["surfaces"])
        surfaces[0] = "production"
        with self.assertRaisesRegex(P23E2EValidationError, "noncanonical surface"):
            self._load_with_policy(raw)

    def test_browser_certification_cannot_be_claimed(self) -> None:
        raw = self._policy_raw()
        boundary = cast(dict[str, object], raw["certification_boundaries"])
        boundary["browser_runtime_certification"] = True
        with self.assertRaisesRegex(P23E2EValidationError, "certification boundary drift"):
            self._load_with_policy(raw)

    def test_p24_activation_cannot_be_claimed(self) -> None:
        raw = self._policy_raw()
        safety = cast(dict[str, object], raw["safety"])
        safety["p24_state"] = "ACTIVE"
        with self.assertRaisesRegex(P23E2EValidationError, "P23-I safety boundary drift"):
            self._load_with_policy(raw)


if __name__ == "__main__":
    unittest.main()
