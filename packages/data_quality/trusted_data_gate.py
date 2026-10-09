from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
from pathlib import Path
import re
from typing import Mapping, cast


class TrustedDataGateError(ValueError):
    """Trusted-data gate policy is invalid."""


class GateOutcome(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SHA256_PREFIXED = re.compile(r"^sha256:[0-9a-f]{64}$")
_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TrustedDataGateError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TrustedDataGateError(f"{field} must be a non-empty string")
    return value.strip()


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True, slots=True)
class RequiredWorkstream:
    task_id: str
    document: str


@dataclass(frozen=True, slots=True)
class TrustedDataGatePolicy:
    gate_id: str
    policy_version: str
    required_workstreams: tuple[RequiredWorkstream, ...]
    required_state: str
    required_lock_state: str
    require_live_trading: str
    require_auto_trading: str
    require_country_assumption: str
    require_feature_quality_adapter: bool
    require_non_accepted_downstream_allowed: bool
    require_no_data_blocking: bool

    @classmethod
    def from_path(cls, path: Path) -> "TrustedDataGatePolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise TrustedDataGateError(f"invalid trusted-data gate policy JSON: {exc}") from exc
        raw = _mapping(raw_value, field="root")
        if raw.get("schema_version") != "1.0":
            raise TrustedDataGateError("unsupported trusted-data gate policy schema_version")
        if raw.get("task_id") != "FIN-P07-WH-001":
            raise TrustedDataGateError("unexpected trusted-data gate task_id")
        if raw.get("mode") != "CANONICAL_EVIDENCE_FAIL_CLOSED":
            raise TrustedDataGateError("unsupported trusted-data gate mode")
        if raw.get("pass_state") != "PASS" or raw.get("failure_state") != "FAIL":
            raise TrustedDataGateError("trusted-data gate must use PASS/FAIL states")
        if raw.get("network_required") is not False or raw.get("credentials_required") is not False:
            raise TrustedDataGateError("trusted-data gate must be offline")

        workstreams_raw = raw.get("required_workstreams")
        if not isinstance(workstreams_raw, list) or not workstreams_raw:
            raise TrustedDataGateError("required_workstreams must be a non-empty list")
        workstreams: list[RequiredWorkstream] = []
        for idx, item in enumerate(cast(list[object], workstreams_raw)):
            value = _mapping(item, field=f"required_workstreams[{idx}]")
            workstreams.append(
                RequiredWorkstream(
                    task_id=_text(value.get("task_id"), field="task_id"),
                    document=_text(value.get("document"), field="document"),
                )
            )
        if len({item.task_id for item in workstreams}) != len(workstreams):
            raise TrustedDataGateError("required workstream task IDs must be unique")
        if len({item.document for item in workstreams}) != len(workstreams):
            raise TrustedDataGateError("required workstream document paths must be unique")

        expected = {f"FIN-P07-W{letter}-001" for letter in "ABCDEFG"}
        if {item.task_id for item in workstreams} != expected:
            raise TrustedDataGateError("trusted-data gate must require exactly P07-A through P07-G")

        for field in (
            "require_post_merge_governance",
            "require_post_merge_artifact",
            "require_post_merge_branch_hygiene",
        ):
            if raw.get(field) is not True:
                raise TrustedDataGateError(f"{field} must remain true")

        if raw.get("next_phase") != "P08":
            raise TrustedDataGateError("trusted-data gate next phase must be P08")
        if raw.get("next_phase_state_after_pass") != "NOT_STARTED_OWNER_PHASE_AUTHORIZATION_REQUIRED":
            raise TrustedDataGateError("P08 must require Owner phase authorization after G5")

        return cls(
            gate_id=_text(raw.get("gate_id"), field="gate_id"),
            policy_version=_text(raw.get("policy_version"), field="policy_version"),
            required_workstreams=tuple(sorted(workstreams, key=lambda item: item.task_id)),
            required_state=_text(raw.get("required_state"), field="required_state"),
            required_lock_state=_text(raw.get("required_lock_state"), field="required_lock_state"),
            require_live_trading=_text(raw.get("require_live_trading"), field="require_live_trading"),
            require_auto_trading=_text(raw.get("require_auto_trading"), field="require_auto_trading"),
            require_country_assumption=_text(
                raw.get("require_country_assumption"),
                field="require_country_assumption",
            ),
            require_feature_quality_adapter=raw.get("require_feature_quality_adapter") is True,
            require_non_accepted_downstream_allowed=(
                raw.get("require_non_accepted_downstream_allowed") is True
            ),
            require_no_data_blocking=raw.get("require_no_data_blocking") is True,
        )


@dataclass(frozen=True, slots=True)
class GateIssue:
    code: str
    task_id: str
    field: str
    message: str

    def payload(self) -> dict[str, str]:
        return {
            "code": self.code,
            "task_id": self.task_id,
            "field": self.field,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class TrustedDataGateReport:
    gate_id: str
    policy_version: str
    outcome: GateOutcome
    issues: tuple[GateIssue, ...]
    certified_task_ids: tuple[str, ...]
    document_sha256s: tuple[tuple[str, str], ...]
    live_trading: str
    auto_trading: str
    next_phase: str
    next_phase_state: str

    @property
    def is_pass(self) -> bool:
        return self.outcome is GateOutcome.PASS

    @property
    def fingerprint(self) -> str:
        payload = {
            "schema_version": "1.0",
            "gate_id": self.gate_id,
            "policy_version": self.policy_version,
            "outcome": self.outcome.value,
            "issues": [issue.payload() for issue in self.issues],
            "certified_task_ids": list(self.certified_task_ids),
            "document_sha256s": [
                {"document": path, "sha256": digest}
                for path, digest in self.document_sha256s
            ],
            "live_trading": self.live_trading,
            "auto_trading": self.auto_trading,
            "next_phase": self.next_phase,
            "next_phase_state": self.next_phase_state,
        }
        return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _issue(code: str, task_id: str, field: str, message: str) -> GateIssue:
    return GateIssue(code=code, task_id=task_id, field=field, message=message)


class TrustedDataGateEvaluator:
    def __init__(self, policy: TrustedDataGatePolicy) -> None:
        self._policy = policy

    def evaluate(self, documents: Mapping[str, bytes]) -> TrustedDataGateReport:
        issues: list[GateIssue] = []
        certified: list[str] = []
        digests: list[tuple[str, str]] = []

        required_paths = {item.document for item in self._policy.required_workstreams}
        unexpected_paths = set(documents) - required_paths
        for path in sorted(unexpected_paths):
            issues.append(
                _issue(
                    "UNEXPECTED_DOCUMENT",
                    "G5",
                    path,
                    "document is not part of the required P07-A..G gate input set",
                )
            )

        for required in self._policy.required_workstreams:
            data = documents.get(required.document)
            if data is None:
                issues.append(
                    _issue(
                        "MISSING_DOCUMENT",
                        required.task_id,
                        required.document,
                        "required canonical workstream document is missing",
                    )
                )
                continue
            digest = hashlib.sha256(data).hexdigest()
            digests.append((required.document, digest))

            try:
                raw_value: object = json.loads(data.decode("utf-8"))
                raw = _mapping(raw_value, field="root")
            except Exception as exc:
                issues.append(
                    _issue(
                        "MALFORMED_DOCUMENT",
                        required.task_id,
                        required.document,
                        f"document cannot be parsed: {type(exc).__name__}",
                    )
                )
                continue

            task_value = raw.get("task_id")
            if task_value != required.task_id:
                issues.append(
                    _issue(
                        "TASK_ID_MISMATCH",
                        required.task_id,
                        "task_id",
                        "machine document task_id does not match gate policy",
                    )
                )
            if raw.get("state") != self._policy.required_state:
                issues.append(
                    _issue(
                        "NON_CANONICAL_STATE",
                        required.task_id,
                        "state",
                        "prerequisite workstream is not CANONICAL_COMPLETE",
                    )
                )
            if raw.get("live_trading") != self._policy.require_live_trading:
                issues.append(
                    _issue(
                        "LIVE_TRADING_SAFETY_VIOLATION",
                        required.task_id,
                        "live_trading",
                        "Live Trading safety state changed",
                    )
                )
            if raw.get("auto_trading") != self._policy.require_auto_trading:
                issues.append(
                    _issue(
                        "AUTO_TRADING_SAFETY_VIOLATION",
                        required.task_id,
                        "auto_trading",
                        "Auto Trading safety state changed",
                    )
                )
            if raw.get("country_assumption") != self._policy.require_country_assumption:
                issues.append(
                    _issue(
                        "COUNTRY_ASSUMPTION_VIOLATION",
                        required.task_id,
                        "country_assumption",
                        "country assumption must remain NONE",
                    )
                )
            if raw.get("network_required") is not False:
                issues.append(
                    _issue(
                        "NETWORK_REQUIREMENT_VIOLATION",
                        required.task_id,
                        "network_required",
                        "canonical reference control must remain offline",
                    )
                )
            if raw.get("credentials_required") is not False:
                issues.append(
                    _issue(
                        "CREDENTIAL_REQUIREMENT_VIOLATION",
                        required.task_id,
                        "credentials_required",
                        "canonical reference control must not require credentials",
                    )
                )

            closure_value = raw.get("closure")
            if not isinstance(closure_value, Mapping):
                issues.append(
                    _issue(
                        "MISSING_CLOSURE_EVIDENCE",
                        required.task_id,
                        "closure",
                        "canonical closure evidence is missing",
                    )
                )
            else:
                closure = cast(Mapping[str, object], closure_value)
                if closure.get("lock") != self._policy.required_lock_state:
                    issues.append(
                        _issue(
                            "LOCK_NOT_RELEASED",
                            required.task_id,
                            "closure.lock",
                            "prerequisite lock is not RELEASED",
                        )
                    )
                merge_sha = closure.get("merge_sha")
                if not isinstance(merge_sha, str) or _GIT_SHA.fullmatch(merge_sha) is None:
                    issues.append(
                        _issue(
                            "INVALID_MERGE_SHA",
                            required.task_id,
                            "closure.merge_sha",
                            "valid canonical merge SHA is required",
                        )
                    )
                governance_run = closure.get("post_merge_governance_run")
                if (
                    isinstance(governance_run, bool)
                    or not isinstance(governance_run, int)
                    or governance_run <= 0
                ):
                    issues.append(
                        _issue(
                            "INVALID_GOVERNANCE_EVIDENCE",
                            required.task_id,
                            "closure.post_merge_governance_run",
                            "positive post-merge Governance run ID is required",
                        )
                    )
                artifact = closure.get("post_merge_artifact_digest")
                if not isinstance(artifact, str) or _SHA256_PREFIXED.fullmatch(artifact) is None:
                    issues.append(
                        _issue(
                            "INVALID_ARTIFACT_EVIDENCE",
                            required.task_id,
                            "closure.post_merge_artifact_digest",
                            "valid post-merge artifact digest is required",
                        )
                    )
                hygiene_run = closure.get("post_merge_branch_hygiene_run")
                if (
                    isinstance(hygiene_run, bool)
                    or not isinstance(hygiene_run, int)
                    or hygiene_run <= 0
                ):
                    issues.append(
                        _issue(
                            "INVALID_BRANCH_HYGIENE_EVIDENCE",
                            required.task_id,
                            "closure.post_merge_branch_hygiene_run",
                            "positive post-merge Branch Hygiene run ID is required",
                        )
                    )

            if required.task_id == "FIN-P07-WE-001":
                if raw.get("feature_quality_adapter") is not self._policy.require_feature_quality_adapter:
                    issues.append(
                        _issue(
                            "FEATURE_QUALITY_ADAPTER_VIOLATION",
                            required.task_id,
                            "feature_quality_adapter",
                            "P07-E canonical feature quality adapter invariant failed",
                        )
                    )
            elif required.task_id == "FIN-P07-WF-001":
                if (
                    raw.get("non_accepted_downstream_allowed")
                    is not self._policy.require_non_accepted_downstream_allowed
                ):
                    issues.append(
                        _issue(
                            "FAIL_CLOSED_ROUTING_VIOLATION",
                            required.task_id,
                            "non_accepted_downstream_allowed",
                            "P07-F must deny non-accepted downstream routing",
                        )
                    )
            elif required.task_id == "FIN-P07-WG-001":
                if raw.get("no_data_blocking") is not self._policy.require_no_data_blocking:
                    issues.append(
                        _issue(
                            "NO_DATA_BLOCKING_VIOLATION",
                            required.task_id,
                            "no_data_blocking",
                            "P07-G must treat NO_DATA as blocking",
                        )
                    )

            if not any(issue.task_id == required.task_id for issue in issues):
                certified.append(required.task_id)

        ordered_issues = tuple(
            sorted(issues, key=lambda item: (item.code, item.task_id, item.field, item.message))
        )
        outcome = GateOutcome.FAIL if ordered_issues else GateOutcome.PASS
        return TrustedDataGateReport(
            gate_id=self._policy.gate_id,
            policy_version=self._policy.policy_version,
            outcome=outcome,
            issues=ordered_issues,
            certified_task_ids=tuple(sorted(certified)),
            document_sha256s=tuple(sorted(digests)),
            live_trading="DISABLED",
            auto_trading="DISABLED",
            next_phase="P08",
            next_phase_state="NOT_STARTED_OWNER_PHASE_AUTHORIZATION_REQUIRED",
        )
