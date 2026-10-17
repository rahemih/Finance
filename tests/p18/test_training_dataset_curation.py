from __future__ import annotations

from dataclasses import replace
import unittest

from packages.learning.dataset_curation import (
    TrainingDatasetCurationError,
    TrainingDatasetSpec,
    curate_training_dataset,
)
from packages.learning.journal import (
    DecisionJournalEntry,
    OutcomeJournalEntry,
)


def spec() -> TrainingDatasetSpec:
    return TrainingDatasetSpec(
        dataset_name="demo-learning-v1",
        source_journal_root_id="f" * 64,
        outcome_definition_id="return-bps",
        outcome_definition_version="1.0.0",
        train_end_ns=3000,
        validation_end_ns=6000,
        dataset_cutoff_ns=10000,
    )


def decision(
    decision_id: str,
    sequence: int,
    decision_time_ns: int,
    *,
    asset_id: str = "BTC-USD",
) -> DecisionJournalEntry:
    return DecisionJournalEntry(
        decision_id=decision_id,
        session_spec_id="a" * 64,
        session_state_id="b" * 64,
        sequence=sequence,
        decision_time_ns=decision_time_ns,
        asset_id=asset_id,
        quantity_delta="1",
        strategy_id="strategy-alpha",
        strategy_version="1.0.0",
        model_id="model-alpha",
        model_version="2.0.0",
        signal_id=f"signal-{sequence}",
        risk_decision_id=f"risk-{sequence}",
        firewall_decision_id=f"firewall-{sequence}",
        market_evidence_sha256="c" * 64,
    )


def outcome(
    entry: DecisionJournalEntry,
    *,
    outcome_id: str,
    observed_at_ns: int,
    value: str = "125",
    definition_id: str = "return-bps",
    definition_version: str = "1.0.0",
) -> OutcomeJournalEntry:
    return OutcomeJournalEntry(
        outcome_id=outcome_id,
        decision_record_id=entry.record_id,
        observed_at_ns=observed_at_ns,
        outcome_definition_id=definition_id,
        outcome_definition_version=definition_version,
        outcome_value=value,
        outcome_evidence_sha256="d" * 64,
    )


class TestTrainingDatasetCuration(unittest.TestCase):
    def test_deterministic_temporal_splits_and_manifest(self) -> None:
        train = decision("d-train", 1, 1000)
        validation = decision("d-validation", 2, 4000)
        test = decision("d-test", 3, 8000)
        decisions = (test, train, validation)
        outcomes = (
            outcome(train, outcome_id="o-train", observed_at_ns=2000),
            outcome(
                validation,
                outcome_id="o-validation",
                observed_at_ns=5000,
            ),
            outcome(test, outcome_id="o-test", observed_at_ns=9000),
        )

        first = curate_training_dataset(
            spec=spec(),
            decisions=decisions,
            outcomes=outcomes,
        )
        second = curate_training_dataset(
            spec=spec(),
            decisions=decisions,
            outcomes=outcomes,
        )

        self.assertEqual(first.manifest.dataset_id, second.manifest.dataset_id)
        self.assertEqual(
            tuple(row.row_id for row in first.rows),
            tuple(row.row_id for row in second.rows),
        )
        self.assertEqual(
            tuple(row.split for row in first.rows),
            ("TRAIN", "VALIDATION", "TEST"),
        )
        self.assertEqual(len(first.manifest.train_row_ids), 1)
        self.assertEqual(len(first.manifest.validation_row_ids), 1)
        self.assertEqual(len(first.manifest.test_row_ids), 1)

    def test_label_after_split_cutoff_is_excluded(self) -> None:
        train = decision("d-train", 1, 1000)
        curated = curate_training_dataset(
            spec=spec(),
            decisions=(train,),
            outcomes=(
                outcome(
                    train,
                    outcome_id="o-train",
                    observed_at_ns=3500,
                ),
            ),
        )
        self.assertEqual(curated.rows, ())
        self.assertEqual(
            curated.manifest.exclusions[0].reason,
            "TRAIN_LABEL_NOT_AVAILABLE_BY_SPLIT_CUTOFF",
        )

    def test_future_outcome_after_dataset_cutoff_is_excluded(self) -> None:
        test = decision("d-test", 1, 8000)
        curated = curate_training_dataset(
            spec=spec(),
            decisions=(test,),
            outcomes=(
                outcome(
                    test,
                    outcome_id="o-test",
                    observed_at_ns=11000,
                ),
            ),
        )
        self.assertEqual(curated.rows, ())
        self.assertEqual(
            curated.manifest.exclusions[0].reason,
            "OUTCOME_AFTER_DATASET_CUTOFF",
        )

    def test_decision_after_dataset_cutoff_is_excluded(self) -> None:
        future = decision("d-future", 1, 11000)
        curated = curate_training_dataset(
            spec=spec(),
            decisions=(future,),
            outcomes=(),
        )
        self.assertEqual(curated.rows, ())
        self.assertEqual(
            curated.manifest.exclusions[0].reason,
            "DECISION_AFTER_DATASET_CUTOFF",
        )

    def test_missing_outcome_is_excluded(self) -> None:
        entry = decision("d-missing", 1, 1000)
        curated = curate_training_dataset(
            spec=spec(),
            decisions=(entry,),
            outcomes=(),
        )
        self.assertEqual(curated.rows, ())
        self.assertEqual(
            curated.manifest.exclusions[0].reason,
            "MISSING_OUTCOME",
        )

    def test_unknown_outcome_fails_closed(self) -> None:
        known = decision("d-known", 1, 1000)
        unknown = decision("d-unknown", 2, 2000)
        with self.assertRaisesRegex(
            TrainingDatasetCurationError,
            "unknown decision",
        ):
            curate_training_dataset(
                spec=spec(),
                decisions=(known,),
                outcomes=(
                    outcome(
                        unknown,
                        outcome_id="o-unknown",
                        observed_at_ns=2500,
                    ),
                ),
            )

    def test_duplicate_decision_identity_fails_closed(self) -> None:
        first = decision("same", 1, 1000)
        second = replace(first, sequence=2, decision_time_ns=1500)
        with self.assertRaisesRegex(
            TrainingDatasetCurationError,
            "duplicate or conflicting decision",
        ):
            curate_training_dataset(
                spec=spec(),
                decisions=(first, second),
                outcomes=(),
            )

    def test_multiple_outcomes_for_one_decision_fail_closed(self) -> None:
        entry = decision("d-1", 1, 1000)
        with self.assertRaisesRegex(
            TrainingDatasetCurationError,
            "multiple outcomes",
        ):
            curate_training_dataset(
                spec=spec(),
                decisions=(entry,),
                outcomes=(
                    outcome(
                        entry,
                        outcome_id="o-1",
                        observed_at_ns=2000,
                    ),
                    outcome(
                        entry,
                        outcome_id="o-2",
                        observed_at_ns=2500,
                    ),
                ),
            )

    def test_outcome_definition_mismatch_fails_closed(self) -> None:
        entry = decision("d-1", 1, 1000)
        with self.assertRaisesRegex(
            TrainingDatasetCurationError,
            "outcome definition",
        ):
            curate_training_dataset(
                spec=spec(),
                decisions=(entry,),
                outcomes=(
                    outcome(
                        entry,
                        outcome_id="o-1",
                        observed_at_ns=2000,
                        definition_version="2.0.0",
                    ),
                ),
            )

    def test_outcome_before_decision_fails_closed(self) -> None:
        entry = decision("d-1", 1, 2000)
        with self.assertRaisesRegex(
            TrainingDatasetCurationError,
            "before decision",
        ):
            curate_training_dataset(
                spec=spec(),
                decisions=(entry,),
                outcomes=(
                    outcome(
                        entry,
                        outcome_id="o-1",
                        observed_at_ns=1999,
                    ),
                ),
            )

    def test_exact_lineage_is_preserved(self) -> None:
        entry = decision("d-1", 1, 1000, asset_id="ETH-USD")
        curated = curate_training_dataset(
            spec=spec(),
            decisions=(entry,),
            outcomes=(
                outcome(
                    entry,
                    outcome_id="o-1",
                    observed_at_ns=2000,
                ),
            ),
        )
        row = curated.rows[0]
        self.assertEqual(row.decision_record_id, entry.record_id)
        self.assertEqual(row.asset_id, "ETH-USD")
        self.assertEqual(row.strategy_id, "strategy-alpha")
        self.assertEqual(row.strategy_version, "1.0.0")
        self.assertEqual(row.model_id, "model-alpha")
        self.assertEqual(row.model_version, "2.0.0")
        self.assertEqual(row.signal_id, "signal-1")
        self.assertEqual(row.risk_decision_id, "risk-1")
        self.assertEqual(row.firewall_decision_id, "firewall-1")
        self.assertEqual(row.market_evidence_sha256, "c" * 64)

    def test_no_experiment_training_or_live_authority(self) -> None:
        entry = decision("d-1", 1, 1000)
        manifest = curate_training_dataset(
            spec=spec(),
            decisions=(entry,),
            outcomes=(
                outcome(
                    entry,
                    outcome_id="o-1",
                    observed_at_ns=2000,
                ),
            ),
        ).manifest
        self.assertFalse(manifest.experiment_authority)
        self.assertFalse(manifest.training_execution_authority)
        self.assertFalse(manifest.retraining_authority)
        self.assertFalse(manifest.broker_exchange_routing)
        self.assertFalse(manifest.automatic_live_promotion)
        self.assertEqual(manifest.live_trading, "DISABLED")
        self.assertEqual(manifest.auto_trading, "DISABLED")


if __name__ == "__main__":
    unittest.main()
