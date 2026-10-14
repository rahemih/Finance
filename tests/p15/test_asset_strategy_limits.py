from __future__ import annotations

import unittest

from packages.risk.asset_strategy_limits import (
    AssetStrategyLimitError,
    AssetStrategyLimitPolicy,
    AssetStrategyLimitRequest,
    LimitRule,
    LimitUsage,
)


def policy() -> AssetStrategyLimitPolicy:
    return AssetStrategyLimitPolicy.build(
        policy_version="p15c-test-v1",
        rules=(
            LimitRule("ASSET", "BTC", 1200, 3),
            LimitRule("STRATEGY", "TREND", 800, 2),
        ),
    )


def request(**overrides: object) -> AssetStrategyLimitRequest:
    values: dict[str, object] = {
        "request_id": "limit-1",
        "upstream_size_decision_id": "size-1",
        "upstream_size_status": "SIZE_CANDIDATE",
        "asset_id": "BTC",
        "strategy_id": "TREND",
        "incremental_risk_bps": 100,
        "incremental_positions": 1,
        "as_of_ns": 1000,
    }
    values.update(overrides)
    return AssetStrategyLimitRequest(**values)  # type: ignore[arg-type]


def usage() -> tuple[LimitUsage, ...]:
    return (
        LimitUsage("ASSET", "BTC", 500, 1),
        LimitUsage("STRATEGY", "TREND", 300, 1),
    )


class AssetStrategyLimitTests(unittest.TestCase):
    def test_candidate_within_both_limits_is_eligible(self) -> None:
        decision = policy().evaluate(request=request(), usage=usage())
        self.assertEqual(decision.status, "LIMITS_ELIGIBLE")
        self.assertFalse(decision.portfolio_correlation_authority)
        self.assertFalse(decision.leverage_authority)
        self.assertFalse(decision.execution_authority)

    def test_upstream_non_candidate_vetoes(self) -> None:
        decision = policy().evaluate(
            request=request(upstream_size_status="VETO"),
            usage=usage(),
        )
        self.assertEqual(decision.status, "VETO")
        self.assertIn("UPSTREAM_SIZE_NOT_CANDIDATE", decision.reason_codes)

    def test_missing_asset_rule_vetoes(self) -> None:
        p = AssetStrategyLimitPolicy.build(
            policy_version="x",
            rules=(LimitRule("STRATEGY", "TREND", 800, 2),),
        )
        decision = p.evaluate(request=request(), usage=usage())
        self.assertIn("MISSING_RULE:ASSET:BTC", decision.reason_codes)

    def test_missing_usage_vetoes(self) -> None:
        decision = policy().evaluate(
            request=request(),
            usage=(LimitUsage("ASSET", "BTC", 500, 1),),
        )
        self.assertIn("MISSING_USAGE:STRATEGY:TREND", decision.reason_codes)

    def test_asset_risk_limit_vetoes(self) -> None:
        decision = policy().evaluate(
            request=request(incremental_risk_bps=800),
            usage=usage(),
        )
        self.assertIn("RISK_LIMIT_EXCEEDED:ASSET:BTC", decision.reason_codes)

    def test_strategy_risk_limit_vetoes(self) -> None:
        decision = policy().evaluate(
            request=request(incremental_risk_bps=600),
            usage=usage(),
        )
        self.assertIn("RISK_LIMIT_EXCEEDED:STRATEGY:TREND", decision.reason_codes)

    def test_asset_position_count_limit_vetoes(self) -> None:
        decision = policy().evaluate(
            request=request(incremental_positions=3),
            usage=usage(),
        )
        self.assertIn(
            "POSITION_COUNT_LIMIT_EXCEEDED:ASSET:BTC",
            decision.reason_codes,
        )

    def test_strategy_position_count_limit_vetoes(self) -> None:
        decision = policy().evaluate(
            request=request(incremental_positions=2),
            usage=usage(),
        )
        self.assertIn(
            "POSITION_COUNT_LIMIT_EXCEEDED:STRATEGY:TREND",
            decision.reason_codes,
        )

    def test_exact_limit_boundary_is_eligible(self) -> None:
        decision = policy().evaluate(
            request=request(incremental_risk_bps=500, incremental_positions=1),
            usage=(
                LimitUsage("ASSET", "BTC", 700, 2),
                LimitUsage("STRATEGY", "TREND", 300, 1),
            ),
        )
        self.assertEqual(decision.status, "LIMITS_ELIGIBLE")

    def test_duplicate_rules_fail_closed(self) -> None:
        with self.assertRaises(AssetStrategyLimitError):
            AssetStrategyLimitPolicy.build(
                policy_version="x",
                rules=(
                    LimitRule("ASSET", "BTC", 1000, 2),
                    LimitRule("ASSET", "BTC", 900, 2),
                ),
            )

    def test_current_usage_above_limit_fails_closed(self) -> None:
        with self.assertRaises(AssetStrategyLimitError):
            policy().evaluate(
                request=request(),
                usage=(
                    LimitUsage("ASSET", "BTC", 1300, 1),
                    LimitUsage("STRATEGY", "TREND", 300, 1),
                ),
            )

    def test_identity_is_repeatable(self) -> None:
        left = policy().evaluate(request=request(), usage=usage())
        right = policy().evaluate(request=request(), usage=usage())
        self.assertEqual(left.decision_id, right.decision_id)


if __name__ == "__main__":
    unittest.main()
