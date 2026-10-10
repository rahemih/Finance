from __future__ import annotations

from dataclasses import dataclass, fields
import hashlib
import json
from pathlib import Path
from typing import Mapping, cast

from .volume_ontology import (
    VolumeObservation,
    VolumeProxyPolicy,
    validate_volume_observation,
)


class ForexProxyCoverageError(ValueError):
    """Raised when P09-G proxy coverage-confidence invariants fail closed."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ForexProxyCoverageError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _object_list(value: object, *, field: str) -> list[object]:
    if not isinstance(value, list):
        raise ForexProxyCoverageError(f"{field} must be a list")
    return cast(list[object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ForexProxyCoverageError(f"{field} must be non-empty text")
    return value.strip()


def _boolean(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise ForexProxyCoverageError(f"{field} must be boolean")
    return value


def _bps(value: object, *, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 10_000:
        raise ForexProxyCoverageError(f"{field} must be integer basis points in [0,10000]")
    return value


def _sha256_text(value: object, *, field: str) -> str:
    text = _text(value, field=field).lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise ForexProxyCoverageError(f"{field} must be lowercase sha256 hex")
    return text


@dataclass(frozen=True, slots=True)
class ForexProxyCoveragePolicy:
    required_market_class: str
    required_components: tuple[str, ...]
    benchmark_agreement_required: bool
    confidence_aggregation: str
    global_market_share_claim_allowed: bool
    cross_provider_aggregation_allowed: bool
    weighted_confidence_score_allowed: bool
    direct_trade_output_allowed: bool
    production_fx_order_flow_vendor: str

    @classmethod
    def from_path(cls, path: Path) -> "ForexProxyCoveragePolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        raw = _mapping(raw_value, field="policy root")
        if raw.get("schema_version") != "1.0":
            raise ForexProxyCoverageError("unsupported policy schema_version")

        market_class = _text(raw.get("required_market_class"), field="required_market_class")
        components = tuple(
            _text(item, field="required_component").upper()
            for item in _object_list(raw.get("required_components"), field="required_components")
        )
        benchmark_required = _boolean(
            raw.get("benchmark_agreement_required"),
            field="benchmark_agreement_required",
        )
        aggregation = _text(raw.get("confidence_aggregation"), field="confidence_aggregation").upper()
        market_share = _boolean(
            raw.get("global_market_share_claim_allowed"),
            field="global_market_share_claim_allowed",
        )
        cross_provider = _boolean(
            raw.get("cross_provider_aggregation_allowed"),
            field="cross_provider_aggregation_allowed",
        )
        weighted = _boolean(
            raw.get("weighted_confidence_score_allowed"),
            field="weighted_confidence_score_allowed",
        )
        direct = _boolean(raw.get("direct_trade_output_allowed"), field="direct_trade_output_allowed")
        vendor = _text(
            raw.get("production_fx_order_flow_vendor"),
            field="production_fx_order_flow_vendor",
        )

        expected = {"PROVIDER_SCOPE", "INTERNAL_COMPLETENESS", "FRESHNESS"}
        if set(components) != expected or len(components) != len(expected):
            raise ForexProxyCoverageError("P09-G required confidence components are fixed")
        if market_class != "FOREX_SPOT":
            raise ForexProxyCoverageError("P09-G requires FOREX_SPOT")
        if aggregation != "CONSERVATIVE_MINIMUM":
            raise ForexProxyCoverageError("P09-G requires conservative-minimum aggregation")
        if market_share:
            raise ForexProxyCoverageError("P09-G forbids global FX market-share claims")
        if cross_provider:
            raise ForexProxyCoverageError("P09-G forbids cross-provider aggregation")
        if weighted:
            raise ForexProxyCoverageError("P09-G forbids arbitrary weighted confidence scores")
        if direct:
            raise ForexProxyCoverageError("P09-G forbids direct trade output")

        return cls(
            required_market_class=market_class,
            required_components=components,
            benchmark_agreement_required=benchmark_required,
            confidence_aggregation=aggregation,
            global_market_share_claim_allowed=market_share,
            cross_provider_aggregation_allowed=cross_provider,
            weighted_confidence_score_allowed=weighted,
            direct_trade_output_allowed=direct,
            production_fx_order_flow_vendor=vendor,
        )


@dataclass(frozen=True, slots=True)
class ForexProxyCoverageInputs:
    provider_scope_confidence_bps: int
    provider_scope_evidence_sha256: str
    internal_completeness_confidence_bps: int
    internal_completeness_evidence_sha256: str
    freshness_confidence_bps: int
    freshness_evidence_sha256: str
    benchmark_agreement_confidence_bps: int | None = None
    benchmark_agreement_evidence_sha256: str | None = None

    def normalized(self) -> "ForexProxyCoverageInputs":
        provider_scope_bps = _bps(
            self.provider_scope_confidence_bps,
            field="provider_scope_confidence_bps",
        )
        completeness_bps = _bps(
            self.internal_completeness_confidence_bps,
            field="internal_completeness_confidence_bps",
        )
        freshness_bps = _bps(
            self.freshness_confidence_bps,
            field="freshness_confidence_bps",
        )
        provider_scope_sha = _sha256_text(
            self.provider_scope_evidence_sha256,
            field="provider_scope_evidence_sha256",
        )
        completeness_sha = _sha256_text(
            self.internal_completeness_evidence_sha256,
            field="internal_completeness_evidence_sha256",
        )
        freshness_sha = _sha256_text(
            self.freshness_evidence_sha256,
            field="freshness_evidence_sha256",
        )

        benchmark_bps = self.benchmark_agreement_confidence_bps
        benchmark_sha = self.benchmark_agreement_evidence_sha256
        if (benchmark_bps is None) != (benchmark_sha is None):
            raise ForexProxyCoverageError(
                "benchmark confidence and evidence digest must be both present or both absent"
            )
        normalized_benchmark_bps: int | None = None
        normalized_benchmark_sha: str | None = None
        if benchmark_bps is not None and benchmark_sha is not None:
            normalized_benchmark_bps = _bps(
                benchmark_bps,
                field="benchmark_agreement_confidence_bps",
            )
            normalized_benchmark_sha = _sha256_text(
                benchmark_sha,
                field="benchmark_agreement_evidence_sha256",
            )

        return ForexProxyCoverageInputs(
            provider_scope_confidence_bps=provider_scope_bps,
            provider_scope_evidence_sha256=provider_scope_sha,
            internal_completeness_confidence_bps=completeness_bps,
            internal_completeness_evidence_sha256=completeness_sha,
            freshness_confidence_bps=freshness_bps,
            freshness_evidence_sha256=freshness_sha,
            benchmark_agreement_confidence_bps=normalized_benchmark_bps,
            benchmark_agreement_evidence_sha256=normalized_benchmark_sha,
        )

    def payload(self) -> dict[str, object]:
        return {
            "provider_scope_confidence_bps": self.provider_scope_confidence_bps,
            "provider_scope_evidence_sha256": self.provider_scope_evidence_sha256,
            "internal_completeness_confidence_bps": self.internal_completeness_confidence_bps,
            "internal_completeness_evidence_sha256": self.internal_completeness_evidence_sha256,
            "freshness_confidence_bps": self.freshness_confidence_bps,
            "freshness_evidence_sha256": self.freshness_evidence_sha256,
            "benchmark_agreement_confidence_bps": self.benchmark_agreement_confidence_bps,
            "benchmark_agreement_evidence_sha256": self.benchmark_agreement_evidence_sha256,
        }


@dataclass(frozen=True, slots=True)
class ForexProxyCoverageAssessment:
    observation_id: str
    symbol: str
    provider: str
    venue: str
    volume_kind: str
    coverage_scope: str
    proxy_target: str
    as_of_time_ns: int
    declared_coverage_confidence_bps: int
    provider_scope_confidence_bps: int
    internal_completeness_confidence_bps: int
    freshness_confidence_bps: int
    benchmark_agreement_confidence_bps: int | None
    validated_proxy_coverage_confidence_bps: int
    confidence_semantics: str
    global_market_share_claimed: bool
    evidence_inputs: ForexProxyCoverageInputs

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "observation_id": self.observation_id,
            "symbol": self.symbol,
            "provider": self.provider,
            "venue": self.venue,
            "volume_kind": self.volume_kind,
            "coverage_scope": self.coverage_scope,
            "proxy_target": self.proxy_target,
            "as_of_time_ns": self.as_of_time_ns,
            "declared_coverage_confidence_bps": self.declared_coverage_confidence_bps,
            "provider_scope_confidence_bps": self.provider_scope_confidence_bps,
            "internal_completeness_confidence_bps": self.internal_completeness_confidence_bps,
            "freshness_confidence_bps": self.freshness_confidence_bps,
            "benchmark_agreement_confidence_bps": self.benchmark_agreement_confidence_bps,
            "validated_proxy_coverage_confidence_bps": self.validated_proxy_coverage_confidence_bps,
            "confidence_semantics": self.confidence_semantics,
            "global_market_share_claimed": self.global_market_share_claimed,
            "evidence_inputs": self.evidence_inputs.payload(),
        }

    @property
    def assessment_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


def assess_forex_proxy_coverage(
    observation: VolumeObservation,
    *,
    evidence: ForexProxyCoverageInputs,
    coverage_policy: ForexProxyCoveragePolicy,
    volume_policy: VolumeProxyPolicy,
) -> ForexProxyCoverageAssessment:
    validated_observation = validate_volume_observation(observation, policy=volume_policy)
    if validated_observation.market_class != coverage_policy.required_market_class:
        raise ForexProxyCoverageError("P09-G accepts FOREX_SPOT observations only")
    if not validated_observation.is_proxy:
        raise ForexProxyCoverageError("P09-G accepts explicit spot-FX proxy observations only")

    normalized = evidence.normalized()
    if (
        coverage_policy.benchmark_agreement_required
        and normalized.benchmark_agreement_confidence_bps is None
    ):
        raise ForexProxyCoverageError("benchmark agreement evidence is required by policy")

    confidence_components = [
        validated_observation.coverage_confidence_bps,
        normalized.provider_scope_confidence_bps,
        normalized.internal_completeness_confidence_bps,
        normalized.freshness_confidence_bps,
    ]
    if normalized.benchmark_agreement_confidence_bps is not None:
        confidence_components.append(normalized.benchmark_agreement_confidence_bps)

    validated_confidence = min(confidence_components)

    return ForexProxyCoverageAssessment(
        observation_id=validated_observation.observation_id,
        symbol=validated_observation.symbol,
        provider=validated_observation.provider,
        venue=validated_observation.venue,
        volume_kind=validated_observation.volume_kind,
        coverage_scope=validated_observation.coverage_scope,
        proxy_target=validated_observation.proxy_target,
        as_of_time_ns=validated_observation.as_of_time_ns,
        declared_coverage_confidence_bps=validated_observation.coverage_confidence_bps,
        provider_scope_confidence_bps=normalized.provider_scope_confidence_bps,
        internal_completeness_confidence_bps=normalized.internal_completeness_confidence_bps,
        freshness_confidence_bps=normalized.freshness_confidence_bps,
        benchmark_agreement_confidence_bps=normalized.benchmark_agreement_confidence_bps,
        validated_proxy_coverage_confidence_bps=validated_confidence,
        confidence_semantics="PROXY_SCOPE_CONFIDENCE_NOT_GLOBAL_MARKET_SHARE",
        global_market_share_claimed=False,
        evidence_inputs=normalized,
    )


def assert_no_global_share_or_trade_authority_fields() -> None:
    forbidden = {
        "global_market_share_bps",
        "global_market_share_percent",
        "global_volume_share",
        "order",
        "quantity",
        "leverage",
        "stop_loss",
        "take_profit",
        "recommendation",
        "probability",
        "entry",
        "exit",
    }
    contract_fields = (
        {field.name for field in fields(ForexProxyCoverageInputs)}
        | {field.name for field in fields(ForexProxyCoverageAssessment)}
    )
    if forbidden & contract_fields:
        raise ForexProxyCoverageError(
            "P09-G contracts must not expose global-market-share or trade-authority fields"
        )
