from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence, cast


class PreTradeSafetyGateError(ValueError):
    """P16-H G8 pre-trade safety gate invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise PreTradeSafetyGateError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PreTradeSafetyGateError(f"{field} must be non-empty text")
    return value.strip()


@dataclass(frozen=True, slots=True)
class RequiredPreTradeWorkstream:
    workstream: str
    required_status: str


@dataclass(frozen=True, slots=True)
class PreTradeSafetyGatePolicy:
    gate_name: str
    required_workstreams: tuple[RequiredPreTradeWorkstream, ...]
    next_phase: str
    next_phase_state_after_pass: str
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "PreTradeSafetyGatePolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise PreTradeSafetyGateError(
                f"invalid P16-H policy JSON: {exc}"
            ) from exc
        raw = _mapping(raw_value, field="root")
        if (
            raw.get("schema_version") != "1.0"
            or raw.get("task_id") != "FIN-P16-WH-001"
            or raw.get("mode") != "DETERMINISTIC_PRETRADE_SAFETY_GATE"
            or raw.get("gate_name") != "G8_PRETRADE_SAFE"
        ):
            raise PreTradeSafetyGateError("unsupported P16-H policy")

        required_raw = raw.get("required_workstreams")
        if not isinstance(required_raw, list):
            raise PreTradeSafetyGateError("required_workstreams must be a list")
        required: list[RequiredPreTradeWorkstream] = []
        for index, item in enumerate(cast(list[object], required_raw)):
            record = _mapping(item, field=f"required_workstreams[{index}]")
            required.append(
                RequiredPreTradeWorkstream(
                    workstream=_text(record.get("workstream"), field="workstream"),
                    required_status=_text(
                        record.get("required_status"),
                        field="required_status",
                    ),
                )
            )

        expected = (
            ("P16-A", "PRETRADE_A_ELIGIBLE"),
            ("P16-B", "PRETRADE_B_ELIGIBLE"),
            ("P16-C", "PRETRADE_C_ELIGIBLE"),
            ("P16-D", "PRETRADE_D_ELIGIBLE"),
            ("P16-E", "PRETRADE_E_ELIGIBLE"),
            ("P16-F", "PRETRADE_F_ELIGIBLE"),
            ("P16-G", "PRETRADE_G_ELIGIBLE"),
        )
        actual = tuple(
            (item.workstream, item.required_status) for item in required
        )
        if actual != expected:
            raise PreTradeSafetyGateError(
                "P16-H required workstream/status coverage mismatch"
            )

        required_true = (
            "exact_lineage_required",
        )
        if any(raw.get(field) is not True for field in required_true):
            raise PreTradeSafetyGateError("P16-H lineage must remain required")

        required_false = (
            "duplicate_decision_ids_allowed",
            "waiting_for_approval_allowed",
            "veto_allowed",
            "upstream_execution_authority_allowed",
            "upstream_g8_authority_allowed",
            "execution_authority",
            "order_routing_authority",
            "p17_started",
        )
        if any(raw.get(field) is not False for field in required_false):
            raise PreTradeSafetyGateError("P16-H authority/safety policy drift")

        if raw.get("next_phase") != "P17":
            raise PreTradeSafetyGateError("P16-H next phase must be P17")
        if (
            raw.get("next_phase_state_after_pass")
            != "NOT_STARTED_OWNER_PHASE_AUTHORIZATION_REQUIRED"
        ):
            raise PreTradeSafetyGateError(
                "P17 must require Owner phase authorization after G8"
            )
        if (
            raw.get("live_trading") != "DISABLED"
            or raw.get("auto_trading") != "DISABLED"
        ):
            raise PreTradeSafetyGateError("P16-H cannot enable trading")

        return cls(
            gate_name="G8_PRETRADE_SAFE",
            required_workstreams=tuple(required),
            next_phase="P17",
            next_phase_state_after_pass=(
                "NOT_STARTED_OWNER_PHASE_AUTHORIZATION_REQUIRED"
            ),
            live_trading="DISABLED",
            auto_trading="DISABLED",
        )


@dataclass(frozen=True, slots=True)
class PreTradeStageCertificate:
    workstream: str
    decision_id: str
    status: str
    upstream_decision_id: str | None
    execution_authority: bool = False
    g8_authority: bool = False

    def __post_init__(self) -> None:
        if not self.workstream.strip():
            raise PreTradeSafetyGateError("workstream must be non-empty")
        if not self.decision_id.strip():
            raise PreTradeSafetyGateError("decision_id must be non-empty")
        if not self.status.strip():
            raise PreTradeSafetyGateError("status must be non-empty")
        if (
            self.upstream_decision_id is not None
            and not self.upstream_decision_id.strip()
        ):
            raise PreTradeSafetyGateError(
                "upstream_decision_id must be non-empty when present"
            )

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "workstream": self.workstream,
            "decision_id": self.decision_id,
            "status": self.status,
            "upstream_decision_id": self.upstream_decision_id,
            "execution_authority": self.execution_authority,
            "g8_authority": self.g8_authority,
        }

    @property
    def certificate_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class PreTradeSafetyGate:
    gate_name: str
    state: str
    workstream_coverage: tuple[str, ...]
    certificate_ids: tuple[str, ...]
    next_phase: str
    next_phase_state: str
    p17_started: bool = False
    execution_authority: bool = False
    order_routing_authority: bool = False
    live_trading: str = "DISABLED"
    auto_trading: str = "DISABLED"

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "gate_name": self.gate_name,
            "state": self.state,
            "workstream_coverage": list(self.workstream_coverage),
            "certificate_ids": list(self.certificate_ids),
            "next_phase": self.next_phase,
            "next_phase_state": self.next_phase_state,
            "p17_started": self.p17_started,
            "execution_authority": self.execution_authority,
            "order_routing_authority": self.order_routing_authority,
            "live_trading": self.live_trading,
            "auto_trading": self.auto_trading,
        }

    @property
    def gate_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


def certify_g8_pretrade_safe(
    *,
    policy: PreTradeSafetyGatePolicy,
    certificates: Sequence[PreTradeStageCertificate],
) -> PreTradeSafetyGate:
    records = tuple(certificates)
    if len(records) != len(policy.required_workstreams):
        raise PreTradeSafetyGateError(
            "G8 requires exactly one certificate per P16-A..P16-G workstream"
        )

    by_workstream: dict[str, PreTradeStageCertificate] = {}
    decision_ids: set[str] = set()
    for certificate in records:
        if certificate.workstream in by_workstream:
            raise PreTradeSafetyGateError("duplicate P16 workstream certificate")
        if certificate.decision_id in decision_ids:
            raise PreTradeSafetyGateError("duplicate P16 decision ID")
        if certificate.execution_authority:
            raise PreTradeSafetyGateError(
                "upstream execution authority is forbidden"
            )
        if certificate.g8_authority:
            raise PreTradeSafetyGateError(
                "upstream G8 authority is forbidden"
            )
        by_workstream[certificate.workstream] = certificate
        decision_ids.add(certificate.decision_id)

    expected_names = tuple(
        required.workstream for required in policy.required_workstreams
    )
    if set(by_workstream) != set(expected_names):
        raise PreTradeSafetyGateError(
            "G8 workstream coverage must be exactly P16-A..P16-G"
        )

    ordered: list[PreTradeStageCertificate] = []
    previous: PreTradeStageCertificate | None = None
    for required in policy.required_workstreams:
        certificate = by_workstream[required.workstream]
        if certificate.status != required.required_status:
            raise PreTradeSafetyGateError(
                f"{required.workstream} status is not canonical eligible"
            )
        if previous is None:
            if certificate.upstream_decision_id is not None:
                raise PreTradeSafetyGateError(
                    "P16-A must not claim an upstream P16 decision"
                )
        elif certificate.upstream_decision_id != previous.decision_id:
            raise PreTradeSafetyGateError(
                f"{required.workstream} upstream decision lineage mismatch"
            )
        ordered.append(certificate)
        previous = certificate

    return PreTradeSafetyGate(
        gate_name=policy.gate_name,
        state="PASS",
        workstream_coverage=expected_names,
        certificate_ids=tuple(item.certificate_id for item in ordered),
        next_phase=policy.next_phase,
        next_phase_state=policy.next_phase_state_after_pass,
        p17_started=False,
        execution_authority=False,
        order_routing_authority=False,
        live_trading=policy.live_trading,
        auto_trading=policy.auto_trading,
    )
