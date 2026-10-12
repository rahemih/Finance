from __future__ import annotations

from dataclasses import dataclass
from math import isqrt
import json
from pathlib import Path
import re
from typing import Mapping, Sequence, cast

from .knowledge_graph import KnowledgeGraphPolicy


class HistoricalAnalogError(ValueError):
    """P12-E historical-analog policy or evidence violates governed invariants."""


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _integer(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise HistoricalAnalogError(f"{field} must be integer")
    return value


def _positive_integer(value: object, *, field: str) -> int:
    number = _integer(value, field=field)
    if number <= 0:
        raise HistoricalAnalogError(f"{field} must be positive")
    return number


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HistoricalAnalogError(f"{field} must be non-empty text")
    return value.strip()


def _sha256(value: str, *, field: str) -> str:
    text = _text(value, field=field)
    if _SHA256.fullmatch(text) is None:
        raise HistoricalAnalogError(f"{field} must be lowercase SHA-256")
    return text


@dataclass(frozen=True, slots=True)
class HistoricalAnalogPolicy:
    feature_names: tuple[str, ...]
    minimum_shared_features: int
    allowed_top_k: tuple[int, ...]
    feature_min_bps: int
    feature_max_bps: int
    similarity_min_bps: int
    similarity_max_bps: int
    uncertainty_min_bps: int
    uncertainty_max_bps: int
    exact_regime_match_required: bool
    historical_only_required: bool
    future_outcome_consumed: bool
    similarity_is_probability: bool
    canonical_tests_network_required: bool
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "HistoricalAnalogPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw_value, Mapping):
            raise HistoricalAnalogError("policy root must be object")
        raw = cast(Mapping[str, object], raw_value)
        if raw.get("schema_version") != "1.0" or raw.get("mode") != "REGIME_AWARE_HISTORICAL_ANALOG":
            raise HistoricalAnalogError("unsupported P12-E policy")

        features_value = raw.get("feature_names")
        if not isinstance(features_value, list) or not features_value:
            raise HistoricalAnalogError("feature_names must be non-empty list")
        features = tuple(str(item).strip().upper() for item in cast(list[object], features_value))
        if any(not item for item in features) or len(features) != len(set(features)):
            raise HistoricalAnalogError("feature_names must be unique non-empty values")
        required = {
            "TREND",
            "MOMENTUM",
            "VOLATILITY",
            "LIQUIDITY",
            "ORDER_FLOW",
            "MACRO",
            "NEWS",
            "CAPITAL_FLOW",
        }
        if set(features) != required:
            raise HistoricalAnalogError("feature ontology drift")

        minimum = _positive_integer(raw.get("minimum_shared_features"), field="minimum_shared_features")
        if minimum > len(features):
            raise HistoricalAnalogError("minimum_shared_features exceeds feature ontology")

        top_value = raw.get("allowed_top_k")
        if not isinstance(top_value, list) or not top_value:
            raise HistoricalAnalogError("allowed_top_k must be non-empty list")
        top_k = tuple(sorted({_positive_integer(item, field="allowed_top_k") for item in cast(list[object], top_value)}))
        if not top_k:
            raise HistoricalAnalogError("allowed_top_k must contain positive values")

        feature_min = _integer(raw.get("feature_min_bps"), field="feature_min_bps")
        feature_max = _integer(raw.get("feature_max_bps"), field="feature_max_bps")
        if (feature_min, feature_max) != (-10000, 10000):
            raise HistoricalAnalogError("feature scale must be signed basis points")

        similarity_min = _integer(raw.get("similarity_min_bps"), field="similarity_min_bps")
        similarity_max = _integer(raw.get("similarity_max_bps"), field="similarity_max_bps")
        if (similarity_min, similarity_max) != (0, 10000):
            raise HistoricalAnalogError("similarity scale must be unsigned basis points")

        uncertainty_min = _integer(raw.get("uncertainty_min_bps"), field="uncertainty_min_bps")
        uncertainty_max = _integer(raw.get("uncertainty_max_bps"), field="uncertainty_max_bps")
        if (uncertainty_min, uncertainty_max) != (0, 10000):
            raise HistoricalAnalogError("uncertainty scale must be unsigned basis points")

        for name in (
            "exact_regime_match_required",
            "historical_only_required",
            "future_outcome_consumed",
            "similarity_is_probability",
            "canonical_tests_network_required",
        ):
            if not isinstance(raw.get(name), bool):
                raise HistoricalAnalogError(f"{name} must be boolean")

        if raw.get("exact_regime_match_required") is not True:
            raise HistoricalAnalogError("P12-E requires exact regime match")
        if raw.get("historical_only_required") is not True:
            raise HistoricalAnalogError("P12-E requires historical-only candidates")
        if raw.get("future_outcome_consumed") is not False:
            raise HistoricalAnalogError("future outcome leakage is forbidden")
        if raw.get("similarity_is_probability") is not False:
            raise HistoricalAnalogError("similarity cannot be probability")
        if raw.get("canonical_tests_network_required") is not False:
            raise HistoricalAnalogError("canonical tests must remain offline")
        if raw.get("live_trading") != "DISABLED" or raw.get("auto_trading") != "DISABLED":
            raise HistoricalAnalogError("P12-E cannot enable trading")

        return cls(
            feature_names=features,
            minimum_shared_features=minimum,
            allowed_top_k=top_k,
            feature_min_bps=feature_min,
            feature_max_bps=feature_max,
            similarity_min_bps=similarity_min,
            similarity_max_bps=similarity_max,
            uncertainty_min_bps=uncertainty_min,
            uncertainty_max_bps=uncertainty_max,
            exact_regime_match_required=True,
            historical_only_required=True,
            future_outcome_consumed=False,
            similarity_is_probability=False,
            canonical_tests_network_required=False,
            live_trading="DISABLED",
            auto_trading="DISABLED",
        )


@dataclass(frozen=True, slots=True)
class HistoricalFeatureState:
    state_id: str
    as_of_ns: int
    regime_label: str
    features: tuple[tuple[str, int], ...]
    provenance_sha256: tuple[str, ...]
    source_dataset_versions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class HistoricalAnalogMatch:
    state_id: str
    as_of_ns: int
    regime_label: str
    shared_features: tuple[str, ...]
    shared_feature_count: int
    coverage_bps: int
    mean_distance_bps: int
    similarity_bps: int
    uncertainty_bps: int
    provenance_sha256: tuple[str, ...]
    source_dataset_versions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class HistoricalAnalogResult:
    query_state_id: str
    query_as_of_ns: int
    regime_label: str
    requested_top_k: int
    matches: tuple[HistoricalAnalogMatch, ...]


def validate_feature_state(
    state: HistoricalFeatureState,
    *,
    graph_policy: KnowledgeGraphPolicy,
    policy: HistoricalAnalogPolicy,
) -> HistoricalFeatureState:
    state_id = _text(state.state_id, field="state_id")
    as_of = _integer(state.as_of_ns, field="as_of_ns")
    if as_of < 0:
        raise HistoricalAnalogError("as_of_ns must be non-negative")
    regime = _text(state.regime_label, field="regime_label").upper()
    if regime not in graph_policy.regime_labels:
        raise HistoricalAnalogError("unknown regime_label")

    names: list[str] = []
    normalized_features: list[tuple[str, int]] = []
    for raw_name, raw_value in state.features:
        name = _text(raw_name, field="feature_name").upper()
        if name not in policy.feature_names:
            raise HistoricalAnalogError("unknown feature_name")
        value = _integer(raw_value, field="feature_value_bps")
        if not policy.feature_min_bps <= value <= policy.feature_max_bps:
            raise HistoricalAnalogError("feature value outside governed bounds")
        names.append(name)
        normalized_features.append((name, value))
    if len(names) != len(set(names)):
        raise HistoricalAnalogError("duplicate feature_name")
    if len(normalized_features) < policy.minimum_shared_features:
        raise HistoricalAnalogError("feature state has insufficient governed features")

    provenance = tuple(sorted({_sha256(value, field="provenance_sha256") for value in state.provenance_sha256}))
    if not provenance:
        raise HistoricalAnalogError("provenance is required")
    versions = tuple(sorted({_text(value, field="source_dataset_version") for value in state.source_dataset_versions}))
    if not versions:
        raise HistoricalAnalogError("source dataset versions are required")

    return HistoricalFeatureState(
        state_id=state_id,
        as_of_ns=as_of,
        regime_label=regime,
        features=tuple(sorted(normalized_features)),
        provenance_sha256=provenance,
        source_dataset_versions=versions,
    )


def find_historical_analogs(
    query: HistoricalFeatureState,
    candidates: Sequence[HistoricalFeatureState],
    *,
    top_k: int,
    graph_policy: KnowledgeGraphPolicy,
    policy: HistoricalAnalogPolicy,
) -> HistoricalAnalogResult:
    if top_k not in policy.allowed_top_k:
        raise HistoricalAnalogError("top_k is not governed")
    normalized_query = validate_feature_state(query, graph_policy=graph_policy, policy=policy)
    normalized_candidates = tuple(
        validate_feature_state(item, graph_policy=graph_policy, policy=policy)
        for item in candidates
    )
    if not normalized_candidates:
        raise HistoricalAnalogError("historical analog candidates must be non-empty")

    candidate_ids = [item.state_id for item in normalized_candidates]
    candidate_times = [item.as_of_ns for item in normalized_candidates]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise HistoricalAnalogError("duplicate candidate state_id")
    if len(candidate_times) != len(set(candidate_times)):
        raise HistoricalAnalogError("duplicate candidate as_of_ns")

    query_features = dict(normalized_query.features)
    matches: list[HistoricalAnalogMatch] = []
    for candidate in normalized_candidates:
        if candidate.as_of_ns >= normalized_query.as_of_ns:
            raise HistoricalAnalogError("candidate must be strictly historical")
        if policy.exact_regime_match_required and candidate.regime_label != normalized_query.regime_label:
            continue

        candidate_features = dict(candidate.features)
        shared = tuple(sorted(set(query_features) & set(candidate_features)))
        if len(shared) < policy.minimum_shared_features:
            continue

        normalized_distances = tuple(
            abs(query_features[name] - candidate_features[name]) // 2
            for name in shared
        )
        mean_distance = sum(normalized_distances) // len(normalized_distances)
        mean_distance = min(10000, max(0, mean_distance))
        similarity = 10000 - mean_distance
        coverage = (len(shared) * 10000) // len(policy.feature_names)
        sampling_uncertainty = 10000 // max(1, isqrt(len(shared)))
        uncertainty = min(
            policy.uncertainty_max_bps,
            max(policy.uncertainty_min_bps, sampling_uncertainty, 10000 - coverage),
        )
        matches.append(
            HistoricalAnalogMatch(
                state_id=candidate.state_id,
                as_of_ns=candidate.as_of_ns,
                regime_label=candidate.regime_label,
                shared_features=shared,
                shared_feature_count=len(shared),
                coverage_bps=coverage,
                mean_distance_bps=mean_distance,
                similarity_bps=similarity,
                uncertainty_bps=uncertainty,
                provenance_sha256=candidate.provenance_sha256,
                source_dataset_versions=candidate.source_dataset_versions,
            )
        )

    if not matches:
        raise HistoricalAnalogError("no historical analog satisfies governed regime/feature rules")
    ordered = tuple(
        sorted(
            matches,
            key=lambda item: (
                -item.similarity_bps,
                item.uncertainty_bps,
                -item.as_of_ns,
                item.state_id,
            ),
        )[:top_k]
    )
    return HistoricalAnalogResult(
        query_state_id=normalized_query.state_id,
        query_as_of_ns=normalized_query.as_of_ns,
        regime_label=normalized_query.regime_label,
        requested_top_k=top_k,
        matches=ordered,
    )
