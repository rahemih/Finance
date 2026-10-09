from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
import hashlib
import json
from itertools import combinations
from pathlib import Path
import re
from typing import Mapping, cast


class CrossProviderError(ValueError):
    """Cross-provider comparison policy or input is invalid."""


class CrossProviderOutcome(StrEnum):
    VALID = "VALID"
    INVALID_CRITICAL = "INVALID_CRITICAL"


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise CrossProviderError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise CrossProviderError(f"{field} must be a positive integer")
    return value


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True, slots=True)
class CrossProviderPolicy:
    max_observations_per_batch: int
    coverage_scale_bps: int
    relative_denominator_epsilon: Decimal
    production_data_quality_vendor: str

    @classmethod
    def from_path(cls, path: Path) -> "CrossProviderPolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise CrossProviderError(f"invalid cross-provider policy JSON: {exc}") from exc
        raw = _mapping(raw_value, field="root")
        if raw.get("schema_version") != "1.0":
            raise CrossProviderError("unsupported policy schema_version")
        if raw.get("mode") != "ALIGNED_SAMPLE_SEMANTIC_FAMILY_PAIRWISE":
            raise CrossProviderError("unsupported comparison mode")
        if raw.get("critical_outcome") != "INVALID_CRITICAL":
            raise CrossProviderError("critical comparison violations must fail closed")
        if raw.get("network_required") is not False or raw.get("credentials_required") is not False:
            raise CrossProviderError("reference comparison must be offline")
        epsilon_raw = raw.get("relative_denominator_epsilon")
        if not isinstance(epsilon_raw, str):
            raise CrossProviderError("relative_denominator_epsilon must be a decimal string")
        epsilon = Decimal(epsilon_raw)
        if not epsilon.is_finite() or epsilon <= 0:
            raise CrossProviderError("relative_denominator_epsilon must be positive and finite")
        vendor = raw.get("production_data_quality_vendor")
        if not isinstance(vendor, str) or not vendor.strip():
            raise CrossProviderError("production_data_quality_vendor must be non-empty")
        return cls(
            max_observations_per_batch=_positive_int(raw.get("max_observations_per_batch"), field="max_observations_per_batch"),
            coverage_scale_bps=_positive_int(raw.get("coverage_scale_bps"), field="coverage_scale_bps"),
            relative_denominator_epsilon=epsilon,
            production_data_quality_vendor=vendor.strip(),
        )


@dataclass(frozen=True, slots=True)
class ProviderObservation:
    sample_id: str
    canonical_id: str
    metric: str
    comparison_family: str
    provider: str
    value: Decimal
    coverage_bps: int
    upstream_quality_evidence_sha256: str

    def __post_init__(self) -> None:
        for field, value in (
            ("sample_id", self.sample_id),
            ("canonical_id", self.canonical_id),
            ("metric", self.metric),
            ("comparison_family", self.comparison_family),
            ("provider", self.provider),
        ):
            if not value.strip():
                raise CrossProviderError(f"{field} must be non-empty")
        if not self.value.is_finite():
            raise CrossProviderError("observation value must be finite")
        if isinstance(self.coverage_bps, bool) or self.coverage_bps < 0 or self.coverage_bps > 10000:
            raise CrossProviderError("coverage_bps must be between 0 and 10000")
        if _SHA256.fullmatch(self.upstream_quality_evidence_sha256) is None:
            raise CrossProviderError("upstream quality evidence must be lowercase SHA-256")


@dataclass(frozen=True, slots=True)
class ComparisonRule:
    metric: str
    comparison_family: str
    min_provider_count: int
    min_coverage_bps: int
    max_abs_diff: Decimal | None = None
    max_rel_diff: Decimal | None = None

    def __post_init__(self) -> None:
        if not self.metric.strip() or not self.comparison_family.strip():
            raise CrossProviderError("comparison rule metric/family must be non-empty")
        if isinstance(self.min_provider_count, bool) or self.min_provider_count < 2:
            raise CrossProviderError("min_provider_count must be >= 2")
        if isinstance(self.min_coverage_bps, bool) or not (0 <= self.min_coverage_bps <= 10000):
            raise CrossProviderError("min_coverage_bps must be between 0 and 10000")
        if self.max_abs_diff is None and self.max_rel_diff is None:
            raise CrossProviderError("comparison rule must define at least one divergence threshold")
        if self.max_abs_diff is not None and (not self.max_abs_diff.is_finite() or self.max_abs_diff < 0):
            raise CrossProviderError("max_abs_diff must be finite and non-negative")
        if self.max_rel_diff is not None and (not self.max_rel_diff.is_finite() or self.max_rel_diff < 0):
            raise CrossProviderError("max_rel_diff must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class CrossProviderIssue:
    code: str
    group_key: str
    providers: tuple[str, ...]
    message: str

    def payload(self) -> dict[str, object]:
        return {
            "code": self.code,
            "group_key": self.group_key,
            "providers": list(self.providers),
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class CrossProviderReport:
    outcome: CrossProviderOutcome
    groups_evaluated: int
    issues: tuple[CrossProviderIssue, ...]
    semantic_families: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.outcome is CrossProviderOutcome.VALID

    @property
    def fingerprint(self) -> str:
        payload = {
            "schema_version": "1.0",
            "outcome": self.outcome.value,
            "groups_evaluated": self.groups_evaluated,
            "issues": [issue.payload() for issue in self.issues],
            "semantic_families": list(self.semantic_families),
        }
        return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _rule_key(metric: str, family: str) -> str:
    return f"{metric}|{family}"


def _group_key(value: ProviderObservation) -> str:
    return "|".join((value.sample_id, value.canonical_id, value.metric, value.comparison_family))


class CrossProviderAnalyzer:
    def __init__(self, policy: CrossProviderPolicy) -> None:
        self._policy = policy

    def analyze(
        self,
        observations: tuple[ProviderObservation, ...],
        rules: tuple[ComparisonRule, ...],
    ) -> CrossProviderReport:
        if len(observations) > self._policy.max_observations_per_batch:
            raise CrossProviderError("observation count exceeds policy maximum")

        rule_map = {_rule_key(rule.metric, rule.comparison_family): rule for rule in rules}
        if len(rule_map) != len(rules):
            raise CrossProviderError("comparison rules must be unique by metric/family")

        groups: dict[str, list[ProviderObservation]] = {}
        families: set[str] = set()
        for observation in observations:
            groups.setdefault(_group_key(observation), []).append(observation)
            families.add(observation.comparison_family)

        issues: list[CrossProviderIssue] = []
        groups_evaluated = 0

        for key, values in sorted(groups.items()):
            first = values[0]
            rule = rule_map.get(_rule_key(first.metric, first.comparison_family))
            providers = tuple(sorted(value.provider for value in values))
            if rule is None:
                issues.append(
                    CrossProviderIssue(
                        code="MISSING_COMPARISON_RULE",
                        group_key=key,
                        providers=providers,
                        message="no explicit rule for metric/comparison family",
                    )
                )
                continue

            provider_names = [value.provider for value in values]
            if len(provider_names) != len(set(provider_names)):
                issues.append(
                    CrossProviderIssue(
                        code="DUPLICATE_PROVIDER_OBSERVATION",
                        group_key=key,
                        providers=tuple(sorted(set(provider_names))),
                        message="provider appears more than once in aligned comparison group",
                    )
                )
                continue

            eligible = tuple(
                sorted(
                    (value for value in values if value.coverage_bps >= rule.min_coverage_bps),
                    key=lambda value: value.provider,
                )
            )
            if len(eligible) < rule.min_provider_count:
                issues.append(
                    CrossProviderIssue(
                        code="INSUFFICIENT_PROVIDER_COVERAGE",
                        group_key=key,
                        providers=tuple(value.provider for value in eligible),
                        message="eligible independent-provider count is below explicit minimum",
                    )
                )
                continue

            groups_evaluated += 1
            for left, right in combinations(eligible, 2):
                abs_diff = abs(left.value - right.value)
                pair = (left.provider, right.provider)
                if rule.max_abs_diff is not None and abs_diff > rule.max_abs_diff:
                    issues.append(
                        CrossProviderIssue(
                            code="ABS_DIVERGENCE",
                            group_key=key,
                            providers=pair,
                            message="absolute provider divergence exceeds explicit threshold",
                        )
                    )
                denominator = max(abs(left.value), abs(right.value), self._policy.relative_denominator_epsilon)
                rel_diff = abs_diff / denominator
                if rule.max_rel_diff is not None and rel_diff > rule.max_rel_diff:
                    issues.append(
                        CrossProviderIssue(
                            code="REL_DIVERGENCE",
                            group_key=key,
                            providers=pair,
                            message="relative provider divergence exceeds explicit threshold",
                        )
                    )

        ordered = tuple(sorted(issues, key=lambda item: (item.code, item.group_key, item.providers, item.message)))
        outcome = CrossProviderOutcome.INVALID_CRITICAL if ordered else CrossProviderOutcome.VALID
        return CrossProviderReport(
            outcome=outcome,
            groups_evaluated=groups_evaluated,
            issues=ordered,
            semantic_families=tuple(sorted(families)),
        )
