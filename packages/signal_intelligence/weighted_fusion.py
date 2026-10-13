from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Mapping, cast

from .evidence_contract import EvidenceBundle, SignalEvidence


class WeightedFusionError(ValueError):
    """P14-B weighted-fusion invariant failure."""


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise WeightedFusionError(f"{field} must be object")
    return cast(Mapping[str, object], value)


def _integer(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise WeightedFusionError(f"{field} must be integer")
    return value


def _positive_int(value: object, *, field: str) -> int:
    value_int = _integer(value, field=field)
    if value_int <= 0:
        raise WeightedFusionError(f"{field} must be positive")
    return value_int


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _rounded_divide_signed(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        raise WeightedFusionError("denominator must be positive")
    if numerator >= 0:
        return (numerator + denominator // 2) // denominator
    return -((-numerator + denominator // 2) // denominator)


@dataclass(frozen=True, slots=True)
class WeightedFusionPolicy:
    minimum_directional_independent_groups: int
    minimum_source_families: int
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "WeightedFusionPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        raw = _mapping(raw_value, field="policy root")
        if raw.get("schema_version") != "1.0" or raw.get("mode") != "QUALITY_WEIGHTED_INDEPENDENCE_CAPPED_FUSION":
            raise WeightedFusionError("unsupported P14-B policy")
        if raw.get("representative_selection") != "MAX_ABS_QUALITY_ADJUSTED_THEN_EVIDENCE_ID":
            raise WeightedFusionError("unexpected representative selection")
        if raw.get("group_vote_cap") != 1:
            raise WeightedFusionError("one independence group may contribute at most one representative")
        if raw.get("expired_evidence_behavior") != "EXCLUDE_PRESERVE_ID":
            raise WeightedFusionError("expired evidence behavior must exclude and preserve identity")
        if raw.get("hard_veto_behavior") != "BLOCK_NON_BYPASSABLE":
            raise WeightedFusionError("hard veto must remain non-bypassable")
        forbidden = (
            "family_prior_weights_enabled",
            "llm_weighting_authority",
            "empirical_probability_in_scope",
            "risk_approval_in_scope",
            "position_sizing_in_scope",
            "execution_authority_in_scope",
            "canonical_tests_network_required",
        )
        if any(raw.get(field) is not False for field in forbidden):
            raise WeightedFusionError("P14-B cannot enable family priors, LLM weighting, probability, risk or execution")
        if raw.get("fusion_score_semantics") != "SIGNED_EVIDENCE_SCORE_NOT_PROBABILITY":
            raise WeightedFusionError("fusion score semantics must remain non-probabilistic")
        if raw.get("live_trading") != "DISABLED" or raw.get("auto_trading") != "DISABLED":
            raise WeightedFusionError("P14-B cannot enable trading")
        return cls(
            minimum_directional_independent_groups=_positive_int(raw.get("minimum_directional_independent_groups"), field="minimum_directional_independent_groups"),
            minimum_source_families=_positive_int(raw.get("minimum_source_families"), field="minimum_source_families"),
            live_trading="DISABLED",
            auto_trading="DISABLED",
        )


@dataclass(frozen=True, slots=True)
class FusionRepresentative:
    evidence_id: str
    independence_group: str
    source_family: str
    direction: int
    adjusted_signed_bps: int


@dataclass(frozen=True, slots=True)
class WeightedFusionResult:
    subject_id: str
    as_of_time_ns: int
    state: str
    signed_score_bps: int | None
    direction: int
    representatives: tuple[FusionRepresentative, ...]
    supporting_groups: tuple[str, ...]
    opposing_groups: tuple[str, ...]
    neutral_groups: tuple[str, ...]
    source_families: tuple[str, ...]
    excluded_expired_evidence_ids: tuple[str, ...]
    excluded_correlated_evidence_ids: tuple[str, ...]
    veto_codes: tuple[str, ...]

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "subject_id": self.subject_id,
            "as_of_time_ns": self.as_of_time_ns,
            "state": self.state,
            "signed_score_bps": self.signed_score_bps,
            "direction": self.direction,
            "representatives": [
                {
                    "evidence_id": item.evidence_id,
                    "independence_group": item.independence_group,
                    "source_family": item.source_family,
                    "direction": item.direction,
                    "adjusted_signed_bps": item.adjusted_signed_bps,
                }
                for item in self.representatives
            ],
            "supporting_groups": list(self.supporting_groups),
            "opposing_groups": list(self.opposing_groups),
            "neutral_groups": list(self.neutral_groups),
            "source_families": list(self.source_families),
            "excluded_expired_evidence_ids": list(self.excluded_expired_evidence_ids),
            "excluded_correlated_evidence_ids": list(self.excluded_correlated_evidence_ids),
            "veto_codes": list(self.veto_codes),
            "empirical_probability": None,
        }

    @property
    def fusion_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


def _adjusted_signed_bps(item: SignalEvidence) -> int:
    magnitude = (item.strength_bps * item.quality_bps + 5_000) // 10_000
    return item.direction * magnitude


def _representative(items: tuple[SignalEvidence, ...]) -> SignalEvidence:
    return sorted(items, key=lambda item: (-abs(_adjusted_signed_bps(item)), item.evidence_id))[0]


def fuse_evidence(*, bundle: EvidenceBundle, policy: WeightedFusionPolicy) -> WeightedFusionResult:
    expired_ids = tuple(sorted(bundle.expired_evidence_ids))
    if bundle.hard_veto:
        return WeightedFusionResult(
            subject_id=bundle.subject_id,
            as_of_time_ns=bundle.as_of_time_ns,
            state="BLOCKED",
            signed_score_bps=None,
            direction=0,
            representatives=(),
            supporting_groups=(),
            opposing_groups=(),
            neutral_groups=(),
            source_families=(),
            excluded_expired_evidence_ids=expired_ids,
            excluded_correlated_evidence_ids=(),
            veto_codes=bundle.veto_codes,
        )

    fresh = tuple(item for item in bundle.evidence if item.freshness_state == "FRESH")
    grouped: dict[str, list[SignalEvidence]] = {}
    for item in fresh:
        grouped.setdefault(item.independence_group, []).append(item)

    representatives: list[SignalEvidence] = []
    correlated_excluded: list[str] = []
    for group in sorted(grouped):
        members = tuple(grouped[group])
        selected = _representative(members)
        representatives.append(selected)
        correlated_excluded.extend(item.evidence_id for item in members if item.evidence_id != selected.evidence_id)

    rep_records = tuple(sorted(representatives, key=lambda item: item.independence_group))
    rep_view = tuple(
        FusionRepresentative(
            evidence_id=item.evidence_id,
            independence_group=item.independence_group,
            source_family=item.source_family,
            direction=item.direction,
            adjusted_signed_bps=_adjusted_signed_bps(item),
        )
        for item in rep_records
    )
    directional = tuple(item for item in rep_records if item.direction != 0)
    directional_families = tuple(sorted({item.source_family for item in directional}))
    if len(directional) < policy.minimum_directional_independent_groups or len(directional_families) < policy.minimum_source_families:
        return WeightedFusionResult(
            subject_id=bundle.subject_id,
            as_of_time_ns=bundle.as_of_time_ns,
            state="INSUFFICIENT_EVIDENCE",
            signed_score_bps=None,
            direction=0,
            representatives=rep_view,
            supporting_groups=(),
            opposing_groups=(),
            neutral_groups=tuple(sorted(item.independence_group for item in rep_records if item.direction == 0)),
            source_families=tuple(sorted({item.source_family for item in rep_records})),
            excluded_expired_evidence_ids=expired_ids,
            excluded_correlated_evidence_ids=tuple(sorted(correlated_excluded)),
            veto_codes=(),
        )

    numerator = sum(_adjusted_signed_bps(item) for item in rep_records)
    score = _rounded_divide_signed(numerator, len(rep_records))
    direction = 1 if score > 0 else -1 if score < 0 else 0
    supporting = tuple(sorted(item.independence_group for item in rep_records if item.direction == direction and direction != 0))
    opposing = tuple(sorted(item.independence_group for item in rep_records if item.direction == -direction and direction != 0))
    neutral = tuple(sorted(item.independence_group for item in rep_records if item.direction == 0))
    return WeightedFusionResult(
        subject_id=bundle.subject_id,
        as_of_time_ns=bundle.as_of_time_ns,
        state="FUSED",
        signed_score_bps=score,
        direction=direction,
        representatives=rep_view,
        supporting_groups=supporting,
        opposing_groups=opposing,
        neutral_groups=neutral,
        source_families=tuple(sorted({item.source_family for item in rep_records})),
        excluded_expired_evidence_ids=expired_ids,
        excluded_correlated_evidence_ids=tuple(sorted(correlated_excluded)),
        veto_codes=(),
    )
