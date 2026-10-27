from __future__ import annotations

import json
from pathlib import Path
import tempfile
from typing import cast
import unittest

from packages.ux.operational_screens import (
    EXPECTED_COMPONENT_FAMILIES,
    OperationalScreens,
    OperationalScreensError,
)

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/ux/operational-screens.json"
IA = ROOT / "config/ux/information-architecture.json"
DS = ROOT / "config/ux/design-system.json"


class OperationalScreensTests(unittest.TestCase):
    def _raw(self) -> dict[str, object]:
        value = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertIsInstance(value, dict)
        return cast(dict[str, object], value)

    def _load(self, raw: dict[str, object]) -> OperationalScreens:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "screens.json"
            path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
            return OperationalScreens.from_paths(path, IA, DS)

    def test_canonical_policy_loads(self) -> None:
        policy = OperationalScreens.from_paths(POLICY, IA, DS)
        self.assertEqual(len(policy.screens), 11)
        self.assertEqual(policy.allowed_component_families, EXPECTED_COMPONENT_FAMILIES)
        self.assertEqual(policy.directionality["shell"], "RTL")
        self.assertEqual(policy.directionality["financial_islands"], "LTR")

    def test_id_is_deterministic(self) -> None:
        first = OperationalScreens.from_paths(POLICY, IA, DS)
        second = OperationalScreens.from_paths(POLICY, IA, DS)
        self.assertEqual(first.operational_screens_id, second.operational_screens_id)

    def test_surface_route_drift_fails_closed(self) -> None:
        raw = self._raw()
        screens = cast(list[dict[str, object]], raw["screens"])
        screens[0]["route"] = "/other"
        with self.assertRaisesRegex(OperationalScreensError, "exactly bind"):
            self._load(raw)

    def test_surface_coverage_drift_fails_closed(self) -> None:
        raw = self._raw()
        screens = cast(list[dict[str, object]], raw["screens"])
        screens.pop()
        with self.assertRaisesRegex(OperationalScreensError, "coverage"):
            self._load(raw)

    def test_critical_state_drift_fails_closed(self) -> None:
        raw = self._raw()
        states = cast(list[str], raw["critical_states"])
        states.remove("OFFLINE")
        with self.assertRaisesRegex(OperationalScreensError, "critical state"):
            self._load(raw)

    def test_unknown_shell_fails_closed(self) -> None:
        raw = self._raw()
        screens = cast(list[dict[str, object]], raw["screens"])
        screens[0]["shell"] = "execution"
        with self.assertRaisesRegex(OperationalScreensError, "unknown shell"):
            self._load(raw)

    def test_duplicate_section_fails_closed(self) -> None:
        raw = self._raw()
        screens = cast(list[dict[str, object]], raw["screens"])
        sections = cast(list[str], screens[0]["sections"])
        sections.append(sections[0])
        with self.assertRaisesRegex(OperationalScreensError, "sections must be unique"):
            self._load(raw)

    def test_provenance_cannot_be_weakened(self) -> None:
        raw = self._raw()
        provenance = cast(dict[str, object], raw["provenance"])
        provenance["realtime_surfaces_show_freshness"] = False
        with self.assertRaisesRegex(OperationalScreensError, "weakened"):
            self._load(raw)

    def test_reserved_owner_drift_fails_closed(self) -> None:
        raw = self._raw()
        reserved = cast(dict[str, object], raw["reserved_behavior_owners"])
        reserved["notification_delivery"] = "P23-C"
        with self.assertRaisesRegex(OperationalScreensError, "ownership drift"):
            self._load(raw)

    def test_component_family_drift_fails_closed(self) -> None:
        raw = self._raw()
        families = cast(list[str], raw["allowed_component_families"])
        families.append("ExecuteOrderButton")
        with self.assertRaisesRegex(OperationalScreensError, "component-family"):
            self._load(raw)

    def test_authority_drift_fails_closed(self) -> None:
        raw = self._raw()
        raw["authority"] = "EXECUTE_ORDER"
        with self.assertRaisesRegex(OperationalScreensError, "policy mismatch: authority"):
            self._load(raw)

    def test_directionality_drift_fails_closed(self) -> None:
        raw = self._raw()
        directionality = cast(dict[str, object], raw["directionality"])
        directionality["bidi_isolation_required"] = False
        with self.assertRaisesRegex(OperationalScreensError, "directionality"):
            self._load(raw)

    def test_figma_binding_required(self) -> None:
        raw = self._raw()
        figma = cast(dict[str, object], raw["figma"])
        figma["node_id"] = ""
        with self.assertRaisesRegex(OperationalScreensError, "non-empty text"):
            self._load(raw)

    def test_p24_activation_fails_closed(self) -> None:
        raw = self._raw()
        safety = cast(dict[str, object], raw["safety"])
        safety["p24_state"] = "ACTIVE"
        with self.assertRaisesRegex(OperationalScreensError, "safety boundary"):
            self._load(raw)

    def test_live_authority_fails_closed(self) -> None:
        raw = self._raw()
        safety = cast(dict[str, object], raw["safety"])
        safety["live_trading"] = "ENABLED"
        with self.assertRaisesRegex(OperationalScreensError, "safety boundary"):
            self._load(raw)


if __name__ == "__main__":
    unittest.main()
