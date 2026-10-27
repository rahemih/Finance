from __future__ import annotations

import json
from pathlib import Path
import tempfile
from typing import cast
import unittest

from packages.ux.accessibility_performance import (
    AccessibilityPerformanceError,
    FrontendHardeningPolicy,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/ux/accessibility-responsive-performance.json"
DESIGN = ROOT / "config/ux/design-system.json"
SCREENS = ROOT / "config/ux/operational-screens.json"


class AccessibilityPerformanceTests(unittest.TestCase):
    def _raw(self) -> dict[str, object]:
        value = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertIsInstance(value, dict)
        return cast(dict[str, object], value)

    def _load(self, raw: dict[str, object]) -> FrontendHardeningPolicy:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "policy.json"
            path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
            return FrontendHardeningPolicy.from_paths(path, DESIGN, SCREENS)

    def test_canonical_policy_loads(self) -> None:
        policy = FrontendHardeningPolicy.from_paths(POLICY, DESIGN, SCREENS)
        self.assertEqual(policy.profile_ids, ("mobile", "tablet", "desktop", "wide"))
        self.assertEqual(policy.profile_widths, (360, 768, 1024, 1440))
        self.assertEqual(len(policy.screen_ids), 11)
        self.assertEqual(policy.accessibility["standard"], "WCAG_2_2_AA")

    def test_policy_id_is_deterministic(self) -> None:
        first = FrontendHardeningPolicy.from_paths(POLICY, DESIGN, SCREENS)
        second = FrontendHardeningPolicy.from_paths(POLICY, DESIGN, SCREENS)
        self.assertEqual(first.policy_id, second.policy_id)

    def test_contrast_floor_drift_fails_closed(self) -> None:
        raw = self._raw()
        accessibility = cast(dict[str, object], raw["accessibility"])
        accessibility["minimum_normal_text_contrast"] = 4.0
        with self.assertRaisesRegex(AccessibilityPerformanceError, "accessibility contract drift"):
            self._load(raw)

    def test_touch_target_drift_fails_closed(self) -> None:
        raw = self._raw()
        accessibility = cast(dict[str, object], raw["accessibility"])
        accessibility["minimum_touch_target_px"] = 40
        with self.assertRaisesRegex(AccessibilityPerformanceError, "accessibility contract drift"):
            self._load(raw)

    def test_responsive_profile_drift_fails_closed(self) -> None:
        raw = self._raw()
        responsive = cast(dict[str, object], raw["responsive"])
        profiles = cast(list[dict[str, object]], responsive["profiles"])
        profiles[0]["width_px"] = 320
        with self.assertRaisesRegex(AccessibilityPerformanceError, "responsive profile width drift"):
            self._load(raw)

    def test_clipping_guard_cannot_be_disabled(self) -> None:
        raw = self._raw()
        responsive = cast(dict[str, object], raw["responsive"])
        responsive["critical_content_clipping_forbidden"] = False
        with self.assertRaisesRegex(AccessibilityPerformanceError, "responsive requirement weakened"):
            self._load(raw)

    def test_production_performance_certification_forbidden(self) -> None:
        raw = self._raw()
        performance = cast(dict[str, object], raw["performance"])
        performance["production_certification"] = True
        with self.assertRaisesRegex(AccessibilityPerformanceError, "production performance certification forbidden"):
            self._load(raw)

    def test_reference_budget_drift_fails_closed(self) -> None:
        raw = self._raw()
        performance = cast(dict[str, object], raw["performance"])
        performance["lcp_ms_max"] = 4000
        with self.assertRaisesRegex(AccessibilityPerformanceError, "LCP reference budget drift"):
            self._load(raw)

    def test_safety_drift_fails_closed(self) -> None:
        raw = self._raw()
        safety = cast(dict[str, object], raw["safety"])
        safety["production_activation"] = True
        with self.assertRaisesRegex(AccessibilityPerformanceError, "P23-G safety boundary drift"):
            self._load(raw)


if __name__ == "__main__":
    unittest.main()
