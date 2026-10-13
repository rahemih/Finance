from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence, cast


class EvidenceContractError(ValueError):
    """P14-A evidence-contract input or policy violates governed invariants."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise EvidenceContractError(f"{field} must be object")
    return cast(Mapping[str, object], value)


def _object_list(value: object, *, field: str) -> list[object]:
    if not isinstance(value, list):
        raise EvidenceContractError(f"{field} must be list")
    return cast(list[object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceContractError(f"{field} must be non-empty text")
    return value.strip()


def _integer(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise EvidenceContractError(f"{field} must be integer")
    return value


def _non_negative_int(value: object, *, field: str) -> int:
    parsed = _integer(value, field=field)
    if parsed < 0:
        raise EvidenceContractError(f"{field} must be non-negative")
    return parsed


def _positive_int(value: object, *, field: str) -> int:
    parsed = _integer(value, field=field)
    if parsed <= 0:
        raise EvidenceContractError(f"{field} must be positive")
    return parsed


def _bps(value: object, *, field: str, maximum: int = 10_000) -> int:
    parsed = _non_negative_int(value, field=field)
    if parsed > maximum:
        raise EvidenceContractError(f"{field} exceeds maximum")
    return parsed


def _sha256_text(value: object, *, field: str) -> str:
    parsed = _text(value, field=field).lower()
    if len(parsed) != 64 or any(ch not in "0123456789abcdef" for ch in parsed):
        raise EvidenceContractError(f"{field} must be lowercase SHA-256 hex")
    return parsed


@dataclass(frozen=True, slots=True)
class EvidenceContractPolicy:
    allowed_source_phases: tuple[str, ...]
    allowed_source_families: tuple[str, ...]
    max_strength_bps: int
    max_quality_bps: int
    minimum_sample_count: int
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "EvidenceContractPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        raw = _mapping(raw_value, field="policy root")
        if raw.get("schema_version") != "1.0" or raw.get("mode") != "CROSS_DOMAIN_SIGNAL_EVIDENCE_CONTRACT":
            raise EvidenceContractError("unsupported P14-A policy")

        phases = tuple(_text(item, field="allowed_source_phase") for item in _object_list(raw.get("allowed_source_phases"), field="allowed_source_phases"))
        families = tuple(_text(item, field="allowed_source_family") for item in _object_list(raw.get("allowed_source_families"), field="allowed_source_families"))
        if phases != ("P08", "P09", "P10", "P11", "P12", "P13"):
            raise EvidenceContractError("P14-A source phases must be canonical P08-P13")
        expected_families = (
            "TECHNICAL",
            "ORDER_FLOW_LIQUIDITY",
            "FUNDAMENTAL_MACRO",
            "NEWS_SENTIMENT",
            "MARKET_MEMORY",
            "TIMING_OPPORTUNITY",
        )
        if families != expected_families:
            raise EvidenceContractError("P14-A source families are not canonical")
        directions = tuple(_integer(item, field="allowed_direction") for item in _object_list(raw.get("allowed_directions"), field="allowed_directions"))
        if directions != (-1, 0, 1):
            raise EvidenceContractError("P14-A directions must be -1/0/1")
        if raw.get("require_independence_group") is not True:
            raise EvidenceContractError("independence_group must be required")
        if raw.get("require_valid_until_ns") is not True:
            raise EvidenceContractError("valid_until_ns must be required")
        if raw.get("unknown_source_behavior") != "FAIL_CLOSED":
            raise EvidenceContractError("unknown source behavior must fail closed")
        if raw.get("expired_evidence_behavior") != "PRESERVE_EXPLICIT_NOT_FRESH":
            raise EvidenceContractError("expired evidence must remain explicit")
        if raw.get("hard_veto_behavior") != "PRESERVE_NON_BYPASSABLE":
            raise EvidenceContractError("hard veto behavior must be non-bypassable")
        forbidden_true = (
            "weighted_fusion_in_scope",
            "empirical_probability_in_scope",
            "tp_stop_probability_in_scope",
            "llm_probability_authority",
            "risk_approval_in_scope",
            "position_sizing_in_scope",
            "execution_authority_in_scope",
            "canonical_tests_network_required",
        )
        if any(raw.get(field) is not False for field in forbidden_true):
            raise EvidenceContractError("P14-A cannot enable fusion/probability/risk/execution/network authority")
        if raw.get("live_trading") != "DISABLED" or raw.get("auto_trading") != "DISABLED":
            raise EvidenceContractError("P14-A cannot enable trading")

        return cls(
            allowed_source_phases=phases,
            allowed_source_families=families,
            max_strength_bps=_bps(raw.get("max_strength_bps"), field="max_strength_bps"),
            max_quality_bps=_bps(raw.get("max_quality_bps"), field="max_quality_bps"),
            minimum_sample_count=_positive_int(raw.get("minimum_sample_count"), field="minimum_sample_count"),
            live_trading="DISABLED",
            auto_trading="DISABLED",
        )


@dataclass(frozen=True, slots=True)
class SignalEvidence:
    source_phase: str
    source_family: str
    evidence_family: str
    independence_group: str
    subject_id: str
    timeframe: str
    regime_label: str
    direction: int
    strength_bps: int
    quality_bps: int
    sample_count: int
    event_time_ns: int
    as_of_time_ns: int
    valid_until_ns: int
    source_record_id: str
    provenance_sha256: str
    invalidation: str
    hard_veto: bool = False
    veto_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_phase", _text(self.source_phase, field="source_phase").upper())
        object.__setattr__(self, "source_family", _text(self.source_family, field="source_family").upper())
        object.__setattr__(self, "evidence_family", _text(self.evidence_family, field="evidence_family"))
        object.__setattr__(self, "independence_group", _text(self.independence_group, field="independence_group"))
        object.__setattr__(self, "subject_id", _text(self.subject_id, field="subject_id"))
        object.__setattr__(self, "timeframe", _text(self.timeframe, field="timeframe"))
        object.__setattr__(self, "regime_label", _text(self.regime_label, field="regime_label"))
        if self.direction not in (-1, 0, 1):
            raise EvidenceContractError("direction must be -1, 0 or 1")
        object.__setattr__(self, "strength_bps", _bps(self.strength_bps, field="strength_bps"))
        object.__setattr__(self, "quality_bps", _bps(self.quality_bps, field="quality_bps"))
        object.__setattr__(self, "sample_count", _positive_int(self.sample_count, field="sample_count"))
        event_time = _non_negative_int(self.event_time_ns, field="event_time_ns")
        as_of_time = _non_negative_int(self.as_of_time_ns, field="as_of_time_ns")
        valid_until = _non_negative_int(self.valid_until_ns, field="valid_until_ns")
        if event_time > as_of_time:
            raise EvidenceContractError("event_time_ns cannot exceed as_of_time_ns")
        if valid_until < event_time:
            raise EvidenceContractError("valid_until_ns cannot precede event_time_ns")
        object.__setattr__(self, "source_record_id", _text(self.source_record_id, field="source_record_id"))
        object.__setattr__(self, "provenance_sha256", _sha256_text(self.provenance_sha256, field="provenance_sha256"))
        object.__setattr__(self, "invalidation", _text(self.invalidation, field="invalidation"))
        normalized_codes = tuple(sorted({_text(code, field="veto_code").upper() for code in self.veto_codes}))
        if self.hard_veto and not normalized_codes:
            raise EvidenceContractError("hard_veto requires at least one veto code")
        if not self.hard_veto and normalized_codes:
            raise EvidenceContractError("veto codes require hard_veto=true")
        object.__setattr__(self, "veto_codes", normalized_codes)

    @property
    def freshness_ns(self) -> int:
        return self.as_of_time_ns - self.event_time_ns

    @property
    def freshness_state(self) -> str:
        return "FRESH" if self.as_of_time_ns <= self.valid_until_ns else "EXPIRED"

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "source_phase": self.source_phase,
            "source_family": self.source_family,
            "evidence_family": self.evidence_family,
            "independence_group": self.independence_group,
            "subject_id": self.subject_id,
            "timeframe": self.timeframe,
            "regime_label": self.regime_label,
            "direction": self.direction,
            "strength_bps": self.strength_bps,
            "quality_bps": self.quality_bps,
            "sample_count": self.sample_count,
            "event_time_ns": self.event_time_ns,
            "as_of_time_ns": self.as_of_time_ns,
            "valid_until_ns": self.valid_until_ns,
            "freshness_ns": self.freshness_ns,
            "freshness_state": self.freshness_state,
            "source_record_id": self.source_record_id,
            "provenance_sha256": self.provenance_sha256,
            "invalidation": self.invalidation,
            "hard_veto": self.hard_veto,
            "veto_codes": list(self.veto_codes),
        }

    @property
    def evidence_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class EvidenceBundle:
    subject_id: str
    as_of_time_ns: int
    evidence: tuple[SignalEvidence, ...]

    @classmethod
    def build(
        cls,
        *,
        policy: EvidenceContractPolicy,
        subject_id: str,
        as_of_time_ns: int,
        evidence: Sequence[SignalEvidence],
    ) -> "EvidenceBundle":
        subject = _text(subject_id, field="subject_id")
        as_of = _non_negative_int(as_of_time_ns, field="as_of_time_ns")
        records = tuple(evidence)
        if not records:
            raise EvidenceContractError("evidence bundle cannot be empty")
        seen_ids: set[str] = set()
        for item in records:
            if item.source_phase not in policy.allowed_source_phases:
                raise EvidenceContractError("unknown source_phase")
            if item.source_family not in policy.allowed_source_families:
                raise EvidenceContractError("unknown source_family")
            if item.strength_bps > policy.max_strength_bps or item.quality_bps > policy.max_quality_bps:
                raise EvidenceContractError("evidence bps exceeds policy")
            if item.sample_count < policy.minimum_sample_count:
                raise EvidenceContractError("sample_count below policy minimum")
            if item.subject_id != subject:
                raise EvidenceContractError("evidence subject mismatch")
            if item.as_of_time_ns != as_of:
                raise EvidenceContractError("evidence as_of mismatch")
            evidence_id = item.evidence_id
            if evidence_id in seen_ids:
                raise EvidenceContractError("duplicate evidence identity")
            seen_ids.add(evidence_id)
        ordered = tuple(sorted(records, key=lambda item: item.evidence_id))
        return cls(subject_id=subject, as_of_time_ns=as_of, evidence=ordered)

    @property
    def hard_veto(self) -> bool:
        return any(item.hard_veto for item in self.evidence)

    @property
    def veto_codes(self) -> tuple[str, ...]:
        return tuple(sorted({code for item in self.evidence for code in item.veto_codes}))

    @property
    def expired_evidence_ids(self) -> tuple[str, ...]:
        return tuple(item.evidence_id for item in self.evidence if item.freshness_state == "EXPIRED")

    @property
    def source_phases(self) -> tuple[str, ...]:
        return tuple(sorted({item.source_phase for item in self.evidence}))

    @property
    def independence_groups(self) -> tuple[str, ...]:
        return tuple(sorted({item.independence_group for item in self.evidence}))

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "subject_id": self.subject_id,
            "as_of_time_ns": self.as_of_time_ns,
            "hard_veto": self.hard_veto,
            "veto_codes": list(self.veto_codes),
            "expired_evidence_ids": list(self.expired_evidence_ids),
            "source_phases": list(self.source_phases),
            "independence_groups": list(self.independence_groups),
            "evidence": [item.payload() | {"evidence_id": item.evidence_id} for item in self.evidence],
            "weighted_fusion": None,
            "empirical_probability": None,
        }

    @property
    def bundle_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()
