from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
from typing import cast
import unittest

from packages.ux.design_system import (
    DesignSystem,
    DesignSystemError,
    EXPECTED_BREAKPOINTS,
    EXPECTED_LTR_ISLANDS,
    EXPECTED_RADII,
    EXPECTED_SPACING,
    EXPECTED_STATES,
    EXPECTED_TERMS,
    EXPECTED_TYPOGRAPHY,
    contrast_ratio,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/ux/design-system.json"


class DesignSystemTests(unittest.TestCase):
    def _raw(self) -> dict[str, object]:
        value = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertIsInstance(value, dict)
        return cast(dict[str, object], value)

    def _load(self, raw: dict[str, object]) -> DesignSystem:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "design-system.json"
            path.write_text(
                json.dumps(raw, ensure_ascii=False),
                encoding="utf-8",
            )
            return DesignSystem.from_path(path)

    def test_canonical_policy_loads(self) -> None:
        design = DesignSystem.from_path(POLICY)
        self.assertEqual(design.typography_px, EXPECTED_TYPOGRAPHY)
        self.assertEqual(design.spacing_px, EXPECTED_SPACING)
        self.assertEqual(design.radii_px, EXPECTED_RADII)
        self.assertEqual(design.breakpoints_px, EXPECTED_BREAKPOINTS)
        self.assertEqual(
            tuple(item.state_id for item in design.semantic_states),
            EXPECTED_STATES,
        )
        self.assertEqual(design.terminology_ids, EXPECTED_TERMS)
        self.assertEqual(design.ltr_islands, EXPECTED_LTR_ISLANDS)

    def test_id_is_deterministic(self) -> None:
        first = DesignSystem.from_path(POLICY)
        second = DesignSystem.from_path(POLICY)
        self.assertEqual(first.design_system_id, second.design_system_id)

    def test_light_and_dark_body_contrast_pass(self) -> None:
        raw = self._raw()
        themes = cast(dict[str, dict[str, str]], raw["themes"])
        for theme in themes.values():
            self.assertGreaterEqual(
                contrast_ratio(theme["text"], theme["background"]),
                4.5,
            )
            self.assertGreaterEqual(
                contrast_ratio(theme["muted_text"], theme["surface"]),
                4.5,
            )

    def test_semantic_states_have_non_color_cues(self) -> None:
        design = DesignSystem.from_path(POLICY)
        for item in design.semantic_states:
            self.assertTrue(item.label_fa.strip())
            self.assertTrue(item.icon.strip())

    def test_low_contrast_fails_closed(self) -> None:
        raw = self._raw()
        themes = cast(dict[str, dict[str, str]], raw["themes"])
        themes["light"]["text"] = "#F7F8FA"
        with self.assertRaisesRegex(DesignSystemError, "contrast below"):
            self._load(raw)

    def test_semantic_state_order_drift_fails_closed(self) -> None:
        raw = self._raw()
        states = cast(dict[str, object], raw["semantic_states"])
        rebuilt = {"warning": states["warning"], **{
            key: value for key, value in states.items() if key != "warning"
        }}
        raw["semantic_states"] = rebuilt
        with self.assertRaisesRegex(DesignSystemError, "coverage/order drift"):
            self._load(raw)

    def test_ltr_island_removal_fails_closed(self) -> None:
        raw = self._raw()
        directionality = cast(dict[str, object], raw["directionality"])
        islands = cast(list[str], directionality["ltr_islands"])
        islands.remove("order_id")
        with self.assertRaisesRegex(DesignSystemError, "LTR financial island"):
            self._load(raw)

    def test_bidi_isolation_cannot_be_disabled(self) -> None:
        raw = self._raw()
        directionality = cast(dict[str, object], raw["directionality"])
        directionality["ltr_island_isolation_required"] = False
        with self.assertRaisesRegex(DesignSystemError, "bidi isolation"):
            self._load(raw)

    def test_long_short_wait_no_trade_keep_canonical_identifier(self) -> None:
        raw = self._raw()
        terms = cast(list[dict[str, object]], raw["terminology"])
        long_term = next(item for item in terms if item["id"] == "long")
        long_term["fa"] = "خرید"
        with self.assertRaisesRegex(DesignSystemError, "identifier hidden"):
            self._load(raw)

    def test_financial_digit_policy_fails_closed(self) -> None:
        raw = self._raw()
        policy = cast(dict[str, object], raw["digit_policy"])
        latin = cast(list[str], policy["latin_digits"])
        latin.remove("prices")
        with self.assertRaisesRegex(DesignSystemError, "financial digit"):
            self._load(raw)

    def test_accessibility_guardrails_fail_closed(self) -> None:
        raw = self._raw()
        accessibility = cast(dict[str, object], raw["accessibility"])
        accessibility["color_only_state_forbidden"] = False
        with self.assertRaisesRegex(DesignSystemError, "color-only"):
            self._load(raw)

    def test_safety_drift_fails_closed(self) -> None:
        raw = self._raw()
        safety = cast(dict[str, object], raw["safety"])
        safety["production_activation"] = True
        with self.assertRaisesRegex(DesignSystemError, "safety boundary drift"):
            self._load(raw)


if __name__ == "__main__":
    unittest.main()
