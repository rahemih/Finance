from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Sequence


class WalkForwardError(ValueError):
    """P17-D OOS/walk-forward invariant failure."""


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$")


def _safe_id(value: str, *, field: str) -> str:
    parsed=value.strip()
    if _SAFE_ID.fullmatch(parsed) is None:
        raise WalkForwardError(f"{field} contains unsafe characters")
    return parsed


def _sha(value: str, *, field: str) -> str:
    parsed=value.strip().lower()
    if _SHA256.fullmatch(parsed) is None:
        raise WalkForwardError(f"{field} must be lowercase SHA-256")
    return parsed


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True,slots=True)
class WalkForwardFold:
    fold_id: str
    train_start_ns: int
    train_end_ns: int
    validation_start_ns: int
    validation_end_ns: int
    test_start_ns: int
    test_end_ns: int

    def __post_init__(self)->None:
        _safe_id(self.fold_id,field="fold_id")
        values=(
            self.train_start_ns,self.train_end_ns,
            self.validation_start_ns,self.validation_end_ns,
            self.test_start_ns,self.test_end_ns,
        )
        if any(value<0 for value in values):
            raise WalkForwardError("fold timestamps must be non-negative")
        if not (
            self.train_start_ns < self.train_end_ns
            <= self.validation_start_ns < self.validation_end_ns
            <= self.test_start_ns < self.test_end_ns
        ):
            raise WalkForwardError(
                "fold windows must be ordered train then validation then test"
            )

    def payload(self)->dict[str,object]:
        return {
            "fold_id":self.fold_id,
            "train_start_ns":self.train_start_ns,
            "train_end_ns":self.train_end_ns,
            "validation_start_ns":self.validation_start_ns,
            "validation_end_ns":self.validation_end_ns,
            "test_start_ns":self.test_start_ns,
            "test_end_ns":self.test_end_ns,
        }


@dataclass(frozen=True,slots=True)
class CandidateSelection:
    selection_id: str
    fold_id: str
    candidate_id: str
    selected_at_ns: int
    training_artifact_sha256: str
    validation_artifact_sha256: str

    def __post_init__(self)->None:
        _safe_id(self.selection_id,field="selection_id")
        _safe_id(self.fold_id,field="fold_id")
        _safe_id(self.candidate_id,field="candidate_id")
        if self.selected_at_ns<0:
            raise WalkForwardError("selected_at_ns must be non-negative")
        _sha(self.training_artifact_sha256,field="training_artifact_sha256")
        _sha(self.validation_artifact_sha256,field="validation_artifact_sha256")

    def payload(self)->dict[str,object]:
        return {
            "selection_id":self.selection_id,
            "fold_id":self.fold_id,
            "candidate_id":self.candidate_id,
            "selected_at_ns":self.selected_at_ns,
            "training_artifact_sha256":self.training_artifact_sha256,
            "validation_artifact_sha256":self.validation_artifact_sha256,
        }


@dataclass(frozen=True,slots=True)
class OutOfSampleResultRef:
    result_ref_id: str
    fold_id: str
    backtest_result_id: str
    information_hygiene_certificate_id: str
    test_start_ns: int
    test_end_ns: int

    def __post_init__(self)->None:
        _safe_id(self.result_ref_id,field="result_ref_id")
        _safe_id(self.fold_id,field="fold_id")
        _sha(self.backtest_result_id,field="backtest_result_id")
        _sha(
            self.information_hygiene_certificate_id,
            field="information_hygiene_certificate_id",
        )
        if self.test_start_ns<0 or self.test_end_ns<=self.test_start_ns:
            raise WalkForwardError("invalid OOS result test window")

    def payload(self)->dict[str,object]:
        return {
            "result_ref_id":self.result_ref_id,
            "fold_id":self.fold_id,
            "backtest_result_id":self.backtest_result_id,
            "information_hygiene_certificate_id":self.information_hygiene_certificate_id,
            "test_start_ns":self.test_start_ns,
            "test_end_ns":self.test_end_ns,
        }


@dataclass(frozen=True,slots=True)
class WalkForwardCertificate:
    certificate_id: str
    status: str
    fold_ids: tuple[str,...]
    selection_ids: tuple[str,...]
    result_ref_ids: tuple[str,...]
    g9_authority: bool=False
    profitability_claim_authority: bool=False
    execution_authority: bool=False
    order_routing_authority: bool=False
    live_trading: str="DISABLED"
    auto_trading: str="DISABLED"


def certify_walk_forward(
    *,
    folds: Sequence[WalkForwardFold],
    selections: Sequence[CandidateSelection],
    results: Sequence[OutOfSampleResultRef],
)->WalkForwardCertificate:
    ordered_folds=tuple(sorted(folds,key=lambda x:(x.test_start_ns,x.fold_id)))
    if not ordered_folds:
        raise WalkForwardError("walk-forward requires at least one fold")
    fold_ids=tuple(x.fold_id for x in ordered_folds)
    if len(fold_ids)!=len(set(fold_ids)):
        raise WalkForwardError("duplicate fold_id")

    previous_test_end: int|None=None
    for fold in ordered_folds:
        if previous_test_end is not None and fold.test_start_ns < previous_test_end:
            raise WalkForwardError("test windows overlap across folds")
        previous_test_end=fold.test_end_ns

    ordered_selections=tuple(sorted(selections,key=lambda x:(x.fold_id,x.selection_id)))
    selection_ids=tuple(x.selection_id for x in ordered_selections)
    if len(selection_ids)!=len(set(selection_ids)):
        raise WalkForwardError("duplicate selection_id")
    by_selection: dict[str,CandidateSelection]={}
    for item in ordered_selections:
        if item.fold_id in by_selection:
            raise WalkForwardError("multiple selections for one fold")
        by_selection[item.fold_id]=item

    ordered_results=tuple(sorted(results,key=lambda x:(x.fold_id,x.result_ref_id)))
    result_ids=tuple(x.result_ref_id for x in ordered_results)
    if len(result_ids)!=len(set(result_ids)):
        raise WalkForwardError("duplicate result_ref_id")
    by_result: dict[str,OutOfSampleResultRef]={}
    for item in ordered_results:
        if item.fold_id in by_result:
            raise WalkForwardError("multiple OOS results for one fold")
        by_result[item.fold_id]=item

    for fold in ordered_folds:
        selection=by_selection.get(fold.fold_id)
        if selection is None:
            raise WalkForwardError("missing candidate selection for fold")
        if selection.selected_at_ns >= fold.test_start_ns:
            raise WalkForwardError("candidate selection is test-informed")

        result=by_result.get(fold.fold_id)
        if result is None:
            raise WalkForwardError("missing OOS result for fold")
        if (
            result.test_start_ns != fold.test_start_ns
            or result.test_end_ns != fold.test_end_ns
        ):
            raise WalkForwardError("OOS result test window mismatch")

    if set(by_selection)!=set(fold_ids) or set(by_result)!=set(fold_ids):
        raise WalkForwardError("fold coverage mismatch")

    body={
        "schema_version":"1.0",
        "kind":"NEXUS_QUANT_P17D_WALK_FORWARD_CERTIFICATE",
        "status":"PASS",
        "folds":[x.payload() for x in ordered_folds],
        "selections":[x.payload() for x in ordered_selections],
        "results":[x.payload() for x in ordered_results],
        "g9_authority":False,
        "profitability_claim_authority":False,
        "execution_authority":False,
        "order_routing_authority":False,
        "live_trading":"DISABLED",
        "auto_trading":"DISABLED",
    }
    return WalkForwardCertificate(
        certificate_id=hashlib.sha256(_canonical_bytes(body)).hexdigest(),
        status="PASS",
        fold_ids=fold_ids,
        selection_ids=selection_ids,
        result_ref_ids=result_ids,
    )
