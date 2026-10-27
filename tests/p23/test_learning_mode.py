from __future__ import annotations

import json
from pathlib import Path
import tempfile
from typing import cast
import unittest

from packages.ux.learning_mode import LearningMode, LearningModeError

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/ux/learning-mode-glossary.json"
DS = ROOT / "config/ux/design-system.json"


class LearningModeTests(unittest.TestCase):
    def _raw(self) -> dict[str, object]:
        value = json.loads(POLICY.read_text(encoding="utf-8"))
        self.assertIsInstance(value, dict)
        return cast(dict[str, object], value)

    def _load(self, raw: dict[str, object]) -> LearningMode:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "policy.json"
            path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
            return LearningMode.from_paths(path, DS)

    def test_canonical_policy_loads(self) -> None:
        policy = LearningMode.from_paths(POLICY, DS)
        self.assertEqual(policy.modes, ("OFF", "GUIDED", "DETAILED"))
        self.assertEqual(policy.glossary_route, "/glossary")
        self.assertEqual(len(policy.entries), 15)

    def test_id_is_deterministic(self) -> None:
        first = LearningMode.from_paths(POLICY, DS)
        second = LearningMode.from_paths(POLICY, DS)
        self.assertEqual(first.learning_mode_id, second.learning_mode_id)

    def test_mode_order_drift_fails_closed(self) -> None:
        raw = self._raw()
        learning = cast(dict[str, object], raw["learning_mode"])
        learning["modes"] = ["GUIDED", "OFF", "DETAILED"]
        with self.assertRaisesRegex(LearningModeError, "order/coverage"):
            self._load(raw)

    def test_authority_drift_fails_closed(self) -> None:
        raw = self._raw()
        learning = cast(dict[str, object], raw["learning_mode"])
        learning["authority"] = "SIGNAL_ADVICE"
        with self.assertRaisesRegex(LearningModeError, "authority drift"):
            self._load(raw)

    def test_signal_mutation_fails_closed(self) -> None:
        raw = self._raw()
        learning = cast(dict[str, object], raw["learning_mode"])
        learning["mutates_signal"] = True
        with self.assertRaisesRegex(LearningModeError, "forbidden"):
            self._load(raw)

    def test_personalized_advice_fails_closed(self) -> None:
        raw = self._raw()
        learning = cast(dict[str, object], raw["learning_mode"])
        learning["personalized_advice"] = True
        with self.assertRaisesRegex(LearningModeError, "forbidden"):
            self._load(raw)

    def test_glossary_route_drift_fails_closed(self) -> None:
        raw = self._raw()
        glossary = cast(dict[str, object], raw["glossary"])
        glossary["route"] = "/learn"
        with self.assertRaisesRegex(LearningModeError, "route drift"):
            self._load(raw)

    def test_glossary_coverage_drift_fails_closed(self) -> None:
        raw = self._raw()
        glossary = cast(dict[str, object], raw["glossary"])
        entries = cast(list[dict[str, object]], glossary["entries"])
        entries.pop()
        with self.assertRaisesRegex(LearningModeError, "coverage"):
            self._load(raw)

    def test_canonical_term_drift_fails_closed(self) -> None:
        raw = self._raw()
        glossary = cast(dict[str, object], raw["glossary"])
        entries = cast(list[dict[str, object]], glossary["entries"])
        entries[-1]["canonical"] = "TRADE"
        with self.assertRaisesRegex(LearningModeError, "must match P23-B"):
            self._load(raw)

    def test_empty_definition_fails_closed(self) -> None:
        raw = self._raw()
        glossary = cast(dict[str, object], raw["glossary"])
        entries = cast(list[dict[str, object]], glossary["entries"])
        entries[0]["definition_fa"] = ""
        with self.assertRaisesRegex(LearningModeError, "non-empty text"):
            self._load(raw)

    def test_provenance_cannot_be_weakened(self) -> None:
        raw = self._raw()
        provenance = cast(dict[str, object], raw["provenance"])
        provenance["limitations_required"] = False
        with self.assertRaisesRegex(LearningModeError, "provenance drift"):
            self._load(raw)

    def test_p24_activation_fails_closed(self) -> None:
        raw = self._raw()
        safety = cast(dict[str, object], raw["safety"])
        safety["p24_state"] = "ACTIVE"
        with self.assertRaisesRegex(LearningModeError, "safety boundary"):
            self._load(raw)


if __name__ == "__main__":
    unittest.main()
