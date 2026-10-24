from __future__ import annotations

import hashlib
from pathlib import Path
import unittest

from packages.position_management import CanonicalPositionEngine, CanonicalPositionError, CanonicalPositionPolicy, PositionFillEvent, PositionSpec

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "config/position-management/canonical-position-state-policy.json"


def h(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def spec() -> PositionSpec:
    return PositionSpec("pos-1", "portfolio-1", "strategy-1", "BTC-USDT", "CRYPTO", "LONG", 100_000, 100, h("risk"), h("firewall"))


def event(seq: int, kind: str, qty: int, price: int, token: str) -> PositionFillEvent:
    return PositionFillEvent("pos-1", seq, 1_000 + seq, kind, qty, price, f"order-{token}", f"client-{token}", h(f"oms-{token}"), h(f"recon-{token}"))


class PositionTransitionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = CanonicalPositionPolicy.from_path(POLICY)
        self.engine = CanonicalPositionEngine(self.policy)
        self.engine.register(spec())

    def test_open_add_partial_close_close(self) -> None:
        self.engine.apply(event(1, "OPEN_FILL", 100_000, 10_000, "a"))
        added = self.engine.apply(event(2, "ADD_FILL", 50_000, 11_000, "b"))
        partial = self.engine.apply(event(3, "REDUCE_FILL", 25_000, 12_000, "c"))
        closed = self.engine.apply(event(4, "REDUCE_FILL", 125_000, 12_100, "d"))
        self.assertEqual(added.entry_value_product_scaled, 1_550_000_000)
        self.assertEqual(added.average_entry_price_scaled_floor, 10_333)
        self.assertEqual(added.average_entry_price_remainder, 50_000)
        self.assertEqual(partial.state, "PARTIALLY_CLOSED")
        self.assertEqual(closed.state, "CLOSED")
        self.assertEqual(closed.open_quantity_scaled, 0)

    def test_over_close_fails_closed(self) -> None:
        self.engine.apply(event(1, "OPEN_FILL", 100_000, 10_000, "a"))
        with self.assertRaises(CanonicalPositionError):
            self.engine.apply(event(2, "REDUCE_FILL", 100_001, 11_000, "b"))

    def test_scale_in_after_reduction_fails_closed(self) -> None:
        self.engine.apply(event(1, "OPEN_FILL", 100_000, 10_000, "a"))
        self.engine.apply(event(2, "REDUCE_FILL", 10_000, 11_000, "b"))
        with self.assertRaises(CanonicalPositionError):
            self.engine.apply(event(3, "ADD_FILL", 10_000, 10_500, "c"))


if __name__ == "__main__":
    unittest.main()
