"""D02 synthetic-only lifecycle tests for both venue labels; no SDK/network calls."""
import unittest

from packages.production.offline_order_lifecycle import LifecycleError, OfflineOrder, State


class OfflineOrderLifecycleTests(unittest.TestCase):
    def test_both_venue_labels_have_no_execution_authority(self):
        for venue in ("XCHIEF_MT5_DEMO_MOCK", "TOOBIT_PAPER_MOCK"):
            with self.subTest(venue=venue):
                order = OfflineOrder(venue + "-trace", 10)
                order.submit_unknown()
                self.assertFalse(order.may_submit_again)
                order.acknowledge(order.client_id)
                order.reconcile(order.client_id, 4)
                self.assertEqual(order.state, State.PARTIAL)
                order.reconcile(order.client_id, 10)
                self.assertEqual(order.state, State.FILLED)

    def test_unknown_ack_does_not_allow_retry(self):
        order = OfflineOrder("trace", 2)
        order.submit_unknown()
        with self.assertRaises(LifecycleError):
            order.submit_unknown()

    def test_wrong_id_and_regressed_fill_fail_closed(self):
        order = OfflineOrder("trace", 10)
        order.submit_unknown()
        with self.assertRaises(LifecycleError):
            order.acknowledge("other")
        order.reconcile("trace", 5)
        with self.assertRaises(LifecycleError):
            order.reconcile("trace", 4)
        with self.assertRaises(LifecycleError):
            order.reconcile("trace", 3, canceled=False)
        self.assertEqual((order.state, order.filled_units), (State.CANCELED, 3))

    def test_cancel_and_terminal_replay(self):
        order = OfflineOrder("trace", 10)
        order.submit_unknown()
        order.reconcile("trace", 3, canceled=True)
        self.assertEqual(order.state, State.CANCELED)
        order.reconcile("trace", 3, canceled=True)
        with self.assertRaises(LifecycleError):
            order.reconcile("trace", 4)

    def test_contradictory_full_fill_cancel_is_atomic(self):
        order = OfflineOrder("trace", 10)
        order.submit_unknown()
        order.reconcile("trace", 3)
        with self.assertRaises(LifecycleError):
            order.reconcile("trace", 10, canceled=True)
        self.assertEqual(order.filled_units, 3)
        self.assertEqual(order.state, State.PARTIAL)
        order.reconcile("trace", 10)
        self.assertEqual(order.state, State.FILLED)

    def test_boolean_fill_and_invalid_units_rejected(self):
        with self.assertRaises(LifecycleError):
            OfflineOrder("trace", True)
        order = OfflineOrder("trace", 2)
        order.submit_unknown()
        with self.assertRaises(LifecycleError):
            order.reconcile("trace", True)


    def test_forged_initial_state_and_non_string_identity_fail_closed(self):
        for kwargs in (
            {"filled_units": 1},
            {"filled_units": True},
            {"state": State.ACKED},
            {"state": "NEW"},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(LifecycleError):
                OfflineOrder("trace", 2, **kwargs)
        for client_id in (123, "   ", None):
            with self.subTest(client_id=client_id), self.assertRaises(LifecycleError):
                OfflineOrder(client_id, 2)


    def test_non_boolean_cancel_flag_is_rejected_atomically(self):
        order = OfflineOrder("trace", 10)
        order.submit_unknown()
        for flag in ("false", "true", 0, 1, None, []):
            with self.subTest(flag=flag):
                before = (order.state, order.filled_units)
                with self.assertRaises(LifecycleError):
                    order.reconcile("trace", 3, canceled=flag)
                self.assertEqual((order.state, order.filled_units), before)
        order.reconcile("trace", 3, canceled=False)
        self.assertEqual((order.state, order.filled_units), (State.PARTIAL, 3))

    def test_invalid_reconciliation_preserves_order_snapshot(self):
        """Rejected evidence must not partially mutate an ambiguous order."""
        order = OfflineOrder("trace", 10)
        order.submit_unknown()
        for client_id, cumulative, canceled in (
            ("other", 4, False),
            ("trace", -1, False),
            ("trace", 11, False),
            ("trace", True, False),
            ("trace", 10, True),
        ):
            with self.subTest(client_id=client_id, cumulative=cumulative, canceled=canceled):
                before = (order.state, order.filled_units)
                with self.assertRaises(LifecycleError):
                    order.reconcile(client_id, cumulative, canceled=canceled)
                self.assertEqual((order.state, order.filled_units), before)
        order.reconcile("trace", 4)
        self.assertEqual((order.state, order.filled_units), (State.PARTIAL, 4))

if __name__ == "__main__":
    unittest.main()
