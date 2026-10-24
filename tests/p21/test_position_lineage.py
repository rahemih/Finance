from __future__ import annotations

import hashlib
from pathlib import Path
import unittest

from packages.position_management import CanonicalPositionEngine, CanonicalPositionError, CanonicalPositionPolicy, PositionFillEvent, PositionSpec

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/position-management/canonical-position-state-policy.json"


def h(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def spec(position_id: str) -> PositionSpec:
    return PositionSpec(position_id, "portfolio", "strategy", "BTC-USDT", "CRYPTO", "LONG", 100_000, 100, h("risk-"+position_id), h("fw-"+position_id))


def event(position_id: str, seq: int, kind: str, token: str, *, at: int) -> PositionFillEvent:
    return PositionFillEvent(position_id, seq, at, kind, 10_000, 10_000, f"order-{token}", f"client-{token}", h("oms-"+token), h("recon-"+token))


class PositionLineageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = CanonicalPositionPolicy.from_path(POLICY)

    def test_first_event_sequence_and_kind_are_strict(self) -> None:
        engine = CanonicalPositionEngine(self.policy)
        engine.register(spec("p1"))
        with self.assertRaises(CanonicalPositionError):
            engine.apply(event("p1", 2, "OPEN_FILL", "a", at=10))
        with self.assertRaises(CanonicalPositionError):
            engine.apply(event("p1", 1, "REDUCE_FILL", "b", at=10))

    def test_duplicate_oms_lineage_fails_closed(self) -> None:
        engine = CanonicalPositionEngine(self.policy)
        engine.register(spec("p1"))
        first = event("p1", 1, "OPEN_FILL", "same", at=10)
        engine.apply(first)
        duplicate = PositionFillEvent("p1", 2, 11, "ADD_FILL", 10_000, 10_100, "order-2", "client-2", first.oms_record_id, h("recon-2"))
        with self.assertRaises(CanonicalPositionError):
            engine.apply(duplicate)

    def test_sequence_gap_and_time_regression_fail_closed(self) -> None:
        engine = CanonicalPositionEngine(self.policy)
        engine.register(spec("p1"))
        engine.apply(event("p1", 1, "OPEN_FILL", "a", at=10))
        with self.assertRaises(CanonicalPositionError):
            engine.apply(event("p1", 3, "ADD_FILL", "b", at=11))
        with self.assertRaises(CanonicalPositionError):
            engine.apply(event("p1", 2, "ADD_FILL", "c", at=9))


if __name__ == "__main__":
    unittest.main()
