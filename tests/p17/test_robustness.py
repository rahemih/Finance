from __future__ import annotations

from dataclasses import replace
import unittest

from quant.backtesting.robustness import (
    MonteCarloSpec,
    RobustnessError,
    SensitivityVariant,
    StressScenario,
    evaluate_robustness,
)


WALK_FORWARD = "a" * 64
SEED = "b" * 64


def monte(**overrides: object) -> MonteCarloSpec:
    values: dict[str, object] = {
        "seed_sha256": SEED,
        "path_count": 16,
        "path_length": 8,
        "block_size": 2,
    }
    values.update(overrides)
    return MonteCarloSpec(**values)  # type: ignore[arg-type]


def stresses() -> tuple[StressScenario, ...]:
    return (
        StressScenario("cost-spike", 0, 25),
        StressScenario("market-shock", 100, 0),
    )


def sensitivities() -> tuple[SensitivityVariant, ...]:
    return (
        SensitivityVariant("base-near", "c" * 64, 180),
        SensitivityVariant("looser", "d" * 64, 120),
        SensitivityVariant("tighter", "e" * 64, 150),
    )


def evaluate(
    *,
    spec: MonteCarloSpec | None = None,
    scenarios: tuple[StressScenario, ...] | None = None,
    variants: tuple[SensitivityVariant, ...] | None = None,
):
    return evaluate_robustness(
        walk_forward_certificate_id=WALK_FORWARD,
        oos_return_bps=(100, -40, 70, -20, 55, 15, -35, 90),
        monte_carlo=spec or monte(),
        baseline_metric_bps=175,
        stress_scenarios=scenarios or stresses(),
        sensitivity_variants=variants or sensitivities(),
    )


class RobustnessTests(unittest.TestCase):
    def test_deterministic_certificate(self) -> None:
        left = evaluate()
        right = evaluate()
        self.assertEqual(left.certificate_id, right.certificate_id)
        self.assertEqual(left.status, "ROBUSTNESS_EVALUATED")
        self.assertFalse(left.profitability_claim_authority)
        self.assertFalse(left.candidate_selection_authority)
        self.assertFalse(left.g9_authority)
        self.assertFalse(left.execution_authority)
        self.assertFalse(left.order_routing_authority)

    def test_input_order_for_scenarios_and_variants_is_canonical(self) -> None:
        left = evaluate()
        right = evaluate(
            scenarios=tuple(reversed(stresses())),
            variants=tuple(reversed(sensitivities())),
        )
        self.assertEqual(left.certificate_id, right.certificate_id)

    def test_changed_seed_changes_certificate(self) -> None:
        left = evaluate()
        right = evaluate(spec=replace(monte(), seed_sha256="f" * 64))
        self.assertNotEqual(left.certificate_id, right.certificate_id)

    def test_stress_is_explicit_and_adverse(self) -> None:
        result = evaluate()
        by_id = {item.scenario_id: item for item in result.stress_diagnostics}
        self.assertLess(
            by_id["market-shock"].terminal_return_bps,
            by_id["cost-spike"].terminal_return_bps,
        )

    def test_sensitivity_diagnostics(self) -> None:
        result = evaluate()
        self.assertEqual(result.sensitivity_min_metric_bps, 120)
        self.assertEqual(result.sensitivity_max_metric_bps, 180)
        self.assertEqual(result.sensitivity_dispersion_bps, 60)
        self.assertEqual(result.sensitivity_worst_degradation_bps, 55)

    def test_invalid_oos_return_fails_closed(self) -> None:
        with self.assertRaises(RobustnessError):
            evaluate_robustness(
                walk_forward_certificate_id=WALK_FORWARD,
                oos_return_bps=(10, -10_000),
                monte_carlo=monte(),
                baseline_metric_bps=1,
                stress_scenarios=stresses(),
                sensitivity_variants=sensitivities(),
            )

    def test_invalid_monte_carlo_spec_fails_closed(self) -> None:
        with self.assertRaises(RobustnessError):
            monte(path_count=0)
        with self.assertRaises(RobustnessError):
            monte(seed_sha256="bad")
        with self.assertRaises(RobustnessError):
            evaluate(spec=monte(block_size=99))

    def test_monte_carlo_safety_cap(self) -> None:
        with self.assertRaises(RobustnessError):
            monte(path_count=1001, path_length=1000)

    def test_duplicate_scenario_and_variant_fail_closed(self) -> None:
        scenario = StressScenario("same", 1, 1)
        with self.assertRaises(RobustnessError):
            evaluate(scenarios=(scenario, scenario))
        variant = SensitivityVariant("same", "1" * 64, 1)
        with self.assertRaises(RobustnessError):
            evaluate(variants=(variant, variant))

    def test_duplicate_parameter_set_fails_closed(self) -> None:
        with self.assertRaises(RobustnessError):
            evaluate(
                variants=(
                    SensitivityVariant("v1", "1" * 64, 1),
                    SensitivityVariant("v2", "1" * 64, 2),
                )
            )


if __name__ == "__main__":
    unittest.main()
