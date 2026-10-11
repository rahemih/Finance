from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Mapping, cast


class P10ValidationError(ValueError):
    """Raised when the P10-H validation policy is invalid."""


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise P10ValidationError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise P10ValidationError(f"{field} must be non-empty text")
    return value.strip()


def _boolean(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise P10ValidationError(f"{field} must be boolean")
    return value


def _positive_int(value: object, *, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise P10ValidationError(f"{field} must be a positive integer")
    return value


@dataclass(frozen=True, slots=True)
class RequiredP10Workstream:
    workstream: str
    task_id: str
    document: str


@dataclass(frozen=True, slots=True)
class P10ValidationPolicy:
    required_phase: str
    required_workstreams: tuple[RequiredP10Workstream, ...]
    required_state: str
    required_lock: str
    required_country_assumption: str
    required_live_trading: str
    required_auto_trading: str
    performance_semantics: str
    p10_unit_suite_max_seconds: int
    network_required: bool
    production_slo_certified: bool
    production_provider_performance_certified: bool
    profitability_certified: bool
    trade_success_probability_certified: bool
    production_execution_certified: bool
    next_phase: str
    next_phase_state: str

    @classmethod
    def from_path(cls, path: Path) -> "P10ValidationPolicy":
        root = _mapping(json.loads(path.read_text(encoding="utf-8")), field="policy root")
        if root.get("schema_version") != "1.0":
            raise P10ValidationError("unsupported policy schema_version")
        raw_items = root.get("required_workstreams")
        if not isinstance(raw_items, list):
            raise P10ValidationError("required_workstreams must be a list")
        items: list[RequiredP10Workstream] = []
        for raw_item in raw_items:
            item = _mapping(raw_item, field="required_workstream")
            items.append(RequiredP10Workstream(
                workstream=_text(item.get("workstream"), field="workstream"),
                task_id=_text(item.get("task_id"), field="task_id"),
                document=_text(item.get("document"), field="document"),
            ))
        if [x.workstream for x in items] != [f"P10-{c}" for c in "ABCDEFG"]:
            raise P10ValidationError("P10-H requires exactly ordered P10-A..P10-G prerequisites")
        performance = _mapping(root.get("performance"), field="performance")
        semantics = _mapping(root.get("validation_semantics"), field="validation_semantics")
        performance_semantics = _text(performance.get("semantics"), field="performance.semantics")
        if performance_semantics != "CI_REGRESSION_BUDGET_NOT_PRODUCTION_SLO":
            raise P10ValidationError("P10-H performance semantics must remain CI-only")
        network_required = _boolean(performance.get("network_required"), field="performance.network_required")
        production_slo = _boolean(performance.get("production_slo_certified"), field="performance.production_slo_certified")
        provider_perf = _boolean(performance.get("production_provider_performance_certified"), field="performance.production_provider_performance_certified")
        profitability = _boolean(semantics.get("profitability_certified"), field="validation_semantics.profitability_certified")
        trade_probability = _boolean(semantics.get("trade_success_probability_certified"), field="validation_semantics.trade_success_probability_certified")
        execution = _boolean(semantics.get("production_execution_certified"), field="validation_semantics.production_execution_certified")
        semantic_provider_perf = _boolean(semantics.get("production_provider_performance_certified"), field="validation_semantics.production_provider_performance_certified")
        if network_required or production_slo or provider_perf or profitability or trade_probability or execution or semantic_provider_perf:
            raise P10ValidationError("P10-H cannot certify network, production or trading performance")
        next_phase = _text(root.get("next_phase"), field="next_phase")
        next_state = _text(root.get("next_phase_state"), field="next_phase_state")
        if next_phase != "P11" or next_state != "OWNER_PHASE_AUTHORIZATION_REQUIRED":
            raise P10ValidationError("P10-H must leave P11 behind Owner phase authorization")
        return cls(
            required_phase=_text(root.get("required_phase"), field="required_phase"),
            required_workstreams=tuple(items),
            required_state=_text(root.get("required_state"), field="required_state"),
            required_lock=_text(root.get("required_lock"), field="required_lock"),
            required_country_assumption=_text(root.get("required_country_assumption"), field="required_country_assumption"),
            required_live_trading=_text(root.get("required_live_trading"), field="required_live_trading"),
            required_auto_trading=_text(root.get("required_auto_trading"), field="required_auto_trading"),
            performance_semantics=performance_semantics,
            p10_unit_suite_max_seconds=_positive_int(performance.get("p10_unit_suite_max_seconds"), field="performance.p10_unit_suite_max_seconds"),
            network_required=network_required,
            production_slo_certified=production_slo,
            production_provider_performance_certified=provider_perf,
            profitability_certified=profitability,
            trade_success_probability_certified=trade_probability,
            production_execution_certified=execution,
            next_phase=next_phase,
            next_phase_state=next_state,
        )


@dataclass(frozen=True, slots=True)
class P10ValidationIssue:
    code: str
    document: str
    detail: str

    def payload(self) -> dict[str, str]:
        return {"code": self.code, "document": self.document, "detail": self.detail}


@dataclass(frozen=True, slots=True)
class P10ValidationReport:
    outcome: str
    issues: tuple[P10ValidationIssue, ...]
    certified_task_ids: tuple[str, ...]
    document_sha256s: tuple[tuple[str, str], ...]
    performance_semantics: str
    next_phase: str
    next_phase_state: str

    @property
    def fingerprint(self) -> str:
        payload = {
            "outcome": self.outcome,
            "issues": [x.payload() for x in self.issues],
            "certified_task_ids": list(self.certified_task_ids),
            "document_sha256s": [{"document": p, "sha256": d} for p, d in self.document_sha256s],
            "performance_semantics": self.performance_semantics,
            "next_phase": self.next_phase,
            "next_phase_state": self.next_phase_state,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class P10ValidationEvaluator:
    _forbidden_true = (
        "direct_trade_output_allowed",
        "market_direction_interpretation_allowed",
        "bullish_bearish_interpretation_allowed",
        "causal_market_impact_claim_allowed",
        "signal_probability_allowed",
        "production_slo_certified",
        "production_provider_performance_certified",
    )

    def __init__(self, policy: P10ValidationPolicy) -> None:
        self.policy = policy

    def evaluate(self, documents: Mapping[str, bytes]) -> P10ValidationReport:
        issues: list[P10ValidationIssue] = []
        certified: list[str] = []
        required = {x.document for x in self.policy.required_workstreams}
        for path in sorted(required - set(documents)):
            issues.append(P10ValidationIssue("MISSING_DOCUMENT", path, "required prerequisite is absent"))
        for path in sorted(set(documents) - required):
            issues.append(P10ValidationIssue("UNEXPECTED_DOCUMENT", path, "input set must contain exactly P10-A..P10-G"))
        digests = tuple(sorted((p, hashlib.sha256(v).hexdigest()) for p, v in documents.items()))
        for item in self.policy.required_workstreams:
            content = documents.get(item.document)
            if content is None:
                continue
            before = len(issues)
            try:
                raw = _mapping(json.loads(content.decode("utf-8")), field=item.document)
            except (UnicodeDecodeError, json.JSONDecodeError, P10ValidationError) as exc:
                issues.append(P10ValidationIssue("MALFORMED_DOCUMENT", item.document, str(exc)))
                continue
            expected = {
                "schema_version": "1.0",
                "task_id": item.task_id,
                "workstream": item.workstream,
                "phase": self.policy.required_phase,
                "state": self.policy.required_state,
                "lock": self.policy.required_lock,
                "country_assumption": self.policy.required_country_assumption,
                "live_trading": self.policy.required_live_trading,
                "auto_trading": self.policy.required_auto_trading,
            }
            for field, value in expected.items():
                if raw.get(field) != value:
                    issues.append(P10ValidationIssue("INVARIANT_DRIFT", item.document, f"{field} must equal {value!r}"))
            closure = raw.get("canonical_closure")
            if not isinstance(closure, Mapping):
                issues.append(P10ValidationIssue("MISSING_CLOSURE_EVIDENCE", item.document, "canonical_closure is required"))
            for field in self._forbidden_true:
                if raw.get(field) is True:
                    issues.append(P10ValidationIssue("SAFETY_BOUNDARY_DRIFT", item.document, f"{field} must not be true"))
            if len(issues) == before:
                certified.append(item.task_id)
        return P10ValidationReport(
            outcome="PASS" if not issues else "FAIL",
            issues=tuple(issues),
            certified_task_ids=tuple(certified),
            document_sha256s=digests,
            performance_semantics=self.policy.performance_semantics,
            next_phase=self.policy.next_phase,
            next_phase_state=self.policy.next_phase_state,
        )
