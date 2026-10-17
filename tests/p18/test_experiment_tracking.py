from __future__ import annotations

import unittest

from packages.learning.experiments import (
    ExperimentRegistry,
    ExperimentRun,
    ExperimentSpec,
    ExperimentTrackingError,
)


def spec(name: str = "exp-1") -> ExperimentSpec:
    return ExperimentSpec.create(
        experiment_name=name,
        hypothesis_id="hypothesis-1",
        dataset_id="a" * 64,
        code_sha256="b" * 64,
        strategy_id="strategy-alpha",
        strategy_version="1.0.0",
        model_id="model-alpha",
        model_version="1.0.0",
        parameters={"lr":"0.0100","depth":"4"},
    )


def run(experiment_id: str, name: str = "run-1") -> ExperimentRun:
    return ExperimentRun.create(
        run_name=name,
        experiment_id=experiment_id,
        started_at_ns=1000,
        completed_at_ns=2000,
        metrics={"sharpe":"1.2500","loss":"0.050"},
        artifact_sha256="c" * 64,
    )


class TestExperimentTracking(unittest.TestCase):
    def test_deterministic_identities_and_snapshot(self) -> None:
        a, b = ExperimentRegistry(), ExperimentRegistry()
        sa, sb = spec(), spec()
        ea, eb = a.register_experiment(sa), b.register_experiment(sb)
        self.assertEqual(ea, eb)
        ra, rb = a.register_run(run(ea)), b.register_run(run(eb))
        self.assertEqual(ra, rb)
        self.assertEqual(a.snapshot().snapshot_id, b.snapshot().snapshot_id)

    def test_numeric_canonicalization(self) -> None:
        first = spec()
        second = ExperimentSpec.create(
            experiment_name="exp-1",
            hypothesis_id="hypothesis-1",
            dataset_id="a"*64,
            code_sha256="b"*64,
            strategy_id="strategy-alpha",
            strategy_version="1.0.0",
            model_id="model-alpha",
            model_version="1.0.0",
            parameters={"depth":"4.0","lr":"0.01"},
        )
        self.assertEqual(first.experiment_id, second.experiment_id)

    def test_duplicate_experiment_name_fails_closed(self) -> None:
        registry=ExperimentRegistry()
        registry.register_experiment(spec())
        with self.assertRaisesRegex(ExperimentTrackingError,"experiment name"):
            registry.register_experiment(spec())

    def test_unknown_experiment_run_fails_closed(self) -> None:
        with self.assertRaisesRegex(ExperimentTrackingError,"unknown experiment"):
            ExperimentRegistry().register_run(run("d"*64))

    def test_duplicate_run_name_fails_closed(self) -> None:
        registry=ExperimentRegistry()
        eid=registry.register_experiment(spec())
        registry.register_run(run(eid))
        with self.assertRaisesRegex(ExperimentTrackingError,"run name"):
            registry.register_run(run(eid))

    def test_authority_boundary(self) -> None:
        snapshot=ExperimentRegistry().snapshot()
        self.assertFalse(snapshot.training_execution_authority)
        self.assertFalse(snapshot.retraining_authority)
        self.assertFalse(snapshot.promotion_authority)
        self.assertFalse(snapshot.broker_exchange_routing)
        self.assertFalse(snapshot.automatic_live_promotion)
        self.assertEqual(snapshot.live_trading,"DISABLED")
        self.assertEqual(snapshot.auto_trading,"DISABLED")


if __name__ == "__main__":
    unittest.main()
