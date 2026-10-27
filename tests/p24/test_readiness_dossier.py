from __future__ import annotations

import json
from pathlib import Path
import tempfile
from typing import cast
import unittest

from packages.production.readiness_dossier import (
    EXPECTED_GATES,
    EXPECTED_PREREQUISITES,
    FIRST_LIVE_OWNER_GATE,
    P24_EXIT_PREREQUISITES,
    PRE_FIRST_LIVE_PREREQUISITES,
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

    def _load(
        self, raw: dict[str, object], state_text: str | None = None
    ) -> ProductionReadinessDossier:
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

    def _satisfy_stage(
        self, raw: dict[str, object], stage: str, state_text: str
    ) -> str:
        prerequisites = cast(list[dict[str, object]], raw["production_prerequisites"])
        additions: list[str] = []
        for item in prerequisites:
            if item["stage"] == stage:
                marker = f"TEST_POSITIVE_{item['id']}"
                item["satisfied"] = True
                item["marker"] = marker
                additions.append(marker)
        return state_text + "\n" + "\n".join(additions) + "\n"

    def test_canonical_dossier_is_not_ready_for_live(self) -> None:
        dossier = ProductionReadinessDossier.from_root(POLICY, ROOT)
        self.assertEqual(dossier.verdict, "NOT_READY_FOR_LIVE")
        self.assertEqual(dossier.gates, EXPECTED_GATES)
        self.assertEqual(
            tuple(x.prerequisite_id for x in dossier.prerequisites),
            EXPECTED_PREREQUISITES,
        )
        self.assertEqual(len(dossier.blocker_ids), 13)
        self.assertEqual(
            dossier.pre_first_live_blocker_ids, PRE_FIRST_LIVE_PREREQUISITES
        )
        self.assertTrue(dossier.first_live_owner_gate_pending)
        self.assertEqual(dossier.p24_exit_blocker_ids, P24_EXIT_PREREQUISITES)
        self.assertEqual(
            dossier.p24_b_state, "BLOCKED_HUMAN_AND_PRODUCTION_PREREQUISITES"
        )

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
        state = STATE.read_text(encoding="utf-8").replace(
            "G12_OPERATIONS_VALIDATED PASS", "G12_OPERATIONS_VALIDATED UNKNOWN"
        )
        with self.assertRaisesRegex(
            ProductionReadinessError, "missing canonical gate marker"
        ):
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
        with self.assertRaisesRegex(
            ProductionReadinessError, "phase authorization boundary"
        ):
            self._load(raw)

    def test_phase_start_cannot_grant_g13(self) -> None:
        raw = self._raw()
        auth = cast(dict[str, object], raw["phase_authorization"])
        auth["grants_g13"] = True
        with self.assertRaisesRegex(
            ProductionReadinessError, "phase authorization boundary"
        ):
            self._load(raw)

    def test_stage_drift_fails_closed(self) -> None:
        raw = self._raw()
        prerequisites = cast(list[dict[str, object]], raw["production_prerequisites"])
        prerequisites[0]["stage"] = "P24_EXIT"
        with self.assertRaisesRegex(ProductionReadinessError, "stage drift"):
            self._load(raw)

    def test_satisfied_prerequisite_requires_evidence_marker(self) -> None:
        raw = self._raw()
        prerequisites = cast(list[dict[str, object]], raw["production_prerequisites"])
        prerequisites[0]["satisfied"] = True
        prerequisites[0]["marker"] = ""
        with self.assertRaisesRegex(
            ProductionReadinessError, "requires evidence marker"
        ):
            self._load(raw)

    def test_production_venue_remains_pre_first_live_blocker(self) -> None:
        dossier = ProductionReadinessDossier.from_root(POLICY, ROOT)
        self.assertIn("PRODUCTION_VENUE_SELECTED", dossier.pre_first_live_blocker_ids)

    def test_credentials_remain_pre_first_live_blocker(self) -> None:
        dossier = ProductionReadinessDossier.from_root(POLICY, ROOT)
        self.assertIn("PRODUCTION_CREDENTIALS_READY", dossier.pre_first_live_blocker_ids)

    def test_pre_live_kill_switch_validation_is_required(self) -> None:
        dossier = ProductionReadinessDossier.from_root(POLICY, ROOT)
        self.assertIn(
            "PRE_LIVE_KILL_SWITCH_VALIDATED", dossier.pre_first_live_blocker_ids
        )

    def test_live_execution_validation_is_phase_exit_only(self) -> None:
        dossier = ProductionReadinessDossier.from_root(POLICY, ROOT)
        self.assertNotIn(
            "LIVE_EXECUTION_VALIDATED", dossier.pre_first_live_blocker_ids
        )
        self.assertIn("LIVE_EXECUTION_VALIDATED", dossier.p24_exit_blocker_ids)

    def test_p24_g_drills_are_phase_exit_only(self) -> None:
        dossier = ProductionReadinessDossier.from_root(POLICY, ROOT)
        self.assertNotIn(
            "P24_G_KILL_SWITCH_DRILLS_COMPLETE",
            dossier.pre_first_live_blocker_ids,
        )
        self.assertIn(
            "P24_G_KILL_SWITCH_DRILLS_COMPLETE", dossier.p24_exit_blocker_ids
        )

    def test_g13_is_phase_exit_only(self) -> None:
        dossier = ProductionReadinessDossier.from_root(POLICY, ROOT)
        self.assertNotIn(
            "G13_OWNER_LIVE_APPROVAL", dossier.pre_first_live_blocker_ids
        )
        self.assertIn("G13_OWNER_LIVE_APPROVAL", dossier.p24_exit_blocker_ids)

    def test_live_gate_freshness_remains_pre_first_live_blocker(self) -> None:
        dossier = ProductionReadinessDossier.from_root(POLICY, ROOT)
        self.assertIn(
            "UPSTREAM_GATE_FRESHNESS_FOR_LIVE",
            dossier.pre_first_live_blocker_ids,
        )

    def test_production_security_posture_remains_pre_first_live_blocker(self) -> None:
        dossier = ProductionReadinessDossier.from_root(POLICY, ROOT)
        self.assertIn(
            "PRODUCTION_SECURITY_POSTURE_VERIFIED",
            dossier.pre_first_live_blocker_ids,
        )

    def test_production_risk_budget_remains_pre_first_live_blocker(self) -> None:
        dossier = ProductionReadinessDossier.from_root(POLICY, ROOT)
        self.assertIn(
            "PRODUCTION_RISK_BUDGET_DEFINED", dossier.pre_first_live_blocker_ids
        )

    def test_first_live_owner_gate_is_separate_from_technical_readiness(self) -> None:
        dossier = ProductionReadinessDossier.from_root(POLICY, ROOT)
        self.assertTrue(dossier.first_live_owner_gate_pending)
        self.assertNotIn(FIRST_LIVE_OWNER_GATE, dossier.pre_first_live_blocker_ids)

    def test_ready_for_owner_gate_does_not_require_g13_or_live_execution(self) -> None:
        raw = self._raw()
        state = STATE.read_text(encoding="utf-8")
        state = self._satisfy_stage(raw, "PRE_FIRST_LIVE", state)
        raw["expected_verdict"] = "READY_FOR_FIRST_LIVE_OWNER_GATE"
        next_state = cast(dict[str, object], raw["next"])
        next_state["p24_b"] = "FIRST_LIVE_OWNER_HUMAN_GATE_REQUIRED"
        dossier = self._load(raw, state)
        self.assertEqual(dossier.verdict, "READY_FOR_FIRST_LIVE_OWNER_GATE")
        self.assertEqual(
            dossier.p24_b_state, "FIRST_LIVE_OWNER_HUMAN_GATE_REQUIRED"
        )
        self.assertIn("LIVE_EXECUTION_VALIDATED", dossier.p24_exit_blocker_ids)
        self.assertIn("G13_OWNER_LIVE_APPROVAL", dossier.p24_exit_blocker_ids)

    def test_manual_live_ready_only_after_explicit_owner_gate(self) -> None:
        raw = self._raw()
        state = STATE.read_text(encoding="utf-8")
        state = self._satisfy_stage(raw, "PRE_FIRST_LIVE", state)
        prerequisites = cast(list[dict[str, object]], raw["production_prerequisites"])
        owner = next(item for item in prerequisites if item["id"] == FIRST_LIVE_OWNER_GATE)
        owner["satisfied"] = True
        owner["marker"] = "TEST_FIRST_LIVE_OWNER_APPROVAL"
        state += "\nTEST_FIRST_LIVE_OWNER_APPROVAL\n"
        raw["expected_verdict"] = "READY_FOR_MANUAL_LIVE"
        next_state = cast(dict[str, object], raw["next"])
        next_state["p24_b"] = "READY_FOR_MANUAL_LIVE"
        dossier = self._load(raw, state)
        self.assertEqual(dossier.verdict, "READY_FOR_MANUAL_LIVE")
        self.assertEqual(dossier.p24_b_state, "READY_FOR_MANUAL_LIVE")
        self.assertTrue(dossier.p24_exit_blocker_ids)

    def test_g13_cannot_be_satisfied_by_p24_a(self) -> None:
        raw = self._raw()
        prerequisites = cast(list[dict[str, object]], raw["production_prerequisites"])
        g13 = next(item for item in prerequisites if item["id"] == "G13_OWNER_LIVE_APPROVAL")
        g13["satisfied"] = True
        g13["marker"] = "TEST_G13_APPROVAL"
        state = STATE.read_text(encoding="utf-8") + "\nTEST_G13_APPROVAL\n"
        with self.assertRaisesRegex(ProductionReadinessError, "G13 cannot"):
            self._load(raw, state)

    def test_safety_authority_drift_fails_closed(self) -> None:
        raw = self._raw()
        safety = cast(dict[str, object], raw["safety"])
        safety["external_order_authority"] = True
        with self.assertRaisesRegex(ProductionReadinessError, "safety boundary drift"):
            self._load(raw)

    def test_p24_b_cannot_be_marked_ready_while_prerequisites_are_open(self) -> None:
        raw = self._raw()
        next_state = cast(dict[str, object], raw["next"])
        next_state["p24_b"] = "READY_FOR_MANUAL_LIVE"
        with self.assertRaisesRegex(ProductionReadinessError, "next-state boundary drift"):
            self._load(raw)


if __name__ == "__main__":
    unittest.main()
