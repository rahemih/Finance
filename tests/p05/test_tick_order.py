import unittest
from adapters.market_data.tick_order import TickDecision, TickOrderGate


class TickOrderTests(unittest.TestCase):
    def test_accept_and_reject_without_advancing_watermark(self):
        gate = TickOrderGate(max_age_ns=10)
        self.assertEqual(gate.inspect(sequence=1, event_ns=100, now_ns=101), TickDecision.ACCEPT)
        self.assertEqual(gate.inspect(sequence=1, event_ns=100, now_ns=101), TickDecision.DUPLICATE)
        self.assertEqual(gate.inspect(sequence=0, event_ns=100, now_ns=101), TickDecision.OUT_OF_ORDER)
        self.assertEqual(gate.inspect(sequence=2, event_ns=99, now_ns=101), TickDecision.OUT_OF_ORDER)
        self.assertEqual(gate.inspect(sequence=2, event_ns=101, now_ns=112), TickDecision.STALE)
        self.assertEqual(gate.inspect(sequence=2, event_ns=113, now_ns=112), TickDecision.STALE)
        self.assertEqual(gate.inspect(sequence=2, event_ns=102, now_ns=103), TickDecision.ACCEPT)

    def test_boundary_and_invalid_values(self):
        gate = TickOrderGate(10)
        self.assertEqual(gate.inspect(sequence=0, event_ns=10, now_ns=20), TickDecision.ACCEPT)
        self.assertEqual(gate.inspect(sequence=True, event_ns=21, now_ns=21), TickDecision.INVALID)
        self.assertEqual(gate.inspect(sequence=1, event_ns=-1, now_ns=21), TickDecision.INVALID)
        self.assertEqual(gate.inspect(sequence=1, event_ns=21, now_ns=21), TickDecision.ACCEPT)

    def test_invalid_configuration(self):
        for age in (-1, True, 1.5):
            with self.assertRaises(ValueError):
                TickOrderGate(age)


if __name__ == '__main__':
    unittest.main()
