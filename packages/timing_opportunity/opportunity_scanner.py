from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Mapping, Sequence, cast

from .best_trading_time import TimingWindowAssessment


class OpportunityScannerError(ValueError):
    """P13-C scanner input or policy violates governed invariants."""


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OpportunityScannerError(f"{field} must be non-empty text")
    return value.strip()


def _lineage(values: Sequence[str], *, field: str, sha256: bool = False) -> tuple[str, ...]:
    normalized = tuple(sorted({_text(item, field=field) for item in values}))
    if not normalized:
        raise OpportunityScannerError(f"{field} must be non-empty")
    if sha256 and any(_SHA256.fullmatch(item) is None for item in normalized):
        raise OpportunityScannerError(f"{field} must contain lowercase SHA-256 digests")
    return normalized


@dataclass(frozen=True, slots=True)
class OpportunityScannerPolicy:
    eligible_timing_classes: tuple[str, ...]
    observe_only_timing_classes: tuple[str, ...]
    ineligible_timing_classes: tuple[str, ...]
    candidate_states: tuple[str, ...]
    require_source_lineage: bool
    canonical_stable_ordering: bool
    opportunity_ranking_in_scope: bool
    hard_no_trade_authority: bool
    signal_expiry_in_scope: bool
    signal_probability_in_scope: bool
    canonical_tests_network_required: bool
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "OpportunityScannerPolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw_value, Mapping):
            raise OpportunityScannerError("policy root must be object")
        raw = cast(Mapping[str, object], raw_value)
        if raw.get("schema_version") != "1.0" or raw.get("mode") != "DETERMINISTIC_TIMING_OPPORTUNITY_SCAN":
            raise OpportunityScannerError("unsupported P13-C policy")

        def classes(key: str, expected: tuple[str, ...]) -> tuple[str, ...]:
            value = raw.get(key)
            if not isinstance(value, list):
                raise OpportunityScannerError(f"{key} must be list")
            normalized = tuple(str(item).strip().upper() for item in cast(list[object], value))
            if normalized != expected:
                raise OpportunityScannerError(f"unexpected {key}")
            return normalized

        eligible = classes("eligible_timing_classes", ("PREFERRED", "STANDARD"))
        observe = classes("observe_only_timing_classes", ("WEAK",))
        ineligible = classes("ineligible_timing_classes", ("INSUFFICIENT_EVIDENCE", "CLOSED_CONTEXT"))
        states = classes(
            "candidate_states",
            ("ELIGIBLE_TIMING_CONTEXT", "OBSERVE_ONLY", "INELIGIBLE_CONTEXT"),
        )
        if raw.get("require_source_lineage") is not True:
            raise OpportunityScannerError("source lineage must be required")
        if raw.get("canonical_stable_ordering") is not True:
            raise OpportunityScannerError("canonical stable ordering must be enabled")
        if raw.get("opportunity_ranking_in_scope") is not False:
            raise OpportunityScannerError("opportunity ranking belongs to P13-D")
        if raw.get("hard_no_trade_authority") is not False:
            raise OpportunityScannerError("hard no-trade authority belongs to P13-E")
        if raw.get("signal_expiry_in_scope") is not False:
            raise OpportunityScannerError("signal expiry belongs to P13-F")
        if raw.get("signal_probability_in_scope") is not False:
            raise OpportunityScannerError("signal probability belongs to P14")
        if raw.get("canonical_tests_network_required") is not False:
            raise OpportunityScannerError("canonical P13-C tests must remain offline")
        if raw.get("live_trading") != "DISABLED" or raw.get("auto_trading") != "DISABLED":
            raise OpportunityScannerError("P13-C cannot enable trading")

        return cls(
            eligible_timing_classes=eligible,
            observe_only_timing_classes=observe,
            ineligible_timing_classes=ineligible,
            candidate_states=states,
            require_source_lineage=True,
            canonical_stable_ordering=True,
            opportunity_ranking_in_scope=False,
            hard_no_trade_authority=False,
            signal_expiry_in_scope=False,
            signal_probability_in_scope=False,
            canonical_tests_network_required=False,
            live_trading="DISABLED",
            auto_trading="DISABLED",
        )


@dataclass(frozen=True, slots=True)
class OpportunityScanInput:
    assessment: TimingWindowAssessment
    provenance_sha256: tuple[str, ...]
    source_dataset_versions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OpportunityCandidate:
    candidate_id: str
    window_id: str
    asset_id: str
    strategy_id: str
    timeframe: str
    regime_label: str
    session_labels: tuple[str, ...]
    sample_count: int
    adjusted_edge_bps: int
    timing_class: str
    scanner_state: str
    eligible: bool
    provenance_sha256: tuple[str, ...]
    source_dataset_versions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OpportunityScanResult:
    candidates: tuple[OpportunityCandidate, ...]
    eligible_candidate_ids: tuple[str, ...]
    observe_only_candidate_ids: tuple[str, ...]
    ineligible_candidate_ids: tuple[str, ...]


def _candidate_id(
    assessment: TimingWindowAssessment,
    provenance_sha256: tuple[str, ...],
    source_dataset_versions: tuple[str, ...],
) -> str:
    payload = {
        "window_id": assessment.window_id,
        "asset_id": assessment.asset_id,
        "strategy_id": assessment.strategy_id,
        "timeframe": assessment.timeframe,
        "regime_label": assessment.regime_label,
        "session_labels": list(assessment.session_labels),
        "sample_count": assessment.sample_count,
        "adjusted_edge_bps": assessment.adjusted_edge_bps,
        "timing_class": assessment.timing_class,
        "provenance_sha256": list(provenance_sha256),
        "source_dataset_versions": list(source_dataset_versions),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _scan_one(item: OpportunityScanInput, *, policy: OpportunityScannerPolicy) -> OpportunityCandidate:
    assessment = item.assessment
    timing_class = _text(assessment.timing_class, field="timing_class").upper()
    provenance = _lineage(item.provenance_sha256, field="provenance_sha256", sha256=True)
    versions = _lineage(item.source_dataset_versions, field="source_dataset_versions")

    all_classes = (
        policy.eligible_timing_classes
        + policy.observe_only_timing_classes
        + policy.ineligible_timing_classes
    )
    if timing_class not in all_classes:
        raise OpportunityScannerError("unknown timing_class")

    if timing_class in policy.eligible_timing_classes:
        if not assessment.usable:
            raise OpportunityScannerError("eligible timing class must be usable")
        state = "ELIGIBLE_TIMING_CONTEXT"
        eligible = True
    elif timing_class in policy.observe_only_timing_classes:
        if not assessment.usable:
            raise OpportunityScannerError("observe-only timing class must be usable")
        state = "OBSERVE_ONLY"
        eligible = False
    else:
        if assessment.usable:
            raise OpportunityScannerError("ineligible timing class cannot be usable")
        state = "INELIGIBLE_CONTEXT"
        eligible = False

    return OpportunityCandidate(
        candidate_id=_candidate_id(assessment, provenance, versions),
        window_id=_text(assessment.window_id, field="window_id"),
        asset_id=_text(assessment.asset_id, field="asset_id"),
        strategy_id=_text(assessment.strategy_id, field="strategy_id"),
        timeframe=_text(assessment.timeframe, field="timeframe"),
        regime_label=_text(assessment.regime_label, field="regime_label").upper(),
        session_labels=tuple(sorted({_text(value, field="session_label").upper() for value in assessment.session_labels})),
        sample_count=assessment.sample_count,
        adjusted_edge_bps=assessment.adjusted_edge_bps,
        timing_class=timing_class,
        scanner_state=state,
        eligible=eligible,
        provenance_sha256=provenance,
        source_dataset_versions=versions,
    )


def scan_opportunities(
    items: Sequence[OpportunityScanInput],
    *,
    policy: OpportunityScannerPolicy,
) -> OpportunityScanResult:
    if not items:
        raise OpportunityScannerError("scanner input must be non-empty")
    candidates = tuple(_scan_one(item, policy=policy) for item in items)
    ids = [item.candidate_id for item in candidates]
    if len(ids) != len(set(ids)):
        raise OpportunityScannerError("duplicate canonical opportunity candidate")
    ordered = tuple(
        sorted(
            candidates,
            key=lambda item: (
                item.asset_id,
                item.strategy_id,
                item.timeframe,
                item.regime_label,
                item.candidate_id,
            ),
        )
    )
    return OpportunityScanResult(
        candidates=ordered,
        eligible_candidate_ids=tuple(item.candidate_id for item in ordered if item.scanner_state == "ELIGIBLE_TIMING_CONTEXT"),
        observe_only_candidate_ids=tuple(item.candidate_id for item in ordered if item.scanner_state == "OBSERVE_ONLY"),
        ineligible_candidate_ids=tuple(item.candidate_id for item in ordered if item.scanner_state == "INELIGIBLE_CONTEXT"),
    )
