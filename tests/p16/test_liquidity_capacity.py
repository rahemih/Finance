from __future__ import annotations

from dataclasses import replace
import unittest

from packages.order_flow_liquidity.liquidity_heatmap import (
    LiquidityHeatmapBand,
    LiquidityHeatmapSnapshot,
)
from packages.order_flow_liquidity.order_book import OrderBookMetrics
from packages.pretrade_firewall.liquidity_capacity import (
    PreTradeLiquidityCapacityPolicy,
    PreTradeLiquidityCapacityRequest,
    evaluate_liquidity_capacity,
)


POLICY = PreTradeLiquidityCapacityPolicy(
    policy_version="p16d-test-v1",
    max_spread_bps=20,
    capacity_band_bps=50,
    max_displayed_capacity_utilization_bps=5000,
)


def metrics(**overrides: object) -> OrderBookMetrics:
    values: dict[str, object] = {
        "snapshot_id": "snapshot-1",
        "depth_levels": 5,
        "best_bid_text": "99",
        "best_ask_text": "101",
        "mid_price_text": "100",
        "spread_text": "2",
        "spread_bps": 20,
        "bid_depth_text": "10",
        "ask_depth_text": "10",
        "imbalance_bps": 0,
    }
    values.update(overrides)
    return OrderBookMetrics(**values)  # type: ignore[arg-type]


def band(
    *,
    bid_notional: str = "2000",
    ask_notional: str = "1000",
    upper: int = 50,
) -> LiquidityHeatmapBand:
    return LiquidityHeatmapBand(
        0,
        upper,
        "10",
        "10",
        bid_notional,
        ask_notional,
        "10",
        "10",
        bid_notional,
        ask_notional,
        str(int(bid_notional) + int(ask_notional)),
        6667,
        3333,
    )


def heatmap(
    *,
    source_snapshot_id: str = "snapshot-1",
    bands: tuple[LiquidityHeatmapBand, ...] | None = None,
) -> LiquidityHeatmapSnapshot:
    return LiquidityHeatmapSnapshot(
        source_snapshot_id,
        "BTC-USD",
        "CRYPTO",
        "fixture-provider",
        "fixture-venue",
        "ORDER_BOOK",
        "VENUE_SCOPED",
        1000,
        1000,
        "100",
        50,
        "0",
        "0",
        "0",
        "0",
        bands if bands is not None else (band(),),
    )


def request(**overrides: object) -> PreTradeLiquidityCapacityRequest:
    values: dict[str, object] = {
        "request_id": "d-1",
        "upstream_risk_envelope_decision_id": "c-decision",
        "upstream_risk_envelope_status": "PRETRADE_C_ELIGIBLE",
        "trade_side": "LONG",
        "requested_notional": "500",
        "order_book_metrics": metrics(),
        "liquidity_heatmap": heatmap(),
        "as_of_ns": 1000,
    }
    values.update(overrides)
    return PreTradeLiquidityCapacityRequest(**values)  # type: ignore[arg-type]


class LiquidityCapacityTests(unittest.TestCase):
    def test_long_uses_ask_capacity_and_is_eligible_at_boundary(self) -> None:
        decision = evaluate_liquidity_capacity(
            policy=POLICY,
            request=request(),
        )
        self.assertEqual(decision.status, "PRETRADE_D_ELIGIBLE")
        self.assertEqual(decision.displayed_capacity_notional, "1000")
        self.assertEqual(decision.capacity_utilization_bps, 5000)
        self.assertFalse(decision.fillability_claim)
        self.assertFalse(decision.execution_authority)

    def test_short_uses_bid_capacity(self) -> None:
        decision = evaluate_liquidity_capacity(
            policy=POLICY,
            request=request(trade_side="SHORT", requested_notional="1000"),
        )
        self.assertEqual(decision.status, "PRETRADE_D_ELIGIBLE")
        self.assertEqual(decision.displayed_capacity_notional, "2000")
        self.assertEqual(decision.capacity_utilization_bps, 5000)

    def test_upstream_veto_is_non_bypassable(self) -> None:
        decision = evaluate_liquidity_capacity(
            policy=POLICY,
            request=request(upstream_risk_envelope_status="VETO"),
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn("UPSTREAM_RISK_ENVELOPE_VETO", decision.reason_codes)

    def test_snapshot_mismatch_vetoes(self) -> None:
        decision = evaluate_liquidity_capacity(
            policy=POLICY,
            request=request(liquidity_heatmap=heatmap(source_snapshot_id="other")),
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn(
            "MICROSTRUCTURE_SNAPSHOT_MISMATCH",
            decision.reason_codes,
        )

    def test_spread_above_limit_vetoes(self) -> None:
        decision = evaluate_liquidity_capacity(
            policy=POLICY,
            request=request(order_book_metrics=metrics(spread_bps=21)),
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn("SPREAD_LIMIT_EXCEEDED", decision.reason_codes)

    def test_missing_capacity_band_vetoes(self) -> None:
        decision = evaluate_liquidity_capacity(
            policy=POLICY,
            request=request(liquidity_heatmap=heatmap(bands=(band(upper=25),))),
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn("CAPACITY_BAND_MISSING", decision.reason_codes)

    def test_zero_capacity_vetoes(self) -> None:
        decision = evaluate_liquidity_capacity(
            policy=POLICY,
            request=request(
                liquidity_heatmap=heatmap(
                    bands=(band(bid_notional="2000", ask_notional="0"),)
                )
            ),
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn("NO_DISPLAYED_CAPACITY", decision.reason_codes)

    def test_capacity_above_limit_vetoes_with_ceiling(self) -> None:
        decision = evaluate_liquidity_capacity(
            policy=POLICY,
            request=request(requested_notional="500.01"),
        )
        self.assertEqual(decision.status, "VETO")
        self.assertEqual(decision.capacity_utilization_bps, 5001)
        self.assertIn(
            "DISPLAYED_CAPACITY_LIMIT_EXCEEDED",
            decision.reason_codes,
        )

    def test_identity_is_deterministic(self) -> None:
        left = evaluate_liquidity_capacity(policy=POLICY, request=request())
        right = evaluate_liquidity_capacity(policy=POLICY, request=request())
        self.assertEqual(left.decision_id, right.decision_id)


if __name__ == "__main__":
    unittest.main()
