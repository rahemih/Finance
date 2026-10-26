from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import string
from typing import Mapping, cast

from .broker_reconciliation import PositionReconciliationReport
from .canonical_position import PositionStateRecord


class RestartRecoveryError(ValueError):
    """P21-G deterministic restart/crash-recovery invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RestartRecoveryError(f"{field} must be non-empty text")
    return value.strip()


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RestartRecoveryError(f"{field} must be a positive integer")
    return value


def _sha256_hex(value: object, *, field: str) -> str:
    text = _text(value, field=field).lower()
    if len(text) != 64 or any(ch not in string.hexdigits for ch in text):
        raise RestartRecoveryError(f"{field} must be a sha256 hex digest")
    return text


@dataclass(frozen=True, slots=True)
class RestartRecoveryPolicy:
    required_position_states: tuple[str, ...]
    required_reconciliation_verdict_for_resume: str

    @classmethod
    def from_path(cls, path: Path) -> "RestartRecoveryPolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise RestartRecoveryError(f"invalid P21-G policy JSON: {exc}") from exc
        if not isinstance(raw_value, Mapping):
            raise RestartRecoveryError("P21-G policy root must be an object")
        raw = cast(Mapping[str, object], raw_value)
        expected: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P21G_RESTART_RECOVERY_POLICY",
            "task_id": "FIN-P21-WG-001",
            "mode": "DETERMINISTIC_CHECKPOINT_AND_RECONCILIATION_RECOVERY",
            "required_reconciliation_verdict_for_resume": "MATCHED",
            "require_exact_position_record_id": True,
            "require_checkpoint_content_hash": True,
            "require_reconciliation_report_binding": True,
            "mismatch_disposition": "SAFE_HOLD_NEW_ENTRY_BLOCK",
            "mismatch_action": "MANUAL_GOVERNED_RECOVERY_REQUIRED",
            "automatic_position_mutation": False,
            "automatic_oms_mutation": False,
            "auto_repair": False,
            "auto_flatten": False,
            "real_venue_query": False,
            "credential_mode": "NONE",
            "network_mode": "DISABLED",
            "external_order_submission": False,
            "external_order_mutation": False,
            "live_execution_validated": False,
            "live_execution_authority": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        for key, value in expected.items():
            if raw.get(key) != value:
                raise RestartRecoveryError(f"P21-G policy mismatch: {key}")
        states_raw = raw.get("required_position_states")
        if not isinstance(states_raw, list):
            raise RestartRecoveryError("required_position_states must be an array")
        states = tuple(_text(item, field="required_position_states") for item in cast(list[object], states_raw))
        if states != ("OPEN", "PARTIALLY_CLOSED", "CLOSED"):
            raise RestartRecoveryError("invalid P21-G position-state taxonomy")
        return cls(states, "MATCHED")

    @property
    def policy_id(self) -> str:
        return hashlib.sha256(_canonical_bytes({
            "required_position_states": list(self.required_position_states),
            "required_reconciliation_verdict_for_resume": self.required_reconciliation_verdict_for_resume,
            "mode": "DETERMINISTIC_CHECKPOINT_AND_RECONCILIATION_RECOVERY",
            "automatic_position_mutation": False,
            "live_execution_authority": False,
        })).hexdigest()


@dataclass(frozen=True, slots=True)
class PositionRecoveryCheckpoint:
    position_record_id: str
    position_payload: Mapping[str, object]
    persisted_at_ns: int
    persistence_ref: str
    content_sha256: str

    @classmethod
    def from_record(
        cls,
        record: PositionStateRecord,
        *,
        persisted_at_ns: int,
        persistence_ref: str,
    ) -> "PositionRecoveryCheckpoint":
        _positive_int(persisted_at_ns, field="persisted_at_ns")
        _text(persistence_ref, field="persistence_ref")
        payload = dict(record.payload())
        content_sha256 = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
        return cls(
            position_record_id=record.record_id,
            position_payload=payload,
            persisted_at_ns=persisted_at_ns,
            persistence_ref=persistence_ref,
            content_sha256=content_sha256,
        )

    def validate(self) -> None:
        _sha256_hex(self.position_record_id, field="position_record_id")
        _positive_int(self.persisted_at_ns, field="persisted_at_ns")
        _text(self.persistence_ref, field="persistence_ref")
        expected_hash = hashlib.sha256(_canonical_bytes(dict(self.position_payload))).hexdigest()
        if _sha256_hex(self.content_sha256, field="content_sha256") != expected_hash:
            raise RestartRecoveryError("checkpoint content hash mismatch")
        record_id = hashlib.sha256(_canonical_bytes(dict(self.position_payload))).hexdigest()
        if record_id != self.position_record_id.lower():
            raise RestartRecoveryError("checkpoint payload does not reproduce position_record_id")

    def payload(self) -> dict[str, object]:
        return {
            "position_record_id": self.position_record_id.lower(),
            "position_payload": dict(self.position_payload),
            "persisted_at_ns": self.persisted_at_ns,
            "persistence_ref": self.persistence_ref,
            "content_sha256": self.content_sha256.lower(),
        }

    @property
    def checkpoint_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class RestartRecoveryPlan:
    policy_id: str
    checkpoint_id: str
    position_record_id: str
    position_id: str
    canonical_state: str
    reconciliation_report_id: str
    reconciliation_verdict: str
    disposition: str
    recovered_payload_sha256: str
    safe_hold_required: bool
    new_entry_block_required: bool
    action: str
    automatic_position_mutation: bool = False
    automatic_oms_mutation: bool = False
    auto_repair: bool = False
    auto_flatten: bool = False
    real_venue_query: bool = False
    network_mode: str = "DISABLED"
    external_order_submission: bool = False
    external_order_mutation: bool = False
    live_execution_authority: bool = False

    def payload(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "checkpoint_id": self.checkpoint_id,
            "position_record_id": self.position_record_id,
            "position_id": self.position_id,
            "canonical_state": self.canonical_state,
            "reconciliation_report_id": self.reconciliation_report_id,
            "reconciliation_verdict": self.reconciliation_verdict,
            "disposition": self.disposition,
            "recovered_payload_sha256": self.recovered_payload_sha256,
            "safe_hold_required": self.safe_hold_required,
            "new_entry_block_required": self.new_entry_block_required,
            "action": self.action,
            "automatic_position_mutation": self.automatic_position_mutation,
            "automatic_oms_mutation": self.automatic_oms_mutation,
            "auto_repair": self.auto_repair,
            "auto_flatten": self.auto_flatten,
            "real_venue_query": self.real_venue_query,
            "network_mode": self.network_mode,
            "external_order_submission": self.external_order_submission,
            "external_order_mutation": self.external_order_mutation,
            "live_execution_authority": self.live_execution_authority,
        }

    @property
    def plan_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


class PositionRestartRecovery:
    def __init__(self, policy: RestartRecoveryPolicy) -> None:
        self._policy = policy

    def plan(
        self,
        checkpoint: PositionRecoveryCheckpoint,
        reconciliation: PositionReconciliationReport,
    ) -> RestartRecoveryPlan:
        checkpoint.validate()
        payload = checkpoint.position_payload
        position_id = _text(payload.get("position_id"), field="position_id")
        state = _text(payload.get("state"), field="state")
        if state not in self._policy.required_position_states:
            raise RestartRecoveryError("unsupported checkpoint position state")
        if reconciliation.position_record_id.lower() != checkpoint.position_record_id.lower():
            raise RestartRecoveryError("reconciliation report is not bound to checkpoint position record")
        if reconciliation.position_id != position_id:
            raise RestartRecoveryError("reconciliation report position_id mismatch")
        if reconciliation.safe_hold_required != (reconciliation.verdict != "MATCHED"):
            raise RestartRecoveryError("reconciliation safe-hold semantics are inconsistent")
        if reconciliation.new_entry_block_required != (reconciliation.verdict != "MATCHED"):
            raise RestartRecoveryError("reconciliation entry-block semantics are inconsistent")
        if reconciliation.verdict == "MATCHED":
            if reconciliation.action != "NONE":
                raise RestartRecoveryError("matched reconciliation action must be NONE")
            disposition = "RECOVERABLE_MATCHED_CHECKPOINT"
            safe_hold = False
            new_entry_block = False
            action = "RESTORE_VALIDATED_CANONICAL_STATE"
        else:
            if reconciliation.action != "MANUAL_GOVERNED_RECONCILIATION_REQUIRED":
                raise RestartRecoveryError("mismatched reconciliation action is invalid")
            disposition = "SAFE_HOLD_MANUAL_RECOVERY_REQUIRED"
            safe_hold = True
            new_entry_block = True
            action = "MANUAL_GOVERNED_RECOVERY_REQUIRED"

        return RestartRecoveryPlan(
            policy_id=self._policy.policy_id,
            checkpoint_id=checkpoint.checkpoint_id,
            position_record_id=checkpoint.position_record_id.lower(),
            position_id=position_id,
            canonical_state=state,
            reconciliation_report_id=reconciliation.report_id,
            reconciliation_verdict=reconciliation.verdict,
            disposition=disposition,
            recovered_payload_sha256=checkpoint.content_sha256.lower(),
            safe_hold_required=safe_hold,
            new_entry_block_required=new_entry_block,
            action=action,
        )
