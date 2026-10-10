from __future__ import annotations

from dataclasses import dataclass, fields
import hashlib
import json
from pathlib import Path
import re
from typing import Mapping, Sequence, cast


class CryptoOnchainContextError(ValueError):
    """Raised when P10-G crypto/on-chain context invariants fail closed."""


_HASH = re.compile(r"^0x[0-9a-f]{64}$")
_CHAIN_ID = re.compile(r"^[1-9][0-9]{0,19}$")
_SERIES_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$")
_NON_NEGATIVE_INTEGER_TEXT = re.compile(r"^(0|[1-9][0-9]*)$")


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise CryptoOnchainContextError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _object_list(value: object, *, field: str) -> list[object]:
    if not isinstance(value, list):
        raise CryptoOnchainContextError(f"{field} must be a list")
    return cast(list[object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CryptoOnchainContextError(f"{field} must be non-empty text")
    return value.strip()


def _boolean(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise CryptoOnchainContextError(f"{field} must be boolean")
    return value


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise CryptoOnchainContextError(f"{field} must be a positive integer")
    return value


def _non_negative_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CryptoOnchainContextError(f"{field} must be a non-negative integer")
    return value


def _series_id(value: object) -> str:
    text = _text(value, field="series_id")
    if _SERIES_ID.fullmatch(text) is None:
        raise CryptoOnchainContextError("series_id contains unsafe characters")
    return text


def _integer_text(value: object, *, field: str) -> str:
    text = _text(value, field=field)
    if _NON_NEGATIVE_INTEGER_TEXT.fullmatch(text) is None:
        raise CryptoOnchainContextError(f"{field} must be canonical non-negative integer text")
    return text


@dataclass(frozen=True, slots=True)
class CryptoMetricRule:
    metric_kind: str
    subject_kind: str
    allowed_units: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CryptoOnchainPolicy:
    supplemental_source_id: str
    source_class: str
    independent_validation: str
    production_source_mapping: str
    allowed_finality_states: tuple[str, ...]
    metric_rules: tuple[CryptoMetricRule, ...]
    latest_as_of_rule: str
    reorg_rule: str
    unverified_exchange_wallet_labels_allowed: bool
    market_direction_interpretation_allowed: bool
    causal_market_impact_claim_allowed: bool
    direct_trade_output_allowed: bool
    network_required: bool
    credentials_required: bool
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "CryptoOnchainPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        raw = _mapping(raw_value, field="policy root")
        if raw.get("schema_version") != "1.0":
            raise CryptoOnchainContextError("unsupported crypto/on-chain policy schema_version")

        finality = tuple(_text(x, field="finality") for x in _object_list(raw.get("allowed_finality_states"), field="allowed_finality_states"))
        rules = tuple(
            CryptoMetricRule(
                _text(item.get("metric_kind"), field="metric_kind"),
                _text(item.get("subject_kind"), field="subject_kind"),
                tuple(_text(x, field="unit") for x in _object_list(item.get("allowed_units"), field="allowed_units")),
            )
            for item in (
                _mapping(value, field="metric rule")
                for value in _object_list(raw.get("metric_rules"), field="metric_rules")
            )
        )
        policy = cls(
            supplemental_source_id=_text(raw.get("supplemental_source_id"), field="supplemental_source_id"),
            source_class=_text(raw.get("source_class"), field="source_class"),
            independent_validation=_text(raw.get("independent_validation"), field="independent_validation"),
            production_source_mapping=_text(raw.get("production_source_mapping"), field="production_source_mapping"),
            allowed_finality_states=finality,
            metric_rules=rules,
            latest_as_of_rule=_text(raw.get("latest_as_of_rule"), field="latest_as_of_rule"),
            reorg_rule=_text(raw.get("reorg_rule"), field="reorg_rule"),
            unverified_exchange_wallet_labels_allowed=_boolean(raw.get("unverified_exchange_wallet_labels_allowed"), field="unverified_exchange_wallet_labels_allowed"),
            market_direction_interpretation_allowed=_boolean(raw.get("market_direction_interpretation_allowed"), field="market_direction_interpretation_allowed"),
            causal_market_impact_claim_allowed=_boolean(raw.get("causal_market_impact_claim_allowed"), field="causal_market_impact_claim_allowed"),
            direct_trade_output_allowed=_boolean(raw.get("direct_trade_output_allowed"), field="direct_trade_output_allowed"),
            network_required=_boolean(raw.get("network_required"), field="network_required"),
            credentials_required=_boolean(raw.get("credentials_required"), field="credentials_required"),
            live_trading=_text(raw.get("live_trading"), field="live_trading"),
            auto_trading=_text(raw.get("auto_trading"), field="auto_trading"),
        )
        expected = {
            "TOKEN_TOTAL_SUPPLY": ("TOKEN", ("RAW_BASE_UNITS",)),
            "TOKEN_HOLDER_COUNT": ("TOKEN", ("COUNT",)),
            "TOKEN_TRANSFER_COUNT": ("TOKEN", ("COUNT",)),
            "NETWORK_TRANSACTION_COUNT": ("NETWORK", ("COUNT",)),
        }
        actual = {rule.metric_kind: (rule.subject_kind, rule.allowed_units) for rule in policy.metric_rules}
        if actual != expected or len(actual) != len(policy.metric_rules):
            raise CryptoOnchainContextError("crypto metric-rule policy drift")
        if policy.supplemental_source_id != "BLOCKSCOUT" or policy.source_class != "ONCHAIN_INDEXER":
            raise CryptoOnchainContextError("P10-G source baseline drift")
        if policy.independent_validation != "DIRECT_NODE_OR_SECOND_INDEXER_TBD":
            raise CryptoOnchainContextError("P10-G independent-validation baseline drift")
        if policy.production_source_mapping != "NOT_SELECTED":
            raise CryptoOnchainContextError("P10-G cannot select a production on-chain source")
        if policy.allowed_finality_states != ("PROVISIONAL", "FINALIZED"):
            raise CryptoOnchainContextError("finality-state policy drift")
        if policy.latest_as_of_rule != "LATEST_OBSERVED_CHAIN_VIEW_NOT_AFTER_DECISION_TIME":
            raise CryptoOnchainContextError("latest-as-of policy drift")
        if policy.reorg_rule != "PRESERVE_PRIOR_CHAIN_VIEW_AND_RECORD_LATER_BLOCK_HASH_AS_NEW_OBSERVATION":
            raise CryptoOnchainContextError("reorg policy drift")
        if (
            policy.unverified_exchange_wallet_labels_allowed
            or policy.market_direction_interpretation_allowed
            or policy.causal_market_impact_claim_allowed
            or policy.direct_trade_output_allowed
        ):
            raise CryptoOnchainContextError("P10-G must remain descriptive, label-safe and non-trading")
        if policy.network_required or policy.credentials_required:
            raise CryptoOnchainContextError("P10-G canonical model must remain offline")
        if policy.live_trading != "DISABLED" or policy.auto_trading != "DISABLED":
            raise CryptoOnchainContextError("P10-G cannot enable trading")
        return policy

    def rule_for(self, metric_kind: str) -> CryptoMetricRule:
        for rule in self.metric_rules:
            if rule.metric_kind == metric_kind:
                return rule
        raise CryptoOnchainContextError("unsupported crypto/on-chain metric kind")


@dataclass(frozen=True, slots=True)
class ChainBlockAnchor:
    chain_id: str
    block_number: int
    block_hash: str
    block_timestamp_ns: int
    observed_at_ns: int
    finality_state: str
    source_id: str

    def payload(self) -> dict[str, object]:
        return {
            "chain_id": self.chain_id,
            "block_number": self.block_number,
            "block_hash": self.block_hash,
            "block_timestamp_ns": self.block_timestamp_ns,
            "observed_at_ns": self.observed_at_ns,
            "finality_state": self.finality_state,
            "source_id": self.source_id,
        }

    @property
    def anchor_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


def validate_anchor(anchor: ChainBlockAnchor, *, policy: CryptoOnchainPolicy) -> ChainBlockAnchor:
    if _CHAIN_ID.fullmatch(_text(anchor.chain_id, field="chain_id")) is None:
        raise CryptoOnchainContextError("chain_id must be canonical positive decimal text")
    _non_negative_int(anchor.block_number, field="block_number")
    if _HASH.fullmatch(_text(anchor.block_hash, field="block_hash")) is None:
        raise CryptoOnchainContextError("block_hash must be lowercase 0x-prefixed 32-byte hex")
    _positive_int(anchor.block_timestamp_ns, field="block_timestamp_ns")
    _positive_int(anchor.observed_at_ns, field="observed_at_ns")
    if anchor.observed_at_ns < anchor.block_timestamp_ns:
        raise CryptoOnchainContextError("block cannot be observed before its timestamp")
    if anchor.finality_state not in policy.allowed_finality_states:
        raise CryptoOnchainContextError("unsupported finality state")
    if anchor.source_id != policy.supplemental_source_id:
        raise CryptoOnchainContextError("on-chain anchor source must match governed supplemental source")
    return anchor


@dataclass(frozen=True, slots=True)
class CryptoOnchainPoint:
    series_id: str
    subject_kind: str
    subject_id: str
    metric_kind: str
    value_text: str
    unit: str
    anchor: ChainBlockAnchor
    source_snapshot_sha256: str

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "series_id": self.series_id,
            "subject_kind": self.subject_kind,
            "subject_id": self.subject_id,
            "metric_kind": self.metric_kind,
            "value_text": self.value_text,
            "unit": self.unit,
            "anchor": self.anchor.payload(),
            "source_snapshot_sha256": self.source_snapshot_sha256,
        }

    @property
    def point_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


def validate_point(point: CryptoOnchainPoint, *, policy: CryptoOnchainPolicy) -> CryptoOnchainPoint:
    _series_id(point.series_id)
    _text(point.subject_id, field="subject_id")
    _integer_text(point.value_text, field="value_text")
    if re.fullmatch(r"[0-9a-f]{64}", _text(point.source_snapshot_sha256, field="source_snapshot_sha256")) is None:
        raise CryptoOnchainContextError("source_snapshot_sha256 must be lowercase SHA-256")
    rule = policy.rule_for(_text(point.metric_kind, field="metric_kind"))
    if point.subject_kind != rule.subject_kind:
        raise CryptoOnchainContextError("subject_kind does not match metric rule")
    if point.unit not in rule.allowed_units:
        raise CryptoOnchainContextError("unit is not allowed for metric")
    validate_anchor(point.anchor, policy=policy)
    return point


class CryptoOnchainStore:
    def __init__(self, points: Sequence[CryptoOnchainPoint], *, policy: CryptoOnchainPolicy) -> None:
        frozen = tuple(points)
        if not frozen:
            raise CryptoOnchainContextError("crypto/on-chain store requires at least one point")
        metadata: dict[str, tuple[str, str, str, str]] = {}
        ids: set[str] = set()
        grouped: dict[str, list[CryptoOnchainPoint]] = {}
        for point in frozen:
            valid = validate_point(point, policy=policy)
            if valid.point_id in ids:
                raise CryptoOnchainContextError("duplicate on-chain point")
            ids.add(valid.point_id)
            meta = (valid.subject_kind, valid.subject_id, valid.metric_kind, valid.unit)
            previous = metadata.get(valid.series_id)
            if previous is not None and previous != meta:
                raise CryptoOnchainContextError("series metadata cannot drift")
            metadata[valid.series_id] = meta
            grouped.setdefault(valid.series_id, []).append(valid)
        self._groups = {
            key: tuple(sorted(values, key=lambda item: (item.anchor.observed_at_ns, item.anchor.block_number, item.point_id)))
            for key, values in grouped.items()
        }
        ordered = [point.payload() for point in sorted(frozen, key=lambda item: item.point_id)]
        self._fingerprint = hashlib.sha256(_canonical_bytes(ordered)).hexdigest()

    @property
    def fingerprint(self) -> str:
        return self._fingerprint

    def resolve_latest_as_of(self, *, series_id: str, decision_time_ns: int) -> CryptoOnchainPoint | None:
        safe_series = _series_id(series_id)
        decision = _positive_int(decision_time_ns, field="decision_time_ns")
        eligible = [
            point
            for point in self._groups.get(safe_series, ())
            if point.anchor.observed_at_ns <= decision and point.anchor.block_timestamp_ns <= decision
        ]
        if not eligible:
            return None
        return max(
            eligible,
            key=lambda item: (item.anchor.block_number, item.anchor.observed_at_ns, item.point_id),
        )

    def chain_views_for_block(self, *, series_id: str, block_number: int) -> tuple[CryptoOnchainPoint, ...]:
        safe_series = _series_id(series_id)
        block = _non_negative_int(block_number, field="block_number")
        return tuple(
            point for point in self._groups.get(safe_series, ())
            if point.anchor.block_number == block
        )


def assert_no_crypto_onchain_trade_authority_fields() -> None:
    forbidden = {
        "trade_direction",
        "signal_probability",
        "success_probability",
        "recommendation",
        "risk_approval",
        "execution_authority",
        "order_intent",
        "entry_price",
        "stop_loss",
        "take_profit",
        "bullish",
        "bearish",
        "exchange_reserve_estimate",
    }
    for cls in (ChainBlockAnchor, CryptoOnchainPoint):
        overlap = sorted({field.name for field in fields(cls)} & forbidden)
        if overlap:
            raise CryptoOnchainContextError(f"P10-G trade-authority field leak: {overlap}")
