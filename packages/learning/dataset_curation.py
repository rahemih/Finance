from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from typing import Sequence

from packages.learning.journal import (
    DecisionJournalEntry,
    OutcomeJournalEntry,
)


class TrainingDatasetCurationError(ValueError):
    """P18-C deterministic training-dataset curation invariant failure."""


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$")
_SPLITS = ("TRAIN", "VALIDATION", "TEST")


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _safe_id(value: str, *, field: str) -> str:
    parsed = value.strip()
    if _SAFE_ID.fullmatch(parsed) is None:
        raise TrainingDatasetCurationError(
            f"{field} contains unsafe characters"
        )
    return parsed


def _sha256_text(value: str, *, field: str) -> str:
    parsed = value.strip().lower()
    if _SHA256.fullmatch(parsed) is None:
        raise TrainingDatasetCurationError(
            f"{field} must be lowercase SHA-256"
        )
    return parsed


def _finite_decimal(value: str, *, field: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise TrainingDatasetCurationError(
            f"{field} must be a decimal string"
        ) from exc
    if not parsed.is_finite():
        raise TrainingDatasetCurationError(f"{field} must be finite")
    return parsed


def _decimal_text(value: Decimal) -> str:
    if value == 0:
        return "0"
    normalized = value.normalize()
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


@dataclass(frozen=True, slots=True)
class TrainingDatasetSpec:
    dataset_name: str
    source_journal_root_id: str
    outcome_definition_id: str
    outcome_definition_version: str
    train_end_ns: int
    validation_end_ns: int
    dataset_cutoff_ns: int

    def __post_init__(self) -> None:
        _safe_id(self.dataset_name, field="dataset_name")
        _sha256_text(
            self.source_journal_root_id,
            field="source_journal_root_id",
        )
        _safe_id(
            self.outcome_definition_id,
            field="outcome_definition_id",
        )
        _safe_id(
            self.outcome_definition_version,
            field="outcome_definition_version",
        )
        if min(
            self.train_end_ns,
            self.validation_end_ns,
            self.dataset_cutoff_ns,
        ) < 0:
            raise TrainingDatasetCurationError(
                "dataset time boundaries must be non-negative"
            )
        if not (
            self.train_end_ns
            < self.validation_end_ns
            < self.dataset_cutoff_ns
        ):
            raise TrainingDatasetCurationError(
                "require train_end_ns < validation_end_ns < dataset_cutoff_ns"
            )

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "dataset_name": self.dataset_name,
            "source_journal_root_id": self.source_journal_root_id,
            "outcome_definition_id": self.outcome_definition_id,
            "outcome_definition_version": self.outcome_definition_version,
            "train_end_ns": self.train_end_ns,
            "validation_end_ns": self.validation_end_ns,
            "dataset_cutoff_ns": self.dataset_cutoff_ns,
        }

    @property
    def spec_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class CuratedTrainingRow:
    decision_record_id: str
    outcome_record_id: str
    split: str
    decision_id: str
    decision_time_ns: int
    outcome_observed_at_ns: int
    asset_id: str
    quantity_delta: str
    strategy_id: str
    strategy_version: str
    model_id: str
    model_version: str
    signal_id: str
    risk_decision_id: str
    firewall_decision_id: str
    market_evidence_sha256: str
    outcome_definition_id: str
    outcome_definition_version: str
    outcome_value: str
    outcome_evidence_sha256: str

    def __post_init__(self) -> None:
        _sha256_text(
            self.decision_record_id,
            field="decision_record_id",
        )
        _sha256_text(
            self.outcome_record_id,
            field="outcome_record_id",
        )
        if self.split not in _SPLITS:
            raise TrainingDatasetCurationError("invalid split")
        _safe_id(self.decision_id, field="decision_id")
        if self.decision_time_ns < 0 or self.outcome_observed_at_ns < 0:
            raise TrainingDatasetCurationError(
                "row timestamps must be non-negative"
            )
        if self.outcome_observed_at_ns < self.decision_time_ns:
            raise TrainingDatasetCurationError(
                "outcome observed before decision"
            )
        _safe_id(self.asset_id, field="asset_id")
        _finite_decimal(self.quantity_delta, field="quantity_delta")
        _safe_id(self.strategy_id, field="strategy_id")
        _safe_id(self.strategy_version, field="strategy_version")
        _safe_id(self.model_id, field="model_id")
        _safe_id(self.model_version, field="model_version")
        _safe_id(self.signal_id, field="signal_id")
        _safe_id(self.risk_decision_id, field="risk_decision_id")
        _safe_id(self.firewall_decision_id, field="firewall_decision_id")
        _sha256_text(
            self.market_evidence_sha256,
            field="market_evidence_sha256",
        )
        _safe_id(
            self.outcome_definition_id,
            field="outcome_definition_id",
        )
        _safe_id(
            self.outcome_definition_version,
            field="outcome_definition_version",
        )
        _finite_decimal(self.outcome_value, field="outcome_value")
        _sha256_text(
            self.outcome_evidence_sha256,
            field="outcome_evidence_sha256",
        )

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "decision_record_id": self.decision_record_id,
            "outcome_record_id": self.outcome_record_id,
            "split": self.split,
            "decision_id": self.decision_id,
            "decision_time_ns": self.decision_time_ns,
            "outcome_observed_at_ns": self.outcome_observed_at_ns,
            "asset_id": self.asset_id,
            "quantity_delta": _decimal_text(
                _finite_decimal(
                    self.quantity_delta,
                    field="quantity_delta",
                )
            ),
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "signal_id": self.signal_id,
            "risk_decision_id": self.risk_decision_id,
            "firewall_decision_id": self.firewall_decision_id,
            "market_evidence_sha256": self.market_evidence_sha256,
            "outcome_definition_id": self.outcome_definition_id,
            "outcome_definition_version": self.outcome_definition_version,
            "outcome_value": _decimal_text(
                _finite_decimal(
                    self.outcome_value,
                    field="outcome_value",
                )
            ),
            "outcome_evidence_sha256": self.outcome_evidence_sha256,
        }

    @property
    def row_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class DatasetExclusion:
    decision_record_id: str
    reason: str

    def __post_init__(self) -> None:
        _sha256_text(
            self.decision_record_id,
            field="decision_record_id",
        )
        _safe_id(self.reason, field="reason")

    def payload(self) -> dict[str, object]:
        return {
            "decision_record_id": self.decision_record_id,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class TrainingDatasetManifest:
    spec_id: str
    row_ids: tuple[str, ...]
    train_row_ids: tuple[str, ...]
    validation_row_ids: tuple[str, ...]
    test_row_ids: tuple[str, ...]
    exclusions: tuple[DatasetExclusion, ...]
    experiment_authority: bool = False
    training_execution_authority: bool = False
    retraining_authority: bool = False
    broker_exchange_routing: bool = False
    automatic_live_promotion: bool = False
    live_trading: str = "DISABLED"
    auto_trading: str = "DISABLED"

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P18C_TRAINING_DATASET_MANIFEST",
            "spec_id": self.spec_id,
            "row_ids": list(self.row_ids),
            "train_row_ids": list(self.train_row_ids),
            "validation_row_ids": list(self.validation_row_ids),
            "test_row_ids": list(self.test_row_ids),
            "exclusions": [
                item.payload() for item in self.exclusions
            ],
            "experiment_authority": self.experiment_authority,
            "training_execution_authority": (
                self.training_execution_authority
            ),
            "retraining_authority": self.retraining_authority,
            "broker_exchange_routing": self.broker_exchange_routing,
            "automatic_live_promotion": self.automatic_live_promotion,
            "live_trading": self.live_trading,
            "auto_trading": self.auto_trading,
        }

    @property
    def dataset_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class CuratedTrainingDataset:
    rows: tuple[CuratedTrainingRow, ...]
    manifest: TrainingDatasetManifest


def _split_for(
    decision_time_ns: int,
    spec: TrainingDatasetSpec,
) -> tuple[str, int]:
    if decision_time_ns <= spec.train_end_ns:
        return "TRAIN", spec.train_end_ns
    if decision_time_ns <= spec.validation_end_ns:
        return "VALIDATION", spec.validation_end_ns
    return "TEST", spec.dataset_cutoff_ns


def curate_training_dataset(
    *,
    spec: TrainingDatasetSpec,
    decisions: Sequence[DecisionJournalEntry],
    outcomes: Sequence[OutcomeJournalEntry],
) -> CuratedTrainingDataset:
    decision_by_record: dict[str, DecisionJournalEntry] = {}
    decision_ids: set[str] = set()
    for decision in decisions:
        if decision.record_id in decision_by_record:
            raise TrainingDatasetCurationError(
                "duplicate decision record identity"
            )
        if decision.decision_id in decision_ids:
            raise TrainingDatasetCurationError(
                "duplicate or conflicting decision identity"
            )
        decision_by_record[decision.record_id] = decision
        decision_ids.add(decision.decision_id)

    outcome_by_decision: dict[str, OutcomeJournalEntry] = {}
    outcome_ids: set[str] = set()
    outcome_record_ids: set[str] = set()
    for outcome in outcomes:
        if outcome.decision_record_id not in decision_by_record:
            raise TrainingDatasetCurationError(
                "outcome references unknown decision record"
            )
        if outcome.outcome_id in outcome_ids:
            raise TrainingDatasetCurationError(
                "duplicate or conflicting outcome identity"
            )
        if outcome.record_id in outcome_record_ids:
            raise TrainingDatasetCurationError(
                "duplicate outcome record identity"
            )
        if outcome.decision_record_id in outcome_by_decision:
            raise TrainingDatasetCurationError(
                "conflicting multiple outcomes for one decision"
            )
        if (
            outcome.outcome_definition_id
            != spec.outcome_definition_id
            or outcome.outcome_definition_version
            != spec.outcome_definition_version
        ):
            raise TrainingDatasetCurationError(
                "outcome definition does not match dataset spec"
            )
        decision = decision_by_record[outcome.decision_record_id]
        if outcome.observed_at_ns < decision.decision_time_ns:
            raise TrainingDatasetCurationError(
                "outcome observed before decision"
            )
        outcome_by_decision[outcome.decision_record_id] = outcome
        outcome_ids.add(outcome.outcome_id)
        outcome_record_ids.add(outcome.record_id)

    rows: list[CuratedTrainingRow] = []
    exclusions: list[DatasetExclusion] = []
    seen_row_decisions: set[str] = set()

    ordered_decisions = sorted(
        decisions,
        key=lambda item: (
            item.decision_time_ns,
            item.sequence,
            item.record_id,
        ),
    )
    for decision in ordered_decisions:
        if decision.decision_time_ns > spec.dataset_cutoff_ns:
            exclusions.append(
                DatasetExclusion(
                    decision.record_id,
                    "DECISION_AFTER_DATASET_CUTOFF",
                )
            )
            continue

        outcome = outcome_by_decision.get(decision.record_id)
        if outcome is None:
            exclusions.append(
                DatasetExclusion(
                    decision.record_id,
                    "MISSING_OUTCOME",
                )
            )
            continue
        if outcome.observed_at_ns > spec.dataset_cutoff_ns:
            exclusions.append(
                DatasetExclusion(
                    decision.record_id,
                    "OUTCOME_AFTER_DATASET_CUTOFF",
                )
            )
            continue

        split, split_cutoff_ns = _split_for(
            decision.decision_time_ns,
            spec,
        )
        if outcome.observed_at_ns > split_cutoff_ns:
            exclusions.append(
                DatasetExclusion(
                    decision.record_id,
                    f"{split}_LABEL_NOT_AVAILABLE_BY_SPLIT_CUTOFF",
                )
            )
            continue
        if decision.record_id in seen_row_decisions:
            raise TrainingDatasetCurationError(
                "one decision cannot appear in multiple splits"
            )

        row = CuratedTrainingRow(
            decision_record_id=decision.record_id,
            outcome_record_id=outcome.record_id,
            split=split,
            decision_id=decision.decision_id,
            decision_time_ns=decision.decision_time_ns,
            outcome_observed_at_ns=outcome.observed_at_ns,
            asset_id=decision.asset_id,
            quantity_delta=decision.quantity_delta,
            strategy_id=decision.strategy_id,
            strategy_version=decision.strategy_version,
            model_id=decision.model_id,
            model_version=decision.model_version,
            signal_id=decision.signal_id,
            risk_decision_id=decision.risk_decision_id,
            firewall_decision_id=decision.firewall_decision_id,
            market_evidence_sha256=decision.market_evidence_sha256,
            outcome_definition_id=outcome.outcome_definition_id,
            outcome_definition_version=(
                outcome.outcome_definition_version
            ),
            outcome_value=outcome.outcome_value,
            outcome_evidence_sha256=outcome.outcome_evidence_sha256,
        )
        rows.append(row)
        seen_row_decisions.add(decision.record_id)

    row_ids = tuple(item.row_id for item in rows)
    train_ids = tuple(
        item.row_id for item in rows if item.split == "TRAIN"
    )
    validation_ids = tuple(
        item.row_id for item in rows if item.split == "VALIDATION"
    )
    test_ids = tuple(
        item.row_id for item in rows if item.split == "TEST"
    )
    if len(row_ids) != len(set(row_ids)):
        raise TrainingDatasetCurationError("duplicate curated row identity")

    manifest = TrainingDatasetManifest(
        spec_id=spec.spec_id,
        row_ids=row_ids,
        train_row_ids=train_ids,
        validation_row_ids=validation_ids,
        test_row_ids=test_ids,
        exclusions=tuple(exclusions),
    )
    return CuratedTrainingDataset(
        rows=tuple(rows),
        manifest=manifest,
    )
