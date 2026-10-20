from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence, cast


class ShadowValidationGateError(ValueError):
    """P19-H G10 shadow-validation invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ShadowValidationGateError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ShadowValidationGateError(f"{field} must be non-empty text")
    return value.strip()


def _sha(value: object, *, field: str) -> str:
    parsed = _text(value, field=field).lower()
    if len(parsed) != 64 or any(ch not in "0123456789abcdef" for ch in parsed):
        raise ShadowValidationGateError(f"{field} must be lowercase SHA-256")
    if len(set(parsed)) < 4:
        raise ShadowValidationGateError(f"{field} cannot be a degenerate placeholder")
    return parsed


@dataclass(frozen=True, slots=True)
class ShadowValidationGatePolicy:
    required_workstreams: tuple[str, ...]
    gate_name: str
    gate_claim_scope: str
    next_phase: str
    next_phase_state_after_pass: str
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "ShadowValidationGatePolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ShadowValidationGateError(
                f"invalid P19-H policy JSON: {exc}"
            ) from exc
        raw = _mapping(raw_value, field="policy root")
        expected = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P19H_SHADOW_VALIDATION_GATE_POLICY",
            "task_id": "FIN-P19-WH-001",
            "mode": "DETERMINISTIC_SHADOW_VALIDATION_GATE",
            "gate_name": "G10_SHADOW_VALIDATED",
            "manifest_state_required": "CANONICAL_COMPLETE",
            "manifest_lock_required": "RELEASED",
            "p19g_coverage_state_required": "P19_A_TO_F_COMPLETE",
            "p19g_evidence_pair_match_required": "BYTE_IDENTICAL",
            "p19g_cross_workstream_lineage_required": "VERIFIED",
            "p19g_claim_scope_required": "REFERENCE_REPRODUCIBILITY_ONLY",
            "live_empirical_status_required": "UNAVAILABLE_PRE_P20_H",
            "live_drift_validated_required": False,
            "gate_claim_scope": "SHADOW_REFERENCE_VALIDATION",
            "live_execution_validated": False,
            "broker_certification_validated": False,
            "production_readiness": False,
            "profitability_guarantee": False,
            "next_phase": "P20",
            "next_phase_state_after_pass": (
                "NOT_STARTED_OWNER_PHASE_AUTHORIZATION_REQUIRED"
            ),
            "automatic_p20_activation": False,
            "execution_authority": False,
            "order_routing_authority": False,
            "broker_exchange_routing": False,
            "p20_started": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        for key, value in expected.items():
            if raw.get(key) != value:
                raise ShadowValidationGateError(f"P19-H policy mismatch: {key}")

        workstreams_raw = raw.get("required_workstreams")
        if not isinstance(workstreams_raw, list):
            raise ShadowValidationGateError("required_workstreams must be a list")
        workstreams = tuple(
            _text(item, field="required_workstream")
            for item in cast(list[object], workstreams_raw)
        )
        expected_workstreams = (
            "P19-A",
            "P19-B",
            "P19-C",
            "P19-D",
            "P19-E",
            "P19-F",
            "P19-G",
        )
        if workstreams != expected_workstreams:
            raise ShadowValidationGateError(
                "G10 requires exact P19-A..P19-G workstream order"
            )

        return cls(
            required_workstreams=workstreams,
            gate_name="G10_SHADOW_VALIDATED",
            gate_claim_scope="SHADOW_REFERENCE_VALIDATION",
            next_phase="P20",
            next_phase_state_after_pass=(
                "NOT_STARTED_OWNER_PHASE_AUTHORIZATION_REQUIRED"
            ),
            live_trading="DISABLED",
            auto_trading="DISABLED",
        )

    @property
    def policy_id(self) -> str:
        return hashlib.sha256(
            _canonical_bytes(
                {
                    "required_workstreams": list(self.required_workstreams),
                    "gate_name": self.gate_name,
                    "gate_claim_scope": self.gate_claim_scope,
                    "next_phase": self.next_phase,
                    "next_phase_state_after_pass": self.next_phase_state_after_pass,
                    "live_trading": self.live_trading,
                    "auto_trading": self.auto_trading,
                }
            )
        ).hexdigest()


@dataclass(frozen=True, slots=True)
class ShadowGateWorkstreamRecord:
    workstream: str
    evidence_kind: str
    evidence_sha256: str
    manifest_kind: str
    manifest_sha256: str
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
        if self.workstream not in {
            "P19-A","P19-B","P19-C","P19-D","P19-E","P19-F","P19-G"
        }:
            raise ShadowValidationGateError("unsupported P19-H workstream")
        object.__setattr__(
            self, "evidence_kind", _text(self.evidence_kind, field="evidence_kind")
        )
        object.__setattr__(
            self, "manifest_kind", _text(self.manifest_kind, field="manifest_kind")
        )
        object.__setattr__(
            self,
            "evidence_sha256",
            _sha(self.evidence_sha256, field="evidence_sha256"),
        )
        object.__setattr__(
            self,
            "manifest_sha256",
            _sha(self.manifest_sha256, field="manifest_sha256"),
        )
        if self.manifest_state != "CANONICAL_COMPLETE":
            raise ShadowValidationGateError(
                f"{self.workstream} manifest is not CANONICAL_COMPLETE"
            )
        if self.lock_state != "RELEASED":
            raise ShadowValidationGateError(
                f"{self.workstream} lock is not RELEASED"
            )
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
            raise ShadowValidationGateError(
                f"{self.workstream} carries forbidden authority"
            )
        if self.live_trading != "DISABLED" or self.auto_trading != "DISABLED":
            raise ShadowValidationGateError(
                f"{self.workstream} cannot enable Live/Auto trading"
            )

        if self.workstream == "P19-F":
            if self.claim_scope != "REFERENCE_ONLY":
                raise ShadowValidationGateError(
                    "P19-F claim scope must remain REFERENCE_ONLY"
                )
            if self.live_empirical_status != "UNAVAILABLE_PRE_P20_H":
                raise ShadowValidationGateError(
                    "P19-F live empirical status must remain unavailable pre-P20-H"
                )
            if self.live_drift_validated is not False:
                raise ShadowValidationGateError(
                    "P19-F cannot validate Live drift before P20-H"
                )
        elif self.workstream == "P19-G":
            if self.claim_scope != "REFERENCE_REPRODUCIBILITY_ONLY":
                raise ShadowValidationGateError(
                    "P19-G claim scope must remain reference reproducibility only"
                )
            if self.live_empirical_status != "UNAVAILABLE_PRE_P20_H":
                raise ShadowValidationGateError(
                    "P19-G live empirical status must remain unavailable pre-P20-H"
                )
            if self.live_drift_validated is not False:
                raise ShadowValidationGateError(
                    "P19-G cannot validate Live drift before P20-H"
                )
        elif any(
            item is not None
            for item in (
                self.claim_scope,
                self.live_empirical_status,
                self.live_drift_validated,
            )
        ):
            raise ShadowValidationGateError(
                "reference/live claim fields are allowed only for P19-F/P19-G"
            )

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "workstream": self.workstream,
            "evidence_kind": self.evidence_kind,
            "evidence_sha256": self.evidence_sha256,
            "manifest_kind": self.manifest_kind,
            "manifest_sha256": self.manifest_sha256,
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
class ReproducibilityGateSummary:
    reproducibility_certificate_id: str
    coverage_state: str
    evidence_pair_match: str
    cross_workstream_lineage: str
    claim_scope: str
    live_empirical_status: str
    live_drift_validated: bool
    g10_authority: bool = False
    production_readiness_authority: bool = False
    execution_authority: bool = False
    order_routing_authority: bool = False
    broker_exchange_routing: bool = False
    p20_started: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "reproducibility_certificate_id",
            _sha(
                self.reproducibility_certificate_id,
                field="reproducibility_certificate_id",
            ),
        )
        expected = {
            "coverage_state": "P19_A_TO_F_COMPLETE",
            "evidence_pair_match": "BYTE_IDENTICAL",
            "cross_workstream_lineage": "VERIFIED",
            "claim_scope": "REFERENCE_REPRODUCIBILITY_ONLY",
            "live_empirical_status": "UNAVAILABLE_PRE_P20_H",
        }
        for field, value in expected.items():
            if getattr(self, field) != value:
                raise ShadowValidationGateError(
                    f"P19-G reproducibility summary mismatch: {field}"
                )
        if self.live_drift_validated is not False:
            raise ShadowValidationGateError(
                "P19-G summary cannot validate Live drift"
            )
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
            raise ShadowValidationGateError(
                "P19-G summary carries forbidden authority"
            )

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "reproducibility_certificate_id": self.reproducibility_certificate_id,
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
        }


@dataclass(frozen=True, slots=True)
class ShadowValidationGateCertificate:
    gate_name: str
    state: str
    gate_claim_scope: str
    policy_id: str
    workstream_coverage: tuple[str, ...]
    workstream_record_ids: tuple[str, ...]
    reproducibility_certificate_id: str
    next_phase: str
    next_phase_state: str
    live_execution_validated: bool = False
    broker_certification_validated: bool = False
    production_readiness: bool = False
    profitability_guarantee: bool = False
    automatic_p20_activation: bool = False
    execution_authority: bool = False
    order_routing_authority: bool = False
    broker_exchange_routing: bool = False
    p20_started: bool = False
    live_trading: str = "DISABLED"
    auto_trading: str = "DISABLED"

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "gate_name": self.gate_name,
            "state": self.state,
            "gate_claim_scope": self.gate_claim_scope,
            "policy_id": self.policy_id,
            "workstream_coverage": list(self.workstream_coverage),
            "workstream_record_ids": list(self.workstream_record_ids),
            "reproducibility_certificate_id": self.reproducibility_certificate_id,
            "next_phase": self.next_phase,
            "next_phase_state": self.next_phase_state,
            "live_execution_validated": self.live_execution_validated,
            "broker_certification_validated": self.broker_certification_validated,
            "production_readiness": self.production_readiness,
            "profitability_guarantee": self.profitability_guarantee,
            "automatic_p20_activation": self.automatic_p20_activation,
            "execution_authority": self.execution_authority,
            "order_routing_authority": self.order_routing_authority,
            "broker_exchange_routing": self.broker_exchange_routing,
            "p20_started": self.p20_started,
            "live_trading": self.live_trading,
            "auto_trading": self.auto_trading,
        }

    @property
    def gate_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


def certify_g10_shadow_validated(
    *,
    policy: ShadowValidationGatePolicy,
    workstream_records: Sequence[ShadowGateWorkstreamRecord],
    reproducibility: ReproducibilityGateSummary,
) -> ShadowValidationGateCertificate:
    records = tuple(workstream_records)
    if len(records) != len(policy.required_workstreams):
        raise ShadowValidationGateError(
            "G10 requires exactly one record per P19-A..P19-G workstream"
        )
    coverage = tuple(item.workstream for item in records)
    if coverage != policy.required_workstreams:
        raise ShadowValidationGateError(
            "G10 requires exact ordered P19-A..P19-G coverage"
        )
    if len(set(coverage)) != len(coverage):
        raise ShadowValidationGateError("duplicate P19-H workstream record")
    evidence_ids = tuple(item.evidence_sha256 for item in records)
    manifest_ids = tuple(item.manifest_sha256 for item in records)
    if len(set(evidence_ids)) != len(evidence_ids):
        raise ShadowValidationGateError("duplicate P19 evidence identity")
    if len(set(manifest_ids)) != len(manifest_ids):
        raise ShadowValidationGateError("duplicate P19 manifest identity")

    return ShadowValidationGateCertificate(
        gate_name=policy.gate_name,
        state="PASS",
        gate_claim_scope=policy.gate_claim_scope,
        policy_id=policy.policy_id,
        workstream_coverage=coverage,
        workstream_record_ids=tuple(item.record_id for item in records),
        reproducibility_certificate_id=reproducibility.reproducibility_certificate_id,
        next_phase=policy.next_phase,
        next_phase_state=policy.next_phase_state_after_pass,
        live_execution_validated=False,
        broker_certification_validated=False,
        production_readiness=False,
        profitability_guarantee=False,
        automatic_p20_activation=False,
        execution_authority=False,
        order_routing_authority=False,
        broker_exchange_routing=False,
        p20_started=False,
        live_trading=policy.live_trading,
        auto_trading=policy.auto_trading,
    )
