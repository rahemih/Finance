from __future__ import annotations

from dataclasses import dataclass, replace
import json
from pathlib import Path
from typing import Mapping, cast

from .alerting import AlertNarrativePolicy, build_alert_narrative_input
from .classification import ClassificationPolicy, classify_news_item
from .entity_mapping import EntityRegistry, map_news_item
from .event_decay import EventDecayPolicy, assess_event_decay
from .ingestion import RawNewsItem
from .reliability import ReliabilityPolicy, assess_reliability
from .source_policy import NewsSourcePolicy, NewsSourceRecord


class AdversarialEvaluationError(ValueError):
    """Raised when P11-H evaluation policy or mandatory scenario invariants fail."""


@dataclass(frozen=True, slots=True)
class AdversarialCase:
    name: str
    source_class: str
    admissibility_state: str
    corroborating_source_ids: tuple[str, ...]
    title: str
    body: str
    published_at: str
    observed_at: str
    as_of: str
    attack: str
    expected: tuple[tuple[str, object], ...]


@dataclass(frozen=True, slots=True)
class AdversarialEvaluationPolicy:
    required_case_names: tuple[str, ...]
    cases: tuple[AdversarialCase, ...]
    required_pass_rate_bps: int
    canonical_tests_network_required: bool
    llm_required: bool
    production_news_vendor: str
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "AdversarialEvaluationPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw_value, Mapping):
            raise AdversarialEvaluationError("policy root must be an object")
        raw = cast(Mapping[str, object], raw_value)
        if raw.get("schema_version") != "1.0":
            raise AdversarialEvaluationError("unsupported adversarial policy schema_version")

        required_value = raw.get("required_case_names")
        cases_value = raw.get("cases")
        if not isinstance(required_value, list) or not required_value:
            raise AdversarialEvaluationError("required_case_names must be non-empty list")
        if not isinstance(cases_value, list) or not cases_value:
            raise AdversarialEvaluationError("cases must be non-empty list")

        required = tuple(str(value).strip() for value in cast(list[object], required_value))
        if any(not value for value in required) or len(set(required)) != len(required):
            raise AdversarialEvaluationError("required case names must be unique non-empty values")

        cases: list[AdversarialCase] = []
        for case_value in cast(list[object], cases_value):
            if not isinstance(case_value, Mapping):
                raise AdversarialEvaluationError("case must be an object")
            case_raw = cast(Mapping[str, object], case_value)
            expected_value = case_raw.get("expected")
            corroborators_value = case_raw.get("corroborating_source_ids")
            if not isinstance(expected_value, Mapping) or not expected_value:
                raise AdversarialEvaluationError("case expected must be non-empty object")
            if not isinstance(corroborators_value, list):
                raise AdversarialEvaluationError("corroborating_source_ids must be a list")

            def required_text(field: str) -> str:
                value = case_raw.get(field)
                if not isinstance(value, str) or not value.strip():
                    raise AdversarialEvaluationError(f"{field} must be non-empty text")
                return value.strip()

            expected = tuple(sorted((str(key), value) for key, value in cast(Mapping[object, object], expected_value).items()))
            cases.append(
                AdversarialCase(
                    name=required_text("name"),
                    source_class=required_text("source_class").upper(),
                    admissibility_state=required_text("admissibility_state").upper(),
                    corroborating_source_ids=tuple(str(value).strip() for value in cast(list[object], corroborators_value)),
                    title=required_text("title"),
                    body=required_text("body"),
                    published_at=required_text("published_at"),
                    observed_at=required_text("observed_at"),
                    as_of=required_text("as_of"),
                    attack=required_text("attack").upper(),
                    expected=expected,
                )
            )

        cases.sort(key=lambda case: case.name)
        case_names = tuple(case.name for case in cases)
        if set(case_names) != set(required):
            raise AdversarialEvaluationError("cases must exactly match required_case_names")
        if len(case_names) != len(set(case_names)):
            raise AdversarialEvaluationError("case names must be unique")
        if any(case.attack not in {"NONE", "TAMPER_CLASSIFICATION_ID"} for case in cases):
            raise AdversarialEvaluationError("unsupported adversarial attack")

        pass_rate = raw.get("required_pass_rate_bps")
        if not isinstance(pass_rate, int) or isinstance(pass_rate, bool) or pass_rate != 10000:
            raise AdversarialEvaluationError("P11-H requires 10000 bps pass rate")
        if raw.get("canonical_tests_network_required") is not False:
            raise AdversarialEvaluationError("canonical tests must remain offline")
        if raw.get("llm_required") is not False:
            raise AdversarialEvaluationError("P11-H canonical evaluation cannot require an LLM")
        if raw.get("production_news_vendor") != "NOT_SELECTED":
            raise AdversarialEvaluationError("P11-H cannot select production news vendor")
        if raw.get("live_trading") != "DISABLED" or raw.get("auto_trading") != "DISABLED":
            raise AdversarialEvaluationError("P11-H cannot enable trading")

        return cls(
            required_case_names=tuple(sorted(required)),
            cases=tuple(cases),
            required_pass_rate_bps=10000,
            canonical_tests_network_required=False,
            llm_required=False,
            production_news_vendor="NOT_SELECTED",
            live_trading="DISABLED",
            auto_trading="DISABLED",
        )


@dataclass(frozen=True, slots=True)
class AdversarialCaseResult:
    name: str
    passed: bool
    expected: tuple[tuple[str, object], ...]
    actual: tuple[tuple[str, object], ...]

    def payload(self) -> dict[str, object]:
        return {
            "name": self.name,
            "passed": self.passed,
            "expected": dict(self.expected),
            "actual": dict(self.actual),
        }


@dataclass(frozen=True, slots=True)
class AdversarialEvaluationReport:
    results: tuple[AdversarialCaseResult, ...]

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for result in self.results if result.passed)

    @property
    def failed(self) -> int:
        return self.total - self.passed

    @property
    def pass_rate_bps(self) -> int:
        if self.total == 0:
            return 0
        return (self.passed * 10000) // self.total

    @property
    def all_passed(self) -> bool:
        return self.failed == 0 and self.total > 0

    def payload(self) -> dict[str, object]:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "pass_rate_bps": self.pass_rate_bps,
            "all_passed": self.all_passed,
            "results": [result.payload() for result in self.results],
        }


@dataclass(frozen=True, slots=True)
class P11EvaluationDependencies:
    source_policy: NewsSourcePolicy
    registry: EntityRegistry
    classification_policy: ClassificationPolicy
    reliability_policy: ReliabilityPolicy
    decay_policy: EventDecayPolicy
    alert_policy: AlertNarrativePolicy


def _matches_expected(actual: Mapping[str, object], expected: tuple[tuple[str, object], ...]) -> bool:
    for key, value in expected:
        if key not in actual or actual[key] != value:
            return False
    return True


def evaluate_case(case: AdversarialCase, *, deps: P11EvaluationDependencies) -> AdversarialCaseResult:
    expected = case.expected
    try:
        source = NewsSourceRecord(
            source_id=f"adversarial:{case.name}",
            source_class=case.source_class,
            source_name=f"Adversarial {case.name}",
            source_url=f"https://example.gov/news/{case.name}",
            access_kind="PUBLIC",
            license_state="ATTRIBUTION_REQUIRED",
            admissibility_state=case.admissibility_state,
            attribution=f"Adversarial {case.name}",
            published_at=case.published_at,
            observed_at=case.observed_at,
            corroborating_source_ids=case.corroborating_source_ids,
        )
        item = RawNewsItem(source=source, title=case.title, body=case.body)
        mapping = map_news_item(item, registry=deps.registry)
        classification = classify_news_item(item, mapping=mapping, policy=deps.classification_policy)
        if case.attack == "TAMPER_CLASSIFICATION_ID":
            classification = replace(classification, news_content_id="tampered-content-id")
        reliability = assess_reliability(
            item,
            classification=classification,
            source_policy=deps.source_policy,
            reliability_policy=deps.reliability_policy,
        )
        decay = assess_event_decay(
            item,
            classification=classification,
            reliability=reliability,
            policy=deps.decay_policy,
            as_of=case.as_of,
        )
        alert = build_alert_narrative_input(
            item,
            classification=classification,
            reliability=reliability,
            decay=decay,
            policy=deps.alert_policy,
        )
        actual_map: dict[str, object] = {
            "mapping_state": mapping.state,
            "entity_ids": list(classification.entity_ids),
            "sentiment": classification.sentiment,
            "importance": classification.importance,
            "reliability_band": reliability.reliability_band,
            "rumor_state": reliability.rumor_state,
            "review_state": reliability.review_state,
            "freshness_state": decay.freshness_state,
            "eligible": alert.eligible,
            "severity": alert.severity,
        }
    except ValueError as exc:
        actual_map = {"error": type(exc).__name__}

    actual = tuple(sorted(actual_map.items()))
    return AdversarialCaseResult(
        name=case.name,
        passed=_matches_expected(actual_map, expected),
        expected=expected,
        actual=actual,
    )


def run_adversarial_evaluation(
    policy: AdversarialEvaluationPolicy,
    *,
    deps: P11EvaluationDependencies,
) -> AdversarialEvaluationReport:
    results = tuple(evaluate_case(case, deps=deps) for case in policy.cases)
    report = AdversarialEvaluationReport(results=results)
    if report.pass_rate_bps < policy.required_pass_rate_bps:
        return report
    return report
