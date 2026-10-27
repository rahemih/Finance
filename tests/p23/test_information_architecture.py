from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from packages.ux.information_architecture import (
    EXPECTED_CRITICAL_STATES,
    EXPECTED_SURFACES,
    EXPECTED_WORKFLOWS,
    InformationArchitecture,
    InformationArchitectureError,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/ux/information-architecture.json"


class InformationArchitectureTests(unittest.TestCase):
    def _raw(self) -> dict[str, object]:
        value = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertIsInstance(value, dict)
        return value

    def _load_mutated(self, raw: dict[str, object]) -> InformationArchitecture:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "policy.json"
            path.write_text(
                json.dumps(raw, ensure_ascii=False),
                encoding="utf-8",
            )
            return InformationArchitecture.from_path(path)

    def test_canonical_policy_loads(self) -> None:
        policy = InformationArchitecture.from_path(POLICY)
        self.assertEqual(
            tuple(item.surface_id for item in policy.surfaces),
            EXPECTED_SURFACES,
        )
        self.assertEqual(
            policy.critical_surface_states,
            EXPECTED_CRITICAL_STATES,
        )
        self.assertEqual(
            tuple(item.workflow_id for item in policy.workflows),
            EXPECTED_WORKFLOWS,
        )
        self.assertEqual(policy.locale, "fa-IR")
        self.assertEqual(policy.direction, "RTL")
        self.assertEqual(policy.financial_identifier_direction, "LTR")

    def test_architecture_id_is_deterministic(self) -> None:
        first = InformationArchitecture.from_path(POLICY)
        second = InformationArchitecture.from_path(POLICY)
        self.assertEqual(first.architecture_id, second.architecture_id)

    def test_duplicate_route_fails_closed(self) -> None:
        raw = self._raw()
        surfaces = cast(list[dict[str, object]], raw["surfaces"])
        surfaces[1]["route"] = surfaces[0]["route"]
        with self.assertRaisesRegex(
            InformationArchitectureError,
            "routes must be unique",
        ):
            self._load_mutated(raw)

    def test_dynamic_route_fails_closed(self) -> None:
        raw = self._raw()
        surfaces = cast(list[dict[str, object]], raw["surfaces"])
        surfaces[0]["route"] = "/dashboard/:id"
        with self.assertRaisesRegex(
            InformationArchitectureError,
            "static absolute",
        ):
            self._load_mutated(raw)

    def test_surface_order_or_coverage_drift_fails_closed(self) -> None:
        raw = self._raw()
        surfaces = cast(list[dict[str, object]], raw["surfaces"])
        surfaces.pop()
        with self.assertRaisesRegex(
            InformationArchitectureError,
            "canonical P23 core surfaces",
        ):
            self._load_mutated(raw)

    def test_critical_state_drift_fails_closed(self) -> None:
        raw = self._raw()
        states = cast(list[str], raw["critical_surface_states"])
        states.remove("STALE")
        with self.assertRaisesRegex(
            InformationArchitectureError,
            "fail-visible set",
        ):
            self._load_mutated(raw)

    def test_unknown_workflow_surface_fails_closed(self) -> None:
        raw = self._raw()
        workflows = cast(list[dict[str, object]], raw["workflows"])
        workflow_surfaces = cast(list[str], workflows[0]["surfaces"])
        workflow_surfaces.append("live-trading")
        with self.assertRaisesRegex(
            InformationArchitectureError,
            "unknown surfaces",
        ):
            self._load_mutated(raw)

    def test_workflow_authority_drift_fails_closed(self) -> None:
        raw = self._raw()
        workflows = cast(list[dict[str, object]], raw["workflows"])
        workflows[0]["authority"] = "EXECUTE_ORDER"
        with self.assertRaisesRegex(
            InformationArchitectureError,
            "cannot grant action authority",
        ):
            self._load_mutated(raw)

    def test_workflow_coverage_drift_fails_closed(self) -> None:
        raw = self._raw()
        workflows = cast(list[dict[str, object]], raw["workflows"])
        workflows.pop()
        with self.assertRaisesRegex(
            InformationArchitectureError,
            "canonical P23-A flows",
        ):
            self._load_mutated(raw)

    def test_provenance_requirement_drift_fails_closed(self) -> None:
        raw = self._raw()
        provenance = cast(
            dict[str, object],
            raw["provenance_requirements"],
        )
        provenance["realtime_surfaces_show_freshness"] = False
        with self.assertRaisesRegex(
            InformationArchitectureError,
            "must be true",
        ):
            self._load_mutated(raw)

    def test_live_authority_drift_fails_closed(self) -> None:
        raw = self._raw()
        safety = cast(dict[str, object], raw["safety"])
        safety["live_trading"] = "ENABLED"
        with self.assertRaisesRegex(
            InformationArchitectureError,
            "safety boundary drift",
        ):
            self._load_mutated(raw)

    def test_p24_activation_drift_fails_closed(self) -> None:
        raw = self._raw()
        safety = cast(dict[str, object], raw["safety"])
        safety["p24_state"] = "ACTIVE"
        with self.assertRaisesRegex(
            InformationArchitectureError,
            "safety boundary drift",
        ):
            self._load_mutated(raw)


if __name__ == "__main__":
    unittest.main()
