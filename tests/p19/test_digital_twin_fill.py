from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
import unittest

from packages.shadow.digital_twin_fill import (
    DigitalTwinFillEngine,
    DigitalTwinFillError,
    DigitalTwinFillPolicy,
    DigitalTwinFillRequest,
    DigitalTwinMarketSlice,
)
from quant.backtesting.engine import BacktestMarketEvent
from quant.backtesting.execution_realism import (
    ExecutionRealismPolicy,
    HistoricalDepthLevel,
    HistoricalExecutionContext,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config/shadow/digital-twin-fill-policy.json"


def h(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def policy(*, latency: int = 0, participation: int = 5000) -> DigitalTwinFillPolicy:
    return DigitalTwinFillPolicy(
        accepted_context_quality=("EXPLICIT_HISTORICAL_DEPTH", "DERIVED_REFERENCE_DEPTH"),
        execution_policy=ExecutionRealismPolicy(
            policy_version=f"test-{latency}-{participation}",
            taker_fee_bps=5,
            decision_latency_ns=latency,
            max_displayed_depth_participation_bps=participation,
        ),
    )


def request(*, quantity: str = "0.1", quality: str = "DERIVED_REFERENCE_DEPTH") -> DigitalTwinFillRequest:
    return DigitalTwinFillRequest(
        twin_name="btc-reference-twin",
        incident_replay_root_id=h("incident"),
        decision_replay_session_id=h("decision-session"),
        shadow_record_id=h("shadow-record"),
        asset_id="BTC-USD",
        decision_time_ns=1000,
        quantity_delta=quantity,
        reference_price_scaled=100_000,
        price_scale=100,
        context_quality=quality,
        source_evidence_sha256=h("source"),
    )


def market_slice(
    sequence: int,
    *,
    event_time: int,
    bid: int = 99_900,
    ask: int = 100_100,
    quantity: str = "1",
) -> DigitalTwinMarketSlice:
    event = BacktestMarketEvent(
        sequence=sequence,
        event_time_ns=event_time,
        available_at_ns=event_time,
        asset_id="BTC-USD",
        price_scaled=100_000,
        price_scale=100,
    )
    context = HistoricalExecutionContext(
        sequence=sequence,
        event_time_ns=event_time,
        available_at_ns=event_time,
        asset_id="BTC-USD",
        price_scale=100,
        bids=(
            HistoricalDepthLevel(bid, quantity),
            HistoricalDepthLevel(bid - 100, quantity),
        ),
        asks=(
            HistoricalDepthLevel(ask, quantity),
            HistoricalDepthLevel(ask + 100, quantity),
        ),
        source_evidence_sha256=h(f"context-{sequence}"),
    )
    return DigitalTwinMarketSlice(event=event, context=context)


class DigitalTwinFillTests(unittest.TestCase):
    def test_policy_file_is_governed_reference_only(self) -> None:
        loaded = DigitalTwinFillPolicy.from_path(POLICY_PATH)
        self.assertEqual(loaded.execution_policy.taker_fee_bps, 5)
        self.assertEqual(loaded.execution_policy.decision_latency_ns, 0)

    def test_same_request_and_timeline_are_deterministic(self) -> None:
        timeline=(market_slice(1, event_time=1000),)
        left=DigitalTwinFillEngine(policy()).simulate(request=request(), timeline=timeline)
        right=DigitalTwinFillEngine(policy()).simulate(request=request(), timeline=timeline)
        self.assertEqual(left.result_id, right.result_id)

    def test_full_fill_uses_p17b_and_reports_slippage_fee(self) -> None:
        result=DigitalTwinFillEngine(policy()).simulate(
            request=request(quantity="0.1"),
            timeline=(market_slice(1, event_time=1000),),
        )
        self.assertEqual(result.status, "FULL_FILL")
        self.assertEqual(result.execution_realism_owner, "P17-B")
        self.assertEqual(result.side, "BUY")
        self.assertEqual(result.filled_quantity, "0.1")
        self.assertEqual(result.vwap_price_scaled, "100100")
        self.assertEqual(result.adverse_slippage_bps, "10")
        self.assertNotEqual(result.total_fee_cash, "0")
        self.assertTrue(result.fill_ids)
        self.assertTrue(result.diagnostic_ids)

    def test_insufficient_depth_produces_partial_fill(self) -> None:
        result=DigitalTwinFillEngine(policy(participation=5000)).simulate(
            request=request(quantity="2"),
            timeline=(market_slice(1, event_time=1000, quantity="1"),),
        )
        self.assertEqual(result.status, "PARTIAL_FILL")
        self.assertEqual(result.filled_quantity, "1")
        self.assertEqual(result.remaining_quantity, "1")

    def test_latency_defers_fill_to_later_slice(self) -> None:
        result=DigitalTwinFillEngine(policy(latency=1000)).simulate(
            request=request(quantity="0.1"),
            timeline=(
                market_slice(1, event_time=1000),
                market_slice(2, event_time=2000, ask=100_200),
            ),
        )
        self.assertEqual(result.status, "FULL_FILL")
        self.assertEqual(result.vwap_price_scaled, "100200")

    def test_latency_beyond_timeline_produces_no_fill(self) -> None:
        result=DigitalTwinFillEngine(policy(latency=3000)).simulate(
            request=request(quantity="0.1"),
            timeline=(
                market_slice(1, event_time=1000),
                market_slice(2, event_time=2000),
            ),
        )
        self.assertEqual(result.status, "NO_FILL")
        self.assertEqual(result.filled_quantity, "0")
        self.assertIsNone(result.vwap_price_scaled)
        self.assertIsNone(result.adverse_slippage_bps)

    def test_sell_slippage_uses_bid_side(self) -> None:
        result=DigitalTwinFillEngine(policy()).simulate(
            request=request(quantity="-0.1"),
            timeline=(market_slice(1, event_time=1000, bid=99_900),),
        )
        self.assertEqual(result.status, "FULL_FILL")
        self.assertEqual(result.side, "SELL")
        self.assertEqual(result.vwap_price_scaled, "99900")
        self.assertEqual(result.adverse_slippage_bps, "10")

    def test_timeline_sequence_must_increase(self) -> None:
        with self.assertRaises(DigitalTwinFillError):
            DigitalTwinFillEngine(policy()).simulate(
                request=request(),
                timeline=(
                    market_slice(2, event_time=1000),
                    market_slice(1, event_time=2000),
                ),
            )

    def test_timeline_time_must_increase(self) -> None:
        with self.assertRaises(DigitalTwinFillError):
            DigitalTwinFillEngine(policy()).simulate(
                request=request(),
                timeline=(
                    market_slice(1, event_time=1000),
                    market_slice(2, event_time=1000),
                ),
            )

    def test_slice_context_mismatch_fails_closed(self) -> None:
        base=market_slice(1, event_time=1000)
        bad_context=replace(base.context, asset_id="ETH-USD")
        with self.assertRaises(DigitalTwinFillError):
            DigitalTwinMarketSlice(event=base.event, context=bad_context)

    def test_derived_reference_depth_cannot_claim_production_accuracy(self) -> None:
        result=DigitalTwinFillEngine(policy()).simulate(
            request=request(quality="DERIVED_REFERENCE_DEPTH"),
            timeline=(market_slice(1, event_time=1000),),
        )
        self.assertFalse(result.production_quality_context)
        self.assertFalse(result.production_fill_accuracy_claim)
        self.assertFalse(result.broker_truth)

    def test_explicit_depth_still_does_not_self_certify_production_accuracy(self) -> None:
        result=DigitalTwinFillEngine(policy()).simulate(
            request=request(quality="EXPLICIT_HISTORICAL_DEPTH"),
            timeline=(market_slice(1, event_time=1000),),
        )
        self.assertTrue(result.production_quality_context)
        self.assertFalse(result.production_fill_accuracy_claim)

    def test_incident_root_changes_request_and_result_identity(self) -> None:
        base=request()
        other=replace(base, incident_replay_root_id=h("other-incident"))
        engine=DigitalTwinFillEngine(policy())
        timeline=(market_slice(1, event_time=1000),)
        self.assertNotEqual(base.request_id, other.request_id)
        self.assertNotEqual(
            engine.simulate(request=base, timeline=timeline).result_id,
            engine.simulate(request=other, timeline=timeline).result_id,
        )

    def test_result_has_zero_authority(self) -> None:
        result=DigitalTwinFillEngine(policy()).simulate(
            request=request(),
            timeline=(market_slice(1, event_time=1000),),
        )
        self.assertFalse(result.decision_authority)
        self.assertFalse(result.fill_authority)
        self.assertFalse(result.execution_authority)
        self.assertFalse(result.order_routing_authority)
        self.assertFalse(result.broker_exchange_routing)
        self.assertFalse(result.p20_started)
        self.assertEqual(result.live_trading, "DISABLED")
        self.assertEqual(result.auto_trading, "DISABLED")


if __name__ == "__main__":
    unittest.main()
