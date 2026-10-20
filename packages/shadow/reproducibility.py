from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence, cast


class ReproducibilityError(ValueError):
    """P19-G deterministic reproducibility invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ReproducibilityError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReproducibilityError(f"{field} must be non-empty text")
    return value.strip()


def _sha(value: object, *, field: str) -> str:
    parsed = _text(value, field=field).lower()
    if len(parsed) != 64 or any(ch not in "0123456789abcdef" for ch in parsed):
        raise ReproducibilityError(f"{field} must be lowercase SHA-256")
    if len(set(parsed)) < 4:
        raise ReproducibilityError(f"{field} cannot be a degenerate placeholder")
    return parsed


@dataclass(frozen=True, slots=True)
class ReproducibilityPolicy:
    required_workstreams: tuple[str, ...]
    manifest_state_required: str
    manifest_lock_required: str
    p19f_claim_scope_required: str
    p19f_live_empirical_status_required: str
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "ReproducibilityPolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ReproducibilityError(f"invalid P19-G policy JSON: {exc}") from exc
        raw = _mapping(raw_value, field="policy root")
        expected = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P19G_DETERMINISTIC_REPRODUCIBILITY_POLICY",
            "task_id": "FIN-P19-WG-001",
            "mode": "STRICT_CROSS_WORKSTREAM_REPRODUCIBILITY",
            "evidence_pair_match": "BYTE_IDENTICAL",
            "manifest_state_required": "CANONICAL_COMPLETE",
            "manifest_lock_required": "RELEASED",
            "p19f_claim_scope_required": "REFERENCE_ONLY",
            "p19f_live_empirical_status_required": "UNAVAILABLE_PRE_P20_H",
            "p19f_live_drift_validated_required": False,
            "g10_authority": False,
            "production_readiness_authority": False,
            "execution_authority": False,
            "order_routing_authority": False,
            "broker_exchange_routing": False,
            "p20_started": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        for key, value in expected.items():
            if raw.get(key) != value:
                raise ReproducibilityError(f"P19-G policy mismatch: {key}")
        for field in (
            "cross_workstream_lineage_required",
            "package_policy_identity_required",
        ):
            if raw.get(field) is not True:
                raise ReproducibilityError(f"P19-G required invariant disabled: {field}")
        workstreams_raw = raw.get("required_workstreams")
        if not isinstance(workstreams_raw, list):
            raise ReproducibilityError("required_workstreams must be a list")
        workstreams = tuple(str(item) for item in cast(list[object], workstreams_raw))
        if workstreams != ("P19-A", "P19-B", "P19-C", "P19-D", "P19-E", "P19-F"):
            raise ReproducibilityError("P19-G workstream coverage/order drift")
        return cls(
            required_workstreams=workstreams,
            manifest_state_required="CANONICAL_COMPLETE",
            manifest_lock_required="RELEASED",
            p19f_claim_scope_required="REFERENCE_ONLY",
            p19f_live_empirical_status_required="UNAVAILABLE_PRE_P20_H",
            live_trading="DISABLED",
            auto_trading="DISABLED",
        )

    @property
    def policy_id(self) -> str:
        return hashlib.sha256(
            _canonical_bytes(
                {
                    "required_workstreams": list(self.required_workstreams),
                    "manifest_state_required": self.manifest_state_required,
                    "manifest_lock_required": self.manifest_lock_required,
                    "p19f_claim_scope_required": self.p19f_claim_scope_required,
                    "p19f_live_empirical_status_required": (
                        self.p19f_live_empirical_status_required
                    ),
                    "live_trading": self.live_trading,
                    "auto_trading": self.auto_trading,
                }
            )
        ).hexdigest()


@dataclass(frozen=True, slots=True)
class WorkstreamReproducibilityRecord:
    workstream: str
    evidence_kind: str
    evidence_sha256: str
    manifest_kind: str
    manifest_sha256: str
    package_sha256: str
    policy_sha256: str
    manifest_state: str
    lock_state: str
    claim_scope: str | None = None
    live_empirical_status: str | None = None
    live_drift_validated: bool | None = None
    g10_authority: bool = False
    production_readiness_authority: bool = False
    execution_authority: bool = False
    order_routing_authority: bool = False
    broker_exchange_routing: bool = False
    p20_started: bool = False
    live_trading: str = "DISABLED"
    auto_trading: str = "DISABLED"

    def __post_init__(self) -> None:
        if self.workstream not in {"P19-A", "P19-B", "P19-C", "P19-D", "P19-E", "P19-F"}:
            raise ReproducibilityError("unsupported P19 reproducibility workstream")
        object.__setattr__(
            self,
            "evidence_kind",
            _text(self.evidence_kind, field="evidence_kind"),
        )
        object.__setattr__(
            self,
            "manifest_kind",
            _text(self.manifest_kind, field="manifest_kind"),
        )
        for field in (
            "evidence_sha256",
            "manifest_sha256",
            "package_sha256",
            "policy_sha256",
        ):
            object.__setattr__(self, field, _sha(getattr(self, field), field=field))
        if self.manifest_state != "CANONICAL_COMPLETE":
            raise ReproducibilityError("workstream manifest is not CANONICAL_COMPLETE")
        if self.lock_state != "RELEASED":
            raise ReproducibilityError("workstream manifest lock is not RELEASED")
        if any(
            (
                self.g10_authority,
                self.production_readiness_authority,
                self.execution_authority,
                self.order_routing_authority,
                self.broker_exchange_routing,
                self.p20_started,
            )
        ):
            raise ReproducibilityError("P19-G input carries forbidden authority")
        if self.live_trading != "DISABLED" or self.auto_trading != "DISABLED":
            raise ReproducibilityError("P19-G input cannot enable Live/Auto trading")
        if self.workstream == "P19-F":
            if self.claim_scope != "REFERENCE_ONLY":
                raise ReproducibilityError("P19-F claim scope must remain REFERENCE_ONLY")
            if self.live_empirical_status != "UNAVAILABLE_PRE_P20_H":
                raise ReproducibilityError(
                    "P19-F live empirical status must remain unavailable pre-P20-H"
                )
            if self.live_drift_validated is not False:
                raise ReproducibilityError(
                    "P19-F reference evidence cannot validate Live drift"
                )
        elif any(
            value is not None
            for value in (
                self.claim_scope,
                self.live_empirical_status,
                self.live_drift_validated,
            )
        ):
            raise ReproducibilityError(
                "Live drift claim fields belong only to P19-F record"
            )

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "workstream": self.workstream,
            "evidence_kind": self.evidence_kind,
            "evidence_sha256": self.evidence_sha256,
            "manifest_kind": self.manifest_kind,
            "manifest_sha256": self.manifest_sha256,
            "package_sha256": self.package_sha256,
            "policy_sha256": self.policy_sha256,
            "manifest_state": self.manifest_state,
            "lock_state": self.lock_state,
            "claim_scope": self.claim_scope,
            "live_empirical_status": self.live_empirical_status,
            "live_drift_validated": self.live_drift_validated,
            "g10_authority": self.g10_authority,
            "production_readiness_authority": self.production_readiness_authority,
            "execution_authority": self.execution_authority,
            "order_routing_authority": self.order_routing_authority,
            "broker_exchange_routing": self.broker_exchange_routing,
            "p20_started": self.p20_started,
            "live_trading": self.live_trading,
            "auto_trading": self.auto_trading,
        }

    @property
    def record_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class ReproducibilityCertificate:
    policy_id: str
    record_ids: tuple[str, ...]
    records: tuple[WorkstreamReproducibilityRecord, ...]
    coverage_state: str = "P19_A_TO_F_COMPLETE"
    evidence_pair_match: str = "BYTE_IDENTICAL"
    cross_workstream_lineage: str = "VERIFIED"
    claim_scope: str = "REFERENCE_REPRODUCIBILITY_ONLY"
    live_empirical_status: str = "UNAVAILABLE_PRE_P20_H"
    live_drift_validated: bool = False
    g10_authority: bool = False
    production_readiness_authority: bool = False
    execution_authority: bool = False
    order_routing_authority: bool = False
    broker_exchange_routing: bool = False
    p20_started: bool = False
    live_trading: str = "DISABLED"
    auto_trading: str = "DISABLED"

    @classmethod
    def build(
        cls,
        *,
        records: Sequence[WorkstreamReproducibilityRecord],
        policy: ReproducibilityPolicy,
    ) -> "ReproducibilityCertificate":
        workstreams = tuple(record.workstream for record in records)
        if workstreams != policy.required_workstreams:
            raise ReproducibilityError(
                "P19-G requires exact canonical P19-A..P19-F record order"
            )
        if len(set(workstreams)) != len(workstreams):
            raise ReproducibilityError("duplicate reproducibility workstream")
        return cls(
            policy_id=policy.policy_id,
            record_ids=tuple(record.record_id for record in records),
            records=tuple(records),
            live_trading=policy.live_trading,
            auto_trading=policy.auto_trading,
        )

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "policy_id": self.policy_id,
            "record_ids": list(self.record_ids),
            "records": [record.payload() for record in self.records],
            "coverage_state": self.coverage_state,
            "evidence_pair_match": self.evidence_pair_match,
            "cross_workstream_lineage": self.cross_workstream_lineage,
            "claim_scope": self.claim_scope,
            "live_empirical_status": self.live_empirical_status,
            "live_drift_validated": self.live_drift_validated,
            "g10_authority": self.g10_authority,
            "production_readiness_authority": self.production_readiness_authority,
            "execution_authority": self.execution_authority,
            "order_routing_authority": self.order_routing_authority,
            "broker_exchange_routing": self.broker_exchange_routing,
            "p20_started": self.p20_started,
            "live_trading": self.live_trading,
            "auto_trading": self.auto_trading,
        }

    @property
    def certificate_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()
