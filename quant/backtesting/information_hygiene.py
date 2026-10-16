from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Sequence

from packages.historical_data.replay_snapshot import ReplaySnapshot


class InformationHygieneError(ValueError):
    """P17-C point-in-time information hygiene invariant failure."""


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$")


def _safe_id(value: str, *, field: str) -> str:
    parsed = value.strip()
    if _SAFE_ID.fullmatch(parsed) is None:
        raise InformationHygieneError(f"{field} contains unsafe characters")
    return parsed


def _sha256(value: str, *, field: str) -> str:
    parsed = value.strip().lower()
    if _SHA256.fullmatch(parsed) is None:
        raise InformationHygieneError(f"{field} must be lowercase SHA-256")
    return parsed


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


@dataclass(frozen=True, slots=True)
class UniverseMembershipChange:
    change_id: str
    asset_id: str
    effective_at_ns: int
    available_at_ns: int
    is_member: bool
    evidence_sha256: str

    def __post_init__(self) -> None:
        _safe_id(self.change_id, field="change_id")
        _safe_id(self.asset_id, field="asset_id")
        if self.effective_at_ns < 0 or self.available_at_ns < 0:
            raise InformationHygieneError(
                "universe membership timestamps must be non-negative"
            )
        _sha256(self.evidence_sha256, field="evidence_sha256")

    def payload(self) -> dict[str, object]:
        return {
            "change_id": self.change_id,
            "asset_id": self.asset_id,
            "effective_at_ns": self.effective_at_ns,
            "available_at_ns": self.available_at_ns,
            "is_member": self.is_member,
            "evidence_sha256": self.evidence_sha256,
        }


@dataclass(frozen=True, slots=True)
class DecisionInformationAudit:
    decision_id: str
    asset_id: str
    decision_time_ns: int
    feature_materialization_ids: tuple[str, ...] = ()
    vintage_ids: tuple[str, ...] = ()
    dataset_versions: tuple[str, ...] = ()
    outcome_label_ids: tuple[str, ...] = ()

    @classmethod
    def build(
        cls,
        *,
        decision_id: str,
        asset_id: str,
        decision_time_ns: int,
        feature_materialization_ids: Sequence[str] = (),
        vintage_ids: Sequence[str] = (),
        dataset_versions: Sequence[str] = (),
        outcome_label_ids: Sequence[str] = (),
    ) -> "DecisionInformationAudit":
        def unique_sorted(
            values: Sequence[str],
            *,
            field: str,
            sha: bool,
        ) -> tuple[str, ...]:
            parsed = tuple(
                sorted(
                    _sha256(value, field=field)
                    if sha
                    else _safe_id(value, field=field)
                    for value in values
                )
            )
            if len(parsed) != len(set(parsed)):
                raise InformationHygieneError(f"duplicate {field}")
            return parsed

        return cls(
            decision_id=_safe_id(decision_id, field="decision_id"),
            asset_id=_safe_id(asset_id, field="asset_id"),
            decision_time_ns=decision_time_ns,
            feature_materialization_ids=unique_sorted(
                feature_materialization_ids,
                field="feature_materialization_id",
                sha=True,
            ),
            vintage_ids=unique_sorted(
                vintage_ids,
                field="vintage_id",
                sha=True,
            ),
            dataset_versions=unique_sorted(
                dataset_versions,
                field="dataset_version",
                sha=True,
            ),
            outcome_label_ids=unique_sorted(
                outcome_label_ids,
                field="outcome_label_id",
                sha=False,
            ),
        )

    def __post_init__(self) -> None:
        _safe_id(self.decision_id, field="decision_id")
        _safe_id(self.asset_id, field="asset_id")
        if self.decision_time_ns < 0:
            raise InformationHygieneError(
                "decision_time_ns must be non-negative"
            )

    def payload(self) -> dict[str, object]:
        return {
            "decision_id": self.decision_id,
            "asset_id": self.asset_id,
            "decision_time_ns": self.decision_time_ns,
            "feature_materialization_ids": list(
                self.feature_materialization_ids
            ),
            "vintage_ids": list(self.vintage_ids),
            "dataset_versions": list(self.dataset_versions),
            "outcome_label_ids": list(self.outcome_label_ids),
        }


@dataclass(frozen=True, slots=True)
class InformationHygieneCertificate:
    certificate_id: str
    snapshot_id: str
    status: str
    audited_decision_ids: tuple[str, ...]
    universe_change_ids: tuple[str, ...]
    g9_authority: bool = False
    profitability_claim_authority: bool = False
    execution_authority: bool = False
    order_routing_authority: bool = False
    live_trading: str = "DISABLED"
    auto_trading: str = "DISABLED"


def _is_member_at(
    *,
    asset_id: str,
    decision_time_ns: int,
    changes: tuple[UniverseMembershipChange, ...],
) -> bool | None:
    eligible = [
        item
        for item in changes
        if item.asset_id == asset_id
        and item.effective_at_ns <= decision_time_ns
        and item.available_at_ns <= decision_time_ns
    ]
    if not eligible:
        return None
    latest = max(
        eligible,
        key=lambda item: (
            item.effective_at_ns,
            item.available_at_ns,
            item.change_id,
        ),
    )
    return latest.is_member


def certify_information_hygiene(
    *,
    snapshot: ReplaySnapshot,
    decisions: Sequence[DecisionInformationAudit],
    universe_changes: Sequence[UniverseMembershipChange],
) -> InformationHygieneCertificate:
    ordered_decisions = tuple(
        sorted(
            decisions,
            key=lambda item: (
                item.decision_time_ns,
                item.decision_id,
            ),
        )
    )
    if not ordered_decisions:
        raise InformationHygieneError(
            "information hygiene requires at least one decision audit"
        )
    decision_ids = tuple(item.decision_id for item in ordered_decisions)
    if len(decision_ids) != len(set(decision_ids)):
        raise InformationHygieneError("duplicate decision audit ID")

    ordered_changes = tuple(
        sorted(
            universe_changes,
            key=lambda item: (
                item.effective_at_ns,
                item.available_at_ns,
                item.asset_id,
                item.change_id,
            ),
        )
    )
    change_ids = tuple(item.change_id for item in ordered_changes)
    if len(change_ids) != len(set(change_ids)):
        raise InformationHygieneError(
            "duplicate universe membership change ID"
        )

    for decision in ordered_decisions:
        view = snapshot.view_at(decision.decision_time_ns)

        available_features = {
            item.materialization_id for item in view.feature_refs
        }
        if not set(decision.feature_materialization_ids).issubset(
            available_features
        ):
            raise InformationHygieneError(
                "feature access is unavailable at decision time"
            )

        available_vintages = {item.vintage_id for item in view.vintage_refs}
        if not set(decision.vintage_ids).issubset(available_vintages):
            raise InformationHygieneError(
                "vintage access is unavailable at decision time"
            )

        available_datasets = {
            item.dataset_version for item in view.dataset_refs
        }
        if not set(decision.dataset_versions).issubset(available_datasets):
            raise InformationHygieneError(
                "dataset version is unavailable at decision time"
            )

        if decision.outcome_label_ids:
            raise InformationHygieneError(
                "outcome-label access is forbidden in strategy decisions"
            )

        membership = _is_member_at(
            asset_id=decision.asset_id,
            decision_time_ns=decision.decision_time_ns,
            changes=ordered_changes,
        )
        if membership is None:
            raise InformationHygieneError(
                "missing point-in-time universe membership"
            )
        if not membership:
            raise InformationHygieneError(
                "decision asset is outside point-in-time universe"
            )

    body = {
        "schema_version": "1.0",
        "kind": "NEXUS_QUANT_P17C_INFORMATION_HYGIENE_CERTIFICATE",
        "snapshot_id": snapshot.snapshot_id,
        "status": "PASS",
        "decisions": [item.payload() for item in ordered_decisions],
        "universe_changes": [item.payload() for item in ordered_changes],
        "g9_authority": False,
        "profitability_claim_authority": False,
        "execution_authority": False,
        "order_routing_authority": False,
        "live_trading": "DISABLED",
        "auto_trading": "DISABLED",
    }
    return InformationHygieneCertificate(
        certificate_id=hashlib.sha256(_canonical_bytes(body)).hexdigest(),
        snapshot_id=snapshot.snapshot_id,
        status="PASS",
        audited_decision_ids=decision_ids,
        universe_change_ids=change_ids,
    )
