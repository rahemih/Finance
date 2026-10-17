from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Iterable

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_WORKSTREAMS = (
    "P17-A","P17-B","P17-C","P17-D","P17-E","P17-F","P17-G","P17-H"
)
_REQUIRED_CATEGORIES = (
    "OOS_EDGE","RISK","ROBUSTNESS","CAPACITY","EXECUTION_REALISM"
)
_COMPARATORS = {"GE","LE"}


class QuantGateError(ValueError):
    """P17-I quant gate invariant failure."""


def _sha(value: str, field: str) -> str:
    v=value.strip().lower()
    if _SHA256.fullmatch(v) is None:
        raise QuantGateError(f"{field} must be lowercase SHA-256")
    return v


def _hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class WorkstreamEvidence:
    workstream: str
    evidence_sha256: str

    def __post_init__(self) -> None:
        if self.workstream not in _REQUIRED_WORKSTREAMS:
            raise QuantGateError("unsupported P17 workstream evidence")
        object.__setattr__(self,"evidence_sha256",_sha(self.evidence_sha256,"evidence_sha256"))

    def payload(self) -> dict[str,object]:
        return {"workstream":self.workstream,"evidence_sha256":self.evidence_sha256}


@dataclass(frozen=True, slots=True)
class BenchmarkCriterion:
    category: str
    metric_id: str
    measured_value: int
    threshold_value: int
    comparator: str
    evidence_sha256: str

    def __post_init__(self) -> None:
        if self.category not in _REQUIRED_CATEGORIES:
            raise QuantGateError("unsupported benchmark category")
        if not self.metric_id.strip():
            raise QuantGateError("metric_id must be non-empty")
        if self.comparator not in _COMPARATORS:
            raise QuantGateError("unsupported comparator")
        object.__setattr__(self,"evidence_sha256",_sha(self.evidence_sha256,"evidence_sha256"))

    @property
    def passed(self) -> bool:
        if self.comparator=="GE":
            return self.measured_value >= self.threshold_value
        return self.measured_value <= self.threshold_value

    def payload(self) -> dict[str,object]:
        return {
            "category":self.category,
            "metric_id":self.metric_id,
            "measured_value":self.measured_value,
            "threshold_value":self.threshold_value,
            "comparator":self.comparator,
            "evidence_sha256":self.evidence_sha256,
            "passed":self.passed,
        }


@dataclass(frozen=True, slots=True)
class QuantGateCertificate:
    gate_name: str
    state: str
    gate_id: str
    workstream_evidence: tuple[WorkstreamEvidence,...]
    benchmark_criteria: tuple[BenchmarkCriterion,...]
    strategy_registry_sha256: str
    model_registry_sha256: str
    next_phase: str = "P18"
    next_phase_state: str = "NOT_STARTED_OWNER_PHASE_AUTHORIZATION_REQUIRED"
    automatic_p18_promotion: bool = False
    profitability_guarantee: bool = False
    execution_authority: bool = False
    live_trading: str = "DISABLED"
    auto_trading: str = "DISABLED"


def certify_g9_quant_validated(
    *,
    workstream_evidence: Iterable[WorkstreamEvidence],
    benchmark_criteria: Iterable[BenchmarkCriterion],
    strategy_registry_sha256: str,
    model_registry_sha256: str,
) -> QuantGateCertificate:
    strategy_sha=_sha(strategy_registry_sha256,"strategy_registry_sha256")
    model_sha=_sha(model_registry_sha256,"model_registry_sha256")

    by_ws: dict[str,WorkstreamEvidence]={}
    seen_evidence: set[str]=set()
    for item in workstream_evidence:
        if item.workstream in by_ws:
            raise QuantGateError("duplicate workstream evidence")
        if item.evidence_sha256 in seen_evidence:
            raise QuantGateError("duplicate workstream evidence SHA-256")
        by_ws[item.workstream]=item
        seen_evidence.add(item.evidence_sha256)
    if tuple(sorted(by_ws)) != tuple(sorted(_REQUIRED_WORKSTREAMS)):
        raise QuantGateError("G9 requires exact P17-A..P17-H evidence coverage")

    by_category: dict[str,BenchmarkCriterion]={}
    for criterion in benchmark_criteria:
        if criterion.category in by_category:
            raise QuantGateError("duplicate benchmark category")
        if not criterion.passed:
            raise QuantGateError(f"benchmark criterion failed: {criterion.category}")
        by_category[criterion.category]=criterion
    if tuple(sorted(by_category)) != tuple(sorted(_REQUIRED_CATEGORIES)):
        raise QuantGateError("G9 requires all benchmark categories")

    ordered_ws=tuple(by_ws[name] for name in _REQUIRED_WORKSTREAMS)
    ordered_criteria=tuple(by_category[name] for name in _REQUIRED_CATEGORIES)
    payload={
        "schema_version":"1.0",
        "gate_name":"G9_QUANT_VALIDATED",
        "state":"PASS",
        "workstream_evidence":[x.payload() for x in ordered_ws],
        "benchmark_criteria":[x.payload() for x in ordered_criteria],
        "strategy_registry_sha256":strategy_sha,
        "model_registry_sha256":model_sha,
        "next_phase":"P18",
        "next_phase_state":"NOT_STARTED_OWNER_PHASE_AUTHORIZATION_REQUIRED",
        "automatic_p18_promotion":False,
        "profitability_guarantee":False,
        "execution_authority":False,
        "live_trading":"DISABLED",
        "auto_trading":"DISABLED",
    }
    return QuantGateCertificate(
        gate_name="G9_QUANT_VALIDATED",
        state="PASS",
        gate_id=_hash(payload),
        workstream_evidence=ordered_ws,
        benchmark_criteria=ordered_criteria,
        strategy_registry_sha256=strategy_sha,
        model_registry_sha256=model_sha,
    )
