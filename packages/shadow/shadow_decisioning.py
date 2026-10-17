from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Mapping, cast


class ShadowDecisionError(ValueError):
    """P19-A deterministic shadow-decision invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ShadowDecisionError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ShadowDecisionError(f"{field} must be non-empty text")
    return value.strip()


def _sha256_text(value: object, *, field: str) -> str:
    parsed = _text(value, field=field).lower()
    if len(parsed) != 64 or any(ch not in "0123456789abcdef" for ch in parsed):
        raise ShadowDecisionError(f"{field} must be lowercase SHA-256")
    if len(set(parsed)) < 4:
        raise ShadowDecisionError(f"{field} cannot be a degenerate placeholder identity")
    return parsed


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ShadowDecisionError(f"{field} must be a positive integer")
    return value


def _bps(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 10_000:
        raise ShadowDecisionError(f"{field} must be integer bps in [0, 10000]")
    return value


@dataclass(frozen=True, slots=True)
class ShadowDecisionPolicy:
    signal_actions: tuple[str, ...]
    risk_pass_status: str
    firewall_pass_state: str
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "ShadowDecisionPolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ShadowDecisionError(f"invalid P19-A policy JSON: {exc}") from exc
        raw = _mapping(raw_value, field="policy root")
        expected = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P19A_SHADOW_DECISION_POLICY",
            "task_id": "FIN-P19-WA-001",
            "mode": "DETERMINISTIC_SHADOW_DECISIONING",
            "environment": "SHADOW",
            "authority_ceiling": "SHADOW_ONLY",
            "risk_pass_status": "PASS",
            "firewall_pass_state": "PASS",
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        for key, value in expected.items():
            if raw.get(key) != value:
                raise ShadowDecisionError(f"P19-A policy mismatch: {key}")
        if raw.get("signal_actions") != ["LONG", "SHORT", "WAIT", "NO_TRADE"]:
            raise ShadowDecisionError("invalid P19-A signal action taxonomy")
        required_true = (
            "directional_geometry_required",
            "non_directional_geometry_forbidden",
            "exact_lineage_required",
            "monotonic_event_time_required",
        )
        if any(raw.get(field) is not True for field in required_true):
            raise ShadowDecisionError("P19-A required safety invariant disabled")
        required_false = (
            "future_information_allowed",
            "duplicate_input_allowed",
            "execution_authority",
            "order_routing_authority",
            "broker_exchange_routing",
            "external_order_submission",
            "automatic_live_promotion",
            "p20_started",
        )
        if any(raw.get(field) is not False for field in required_false):
            raise ShadowDecisionError("P19-A authority/safety policy drift")
        return cls(
            signal_actions=("LONG", "SHORT", "WAIT", "NO_TRADE"),
            risk_pass_status="PASS",
            firewall_pass_state="PASS",
            live_trading="DISABLED",
            auto_trading="DISABLED",
        )

    @property
    def policy_id(self) -> str:
        return hashlib.sha256(
            _canonical_bytes(
                {
                    "signal_actions": list(self.signal_actions),
                    "risk_pass_status": self.risk_pass_status,
                    "firewall_pass_state": self.firewall_pass_state,
                    "live_trading": self.live_trading,
                    "auto_trading": self.auto_trading,
                    "authority_ceiling": "SHADOW_ONLY",
                }
            )
        ).hexdigest()


@dataclass(frozen=True, slots=True)
class ShadowDecisionInput:
    asset_id: str
    observed_at_ns: int
    market_available_at_ns: int
    signal_id: str
    signal_as_of_ns: int
    signal_action: str
    empirical_probability_bps: int | None
    overall_uncertainty_bps: int | None
    risk_validation_id: str
    risk_status: str
    risk_scale_bps: int
    firewall_gate_id: str
    firewall_state: str
    strategy_record_id: str
    model_record_id: str
    signal_evidence_sha256: str
    risk_evidence_sha256: str
    firewall_evidence_sha256: str
    quant_evidence_sha256: str
    entry_low_scaled: int | None = None
    entry_high_scaled: int | None = None
    candidate_stop_scaled: int | None = None
    candidate_target_scaled: int | None = None
    price_scale: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "asset_id", _text(self.asset_id, field="asset_id"))
        object.__setattr__(
            self,
            "observed_at_ns",
            _positive_int(self.observed_at_ns, field="observed_at_ns"),
        )
        object.__setattr__(
            self,
            "market_available_at_ns",
            _positive_int(self.market_available_at_ns, field="market_available_at_ns"),
        )
        object.__setattr__(
            self,
            "signal_as_of_ns",
            _positive_int(self.signal_as_of_ns, field="signal_as_of_ns"),
        )
        if self.market_available_at_ns > self.observed_at_ns:
            raise ShadowDecisionError("future market information is forbidden")
        if self.signal_as_of_ns > self.observed_at_ns:
            raise ShadowDecisionError("future signal information is forbidden")
        if self.signal_action not in {"LONG", "SHORT", "WAIT", "NO_TRADE"}:
            raise ShadowDecisionError("unsupported signal_action")
        for field in (
            "signal_id",
            "risk_validation_id",
            "firewall_gate_id",
            "strategy_record_id",
            "model_record_id",
            "signal_evidence_sha256",
            "risk_evidence_sha256",
            "firewall_evidence_sha256",
            "quant_evidence_sha256",
        ):
            object.__setattr__(
                self,
                field,
                _sha256_text(getattr(self, field), field=field),
            )
        if self.empirical_probability_bps is not None:
            object.__setattr__(
                self,
                "empirical_probability_bps",
                _bps(self.empirical_probability_bps, field="empirical_probability_bps"),
            )
        if self.overall_uncertainty_bps is not None:
            object.__setattr__(
                self,
                "overall_uncertainty_bps",
                _bps(self.overall_uncertainty_bps, field="overall_uncertainty_bps"),
            )
        object.__setattr__(
            self,
            "risk_status",
            _text(self.risk_status, field="risk_status"),
        )
        object.__setattr__(
            self,
            "risk_scale_bps",
            _bps(self.risk_scale_bps, field="risk_scale_bps"),
        )
        object.__setattr__(
            self,
            "firewall_state",
            _text(self.firewall_state, field="firewall_state"),
        )
        self._validate_geometry()

    def _validate_geometry(self) -> None:
        fields = (
            self.entry_low_scaled,
            self.entry_high_scaled,
            self.candidate_stop_scaled,
            self.candidate_target_scaled,
            self.price_scale,
        )
        directional = self.signal_action in {"LONG", "SHORT"}
        if directional:
            if any(value is None for value in fields):
                raise ShadowDecisionError("directional signal requires complete price geometry")
            low = _positive_int(self.entry_low_scaled, field="entry_low_scaled")
            high = _positive_int(self.entry_high_scaled, field="entry_high_scaled")
            stop = _positive_int(self.candidate_stop_scaled, field="candidate_stop_scaled")
            target = _positive_int(self.candidate_target_scaled, field="candidate_target_scaled")
            _positive_int(self.price_scale, field="price_scale")
            if low > high:
                raise ShadowDecisionError("entry_low_scaled cannot exceed entry_high_scaled")
            if self.signal_action == "LONG":
                if not stop < low <= high < target:
                    raise ShadowDecisionError("LONG geometry is directionally incoherent")
            elif not target < low <= high < stop:
                raise ShadowDecisionError("SHORT geometry is directionally incoherent")
        elif any(value is not None for value in fields):
            raise ShadowDecisionError("WAIT/NO_TRADE cannot carry directional geometry")

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "asset_id": self.asset_id,
            "observed_at_ns": self.observed_at_ns,
            "market_available_at_ns": self.market_available_at_ns,
            "signal_id": self.signal_id,
            "signal_as_of_ns": self.signal_as_of_ns,
            "signal_action": self.signal_action,
            "empirical_probability_bps": self.empirical_probability_bps,
            "overall_uncertainty_bps": self.overall_uncertainty_bps,
            "risk_validation_id": self.risk_validation_id,
            "risk_status": self.risk_status,
            "risk_scale_bps": self.risk_scale_bps,
            "firewall_gate_id": self.firewall_gate_id,
            "firewall_state": self.firewall_state,
            "strategy_record_id": self.strategy_record_id,
            "model_record_id": self.model_record_id,
            "signal_evidence_sha256": self.signal_evidence_sha256,
            "risk_evidence_sha256": self.risk_evidence_sha256,
            "firewall_evidence_sha256": self.firewall_evidence_sha256,
            "quant_evidence_sha256": self.quant_evidence_sha256,
            "entry_low_scaled": self.entry_low_scaled,
            "entry_high_scaled": self.entry_high_scaled,
            "candidate_stop_scaled": self.candidate_stop_scaled,
            "candidate_target_scaled": self.candidate_target_scaled,
            "price_scale": self.price_scale,
        }

    @property
    def input_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class ShadowDecisionRecord:
    input_id: str
    policy_id: str
    previous_record_id: str | None
    asset_id: str
    observed_at_ns: int
    signal_action: str
    disposition: str
    risk_scale_bps: int
    signal_id: str
    risk_validation_id: str
    firewall_gate_id: str
    strategy_record_id: str
    model_record_id: str
    mode: str = "SHADOW_ONLY"
    execution_authority: bool = False
    order_routing_authority: bool = False
    broker_exchange_routing: bool = False
    external_order_submission: bool = False
    automatic_live_promotion: bool = False
    p20_started: bool = False
    live_trading: str = "DISABLED"
    auto_trading: str = "DISABLED"

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "input_id": self.input_id,
            "policy_id": self.policy_id,
            "previous_record_id": self.previous_record_id,
            "asset_id": self.asset_id,
            "observed_at_ns": self.observed_at_ns,
            "signal_action": self.signal_action,
            "disposition": self.disposition,
            "risk_scale_bps": self.risk_scale_bps,
            "signal_id": self.signal_id,
            "risk_validation_id": self.risk_validation_id,
            "firewall_gate_id": self.firewall_gate_id,
            "strategy_record_id": self.strategy_record_id,
            "model_record_id": self.model_record_id,
            "mode": self.mode,
            "execution_authority": self.execution_authority,
            "order_routing_authority": self.order_routing_authority,
            "broker_exchange_routing": self.broker_exchange_routing,
            "external_order_submission": self.external_order_submission,
            "automatic_live_promotion": self.automatic_live_promotion,
            "p20_started": self.p20_started,
            "live_trading": self.live_trading,
            "auto_trading": self.auto_trading,
        }

    @property
    def record_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class ShadowLedgerSnapshot:
    record_ids: tuple[str, ...]
    last_observed_at_ns: int | None
    mode: str = "SHADOW_ONLY"
    execution_authority: bool = False
    order_routing_authority: bool = False
    p20_started: bool = False
    live_trading: str = "DISABLED"
    auto_trading: str = "DISABLED"

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "record_ids": list(self.record_ids),
            "last_observed_at_ns": self.last_observed_at_ns,
            "mode": self.mode,
            "execution_authority": self.execution_authority,
            "order_routing_authority": self.order_routing_authority,
            "p20_started": self.p20_started,
            "live_trading": self.live_trading,
            "auto_trading": self.auto_trading,
        }

    @property
    def snapshot_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


class ShadowDecisionLedger:
    def __init__(self, policy: ShadowDecisionPolicy) -> None:
        self._policy = policy
        self._records: list[ShadowDecisionRecord] = []
        self._input_ids: set[str] = set()
        self._last_observed_at_ns: int | None = None

    def append(self, decision: ShadowDecisionInput) -> ShadowDecisionRecord:
        if decision.input_id in self._input_ids:
            raise ShadowDecisionError("duplicate shadow input")
        if (
            self._last_observed_at_ns is not None
            and decision.observed_at_ns <= self._last_observed_at_ns
        ):
            raise ShadowDecisionError("shadow decision event time must be strictly increasing")

        if (
            decision.risk_status != self._policy.risk_pass_status
            or decision.risk_scale_bps == 0
        ):
            disposition = "SHADOW_BLOCKED_RISK"
        elif decision.firewall_state != self._policy.firewall_pass_state:
            disposition = "SHADOW_BLOCKED_FIREWALL"
        elif decision.signal_action == "WAIT":
            disposition = "SHADOW_WAIT"
        elif decision.signal_action == "NO_TRADE":
            disposition = "SHADOW_NO_TRADE"
        else:
            disposition = "SHADOW_WOULD_TRADE"

        previous = self._records[-1].record_id if self._records else None
        record = ShadowDecisionRecord(
            input_id=decision.input_id,
            policy_id=self._policy.policy_id,
            previous_record_id=previous,
            asset_id=decision.asset_id,
            observed_at_ns=decision.observed_at_ns,
            signal_action=decision.signal_action,
            disposition=disposition,
            risk_scale_bps=decision.risk_scale_bps,
            signal_id=decision.signal_id,
            risk_validation_id=decision.risk_validation_id,
            firewall_gate_id=decision.firewall_gate_id,
            strategy_record_id=decision.strategy_record_id,
            model_record_id=decision.model_record_id,
            live_trading=self._policy.live_trading,
            auto_trading=self._policy.auto_trading,
        )
        self._records.append(record)
        self._input_ids.add(decision.input_id)
        self._last_observed_at_ns = decision.observed_at_ns
        return record

    @property
    def records(self) -> tuple[ShadowDecisionRecord, ...]:
        return tuple(self._records)

    def snapshot(self) -> ShadowLedgerSnapshot:
        return ShadowLedgerSnapshot(
            record_ids=tuple(record.record_id for record in self._records),
            last_observed_at_ns=self._last_observed_at_ns,
            live_trading=self._policy.live_trading,
            auto_trading=self._policy.auto_trading,
        )
