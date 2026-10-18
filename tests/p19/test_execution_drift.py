from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
import unittest

from packages.shadow.execution_drift import (
    ExecutionDriftError,
    ExecutionDriftPolicy,
    ObservedExecutionSample,
    PaperExecutionSample,
    build_drift_window,
    compare_execution_drift,
)


ROOT = Path(__file__).resolve().parents[2]
POLICY = ExecutionDriftPolicy.from_path(
    ROOT / "config/shadow/execution-drift-policy.json"
)


def h(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def paper(
    index: int = 1,
    *,
    filled: str = "1",
    requested: str = "1",
    slippage: str | None = "10",
    fee_bps: str = "5",
    latency_ns: int = 100_000_000,
    status: str = "FULL_FILL",
) -> PaperExecutionSample:
    return PaperExecutionSample(
        digital_twin_result_id=h(f"twin-{index}"),
        incident_replay_root_id=h(f"incident-{index}"),
        asset_id="BTC-USD",
        side="BUY",
        decision_time_ns=1_000_000_000 + index * 10_000,
        requested_quantity=requested,
        filled_quantity=filled,
        adverse_slippage_bps=slippage,
        fee_bps=fee_bps,
        modeled_latency_ns=latency_ns,
        fill_status=status,
        source_evidence_sha256=h(f"paper-source-{index}"),
    )


def observed(
    base: PaperExecutionSample,
    *,
    name: str = "obs",
    observation_class: str = "REFERENCE_OBSERVATION",
    filled: str | None = None,
    slippage: str | None = "10",
    fee_bps: str = "5",
    latency_ns: int = 100_000_000,
    status: str | None = None,
) -> ObservedExecutionSample:
    return ObservedExecutionSample(
        paper_sample_id=base.sample_id,
        observation_name=name,
        observation_class=observation_class,
        asset_id=base.asset_id,
        side=base.side,
        observed_at_ns=base.decision_time_ns + max(1, latency_ns),
        requested_quantity=base.requested_quantity,
        filled_quantity=base.filled_quantity if filled is None else filled,
        adverse_slippage_bps=slippage,
        fee_bps=fee_bps,
        observed_latency_ns=latency_ns,
        fill_status=base.fill_status if status is None else status,
        source_evidence_sha256=h(f"observed-{name}"),
    )


class ExecutionDriftTests(unittest.TestCase):
    def test_same_pair_is_deterministic(self) -> None:
        p = paper()
        o = observed(p)
        left = compare_execution_drift(paper=p, observed=o, policy=POLICY)
        right = compare_execution_drift(paper=p, observed=o, policy=POLICY)
        self.assertEqual(left.pair_id, right.pair_id)
        self.assertEqual(left.severity, "NORMAL")

    def test_exact_binding_to_paper_sample_is_required(self) -> None:
        p = paper()
        o = replace(observed(p), paper_sample_id=h("wrong-paper"))
        with self.assertRaises(ExecutionDriftError):
            compare_execution_drift(paper=p, observed=o, policy=POLICY)

    def test_asset_side_and_quantity_mismatch_fail_closed(self) -> None:
        p = paper()
        for o in (
            replace(observed(p), asset_id="ETH-USD"),
            replace(observed(p), side="SELL"),
            replace(observed(p), requested_quantity="2"),
        ):
            with self.assertRaises(ExecutionDriftError):
                compare_execution_drift(paper=p, observed=o, policy=POLICY)

    def test_slippage_warn_threshold_is_deterministic(self) -> None:
        p = paper(slippage="10")
        pair = compare_execution_drift(
            paper=p,
            observed=observed(p, slippage="30"),
            policy=POLICY,
        )
        self.assertEqual(pair.abs_slippage_drift_bps, "20")
        self.assertEqual(pair.severity, "WARN")

    def test_slippage_fail_threshold_is_deterministic(self) -> None:
        p = paper(slippage="10")
        pair = compare_execution_drift(
            paper=p,
            observed=observed(p, slippage="70"),
            policy=POLICY,
        )
        self.assertEqual(pair.abs_slippage_drift_bps, "60")
        self.assertEqual(pair.severity, "FAIL")

    def test_fill_ratio_drift_is_measured(self) -> None:
        p = paper()
        pair = compare_execution_drift(
            paper=p,
            observed=observed(
                p,
                filled="0.9",
                status="PARTIAL_FILL",
                slippage="10",
            ),
            policy=POLICY,
        )
        self.assertEqual(pair.fill_ratio_drift_bps, "1000")
        self.assertEqual(pair.severity, "FAIL")

    def test_fill_status_mismatch_is_fail(self) -> None:
        p = paper()
        pair = compare_execution_drift(
            paper=p,
            observed=observed(
                p,
                filled="0.5",
                status="PARTIAL_FILL",
                slippage="10",
            ),
            policy=POLICY,
        )
        self.assertFalse(pair.fill_status_match)
        self.assertEqual(pair.severity, "FAIL")

    def test_fee_and_latency_drift_are_measured(self) -> None:
        p = paper(fee_bps="5", latency_ns=100_000_000)
        pair = compare_execution_drift(
            paper=p,
            observed=observed(
                p,
                fee_bps="8",
                latency_ns=700_000_000,
            ),
            policy=POLICY,
        )
        self.assertEqual(pair.abs_fee_drift_bps, "3")
        self.assertEqual(pair.abs_latency_drift_ns, 600_000_000)
        self.assertEqual(pair.severity, "WARN")

    def test_input_order_does_not_change_window(self) -> None:
        pairs = []
        for i in range(1, 4):
            p = paper(i)
            pairs.append(
                compare_execution_drift(
                    paper=p,
                    observed=observed(p, name=f"obs-{i}"),
                    policy=POLICY,
                )
            )
        left = build_drift_window(pairs=pairs, policy=POLICY)
        right = build_drift_window(pairs=tuple(reversed(pairs)), policy=POLICY)
        self.assertEqual(left.window_id, right.window_id)

    def test_mixed_observation_classes_fail_closed(self) -> None:
        p1 = paper(1)
        p2 = paper(2)
        pairs = (
            compare_execution_drift(
                paper=p1,
                observed=observed(p1, observation_class="REFERENCE_OBSERVATION"),
                policy=POLICY,
            ),
            compare_execution_drift(
                paper=p2,
                observed=observed(
                    p2,
                    observation_class="LIVE_EXECUTION_OBSERVATION",
                ),
                policy=POLICY,
            ),
        )
        with self.assertRaises(ExecutionDriftError):
            build_drift_window(pairs=pairs, policy=POLICY)

    def test_reference_observations_never_validate_live_drift(self) -> None:
        pairs = []
        for i in range(1, POLICY.minimum_live_samples + 1):
            p = paper(i)
            pairs.append(
                compare_execution_drift(
                    paper=p,
                    observed=observed(
                        p,
                        name=f"reference-{i}",
                        observation_class="REFERENCE_OBSERVATION",
                    ),
                    policy=POLICY,
                )
            )
        window = build_drift_window(pairs=pairs, policy=POLICY)
        self.assertEqual(window.claim_scope, "REFERENCE_ONLY")
        self.assertFalse(window.live_drift_validated)

    def test_broker_certification_never_validates_live_drift(self) -> None:
        p = paper()
        pair = compare_execution_drift(
            paper=p,
            observed=observed(
                p,
                observation_class="BROKER_CERTIFICATION_OBSERVATION",
            ),
            policy=POLICY,
        )
        window = build_drift_window(pairs=(pair,), policy=POLICY)
        self.assertEqual(window.claim_scope, "BROKER_CERTIFICATION_ONLY")
        self.assertFalse(window.live_drift_validated)

    def test_live_validation_requires_minimum_normal_samples(self) -> None:
        pairs = []
        for i in range(1, POLICY.minimum_live_samples + 1):
            p = paper(i)
            pairs.append(
                compare_execution_drift(
                    paper=p,
                    observed=observed(
                        p,
                        name=f"live-{i}",
                        observation_class="LIVE_EXECUTION_OBSERVATION",
                    ),
                    policy=POLICY,
                )
            )
        window = build_drift_window(pairs=pairs, policy=POLICY)
        self.assertEqual(window.claim_scope, "LIVE_OBSERVED")
        self.assertEqual(window.severity, "NORMAL")
        self.assertTrue(window.live_drift_validated)

    def test_live_validation_rejects_insufficient_samples(self) -> None:
        p = paper()
        pair = compare_execution_drift(
            paper=p,
            observed=observed(
                p,
                observation_class="LIVE_EXECUTION_OBSERVATION",
            ),
            policy=POLICY,
        )
        self.assertFalse(
            build_drift_window(pairs=(pair,), policy=POLICY).live_drift_validated
        )

    def test_window_has_zero_authority(self) -> None:
        p = paper()
        pair = compare_execution_drift(paper=p, observed=observed(p), policy=POLICY)
        window = build_drift_window(pairs=(pair,), policy=POLICY)
        self.assertFalse(window.g10_authority)
        self.assertFalse(window.production_readiness_authority)
        self.assertFalse(window.execution_authority)
        self.assertFalse(window.order_routing_authority)
        self.assertFalse(window.p20_started)
        self.assertEqual(window.live_trading, "DISABLED")
        self.assertEqual(window.auto_trading, "DISABLED")


if __name__ == "__main__":
    unittest.main()
