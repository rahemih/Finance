from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re


class DecisionOutcomeJournalError(ValueError):
    """P18-B immutable Decision / Outcome Journal invariant failure."""


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$")


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
        raise DecisionOutcomeJournalError(f"{field} contains unsafe characters")
    return parsed


def _sha256_text(value: str, *, field: str) -> str:
    parsed = value.strip().lower()
    if _SHA256.fullmatch(parsed) is None:
        raise DecisionOutcomeJournalError(f"{field} must be lowercase SHA-256")
    return parsed


def _finite_decimal(value: str, *, field: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise DecisionOutcomeJournalError(
            f"{field} must be a decimal string"
        ) from exc
    if not parsed.is_finite():
        raise DecisionOutcomeJournalError(f"{field} must be finite")
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
class DecisionJournalEntry:
    decision_id: str
    session_spec_id: str
    session_state_id: str
    sequence: int
    decision_time_ns: int
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

    def __post_init__(self) -> None:
        _safe_id(self.decision_id, field="decision_id")
        _sha256_text(self.session_spec_id, field="session_spec_id")
        _sha256_text(self.session_state_id, field="session_state_id")
        if self.sequence < 0:
            raise DecisionOutcomeJournalError("sequence must be non-negative")
        if self.decision_time_ns < 0:
            raise DecisionOutcomeJournalError(
                "decision_time_ns must be non-negative"
            )
        _safe_id(self.asset_id, field="asset_id")
        if _finite_decimal(self.quantity_delta, field="quantity_delta") == 0:
            raise DecisionOutcomeJournalError(
                "quantity_delta must be non-zero"
            )
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

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "decision_id": self.decision_id,
            "session_spec_id": self.session_spec_id,
            "session_state_id": self.session_state_id,
            "sequence": self.sequence,
            "decision_time_ns": self.decision_time_ns,
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
        }

    @property
    def record_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class OutcomeJournalEntry:
    outcome_id: str
    decision_record_id: str
    observed_at_ns: int
    outcome_definition_id: str
    outcome_definition_version: str
    outcome_value: str
    outcome_evidence_sha256: str

    def __post_init__(self) -> None:
        _safe_id(self.outcome_id, field="outcome_id")
        _sha256_text(self.decision_record_id, field="decision_record_id")
        if self.observed_at_ns < 0:
            raise DecisionOutcomeJournalError(
                "observed_at_ns must be non-negative"
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
            "outcome_id": self.outcome_id,
            "decision_record_id": self.decision_record_id,
            "observed_at_ns": self.observed_at_ns,
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
    def record_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class JournalView:
    as_of_ns: int
    decision_record_ids: tuple[str, ...]
    outcome_record_ids: tuple[str, ...]
    journal_root_id: str
    dataset_curation_authority: bool = False
    training_authority: bool = False
    broker_exchange_routing: bool = False
    automatic_live_promotion: bool = False
    live_trading: str = "DISABLED"
    auto_trading: str = "DISABLED"


class DecisionOutcomeJournal:
    def __init__(self) -> None:
        self._decisions: list[DecisionJournalEntry] = []
        self._decision_by_record: dict[str, DecisionJournalEntry] = {}
        self._decision_ids: set[str] = set()
        self._outcomes: list[OutcomeJournalEntry] = []
        self._outcome_ids: set[str] = set()
        self._last_decision_sequence = -1
        self._last_decision_time_ns = -1
        self._last_outcome_observed_at_ns = -1

    def append_decision(self, entry: DecisionJournalEntry) -> str:
        if entry.decision_id in self._decision_ids:
            raise DecisionOutcomeJournalError(
                "duplicate or conflicting decision identity"
            )
        if entry.record_id in self._decision_by_record:
            raise DecisionOutcomeJournalError(
                "duplicate decision record identity"
            )
        if entry.sequence <= self._last_decision_sequence:
            raise DecisionOutcomeJournalError(
                "decision sequence must increase strictly"
            )
        if entry.decision_time_ns < self._last_decision_time_ns:
            raise DecisionOutcomeJournalError(
                "decision time cannot decrease"
            )

        self._decisions.append(entry)
        self._decision_by_record[entry.record_id] = entry
        self._decision_ids.add(entry.decision_id)
        self._last_decision_sequence = entry.sequence
        self._last_decision_time_ns = entry.decision_time_ns
        return entry.record_id

    def append_outcome(self, entry: OutcomeJournalEntry) -> str:
        if entry.outcome_id in self._outcome_ids:
            raise DecisionOutcomeJournalError(
                "duplicate or conflicting outcome identity"
            )
        decision = self._decision_by_record.get(entry.decision_record_id)
        if decision is None:
            raise DecisionOutcomeJournalError(
                "outcome references unknown decision record"
            )
        if entry.observed_at_ns < decision.decision_time_ns:
            raise DecisionOutcomeJournalError(
                "outcome cannot be observed before decision time"
            )
        if entry.observed_at_ns < self._last_outcome_observed_at_ns:
            raise DecisionOutcomeJournalError(
                "outcome observed time cannot decrease"
            )
        if any(
            item.record_id == entry.record_id
            for item in self._outcomes
        ):
            raise DecisionOutcomeJournalError(
                "duplicate outcome record identity"
            )

        self._outcomes.append(entry)
        self._outcome_ids.add(entry.outcome_id)
        self._last_outcome_observed_at_ns = entry.observed_at_ns
        return entry.record_id

    @property
    def root_id(self) -> str:
        payload = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P18B_JOURNAL_ROOT",
            "decision_record_ids": [
                item.record_id for item in self._decisions
            ],
            "outcome_record_ids": [
                item.record_id for item in self._outcomes
            ],
        }
        return hashlib.sha256(_canonical_bytes(payload)).hexdigest()

    def view_at(self, as_of_ns: int) -> JournalView:
        if as_of_ns < 0:
            raise DecisionOutcomeJournalError(
                "as_of_ns must be non-negative"
            )
        decision_ids = tuple(
            item.record_id
            for item in self._decisions
            if item.decision_time_ns <= as_of_ns
        )
        visible_decisions = set(decision_ids)
        outcome_ids = tuple(
            item.record_id
            for item in self._outcomes
            if (
                item.observed_at_ns <= as_of_ns
                and item.decision_record_id in visible_decisions
            )
        )
        payload = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P18B_JOURNAL_VIEW",
            "as_of_ns": as_of_ns,
            "decision_record_ids": list(decision_ids),
            "outcome_record_ids": list(outcome_ids),
            "journal_root_id": self.root_id,
        }
        view_root = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
        return JournalView(
            as_of_ns=as_of_ns,
            decision_record_ids=decision_ids,
            outcome_record_ids=outcome_ids,
            journal_root_id=view_root,
        )
