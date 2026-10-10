from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Mapping, cast


class P09ValidationError(ValueError):
    """Raised when the P09-H validation policy itself is invalid."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise P09ValidationError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _object_list(value: object, *, field: str) -> list[object]:
    if not isinstance(value, list):
        raise P09ValidationError(f"{field} must be a list")
    return cast(list[object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise P09ValidationError(f"{field} must be non-empty text")
    return value.strip()


def _boolean(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise P09ValidationError(f"{field} must be boolean")
    return value


def _positive_int(value: object, *, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise P09ValidationError(f"{field} must be a positive integer")
    return value


def _hex_text(value: object, *, field: str, length: int) -> str:
    text = _text(value, field=field).lower()
    if len(text) != length or any(ch not in "0123456789abcdef" for ch in text):
        raise P09ValidationError(f"{field} must be {length}-character lowercase hex")
    return text


@dataclass(frozen=True, slots=True)
class RequiredP09Workstream:
    workstream: str
    task_id: str
    document: str


@dataclass(frozen=True, slots=True)
class P09ValidationPolicy:
    required_phase: str
    required_workstreams: tuple[RequiredP09Workstream, ...]
    required_state: str
    required_lock: str
    required_country_assumption: str
    required_live_trading: str
    required_auto_trading: str
    performance_semantics: str
    p09_unit_suite_max_seconds: int
    network_required: bool
    production_slo_certified: bool
    profitability_certified: bool
    trade_success_probability_certified: bool
    production_execution_certified: bool
    production_provider_performance_certified: bool
    next_phase: str
    next_phase_state: str

    @classmethod
    def from_path(cls, path: Path) -> "P09ValidationPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        raw = _mapping(raw_value, field="policy root")
        if raw.get("schema_version") != "1.0":
            raise P09ValidationError("unsupported policy schema_version")

        workstreams: list[RequiredP09Workstream] = []
        for item_value in _object_list(raw.get("required_workstreams"), field="required_workstreams"):
            item = _mapping(item_value, field="required_workstream")
            workstreams.append(
                RequiredP09Workstream(
                    workstream=_text(item.get("workstream"), field="workstream"),
                    task_id=_text(item.get("task_id"), field="task_id"),
                    document=_text(item.get("document"), field="document"),
                )
            )
        if len(workstreams) != 7:
            raise P09ValidationError("P09-H requires exactly seven prerequisite workstreams")
        if [item.workstream for item in workstreams] != [
            "P09-A",
            "P09-B",
            "P09-C",
            "P09-D",
            "P09-E",
            "P09-F",
            "P09-G",
        ]:
            raise P09ValidationError("P09-H prerequisite workstream order must be P09-A..P09-G")
        if len({item.document for item in workstreams}) != len(workstreams):
            raise P09ValidationError("P09-H prerequisite document paths must be unique")
        if len({item.task_id for item in workstreams}) != len(workstreams):
            raise P09ValidationError("P09-H prerequisite task IDs must be unique")

        performance = _mapping(raw.get("performance"), field="performance")
        semantics = _mapping(raw.get("validation_semantics"), field="validation_semantics")
        performance_semantics = _text(
            performance.get("semantics"),
            field="performance.semantics",
        )
        if performance_semantics != "CI_REGRESSION_BUDGET_NOT_PRODUCTION_SLO":
            raise P09ValidationError("P09-H performance semantics must remain CI-only")

        network_required = _boolean(
            performance.get("network_required"),
            field="performance.network_required",
        )
        production_slo = _boolean(
            performance.get("production_slo_certified"),
            field="performance.production_slo_certified",
        )
        profitability = _boolean(
            semantics.get("profitability_certified"),
            field="validation_semantics.profitability_certified",
        )
        trade_probability = _boolean(
            semantics.get("trade_success_probability_certified"),
            field="validation_semantics.trade_success_probability_certified",
        )
        execution = _boolean(
            semantics.get("production_execution_certified"),
            field="validation_semantics.production_execution_certified",
        )
        provider_performance = _boolean(
            semantics.get("production_provider_performance_certified"),
            field="validation_semantics.production_provider_performance_certified",
        )
        if network_required or production_slo:
            raise P09ValidationError("P09-H CI benchmark must not require network or certify production SLO")
        if profitability or trade_probability or execution or provider_performance:
            raise P09ValidationError("P09-H must not certify trading or production performance")

        next_phase = _text(raw.get("next_phase"), field="next_phase")
        next_phase_state = _text(raw.get("next_phase_state"), field="next_phase_state")
        if next_phase != "P10" or next_phase_state != "OWNER_PHASE_AUTHORIZATION_REQUIRED":
            raise P09ValidationError("P09-H must leave P10 behind the Owner phase gate")

        return cls(
            required_phase=_text(raw.get("required_phase"), field="required_phase"),
            required_workstreams=tuple(workstreams),
            required_state=_text(raw.get("required_state"), field="required_state"),
            required_lock=_text(raw.get("required_lock"), field="required_lock"),
            required_country_assumption=_text(
                raw.get("required_country_assumption"),
                field="required_country_assumption",
            ),
            required_live_trading=_text(raw.get("required_live_trading"), field="required_live_trading"),
            required_auto_trading=_text(raw.get("required_auto_trading"), field="required_auto_trading"),
            performance_semantics=performance_semantics,
            p09_unit_suite_max_seconds=_positive_int(
                performance.get("p09_unit_suite_max_seconds"),
                field="performance.p09_unit_suite_max_seconds",
            ),
            network_required=network_required,
            production_slo_certified=production_slo,
            profitability_certified=profitability,
            trade_success_probability_certified=trade_probability,
            production_execution_certified=execution,
            production_provider_performance_certified=provider_performance,
            next_phase=next_phase,
            next_phase_state=next_phase_state,
        )


@dataclass(frozen=True, slots=True)
class P09ValidationIssue:
    code: str
    document: str
    detail: str

    def payload(self) -> dict[str, str]:
        return {
            "code": self.code,
            "document": self.document,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class P09ValidationReport:
    outcome: str
    issues: tuple[P09ValidationIssue, ...]
    certified_task_ids: tuple[str, ...]
    document_sha256s: tuple[tuple[str, str], ...]
    country_assumption: str
    live_trading: str
    auto_trading: str
    performance_semantics: str
    next_phase: str
    next_phase_state: str

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P09H_VALIDATION_REPORT",
            "outcome": self.outcome,
            "issues": [issue.payload() for issue in self.issues],
            "certified_task_ids": list(self.certified_task_ids),
            "document_sha256s": [
                {"document": document, "sha256": digest}
                for document, digest in self.document_sha256s
            ],
            "country_assumption": self.country_assumption,
            "live_trading": self.live_trading,
            "auto_trading": self.auto_trading,
            "performance_semantics": self.performance_semantics,
            "next_phase": self.next_phase,
            "next_phase_state": self.next_phase_state,
        }

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


class P09ValidationEvaluator:
    def __init__(self, policy: P09ValidationPolicy) -> None:
        self.policy = policy

    def evaluate(self, documents: Mapping[str, bytes]) -> P09ValidationReport:
        issues: list[P09ValidationIssue] = []
        certified: list[str] = []
        required_paths = tuple(item.document for item in self.policy.required_workstreams)
        provided_paths = set(documents)
        required_set = set(required_paths)

        for missing in sorted(required_set - provided_paths):
            issues.append(P09ValidationIssue("MISSING_DOCUMENT", missing, "required prerequisite is absent"))
        for unexpected in sorted(provided_paths - required_set):
            issues.append(
                P09ValidationIssue(
                    "UNEXPECTED_DOCUMENT",
                    unexpected,
                    "input set must contain exactly P09-A..P09-G canonical documents",
                )
            )

        document_sha256s = tuple(
            sorted(
                (path, hashlib.sha256(content).hexdigest())
                for path, content in documents.items()
            )
        )

        for item in self.policy.required_workstreams:
            content = documents.get(item.document)
            if content is None:
                continue
            issue_count_before = len(issues)
            try:
                parsed_value: object = json.loads(content.decode("utf-8"))
                parsed = _mapping(parsed_value, field=item.document)
            except (UnicodeDecodeError, json.JSONDecodeError, P09ValidationError) as exc:
                issues.append(P09ValidationIssue("MALFORMED_DOCUMENT", item.document, str(exc)))
                continue

            self._check_common(item, parsed, issues)
            self._check_specific(item.workstream, item.document, parsed, issues)
            if len(issues) == issue_count_before:
                certified.append(item.task_id)

        outcome = "PASS" if not issues else "FAIL"
        return P09ValidationReport(
            outcome=outcome,
            issues=tuple(issues),
            certified_task_ids=tuple(certified),
            document_sha256s=document_sha256s,
            country_assumption=self.policy.required_country_assumption,
            live_trading=self.policy.required_live_trading,
            auto_trading=self.policy.required_auto_trading,
            performance_semantics=self.policy.performance_semantics,
            next_phase=self.policy.next_phase,
            next_phase_state=self.policy.next_phase_state,
        )

    def _issue(
        self,
        issues: list[P09ValidationIssue],
        code: str,
        document: str,
        detail: str,
    ) -> None:
        issues.append(P09ValidationIssue(code, document, detail))

    def _require_equal(
        self,
        raw: Mapping[str, object],
        field: str,
        expected: object,
        document: str,
        issues: list[P09ValidationIssue],
    ) -> None:
        if raw.get(field) != expected:
            self._issue(
                issues,
                "INVARIANT_DRIFT",
                document,
                f"{field} must equal {expected!r}",
            )

    def _check_common(
        self,
        item: RequiredP09Workstream,
        raw: Mapping[str, object],
        issues: list[P09ValidationIssue],
    ) -> None:
        document = item.document
        self._require_equal(raw, "schema_version", "1.0", document, issues)
        self._require_equal(raw, "task_id", item.task_id, document, issues)
        self._require_equal(raw, "workstream", item.workstream, document, issues)
        self._require_equal(raw, "phase", self.policy.required_phase, document, issues)
        self._require_equal(raw, "state", self.policy.required_state, document, issues)
        self._require_equal(raw, "lock", self.policy.required_lock, document, issues)
        self._require_equal(
            raw,
            "country_assumption",
            self.policy.required_country_assumption,
            document,
            issues,
        )
        self._require_equal(
            raw,
            "live_trading",
            self.policy.required_live_trading,
            document,
            issues,
        )
        self._require_equal(
            raw,
            "auto_trading",
            self.policy.required_auto_trading,
            document,
            issues,
        )
        self._require_equal(raw, "direct_trade_output_allowed", False, document, issues)

        closure_value = raw.get("canonical_closure")
        if not isinstance(closure_value, Mapping):
            self._issue(issues, "MISSING_CLOSURE_EVIDENCE", document, "canonical_closure is required")
            return
        closure = cast(Mapping[str, object], closure_value)
        positive_int_fields = (
            "implementation_pr",
            "pr_governance_run",
            "post_merge_governance_run",
            "post_merge_branch_hygiene_run",
        )
        for field in positive_int_fields:
            value = closure.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                self._issue(issues, "INVALID_CLOSURE_EVIDENCE", document, f"{field} must be positive integer")

        for field in ("final_implementation_head", "implementation_merge_sha"):
            try:
                _hex_text(closure.get(field), field=field, length=40)
            except P09ValidationError as exc:
                self._issue(issues, "INVALID_CLOSURE_EVIDENCE", document, str(exc))

        for field in ("pr_artifact_sha256", "post_merge_artifact_sha256"):
            try:
                _hex_text(closure.get(field), field=field, length=64)
            except P09ValidationError as exc:
                self._issue(issues, "INVALID_CLOSURE_EVIDENCE", document, str(exc))

    def _check_specific(
        self,
        workstream: str,
        document: str,
        raw: Mapping[str, object],
        issues: list[P09ValidationIssue],
    ) -> None:
        if workstream == "P09-A":
            semantics_value = raw.get("spot_fx_volume_semantics")
            if not isinstance(semantics_value, Mapping):
                self._issue(issues, "P09A_PROXY_BOUNDARY_DRIFT", document, "spot_fx_volume_semantics missing")
                return
            semantics = cast(Mapping[str, object], semantics_value)
            required_false = semantics.get("consolidated_market_volume_claim_allowed") is False
            required_true = all(
                semantics.get(field) is True
                for field in (
                    "coverage_confidence_required",
                    "coverage_scope_required",
                    "provider_required",
                    "proxy_target_required",
                )
            )
            kinds_value = semantics.get("allowed_kinds")
            kinds_valid = False
            if isinstance(kinds_value, list):
                kinds = cast(list[object], kinds_value)
                kinds_valid = bool(kinds) and all(
                    isinstance(kind, str) and kind.endswith("_PROXY")
                    for kind in kinds
                )
            if not (required_false and required_true and kinds_valid):
                self._issue(issues, "P09A_PROXY_BOUNDARY_DRIFT", document, "spot-FX proxy semantics changed")
            if raw.get("point_in_time_required") is not True or raw.get("trusted_provenance_required") is not True:
                self._issue(issues, "P09A_PROVENANCE_DRIFT", document, "point-in-time/trusted provenance must remain required")

        elif workstream == "P09-B":
            expected = {
                "quote_updates_as_trade_prints_allowed": False,
                "tick_volume_as_trade_prints_allowed": False,
                "forex_spot_global_flow_claim_allowed": False,
                "unknown_volume_enters_delta": False,
                "cvd_requires_explicit_start": True,
                "cvd_requires_contiguous_sequence": True,
                "point_in_time_quote_context_required": True,
            }
            if any(raw.get(field) != value for field, value in expected.items()):
                self._issue(issues, "P09B_FLOW_BOUNDARY_DRIFT", document, "trade-flow/Delta/CVD invariant changed")

        elif workstream == "P09-C":
            expected = {
                "input_contract": "P09-B TradePrint only",
                "value_area_target_bps": 7000,
                "quote_activity_profile_allowed": False,
                "tick_volume_profile_allowed": False,
                "forex_spot_global_profile_claim_allowed": False,
            }
            if any(raw.get(field) != value for field, value in expected.items()):
                self._issue(issues, "P09C_PROFILE_BOUNDARY_DRIFT", document, "Volume Profile invariant changed")

        elif workstream == "P09-D":
            if (
                raw.get("locked_or_crossed_book_allowed") is not False
                or raw.get("forex_spot_global_book_claim_allowed") is not False
                or raw.get("imbalance_range_bps") != [-10000, 10000]
            ):
                self._issue(issues, "P09D_BOOK_BOUNDARY_DRIFT", document, "order-book invariant changed")

        elif workstream == "P09-E":
            expected = {
                "capacity_semantics": "DISPLAYED_PROVIDER_BOOK_ONLY",
                "hidden_liquidity_inference_allowed": False,
                "fillability_claim_allowed": False,
                "slippage_or_market_impact_claim_allowed": False,
                "cross_provider_aggregation_allowed": False,
                "forex_spot_global_liquidity_claim_allowed": False,
            }
            if any(raw.get(field) != value for field, value in expected.items()):
                self._issue(issues, "P09E_CAPACITY_BOUNDARY_DRIFT", document, "displayed-capacity invariant changed")

        elif workstream == "P09-F":
            expected = {
                "crowding_semantics": "COMPLETE_EVIDENCE_VECTOR_NO_SCORE",
                "cross_provider_aggregation_allowed": False,
                "spot_fx_derivatives_metric_allowed": False,
                "crowding_score_allowed": False,
                "liquidation_forecast_allowed": False,
            }
            if any(raw.get(field) != value for field, value in expected.items()):
                self._issue(issues, "P09F_CROWDING_BOUNDARY_DRIFT", document, "derivatives-crowding invariant changed")

        elif workstream == "P09-G":
            required_components = raw.get("required_components")
            expected_components = ["PROVIDER_SCOPE", "INTERNAL_COMPLETENESS", "FRESHNESS"]
            expected = {
                "confidence_aggregation": "CONSERVATIVE_MINIMUM",
                "confidence_semantics": "PROXY_SCOPE_CONFIDENCE_NOT_GLOBAL_MARKET_SHARE",
                "global_market_share_claim_allowed": False,
                "cross_provider_aggregation_allowed": False,
                "weighted_confidence_score_allowed": False,
            }
            if required_components != expected_components or any(
                raw.get(field) != value for field, value in expected.items()
            ):
                self._issue(issues, "P09G_CONFIDENCE_BOUNDARY_DRIFT", document, "FX proxy confidence invariant changed")
        else:
            self._issue(issues, "UNSUPPORTED_WORKSTREAM", document, workstream)
