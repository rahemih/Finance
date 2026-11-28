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
        self.assertEqual(gate.inspect(sequence=2, event_ns=112, now_ns=113), TickDecision.ACCEPT)

    def test_clock_regression_is_rejected_without_advancing_watermark(self):
        gate = TickOrderGate(10)
        self.assertEqual(gate.inspect(sequence=1, event_ns=100, now_ns=101), TickDecision.ACCEPT)
        self.assertEqual(gate.inspect(sequence=2, event_ns=101, now_ns=100), TickDecision.INVALID)
        self.assertEqual(gate.last_sequence, 1)
        self.assertEqual(gate.inspect(sequence=2, event_ns=102, now_ns=103), TickDecision.ACCEPT)

    def test_boundary_and_invalid_values(self):
        gate = TickOrderGate(10)
        self.assertEqual(gate.inspect(sequence=0, event_ns=10, now_ns=20), TickDecision.ACCEPT)
        self.assertEqual(gate.inspect(sequence=True, event_ns=21, now_ns=21), TickDecision.INVALID)
        self.assertEqual(gate.inspect(sequence=1, event_ns=-1, now_ns=21), TickDecision.INVALID)
        self.assertEqual(gate.inspect(sequence=1, event_ns=21, now_ns=21), TickDecision.ACCEPT)

    def test_independent_instrument_watermarks_and_recovery(self):
        eurusd = TickOrderGate(max_age_ns=10)
        btcusdt = TickOrderGate(max_age_ns=10)
        self.assertEqual(eurusd.inspect(sequence=5, event_ns=100, now_ns=101), TickDecision.ACCEPT)
        self.assertEqual(btcusdt.inspect(sequence=1, event_ns=100, now_ns=101), TickDecision.ACCEPT)
        self.assertEqual(eurusd.inspect(sequence=4, event_ns=101, now_ns=102), TickDecision.OUT_OF_ORDER)
        self.assertEqual(btcusdt.inspect(sequence=2, event_ns=102, now_ns=103), TickDecision.ACCEPT)
        self.assertEqual(eurusd.last_sequence, 5)
        self.assertEqual(eurusd.inspect(sequence=6, event_ns=103, now_ns=104), TickDecision.ACCEPT)

    def test_reused_sequence_with_changed_event_time_is_not_a_duplicate(self):
        gate = TickOrderGate(max_age_ns=20)
        self.assertEqual(gate.inspect(sequence=7, event_ns=100, now_ns=101), TickDecision.ACCEPT)
        self.assertEqual(gate.inspect(sequence=7, event_ns=102, now_ns=103), TickDecision.OUT_OF_ORDER)
        self.assertEqual(gate.last_event_ns, 100)
        self.assertEqual(gate.inspect(sequence=8, event_ns=104, now_ns=105), TickDecision.ACCEPT)

    def test_invalid_configuration(self):
        for age in (-1, True, 1.5):
            with self.assertRaises(ValueError):
                TickOrderGate(age)


if __name__ == '__main__':
    unittest.main()
