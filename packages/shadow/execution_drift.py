from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence, cast


class ExecutionDriftError(ValueError):
    """P19-F deterministic paper/observed execution drift invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ExecutionDriftError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExecutionDriftError(f"{field} must be non-empty text")
    return value.strip()


def _sha(value: object, *, field: str) -> str:
    parsed = _text(value, field=field).lower()
    if len(parsed) != 64 or any(ch not in "0123456789abcdef" for ch in parsed):
        raise ExecutionDriftError(f"{field} must be lowercase SHA-256")
    if len(set(parsed)) < 4:
        raise ExecutionDriftError(f"{field} cannot be degenerate placeholder identity")
    return parsed


def _decimal(value: object, *, field: str) -> Decimal:
    if not isinstance(value, str):
        raise ExecutionDriftError(f"{field} must be decimal text")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ExecutionDriftError(f"{field} must be decimal text") from exc
    if not parsed.is_finite():
        raise ExecutionDriftError(f"{field} must be finite")
    return parsed


def _decimal_text(value: Decimal) -> str:
    if value == 0:
        return "0"
    text = format(value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _positive_decimal(value: object, *, field: str) -> Decimal:
    parsed = _decimal(value, field=field)
    if parsed <= 0:
        raise ExecutionDriftError(f"{field} must be positive")
    return parsed


def _non_negative_decimal(value: object, *, field: str) -> Decimal:
    parsed = _decimal(value, field=field)
    if parsed < 0:
        raise ExecutionDriftError(f"{field} must be non-negative")
    return parsed


def _non_negative_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ExecutionDriftError(f"{field} must be non-negative integer")
    return value


def _positive_int(value: object, *, field: str) -> int:
    parsed = _non_negative_int(value, field=field)
    if parsed == 0:
        raise ExecutionDriftError(f"{field} must be positive integer")
    return parsed


@dataclass(frozen=True, slots=True)
class ExecutionDriftPolicy:
    observation_classes: tuple[str, ...]
    minimum_live_samples: int
    warn_abs_slippage_drift_bps: Decimal
    fail_abs_slippage_drift_bps: Decimal
    warn_fill_ratio_drift_bps: Decimal
    fail_fill_ratio_drift_bps: Decimal
    warn_fee_drift_bps: Decimal
    fail_fee_drift_bps: Decimal
    warn_latency_drift_ns: int
    fail_latency_drift_ns: int
    fill_status_mismatch_is_fail: bool
    live_trading: str = "DISABLED"
    auto_trading: str = "DISABLED"

    @classmethod
    def from_path(cls, path: Path) -> "ExecutionDriftPolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ExecutionDriftError(f"invalid P19-F policy JSON: {exc}") from exc
        raw = _mapping(raw_value, field="policy root")
        expected = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P19F_EXECUTION_DRIFT_POLICY",
            "task_id": "FIN-P19-WF-001",
            "mode": "DETERMINISTIC_PAPER_OBSERVED_EXECUTION_DRIFT",
            "paper_execution_owner": "P19-E",
            "live_observation_owner": "P20-H",
            "broker_certification_owner": "P20-I",
            "canonical_ci_observation_class": "REFERENCE_OBSERVATION",
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        for key, value in expected.items():
            if raw.get(key) != value:
                raise ExecutionDriftError(f"P19-F policy mismatch: {key}")
        classes_raw = raw.get("accepted_observation_classes")
        if not isinstance(classes_raw, list):
            raise ExecutionDriftError("accepted_observation_classes must be a list")
        classes = tuple(
            _text(item, field="accepted_observation_class")
            for item in cast(list[object], classes_raw)
        )
        expected_classes = (
            "REFERENCE_OBSERVATION",
            "BROKER_CERTIFICATION_OBSERVATION",
            "LIVE_EXECUTION_OBSERVATION",
        )
        if classes != expected_classes:
            raise ExecutionDriftError("P19-F observation-class taxonomy drift")

        thresholds = _mapping(raw.get("thresholds"), field="thresholds")
        warn_slippage = _non_negative_decimal(
            thresholds.get("warn_abs_slippage_drift_bps"),
            field="warn_abs_slippage_drift_bps",
        )
        fail_slippage = _non_negative_decimal(
            thresholds.get("fail_abs_slippage_drift_bps"),
            field="fail_abs_slippage_drift_bps",
        )
        warn_fill = _non_negative_decimal(
            thresholds.get("warn_fill_ratio_drift_bps"),
            field="warn_fill_ratio_drift_bps",
        )
        fail_fill = _non_negative_decimal(
            thresholds.get("fail_fill_ratio_drift_bps"),
            field="fail_fill_ratio_drift_bps",
        )
        warn_fee = _non_negative_decimal(
            thresholds.get("warn_fee_drift_bps"),
            field="warn_fee_drift_bps",
        )
        fail_fee = _non_negative_decimal(
            thresholds.get("fail_fee_drift_bps"),
            field="fail_fee_drift_bps",
        )
        warn_latency = _non_negative_int(
            thresholds.get("warn_latency_drift_ns"),
            field="warn_latency_drift_ns",
        )
        fail_latency = _non_negative_int(
            thresholds.get("fail_latency_drift_ns"),
            field="fail_latency_drift_ns",
        )
        if (
            fail_slippage < warn_slippage
            or fail_fill < warn_fill
            or fail_fee < warn_fee
            or fail_latency < warn_latency
        ):
            raise ExecutionDriftError("fail thresholds must not be below warn thresholds")
        if thresholds.get("fill_status_mismatch_is_fail") is not True:
            raise ExecutionDriftError("fill status mismatch must fail closed")

        required_true = (
            "reference_observation_cannot_claim_live_drift",
            "broker_certification_cannot_claim_live_drift",
            "live_claim_requires_live_observation_class",
            "live_claim_requires_minimum_samples",
            "live_claim_requires_normal_severity",
        )
        if any(raw.get(field) is not True for field in required_true):
            raise ExecutionDriftError("P19-F live-claim boundary disabled")
        required_false = (
            "mixed_observation_classes_allowed",
            "canonical_ci_live_drift_validated",
            "g10_authority",
            "production_readiness_authority",
            "execution_authority",
            "order_routing_authority",
            "broker_exchange_routing",
            "p20_started",
        )
        if any(raw.get(field) is not False for field in required_false):
            raise ExecutionDriftError("P19-F authority/claim policy drift")

        minimum_live_samples = _positive_int(
            raw.get("minimum_live_samples"),
            field="minimum_live_samples",
        )
        return cls(
            observation_classes=classes,
            minimum_live_samples=minimum_live_samples,
            warn_abs_slippage_drift_bps=warn_slippage,
            fail_abs_slippage_drift_bps=fail_slippage,
            warn_fill_ratio_drift_bps=warn_fill,
            fail_fill_ratio_drift_bps=fail_fill,
            warn_fee_drift_bps=warn_fee,
            fail_fee_drift_bps=fail_fee,
            warn_latency_drift_ns=warn_latency,
            fail_latency_drift_ns=fail_latency,
            fill_status_mismatch_is_fail=True,
        )

    @property
    def policy_id(self) -> str:
        return hashlib.sha256(
            _canonical_bytes(
                {
                    "observation_classes": list(self.observation_classes),
                    "minimum_live_samples": self.minimum_live_samples,
                    "thresholds": {
                        "warn_abs_slippage_drift_bps": _decimal_text(
                            self.warn_abs_slippage_drift_bps
                        ),
                        "fail_abs_slippage_drift_bps": _decimal_text(
                            self.fail_abs_slippage_drift_bps
                        ),
                        "warn_fill_ratio_drift_bps": _decimal_text(
                            self.warn_fill_ratio_drift_bps
                        ),
                        "fail_fill_ratio_drift_bps": _decimal_text(
                            self.fail_fill_ratio_drift_bps
                        ),
                        "warn_fee_drift_bps": _decimal_text(
                            self.warn_fee_drift_bps
                        ),
                        "fail_fee_drift_bps": _decimal_text(
                            self.fail_fee_drift_bps
                        ),
                        "warn_latency_drift_ns": self.warn_latency_drift_ns,
                        "fail_latency_drift_ns": self.fail_latency_drift_ns,
                        "fill_status_mismatch_is_fail": True,
                    },
                    "live_observation_owner": "P20-H",
                    "broker_certification_owner": "P20-I",
                    "live_trading": self.live_trading,
                    "auto_trading": self.auto_trading,
                }
            )
        ).hexdigest()


_FILL_STATUSES = {"FULL_FILL", "PARTIAL_FILL", "NO_FILL"}
_SIDES = {"BUY", "SELL"}


@dataclass(frozen=True, slots=True)
class PaperExecutionSample:
    digital_twin_result_id: str
    incident_replay_root_id: str
    asset_id: str
    side: str
    decision_time_ns: int
    requested_quantity: str
    filled_quantity: str
    adverse_slippage_bps: str | None
    fee_bps: str
    modeled_latency_ns: int
    fill_status: str
    source_evidence_sha256: str

    def __post_init__(self) -> None:
        for field in (
            "digital_twin_result_id",
            "incident_replay_root_id",
            "source_evidence_sha256",
        ):
            object.__setattr__(self, field, _sha(getattr(self, field), field=field))
        object.__setattr__(self, "asset_id", _text(self.asset_id, field="asset_id"))
        if self.side not in _SIDES:
            raise ExecutionDriftError("unsupported paper side")
        object.__setattr__(
            self,
            "decision_time_ns",
            _positive_int(self.decision_time_ns, field="decision_time_ns"),
        )
        requested = _positive_decimal(self.requested_quantity, field="requested_quantity")
        filled = _non_negative_decimal(self.filled_quantity, field="filled_quantity")
        if filled > requested:
            raise ExecutionDriftError("paper filled quantity cannot exceed requested")
        object.__setattr__(self, "requested_quantity", _decimal_text(requested))
        object.__setattr__(self, "filled_quantity", _decimal_text(filled))
        if self.fill_status not in _FILL_STATUSES:
            raise ExecutionDriftError("unsupported paper fill_status")
        if self.fill_status == "FULL_FILL" and filled != requested:
            raise ExecutionDriftError("FULL_FILL requires filled=requested")
        if self.fill_status == "NO_FILL" and filled != 0:
            raise ExecutionDriftError("NO_FILL requires zero filled quantity")
        if self.fill_status == "PARTIAL_FILL" and not (Decimal(0) < filled < requested):
            raise ExecutionDriftError("PARTIAL_FILL requires 0<filled<requested")
        if filled == 0:
            if self.adverse_slippage_bps is not None:
                raise ExecutionDriftError("NO_FILL paper sample cannot carry slippage")
        else:
            if self.adverse_slippage_bps is None:
                raise ExecutionDriftError("filled paper sample requires slippage")
            object.__setattr__(
                self,
                "adverse_slippage_bps",
                _decimal_text(
                    _decimal(self.adverse_slippage_bps, field="adverse_slippage_bps")
                ),
            )
        object.__setattr__(
            self,
            "fee_bps",
            _decimal_text(_non_negative_decimal(self.fee_bps, field="fee_bps")),
        )
        object.__setattr__(
            self,
            "modeled_latency_ns",
            _non_negative_int(self.modeled_latency_ns, field="modeled_latency_ns"),
        )

    @property
    def fill_ratio_bps(self) -> Decimal:
        return (
            _decimal(self.filled_quantity, field="filled_quantity")
            / _decimal(self.requested_quantity, field="requested_quantity")
            * Decimal(10_000)
        )

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "digital_twin_result_id": self.digital_twin_result_id,
            "incident_replay_root_id": self.incident_replay_root_id,
            "asset_id": self.asset_id,
            "side": self.side,
            "decision_time_ns": self.decision_time_ns,
            "requested_quantity": self.requested_quantity,
            "filled_quantity": self.filled_quantity,
            "adverse_slippage_bps": self.adverse_slippage_bps,
            "fee_bps": self.fee_bps,
            "modeled_latency_ns": self.modeled_latency_ns,
            "fill_status": self.fill_status,
            "source_evidence_sha256": self.source_evidence_sha256,
        }

    @property
    def sample_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class ObservedExecutionSample:
    paper_sample_id: str
    observation_name: str
    observation_class: str
    asset_id: str
    side: str
    observed_at_ns: int
    requested_quantity: str
    filled_quantity: str
    adverse_slippage_bps: str | None
    fee_bps: str
    observed_latency_ns: int
    fill_status: str
    source_evidence_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "paper_sample_id",
            _sha(self.paper_sample_id, field="paper_sample_id"),
        )
        object.__setattr__(
            self,
            "observation_name",
            _text(self.observation_name, field="observation_name"),
        )
        object.__setattr__(
            self,
            "observation_class",
            _text(self.observation_class, field="observation_class"),
        )
        object.__setattr__(self, "asset_id", _text(self.asset_id, field="asset_id"))
        if self.side not in _SIDES:
            raise ExecutionDriftError("unsupported observed side")
        object.__setattr__(
            self,
            "observed_at_ns",
            _positive_int(self.observed_at_ns, field="observed_at_ns"),
        )
        requested = _positive_decimal(self.requested_quantity, field="requested_quantity")
        filled = _non_negative_decimal(self.filled_quantity, field="filled_quantity")
        if filled > requested:
            raise ExecutionDriftError("observed filled quantity cannot exceed requested")
        object.__setattr__(self, "requested_quantity", _decimal_text(requested))
        object.__setattr__(self, "filled_quantity", _decimal_text(filled))
        if self.fill_status not in _FILL_STATUSES:
            raise ExecutionDriftError("unsupported observed fill_status")
        if self.fill_status == "FULL_FILL" and filled != requested:
            raise ExecutionDriftError("observed FULL_FILL requires filled=requested")
        if self.fill_status == "NO_FILL" and filled != 0:
            raise ExecutionDriftError("observed NO_FILL requires zero filled quantity")
        if self.fill_status == "PARTIAL_FILL" and not (Decimal(0) < filled < requested):
            raise ExecutionDriftError(
                "observed PARTIAL_FILL requires 0<filled<requested"
            )
        if filled == 0:
            if self.adverse_slippage_bps is not None:
                raise ExecutionDriftError(
                    "NO_FILL observed sample cannot carry slippage"
                )
        else:
            if self.adverse_slippage_bps is None:
                raise ExecutionDriftError("filled observed sample requires slippage")
            object.__setattr__(
                self,
                "adverse_slippage_bps",
                _decimal_text(
                    _decimal(self.adverse_slippage_bps, field="adverse_slippage_bps")
                ),
            )
        object.__setattr__(
            self,
            "fee_bps",
            _decimal_text(_non_negative_decimal(self.fee_bps, field="fee_bps")),
        )
        object.__setattr__(
            self,
            "observed_latency_ns",
            _non_negative_int(self.observed_latency_ns, field="observed_latency_ns"),
        )
        object.__setattr__(
            self,
            "source_evidence_sha256",
            _sha(self.source_evidence_sha256, field="source_evidence_sha256"),
        )

    @property
    def fill_ratio_bps(self) -> Decimal:
        return (
            _decimal(self.filled_quantity, field="filled_quantity")
            / _decimal(self.requested_quantity, field="requested_quantity")
            * Decimal(10_000)
        )

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "paper_sample_id": self.paper_sample_id,
            "observation_name": self.observation_name,
            "observation_class": self.observation_class,
            "asset_id": self.asset_id,
            "side": self.side,
            "observed_at_ns": self.observed_at_ns,
            "requested_quantity": self.requested_quantity,
            "filled_quantity": self.filled_quantity,
            "adverse_slippage_bps": self.adverse_slippage_bps,
            "fee_bps": self.fee_bps,
            "observed_latency_ns": self.observed_latency_ns,
            "fill_status": self.fill_status,
            "source_evidence_sha256": self.source_evidence_sha256,
        }

    @property
    def observation_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class ExecutionDriftPair:
    paper_sample_id: str
    observation_id: str
    observation_class: str
    decision_time_ns: int
    fill_ratio_drift_bps: str
    slippage_drift_bps: str | None
    abs_slippage_drift_bps: str | None
    slippage_presence_match: bool
    fee_drift_bps: str
    abs_fee_drift_bps: str
    latency_drift_ns: int
    abs_latency_drift_ns: int
    fill_status_match: bool
    severity: str
    g10_authority: bool = False
    production_readiness_authority: bool = False
    execution_authority: bool = False
    order_routing_authority: bool = False
    p20_started: bool = False
    live_trading: str = "DISABLED"
    auto_trading: str = "DISABLED"

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "paper_sample_id": self.paper_sample_id,
            "observation_id": self.observation_id,
            "observation_class": self.observation_class,
            "decision_time_ns": self.decision_time_ns,
            "fill_ratio_drift_bps": self.fill_ratio_drift_bps,
            "slippage_drift_bps": self.slippage_drift_bps,
            "abs_slippage_drift_bps": self.abs_slippage_drift_bps,
            "slippage_presence_match": self.slippage_presence_match,
            "fee_drift_bps": self.fee_drift_bps,
            "abs_fee_drift_bps": self.abs_fee_drift_bps,
            "latency_drift_ns": self.latency_drift_ns,
            "abs_latency_drift_ns": self.abs_latency_drift_ns,
            "fill_status_match": self.fill_status_match,
            "severity": self.severity,
            "g10_authority": self.g10_authority,
            "production_readiness_authority": self.production_readiness_authority,
            "execution_authority": self.execution_authority,
            "order_routing_authority": self.order_routing_authority,
            "p20_started": self.p20_started,
            "live_trading": self.live_trading,
            "auto_trading": self.auto_trading,
        }

    @property
    def pair_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


def compare_execution_drift(
    *,
    paper: PaperExecutionSample,
    observed: ObservedExecutionSample,
    policy: ExecutionDriftPolicy,
) -> ExecutionDriftPair:
    if observed.observation_class not in policy.observation_classes:
        raise ExecutionDriftError("unsupported observed execution class")
    if observed.paper_sample_id != paper.sample_id:
        raise ExecutionDriftError("observed sample does not bind exact paper sample")
    if paper.asset_id != observed.asset_id:
        raise ExecutionDriftError("paper/observed asset mismatch")
    if paper.side != observed.side:
        raise ExecutionDriftError("paper/observed side mismatch")
    if paper.requested_quantity != observed.requested_quantity:
        raise ExecutionDriftError("paper/observed requested quantity mismatch")
    if observed.observed_at_ns < paper.decision_time_ns:
        raise ExecutionDriftError("observed execution cannot precede paper decision")

    fill_ratio_drift = abs(observed.fill_ratio_bps - paper.fill_ratio_bps)
    paper_slippage = (
        None
        if paper.adverse_slippage_bps is None
        else _decimal(paper.adverse_slippage_bps, field="paper.slippage")
    )
    observed_slippage = (
        None
        if observed.adverse_slippage_bps is None
        else _decimal(observed.adverse_slippage_bps, field="observed.slippage")
    )
    slippage_presence_match = (paper_slippage is None) == (observed_slippage is None)
    slippage_drift: Decimal | None = None
    abs_slippage: Decimal | None = None
    if slippage_presence_match and paper_slippage is not None and observed_slippage is not None:
        slippage_drift = observed_slippage - paper_slippage
        abs_slippage = abs(slippage_drift)

    fee_drift = (
        _decimal(observed.fee_bps, field="observed.fee_bps")
        - _decimal(paper.fee_bps, field="paper.fee_bps")
    )
    abs_fee = abs(fee_drift)
    latency_drift = observed.observed_latency_ns - paper.modeled_latency_ns
    abs_latency = abs(latency_drift)
    status_match = paper.fill_status == observed.fill_status

    fail = (
        not slippage_presence_match
        or (policy.fill_status_mismatch_is_fail and not status_match)
        or fill_ratio_drift >= policy.fail_fill_ratio_drift_bps
        or abs_fee >= policy.fail_fee_drift_bps
        or abs_latency >= policy.fail_latency_drift_ns
        or (
            abs_slippage is not None
            and abs_slippage >= policy.fail_abs_slippage_drift_bps
        )
    )
    warn = (
        fill_ratio_drift >= policy.warn_fill_ratio_drift_bps
        or abs_fee >= policy.warn_fee_drift_bps
        or abs_latency >= policy.warn_latency_drift_ns
        or (
            abs_slippage is not None
            and abs_slippage >= policy.warn_abs_slippage_drift_bps
        )
    )
    severity = "FAIL" if fail else ("WARN" if warn else "NORMAL")
    return ExecutionDriftPair(
        paper_sample_id=paper.sample_id,
        observation_id=observed.observation_id,
        observation_class=observed.observation_class,
        decision_time_ns=paper.decision_time_ns,
        fill_ratio_drift_bps=_decimal_text(fill_ratio_drift),
        slippage_drift_bps=(
            None if slippage_drift is None else _decimal_text(slippage_drift)
        ),
        abs_slippage_drift_bps=(
            None if abs_slippage is None else _decimal_text(abs_slippage)
        ),
        slippage_presence_match=slippage_presence_match,
        fee_drift_bps=_decimal_text(fee_drift),
        abs_fee_drift_bps=_decimal_text(abs_fee),
        latency_drift_ns=latency_drift,
        abs_latency_drift_ns=abs_latency,
        fill_status_match=status_match,
        severity=severity,
    )


@dataclass(frozen=True, slots=True)
class ExecutionDriftWindow:
    policy_id: str
    observation_class: str
    claim_scope: str
    pair_ids: tuple[str, ...]
    pairs: tuple[ExecutionDriftPair, ...]
    severity: str
    max_fill_ratio_drift_bps: str
    max_abs_slippage_drift_bps: str | None
    max_abs_fee_drift_bps: str
    max_abs_latency_drift_ns: int
    live_drift_validated: bool
    g10_authority: bool = False
    production_readiness_authority: bool = False
    execution_authority: bool = False
    order_routing_authority: bool = False
    p20_started: bool = False
    live_trading: str = "DISABLED"
    auto_trading: str = "DISABLED"

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "policy_id": self.policy_id,
            "observation_class": self.observation_class,
            "claim_scope": self.claim_scope,
            "pair_ids": list(self.pair_ids),
            "pairs": [pair.payload() for pair in self.pairs],
            "severity": self.severity,
            "max_fill_ratio_drift_bps": self.max_fill_ratio_drift_bps,
            "max_abs_slippage_drift_bps": self.max_abs_slippage_drift_bps,
            "max_abs_fee_drift_bps": self.max_abs_fee_drift_bps,
            "max_abs_latency_drift_ns": self.max_abs_latency_drift_ns,
            "live_drift_validated": self.live_drift_validated,
            "g10_authority": self.g10_authority,
            "production_readiness_authority": self.production_readiness_authority,
            "execution_authority": self.execution_authority,
            "order_routing_authority": self.order_routing_authority,
            "p20_started": self.p20_started,
            "live_trading": self.live_trading,
            "auto_trading": self.auto_trading,
        }

    @property
    def window_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


def build_drift_window(
    *,
    pairs: Sequence[ExecutionDriftPair],
    policy: ExecutionDriftPolicy,
) -> ExecutionDriftWindow:
    if not pairs:
        raise ExecutionDriftError("drift window requires at least one pair")
    classes = {pair.observation_class for pair in pairs}
    if len(classes) != 1:
        raise ExecutionDriftError("mixed observation classes are forbidden")
    observation_class = next(iter(classes))
    if observation_class not in policy.observation_classes:
        raise ExecutionDriftError("unsupported drift window observation class")

    pair_ids = [pair.pair_id for pair in pairs]
    if len(pair_ids) != len(set(pair_ids)):
        raise ExecutionDriftError("duplicate drift pair identity")
    ordered = tuple(sorted(pairs, key=lambda pair: (pair.decision_time_ns, pair.pair_id)))
    severity_rank = {"NORMAL": 0, "WARN": 1, "FAIL": 2}
    if any(pair.severity not in severity_rank for pair in ordered):
        raise ExecutionDriftError("unsupported drift severity")
    severity = max(ordered, key=lambda pair: severity_rank[pair.severity]).severity

    max_fill = max(
        _decimal(pair.fill_ratio_drift_bps, field="fill_ratio_drift_bps")
        for pair in ordered
    )
    slippages = [
        _decimal(pair.abs_slippage_drift_bps, field="abs_slippage_drift_bps")
        for pair in ordered
        if pair.abs_slippage_drift_bps is not None
    ]
    max_slippage = max(slippages) if slippages else None
    max_fee = max(
        _decimal(pair.abs_fee_drift_bps, field="abs_fee_drift_bps")
        for pair in ordered
    )
    max_latency = max(pair.abs_latency_drift_ns for pair in ordered)

    if observation_class == "REFERENCE_OBSERVATION":
        claim_scope = "REFERENCE_ONLY"
    elif observation_class == "BROKER_CERTIFICATION_OBSERVATION":
        claim_scope = "BROKER_CERTIFICATION_ONLY"
    else:
        claim_scope = "LIVE_OBSERVED"

    live_validated = (
        observation_class == "LIVE_EXECUTION_OBSERVATION"
        and len(ordered) >= policy.minimum_live_samples
        and severity == "NORMAL"
    )
    return ExecutionDriftWindow(
        policy_id=policy.policy_id,
        observation_class=observation_class,
        claim_scope=claim_scope,
        pair_ids=tuple(pair.pair_id for pair in ordered),
        pairs=ordered,
        severity=severity,
        max_fill_ratio_drift_bps=_decimal_text(max_fill),
        max_abs_slippage_drift_bps=(
            None if max_slippage is None else _decimal_text(max_slippage)
        ),
        max_abs_fee_drift_bps=_decimal_text(max_fee),
        max_abs_latency_drift_ns=max_latency,
        live_drift_validated=live_validated,
    )
