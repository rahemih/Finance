from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path
import re
from typing import Mapping, cast


class TechnicalValidationGateError(ValueError):
    """P08-I gate policy or evidence is malformed."""


class GateOutcome(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


@dataclass(frozen=True, slots=True)
class RequiredWorkstream:
    task_id: str
    document: str


@dataclass(frozen=True, slots=True)
class TechnicalValidationGatePolicy:
    policy_version: str
    gate_id: str
    fail_closed: bool
    required_workstreams: tuple[RequiredWorkstream, ...]
    required_state: str
    required_lock: str
    required_country_assumption: str
    required_live_trading: str
    required_auto_trading: str
    direct_trade_output_allowed: bool
    required_g6_pre_gate_state: str
    production_fusion_threshold_owner: str
    p09_state_after_pass: str
    network_required: bool
    credentials_required: bool

    @classmethod
    def from_path(cls, path: Path) -> "TechnicalValidationGatePolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        raw = _mapping(raw_value, field="policy root")
        if raw.get("schema_version") != "1.0":
            raise TechnicalValidationGateError(
                "unsupported P08-I policy schema_version"
            )
        if raw.get("kind") != "NEXUS_QUANT_P08I_TECHNICAL_VALIDATION_GATE_POLICY":
            raise TechnicalValidationGateError("unexpected P08-I policy kind")
        if raw.get("gate_id") != "G6_TECHNICAL_VALIDATED":
            raise TechnicalValidationGateError("P08-I gate_id must be G6_TECHNICAL_VALIDATED")
        fail_closed = _boolean(raw.get("fail_closed"), field="fail_closed")
        if not fail_closed:
            raise TechnicalValidationGateError("P08-I gate must fail closed")

        workstream_values = _object_list(
            raw.get("required_workstreams"),
            field="required_workstreams",
        )
        workstreams: list[RequiredWorkstream] = []
        seen_tasks: set[str] = set()
        seen_docs: set[str] = set()
        for value in workstream_values:
            item = _mapping(value, field="required_workstream")
            task_id = _text(item.get("task_id"), field="task_id")
            document = _text(item.get("document"), field="document")
            if task_id in seen_tasks or document in seen_docs:
                raise TechnicalValidationGateError(
                    "P08-I required workstreams must be unique"
                )
            seen_tasks.add(task_id)
            seen_docs.add(document)
            workstreams.append(
                RequiredWorkstream(task_id=task_id, document=document)
            )
        expected = {
            "FIN-P08-WA-001",
            "FIN-P08-WB-001",
            "FIN-P08-WC-001",
            "FIN-P08-WD-001",
            "FIN-P08-WE-001",
            "FIN-P08-WF-001",
            "FIN-P08-WG-001",
            "FIN-P08-WH-001",
        }
        if seen_tasks != expected:
            raise TechnicalValidationGateError(
                "P08-I policy must require exactly P08-A through P08-H"
            )
        if _boolean(
            raw.get("direct_trade_output_allowed"),
            field="direct_trade_output_allowed",
        ):
            raise TechnicalValidationGateError(
                "P08-I policy cannot allow direct trade output"
            )
        if raw.get("production_fusion_threshold_owner") != "P14":
            raise TechnicalValidationGateError(
                "production fusion threshold ownership must remain P14"
            )
        return cls(
            policy_version=_text(raw.get("policy_version"), field="policy_version"),
            gate_id="G6_TECHNICAL_VALIDATED",
            fail_closed=True,
            required_workstreams=tuple(workstreams),
            required_state=_text(raw.get("required_state"), field="required_state"),
            required_lock=_text(raw.get("required_lock"), field="required_lock"),
            required_country_assumption=_text(
                raw.get("required_country_assumption"),
                field="required_country_assumption",
            ),
            required_live_trading=_text(
                raw.get("required_live_trading"),
                field="required_live_trading",
            ),
            required_auto_trading=_text(
                raw.get("required_auto_trading"),
                field="required_auto_trading",
            ),
            direct_trade_output_allowed=False,
            required_g6_pre_gate_state=_text(
                raw.get("required_g6_pre_gate_state"),
                field="required_g6_pre_gate_state",
            ),
            production_fusion_threshold_owner="P14",
            p09_state_after_pass=_text(
                raw.get("p09_state_after_pass"),
                field="p09_state_after_pass",
            ),
            network_required=_boolean(
                raw.get("network_required"),
                field="network_required",
            ),
            credentials_required=_boolean(
                raw.get("credentials_required"),
                field="credentials_required",
            ),
        )


@dataclass(frozen=True, slots=True)
class GateIssue:
    code: str
    task_id: str
    detail: str

    def payload(self) -> dict[str, str]:
        return {
            "code": self.code,
            "task_id": self.task_id,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class TechnicalValidationGateReport:
    gate_id: str
    policy_version: str
    outcome: GateOutcome
    issues: tuple[GateIssue, ...]
    certified_task_ids: tuple[str, ...]
    document_sha256s: tuple[tuple[str, str], ...]
    live_trading: str
    auto_trading: str
    country_assumption: str
    next_phase: str
    next_phase_state: str
    fingerprint: str


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TechnicalValidationGateError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _object_list(value: object, *, field: str) -> list[object]:
    if not isinstance(value, list):
        raise TechnicalValidationGateError(f"{field} must be a list")
    return cast(list[object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TechnicalValidationGateError(f"{field} must be non-empty text")
    return value.strip()


def _boolean(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise TechnicalValidationGateError(f"{field} must be boolean")
    return value


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise TechnicalValidationGateError(f"{field} must be a positive integer")
    return value


def _sha_text(value: object, *, field: str, length: int) -> str:
    text = _text(value, field=field).lower()
    if len(text) != length or re.fullmatch(r"[0-9a-f]+", text) is None:
        raise TechnicalValidationGateError(
            f"{field} must be {length}-character lowercase hex"
        )
    return text


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


class TechnicalValidationGateEvaluator:
    def __init__(self, policy: TechnicalValidationGatePolicy) -> None:
        self._policy = policy

    def _issue(
        self,
        issues: list[GateIssue],
        *,
        code: str,
        task_id: str,
        detail: str,
    ) -> None:
        issues.append(GateIssue(code=code, task_id=task_id, detail=detail))

    def _validate_closure(
        self,
        *,
        task_id: str,
        document: Mapping[str, object],
        issues: list[GateIssue],
    ) -> None:
        try:
            closure = _mapping(
                document.get("closure_evidence"),
                field=f"{task_id}.closure_evidence",
            )
            _positive_int(
                closure.get("implementation_pr"),
                field=f"{task_id}.implementation_pr",
            )
            _sha_text(
                closure.get("final_head"),
                field=f"{task_id}.final_head",
                length=40,
            )
            _sha_text(
                closure.get("implementation_merge_sha"),
                field=f"{task_id}.implementation_merge_sha",
                length=40,
            )
            _positive_int(
                closure.get("pr_governance_run"),
                field=f"{task_id}.pr_governance_run",
            )
            _sha_text(
                closure.get("pr_artifact_sha256"),
                field=f"{task_id}.pr_artifact_sha256",
                length=64,
            )
            _positive_int(
                closure.get("post_merge_governance_run"),
                field=f"{task_id}.post_merge_governance_run",
            )
            _sha_text(
                closure.get("post_merge_artifact_sha256"),
                field=f"{task_id}.post_merge_artifact_sha256",
                length=64,
            )
            _positive_int(
                closure.get("post_merge_branch_hygiene_run"),
                field=f"{task_id}.post_merge_branch_hygiene_run",
            )
            if closure.get("strict_pyright") != "PASS":
                raise TechnicalValidationGateError(
                    f"{task_id}.strict_pyright must be PASS"
                )
            if closure.get("deterministic_evidence") != "PASS":
                raise TechnicalValidationGateError(
                    f"{task_id}.deterministic_evidence must be PASS"
                )
        except TechnicalValidationGateError as exc:
            self._issue(
                issues,
                code="CLOSURE_EVIDENCE_INVALID",
                task_id=task_id,
                detail=str(exc),
            )

    def _validate_common(
        self,
        *,
        expected: RequiredWorkstream,
        document: Mapping[str, object],
        issues: list[GateIssue],
    ) -> None:
        task_id = expected.task_id
        checks = (
            ("TASK_ID_MISMATCH", document.get("task_id"), task_id),
            ("STATE_NOT_CANONICAL", document.get("state"), self._policy.required_state),
            ("LOCK_NOT_RELEASED", document.get("lock"), self._policy.required_lock),
            (
                "COUNTRY_ASSUMPTION_CHANGED",
                document.get("country_assumption"),
                self._policy.required_country_assumption,
            ),
            (
                "LIVE_TRADING_NOT_DISABLED",
                document.get("live_trading"),
                self._policy.required_live_trading,
            ),
            (
                "AUTO_TRADING_NOT_DISABLED",
                document.get("auto_trading"),
                self._policy.required_auto_trading,
            ),
            (
                "G6_PRE_GATE_STATE_INVALID",
                document.get("g6_technical_validated"),
                self._policy.required_g6_pre_gate_state,
            ),
        )
        for code, actual, wanted in checks:
            if actual != wanted:
                self._issue(
                    issues,
                    code=code,
                    task_id=task_id,
                    detail=f"expected {wanted!r}, got {actual!r}",
                )
        if document.get("direct_trade_output_allowed") is not False:
            self._issue(
                issues,
                code="DIRECT_TRADE_OUTPUT_NOT_FORBIDDEN",
                task_id=task_id,
                detail="direct_trade_output_allowed must be false",
            )
        self._validate_closure(
            task_id=task_id,
            document=document,
            issues=issues,
        )

    def _validate_integrated_invariants(
        self,
        documents: Mapping[str, Mapping[str, object]],
        issues: list[GateIssue],
    ) -> None:
        a = documents["FIN-P08-WA-001"]
        if a.get("point_in_time_required") is not True:
            self._issue(
                issues,
                code="POINT_IN_TIME_NOT_REQUIRED",
                task_id="FIN-P08-WA-001",
                detail="P08-A must require point-in-time inputs",
            )
        if a.get("trusted_data_required") is not True:
            self._issue(
                issues,
                code="TRUSTED_DATA_NOT_REQUIRED",
                task_id="FIN-P08-WA-001",
                detail="P08-A must require trusted-data lineage",
            )

        f = documents["FIN-P08-WF-001"]
        if f.get("current_bar_in_reference_channel") is not False:
            self._issue(
                issues,
                code="BREAKOUT_REFERENCE_LEAKAGE",
                task_id="FIN-P08-WF-001",
                detail="current bar must be excluded from breakout reference channel",
            )
        if f.get("expansion_vote_semantics") != "CORRELATED_CONTEXT_NOT_SECOND_VOTE":
            self._issue(
                issues,
                code="BREAKOUT_EXPANSION_DOUBLE_COUNT_RISK",
                task_id="FIN-P08-WF-001",
                detail="expansion must remain correlated context, not a second vote",
            )

        g = documents["FIN-P08-WG-001"]
        if g.get("cross_timeframe_independence_status") != "RELATED_NOT_INDEPENDENT":
            self._issue(
                issues,
                code="MULTI_TIMEFRAME_DOUBLE_COUNT_RISK",
                task_id="FIN-P08-WG-001",
                detail="repeated timeframes must remain related, not independent",
            )

        h = documents["FIN-P08-WH-001"]
        if h.get("cluster_vote_cap") != 1:
            self._issue(
                issues,
                code="CLUSTER_VOTE_CAP_INVALID",
                task_id="FIN-P08-WH-001",
                detail="known correlation clusters must contribute at most one vote",
            )
        if h.get("numeric_dependence_decision_semantics") != "MEASURED_NOT_THRESHOLD_CLASSIFIED":
            self._issue(
                issues,
                code="NUMERIC_DEPENDENCE_OVERCLAIM",
                task_id="FIN-P08-WH-001",
                detail="numeric dependence must remain measurement evidence",
            )
        if h.get("numeric_dependence_threshold") != "TO_BE_CALIBRATED_BY_GOVERNED_EMPIRICAL_EVIDENCE":
            self._issue(
                issues,
                code="UNCALIBRATED_CORRELATION_THRESHOLD",
                task_id="FIN-P08-WH-001",
                detail="universal numeric dependence threshold is not allowed",
            )
        if h.get("production_fusion_threshold_owner") != "P14":
            self._issue(
                issues,
                code="FUSION_THRESHOLD_AUTHORITY_DRIFT",
                task_id="FIN-P08-WH-001",
                detail="production fusion threshold ownership must remain P14",
            )
        if h.get("unregistered_direct_dependency_semantics") != "SEPARATE_CLUSTER_EMPIRICAL_MONITORING_REQUIRED":
            self._issue(
                issues,
                code="UNREGISTERED_DEPENDENCY_OVERCLAIM",
                task_id="FIN-P08-WH-001",
                detail="unregistered pairs cannot be declared independent by default",
            )

    def evaluate(
        self,
        document_bytes: Mapping[str, bytes],
    ) -> TechnicalValidationGateReport:
        issues: list[GateIssue] = []
        parsed: dict[str, Mapping[str, object]] = {}
        hashes: list[tuple[str, str]] = []

        expected_docs = {
            item.document: item
            for item in self._policy.required_workstreams
        }
        if set(document_bytes) != set(expected_docs):
            missing = sorted(set(expected_docs) - set(document_bytes))
            extra = sorted(set(document_bytes) - set(expected_docs))
            issues.append(
                GateIssue(
                    code="DOCUMENT_SET_MISMATCH",
                    task_id="P08",
                    detail=f"missing={missing} extra={extra}",
                )
            )

        for path in sorted(expected_docs):
            expected = expected_docs[path]
            raw = document_bytes.get(path)
            if raw is None:
                continue
            hashes.append((path, hashlib.sha256(raw).hexdigest()))
            try:
                value: object = json.loads(raw.decode("utf-8"))
                document = _mapping(value, field=path)
            except (UnicodeDecodeError, json.JSONDecodeError, TechnicalValidationGateError) as exc:
                self._issue(
                    issues,
                    code="DOCUMENT_MALFORMED",
                    task_id=expected.task_id,
                    detail=f"{path}: {exc}",
                )
                continue
            parsed[expected.task_id] = document
            self._validate_common(
                expected=expected,
                document=document,
                issues=issues,
            )

        if set(parsed) == {
            item.task_id for item in self._policy.required_workstreams
        }:
            self._validate_integrated_invariants(parsed, issues)

        outcome = GateOutcome.PASS if not issues else GateOutcome.FAIL
        certified = (
            tuple(sorted(parsed))
            if outcome is GateOutcome.PASS
            else ()
        )
        fingerprint_payload = {
            "gate_id": self._policy.gate_id,
            "policy_version": self._policy.policy_version,
            "outcome": outcome.value,
            "issues": [issue.payload() for issue in issues],
            "certified_task_ids": list(certified),
            "document_sha256s": [
                {"document": path, "sha256": digest}
                for path, digest in sorted(hashes)
            ],
            "safety": {
                "live_trading": self._policy.required_live_trading,
                "auto_trading": self._policy.required_auto_trading,
                "country_assumption": self._policy.required_country_assumption,
            },
            "next_phase": "P09",
            "next_phase_state": self._policy.p09_state_after_pass,
        }
        fingerprint = hashlib.sha256(
            _canonical_bytes(fingerprint_payload)
        ).hexdigest()
        return TechnicalValidationGateReport(
            gate_id=self._policy.gate_id,
            policy_version=self._policy.policy_version,
            outcome=outcome,
            issues=tuple(issues),
            certified_task_ids=certified,
            document_sha256s=tuple(sorted(hashes)),
            live_trading=self._policy.required_live_trading,
            auto_trading=self._policy.required_auto_trading,
            country_assumption=self._policy.required_country_assumption,
            next_phase="P09",
            next_phase_state=self._policy.p09_state_after_pass,
            fingerprint=fingerprint,
        )
