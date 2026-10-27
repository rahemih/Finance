from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
from typing import cast
import unittest

from packages.production.readiness_dossier import (
    EXPECTED_GATES,
    EXPECTED_PREREQUISITES,
    ProductionReadinessDossier,
    ProductionReadinessError,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/production/production-readiness-dossier.json"
STATE = ROOT / "docs/02-current-state/CURRENT-STATE.md"


class ProductionReadinessDossierTests(unittest.TestCase):
    def _raw(self) -> dict[str, object]:
        value = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertIsInstance(value, dict)
        return cast(dict[str, object], value)

    def _load(self, raw: dict[str, object], state_text: str | None = None) -> ProductionReadinessDossier:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_path = root / "docs/02-current-state/CURRENT-STATE.md"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(
                STATE.read_text(encoding="utf-8") if state_text is None else state_text,
                encoding="utf-8",
            )
            policy = root / "policy.json"
            policy.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
            return ProductionReadinessDossier.from_root(policy, root)

    def test_canonical_dossier_is_not_ready_for_live(self) -> None:
        dossier = ProductionReadinessDossier.from_root(POLICY, ROOT)
        self.assertEqual(dossier.verdict, "NOT_READY_FOR_LIVE")
        self.assertEqual(dossier.gates, EXPECTED_GATES)
        self.assertEqual(tuple(x.prerequisite_id for x in dossier.prerequisites), EXPECTED_PREREQUISITES)
        self.assertEqual(len(dossier.blocker_ids), len(EXPECTED_PREREQUISITES))

    def test_dossier_id_is_deterministic(self) -> None:
        first = ProductionReadinessDossier.from_root(POLICY, ROOT)
        second = ProductionReadinessDossier.from_root(POLICY, ROOT)
        self.assertEqual(first.dossier_id, second.dossier_id)

    def test_gate_order_drift_fails_closed(self) -> None:
        raw = self._raw()
        gates = cast(list[object], raw["required_upstream_gates"])
        gates[0], gates[1] = gates[1], gates[0]
        with self.assertRaisesRegex(ProductionReadinessError, "gate order/coverage"):
            self._load(raw)

    def test_missing_gate_marker_fails_closed(self) -> None:
        state = STATE.read_text(encoding="utf-8").replace("G12_OPERATIONS_VALIDATED PASS", "G12_OPERATIONS_VALIDATED UNKNOWN")
        with self.assertRaisesRegex(ProductionReadinessError, "missing canonical gate marker"):
            self._load(self._raw(), state)

    def test_p23_canonical_marker_is_required(self) -> None:
        raw = self._raw()
        p23 = cast(dict[str, object], raw["p23_requirement"])
        p23["required"] = False
        with self.assertRaisesRegex(ProductionReadinessError, "P23 requirement"):
            self._load(raw)

    def test_phase_start_cannot_grant_first_live(self) -> None:
        raw = self._raw()
        auth = cast(dict[str, object], raw["phase_authorization"])
        auth["first_live_activation"] = "GRANTED"
        with self.assertRaisesRegex(ProductionReadinessError, "phase authorization boundary"):
            self._load(raw)

    def test_phase_start_cannot_grant_g13(self) -> None:
        raw = self._raw()
        auth = cast(dict[str, object], raw["phase_authorization"])
        auth["grants_g13"] = True
        with self.assertRaisesRegex(ProductionReadinessError, "phase authorization boundary"):
            self._load(raw)

    def test_production_venue_remains_a_blocker(self) -> None:
        dossier = ProductionReadinessDossier.from_root(POLICY, ROOT)
        self.assertIn("PRODUCTION_VENUE_SELECTED", dossier.blocker_ids)

    def test_credentials_remain_a_blocker(self) -> None:
        dossier = ProductionReadinessDossier.from_root(POLICY, ROOT)
        self.assertIn("PRODUCTION_CREDENTIALS_READY", dossier.blocker_ids)

    def test_live_execution_validation_remains_a_blocker(self) -> None:
        dossier = ProductionReadinessDossier.from_root(POLICY, ROOT)
        self.assertIn("LIVE_EXECUTION_VALIDATED", dossier.blocker_ids)

    def test_live_gate_freshness_remains_a_blocker(self) -> None:
        dossier = ProductionReadinessDossier.from_root(POLICY, ROOT)
        self.assertIn("UPSTREAM_GATE_FRESHNESS_FOR_LIVE", dossier.blocker_ids)

    def test_production_security_posture_remains_a_blocker(self) -> None:
        dossier = ProductionReadinessDossier.from_root(POLICY, ROOT)
        self.assertIn("PRODUCTION_SECURITY_POSTURE_VERIFIED", dossier.blocker_ids)

    def test_production_risk_budget_remains_a_blocker(self) -> None:
        dossier = ProductionReadinessDossier.from_root(POLICY, ROOT)
        self.assertIn("PRODUCTION_RISK_BUDGET_DEFINED", dossier.blocker_ids)

    def test_first_live_owner_gate_remains_a_blocker(self) -> None:
        dossier = ProductionReadinessDossier.from_root(POLICY, ROOT)
        self.assertIn("FIRST_LIVE_OWNER_APPROVAL", dossier.blocker_ids)

    def test_kill_switch_live_drill_remains_a_blocker(self) -> None:
        dossier = ProductionReadinessDossier.from_root(POLICY, ROOT)
        self.assertIn("LIVE_KILL_SWITCH_DRILL", dossier.blocker_ids)

    def test_g13_remains_a_blocker(self) -> None:
        dossier = ProductionReadinessDossier.from_root(POLICY, ROOT)
        self.assertIn("G13_OWNER_LIVE_APPROVAL", dossier.blocker_ids)

    def test_safety_authority_drift_fails_closed(self) -> None:
        raw = self._raw()
        safety = cast(dict[str, object], raw["safety"])
        safety["external_order_authority"] = True
        with self.assertRaisesRegex(ProductionReadinessError, "safety boundary drift"):
            self._load(raw)

    def test_p24_b_cannot_be_marked_ready(self) -> None:
        raw = self._raw()
        next_state = cast(dict[str, object], raw["next"])
        next_state["p24_b"] = "READY"
        with self.assertRaisesRegex(ProductionReadinessError, "next-state boundary drift"):
            self._load(raw)


if __name__ == "__main__":
    unittest.main()
