#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from packages.learning.dataset_curation import (
    TrainingDatasetSpec,
    curate_training_dataset,
)
from packages.learning.journal import (
    DecisionJournalEntry,
    OutcomeJournalEntry,
)


def decision(
    decision_id: str,
    sequence: int,
    decision_time_ns: int,
) -> DecisionJournalEntry:
    return DecisionJournalEntry(
        decision_id=decision_id,
        session_spec_id="a" * 64,
        session_state_id="b" * 64,
        sequence=sequence,
        decision_time_ns=decision_time_ns,
        asset_id="BTC-USD",
        quantity_delta="1",
        strategy_id="strategy-alpha",
        strategy_version="1.0.0",
        model_id="model-alpha",
        model_version="1.0.0",
        signal_id=f"signal-{sequence}",
        risk_decision_id=f"risk-{sequence}",
        firewall_decision_id=f"firewall-{sequence}",
        market_evidence_sha256="c" * 64,
    )


def outcome(
    entry: DecisionJournalEntry,
    outcome_id: str,
    observed_at_ns: int,
) -> OutcomeJournalEntry:
    return OutcomeJournalEntry(
        outcome_id=outcome_id,
        decision_record_id=entry.record_id,
        observed_at_ns=observed_at_ns,
        outcome_definition_id="return-bps",
        outcome_definition_version="1.0.0",
        outcome_value="125",
        outcome_evidence_sha256="d" * 64,
    )


def build_evidence() -> dict[str, object]:
    train = decision("ci-train", 1, 1000)
    validation = decision("ci-validation", 2, 4000)
    test = decision("ci-test", 3, 8000)
    unavailable = decision("ci-unavailable", 4, 2500)

    curated = curate_training_dataset(
        spec=TrainingDatasetSpec(
            dataset_name="p18c-ci",
            source_journal_root_id="f" * 64,
            outcome_definition_id="return-bps",
            outcome_definition_version="1.0.0",
            train_end_ns=3000,
            validation_end_ns=6000,
            dataset_cutoff_ns=10000,
        ),
        decisions=(test, unavailable, validation, train),
        outcomes=(
            outcome(train, "ci-o-train", 2000),
            outcome(validation, "ci-o-validation", 5000),
            outcome(test, "ci-o-test", 9000),
            outcome(unavailable, "ci-o-unavailable", 3500),
        ),
    )
    manifest = curated.manifest

    if tuple(row.split for row in curated.rows) != (
        "TRAIN",
        "VALIDATION",
        "TEST",
    ):
        raise RuntimeError("P18-C temporal split assignment failed")
    if len(manifest.exclusions) != 1:
        raise RuntimeError("P18-C expected one deterministic exclusion")
    if (
        manifest.exclusions[0].reason
        != "TRAIN_LABEL_NOT_AVAILABLE_BY_SPLIT_CUTOFF"
    ):
        raise RuntimeError("P18-C split label-availability guard failed")
    if (
        manifest.experiment_authority
        or manifest.training_execution_authority
        or manifest.retraining_authority
    ):
        raise RuntimeError("P18-C exceeded curation authority")
    if manifest.live_trading != "DISABLED":
        raise RuntimeError("P18-C live-trading boundary violated")

    return {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P18C_TRAINING_DATASET_EVIDENCE",
        "task_id": "FIN-P18-WC-001",
        "dataset_id": manifest.dataset_id,
        "spec_id": manifest.spec_id,
        "row_ids": list(manifest.row_ids),
        "train_row_ids": list(manifest.train_row_ids),
        "validation_row_ids": list(manifest.validation_row_ids),
        "test_row_ids": list(manifest.test_row_ids),
        "exclusions": [
            item.payload() for item in manifest.exclusions
        ],
        "experiment_authority": manifest.experiment_authority,
        "training_execution_authority": (
            manifest.training_execution_authority
        ),
        "retraining_authority": manifest.retraining_authority,
        "broker_exchange_routing": manifest.broker_exchange_routing,
        "automatic_live_promotion": manifest.automatic_live_promotion,
        "live_trading": manifest.live_trading,
        "auto_trading": manifest.auto_trading,
        "p18_d_started": False,
        "p19_started": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build_evidence()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"P18C_EVIDENCE=PASS output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
