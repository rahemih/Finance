"""Q04 synthetic boundary cases: no broker, network, or order side effects."""
import unittest

from adapters.market_data.tick_order import TickDecision, TickOrderGate


class TickBoundaryTests(unittest.TestCase):
    def test_stale_high_sequence_does_not_block_next_fresh_tick(self):
        gate = TickOrderGate(max_age_ns=10)
        self.assertEqual(gate.inspect(sequence=10, event_ns=100, now_ns=101), TickDecision.ACCEPT)
        self.assertEqual(gate.inspect(sequence=999, event_ns=101, now_ns=120), TickDecision.STALE)
        self.assertEqual(gate.last_sequence, 10)
        self.assertEqual(gate.inspect(sequence=11, event_ns=119, now_ns=120), TickDecision.ACCEPT)

    def test_future_high_sequence_does_not_block_next_fresh_tick(self):
        gate = TickOrderGate(max_age_ns=10)
        self.assertEqual(gate.inspect(sequence=10, event_ns=100, now_ns=101), TickDecision.ACCEPT)
        self.assertEqual(gate.inspect(sequence=999, event_ns=122, now_ns=120), TickDecision.STALE)
        self.assertEqual(gate.last_sequence, 10)
        self.assertEqual(gate.inspect(sequence=11, event_ns=119, now_ns=120), TickDecision.ACCEPT)


if __name__ == "__main__":
    unittest.main()
