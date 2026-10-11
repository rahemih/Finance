from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Mapping, cast

from .classification import ClassificationResult
from .ingestion import RawNewsItem
from .source_policy import NewsSourcePolicy, validate_source_record


class ReliabilityControlError(ValueError):
    """Raised when P11-E reliability/rumor invariants fail closed."""


@dataclass(frozen=True, slots=True)
class ReliabilityPolicy:
    source_class_scores: tuple[tuple[str, int], ...]
    admissibility_adjustments: tuple[tuple[str, int], ...]
    corroboration_bonus_per_source: int
    corroboration_bonus_cap: int
    high_threshold: int
    medium_threshold: int
    community_social_review_required_without_corroboration: bool
    high_importance_single_source_review_required: bool
    reliability_bands: tuple[str, ...]
    rumor_states: tuple[str, ...]
    review_states: tuple[str, ...]
    canonical_tests_network_required: bool
    production_news_vendor: str
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "ReliabilityPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw_value, Mapping):
            raise ReliabilityControlError("policy root must be an object")
        raw = cast(Mapping[str, object], raw_value)
        if raw.get("schema_version") != "1.0":
            raise ReliabilityControlError("unsupported reliability policy schema_version")

        source_value = raw.get("source_class_scores")
        admissibility_value = raw.get("admissibility_adjustments")
        if not isinstance(source_value, Mapping) or not source_value:
            raise ReliabilityControlError("source_class_scores must be non-empty object")
        if not isinstance(admissibility_value, Mapping) or not admissibility_value:
            raise ReliabilityControlError("admissibility_adjustments must be non-empty object")

        source_score_items: list[tuple[str, int]] = []
        for key, value in cast(Mapping[object, object], source_value).items():
            if not isinstance(value, int) or isinstance(value, bool):
                raise ReliabilityControlError("source_class_scores values must be integers")
            source_score_items.append((str(key).strip().upper(), value))
        source_scores = tuple(sorted(source_score_items))

        admissibility_items: list[tuple[str, int]] = []
        for key, value in cast(Mapping[object, object], admissibility_value).items():
            if not isinstance(value, int) or isinstance(value, bool):
                raise ReliabilityControlError("admissibility_adjustments values must be integers")
            admissibility_items.append((str(key).strip().upper(), value))
        admissibility = tuple(sorted(admissibility_items))

        bonus = raw.get("corroboration_bonus_per_source")
        cap = raw.get("corroboration_bonus_cap")
        high = raw.get("high_threshold")
        medium = raw.get("medium_threshold")
        if not all(isinstance(value, int) for value in (bonus, cap, high, medium)):
            raise ReliabilityControlError("numeric reliability policy values must be integers")
        bonus_i = cast(int, bonus)
        cap_i = cast(int, cap)
        high_i = cast(int, high)
        medium_i = cast(int, medium)
        if bonus_i < 0 or cap_i < 0 or medium_i < 0 or high_i <= medium_i:
            raise ReliabilityControlError("invalid reliability thresholds")

        bands_value = raw.get("reliability_bands")
        rumor_value = raw.get("rumor_states")
        review_value = raw.get("review_states")
        if not isinstance(bands_value, list) or not isinstance(rumor_value, list) or not isinstance(review_value, list):
            raise ReliabilityControlError("state fields must be lists")
        bands = tuple(str(v).strip().upper() for v in cast(list[object], bands_value))
        rumor = tuple(str(v).strip().upper() for v in cast(list[object], rumor_value))
        review = tuple(str(v).strip().upper() for v in cast(list[object], review_value))
        if set(bands) != {"HIGH", "MEDIUM", "LOW", "BLOCKED"}:
            raise ReliabilityControlError("unexpected reliability bands")
        if set(rumor) != {"CONFIRMED", "CORROBORATED", "SINGLE_SOURCE", "UNCONFIRMED"}:
            raise ReliabilityControlError("unexpected rumor states")
        if set(review) != {"ACCEPT_DESCRIPTIVE", "REVIEW_REQUIRED", "QUARANTINED"}:
            raise ReliabilityControlError("unexpected review states")

        community_rule = raw.get("community_social_review_required_without_corroboration")
        high_single_rule = raw.get("high_importance_single_source_review_required")
        if not isinstance(community_rule, bool) or not isinstance(high_single_rule, bool):
            raise ReliabilityControlError("review controls must be boolean")
        if raw.get("canonical_tests_network_required") is not False:
            raise ReliabilityControlError("canonical tests must remain offline")
        if raw.get("production_news_vendor") != "NOT_SELECTED":
            raise ReliabilityControlError("P11-E cannot select production news vendor")
        if raw.get("live_trading") != "DISABLED" or raw.get("auto_trading") != "DISABLED":
            raise ReliabilityControlError("P11-E cannot enable trading")

        return cls(
            source_class_scores=source_scores,
            admissibility_adjustments=admissibility,
            corroboration_bonus_per_source=bonus_i,
            corroboration_bonus_cap=cap_i,
            high_threshold=high_i,
            medium_threshold=medium_i,
            community_social_review_required_without_corroboration=community_rule,
            high_importance_single_source_review_required=high_single_rule,
            reliability_bands=bands,
            rumor_states=rumor,
            review_states=review,
            canonical_tests_network_required=False,
            production_news_vendor="NOT_SELECTED",
            live_trading="DISABLED",
            auto_trading="DISABLED",
        )

    def source_score(self, source_class: str) -> int:
        scores = dict(self.source_class_scores)
        try:
            return scores[source_class]
        except KeyError as exc:
            raise ReliabilityControlError("source class has no reliability score") from exc

    def admissibility_adjustment(self, state: str) -> int:
        adjustments = dict(self.admissibility_adjustments)
        try:
            return adjustments[state]
        except KeyError as exc:
            raise ReliabilityControlError("admissibility state has no reliability adjustment") from exc


@dataclass(frozen=True, slots=True)
class ReliabilityAssessment:
    news_content_id: str
    reliability_band: str
    rumor_state: str
    review_state: str
    score: int
    corroboration_count: int
    reason_codes: tuple[str, ...]


def assess_reliability(
    item: RawNewsItem,
    *,
    classification: ClassificationResult,
    source_policy: NewsSourcePolicy,
    reliability_policy: ReliabilityPolicy,
) -> ReliabilityAssessment:
    if classification.news_content_id != item.content_id:
        raise ReliabilityControlError("classification content identity mismatch")

    validate_source_record(item.source, policy=source_policy)

    source_class = item.source.source_class
    rumor_state = item.source.admissibility_state
    corroboration_count = len(item.source.corroborating_source_ids)
    reasons: set[str] = {
        f"SOURCE_CLASS:{source_class}",
        f"RUMOR_STATE:{rumor_state}",
        f"CORROBORATION_COUNT:{corroboration_count}",
    }

    if rumor_state == "UNCONFIRMED":
        reasons.add("FAIL_CLOSED:UNCONFIRMED")
        return ReliabilityAssessment(
            news_content_id=item.content_id,
            reliability_band="BLOCKED",
            rumor_state="UNCONFIRMED",
            review_state="QUARANTINED",
            score=-100,
            corroboration_count=corroboration_count,
            reason_codes=tuple(sorted(reasons)),
        )

    base_score = reliability_policy.source_score(source_class)
    adjustment = reliability_policy.admissibility_adjustment(rumor_state)
    bonus_sources = min(corroboration_count, reliability_policy.corroboration_bonus_cap)
    corroboration_bonus = bonus_sources * reliability_policy.corroboration_bonus_per_source
    score = base_score + adjustment + corroboration_bonus

    if score >= reliability_policy.high_threshold:
        band = "HIGH"
    elif score >= reliability_policy.medium_threshold:
        band = "MEDIUM"
    else:
        band = "LOW"

    review_state = "ACCEPT_DESCRIPTIVE"
    if (
        reliability_policy.community_social_review_required_without_corroboration
        and source_class in {"COMMUNITY", "SOCIAL"}
        and corroboration_count == 0
    ):
        band = "LOW"
        review_state = "REVIEW_REQUIRED"
        reasons.add("REVIEW:COMMUNITY_SOCIAL_NO_CORROBORATION")

    if (
        reliability_policy.high_importance_single_source_review_required
        and classification.importance == "HIGH"
        and rumor_state == "SINGLE_SOURCE"
    ):
        band = "LOW"
        review_state = "REVIEW_REQUIRED"
        reasons.add("REVIEW:HIGH_IMPORTANCE_SINGLE_SOURCE")

    reasons.add(f"RELIABILITY:{band}")
    reasons.add(f"REVIEW_STATE:{review_state}")
    if corroboration_bonus:
        reasons.add(f"CORROBORATION_BONUS:{corroboration_bonus}")

    return ReliabilityAssessment(
        news_content_id=item.content_id,
        reliability_band=band,
        rumor_state=rumor_state,
        review_state=review_state,
        score=score,
        corroboration_count=corroboration_count,
        reason_codes=tuple(sorted(reasons)),
    )
