from __future__ import annotations

import unittest

from quant.backtesting.capacity_testing import (
    CapacityTestingError,
    evaluate_liquidity_capacity,
)
from quant.backtesting.execution_realism import (
    ExecutionRealismPolicy,
    HistoricalDepthLevel,
    HistoricalExecutionContext,
)


ROBUSTNESS = "a" * 64
POLICY = ExecutionRealismPolicy(
    policy_version="p17f-test-v1",
    taker_fee_bps=5,
    decision_latency_ns=0,
    max_displayed_depth_participation_bps=5000,
)


def context(
    sequence: int,
    *,
    asset_id: str = "BTC-USD",
    price_scale: int = 1,
    quantity: str = "100",
) -> HistoricalExecutionContext:
    return HistoricalExecutionContext(
        sequence=sequence,
        event_time_ns=1000 + sequence,
        available_at_ns=1000 + sequence,
        asset_id=asset_id,
        price_scale=price_scale,
        bids=(
            HistoricalDepthLevel(99, quantity),
            HistoricalDepthLevel(98, quantity),
        ),
        asks=(
            HistoricalDepthLevel(101, quantity),
            HistoricalDepthLevel(102, quantity),
        ),
        source_evidence_sha256=f"{sequence + 1:064x}",
    )


def evaluate(
    *,
    side: str = "BUY",
    contexts: tuple[HistoricalExecutionContext, ...] | None = None,
    scales: tuple[int, ...] = (10_000, 20_000, 30_000),
):
    return evaluate_liquidity_capacity(
        robustness_certificate_id=ROBUSTNESS,
        execution_policy=POLICY,
        side=side,
        baseline_quantity="50",
        contexts=contexts or (context(0), context(1)),
        scale_bps=scales,
    )


class CapacityTestingTests(unittest.TestCase):
    def test_capacity_surface_is_deterministic(self) -> None:
        left = evaluate()
        right = evaluate(
            contexts=(context(1), context(0)),
            scales=(30_000, 10_000, 20_000),
        )
        self.assertEqual(left.certificate_id, right.certificate_id)
        self.assertEqual(left.status, "CAPACITY_EVALUATED")
        self.assertEqual(left.max_full_fill_scale_bps, 20_000)
        self.assertFalse(left.hidden_liquidity_inference)
        self.assertFalse(left.market_impact_claim)
        self.assertFalse(left.profitability_claim_authority)
        self.assertFalse(left.g9_authority)
        self.assertFalse(left.execution_authority)

    def test_partial_fill_and_utilization_above_capacity(self) -> None:
        result = evaluate()
        summary = {item.scale_bps: item for item in result.scale_summaries}
        self.assertEqual(summary[30_000].worst_fill_ratio_bps, 6666)
        self.assertEqual(summary[30_000].max_capacity_utilization_bps, 15_000)
        self.assertFalse(summary[30_000].all_contexts_full_fill)

    def test_displayed_depth_slippage_is_adverse(self) -> None:
        result = evaluate()
        summary = {item.scale_bps: item for item in result.scale_summaries}
        self.assertEqual(summary[10_000].worst_adverse_slippage_bps, 0)
        self.assertEqual(summary[20_000].worst_adverse_slippage_bps, 100)

    def test_sell_side_uses_bid_depth(self) -> None:
        result = evaluate(side="SELL", scales=(20_000,))
        summary = result.scale_summaries[0]
        self.assertEqual(summary.worst_fill_ratio_bps, 10_000)
        self.assertEqual(summary.worst_adverse_slippage_bps, 102)

    def test_mixed_assets_and_scales_fail_closed(self) -> None:
        with self.assertRaises(CapacityTestingError):
            evaluate(contexts=(context(0), context(1, asset_id="ETH-USD")))
        with self.assertRaises(CapacityTestingError):
            evaluate(contexts=(context(0), context(1, price_scale=100)))

    def test_duplicate_context_and_scale_fail_closed(self) -> None:
        duplicate = context(0)
        with self.assertRaises(CapacityTestingError):
            evaluate(contexts=(duplicate, duplicate))
        with self.assertRaises(CapacityTestingError):
            evaluate(scales=(10_000, 10_000))

    def test_invalid_side_and_baseline_fail_closed(self) -> None:
        with self.assertRaises(CapacityTestingError):
            evaluate(side="LONG")
        with self.assertRaises(CapacityTestingError):
            evaluate_liquidity_capacity(
                robustness_certificate_id=ROBUSTNESS,
                execution_policy=POLICY,
                side="BUY",
                baseline_quantity="0",
                contexts=(context(0),),
                scale_bps=(10_000,),
            )


if __name__ == "__main__":
    unittest.main()
