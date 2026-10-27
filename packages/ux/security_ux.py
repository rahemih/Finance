from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import cast


class SecurityUxError(ValueError):
    """P23-H dangerous-action/security UX invariant failure."""


EXPECTED_ACTION_TYPES = (
    "CREDENTIAL_CHANGE_REQUEST",
    "PERMISSION_CHANGE_REQUEST",
    "NETWORK_EXPOSURE_CHANGE_REQUEST",
    "EXECUTION_AUTHORITY_CHANGE_REQUEST",
    "LIVE_TRADING_ENABLE_REQUEST",
    "AUTO_TRADING_ENABLE_REQUEST",
    "P24_PRODUCTION_PROMOTION_REQUEST",
    "CONSEQUENTIAL_SETTINGS_CHANGE_REQUEST",
)
EXPECTED_FIELDS = (
    "action_id",
    "action_type",
    "target_resource",
    "environment",
    "requested_change_digest",
    "expires_at",
    "provenance_ref",
)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _object(value: object, *, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise SecurityUxError(f"{field} must be an object")
    raw = cast(dict[object, object], value)
    result: dict[str, object] = {}
    for key, item in raw.items():
        if not isinstance(key, str):
            raise SecurityUxError(f"{field} keys must be strings")
        result[key] = item
    return result


def _list(value: object, *, field: str) -> list[object]:
    if not isinstance(value, list):
        raise SecurityUxError(f"{field} must be a list")
    return cast(list[object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SecurityUxError(f"{field} must be non-empty text")
    return value


@dataclass(frozen=True, slots=True)
class SecurityUxPolicy:
    action_types: tuple[str, ...]
    required_fields: tuple[str, ...]
    confirmation: dict[str, object]
    approval_boundaries: dict[str, object]
    safety: dict[str, object]

    @classmethod
    def from_paths(cls, policy_path: Path, p03_validation_path: Path) -> "SecurityUxPolicy":
        try:
            raw_value: object = json.loads(policy_path.read_text(encoding="utf-8"))
            p03_value: object = json.loads(p03_validation_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise SecurityUxError(f"invalid P23-H JSON: {exc}") from exc

        raw = _object(raw_value, field="root")
        p03 = _object(p03_value, field="p03")

        expected_static: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P23H_DANGEROUS_ACTION_SECURITY_UX",
            "task_id": "FIN-P23-WH-001",
            "phase": "P23",
            "workstream": "P23-H",
            "claim_scope": "SECURITY_UX_VALIDATION_ONLY",
        }
        for key, expected in expected_static.items():
            if raw.get(key) != expected:
                raise SecurityUxError(f"P23-H policy mismatch: {key}")

        upstream = _object(raw.get("upstream"), field="upstream")
        if upstream != {
            "p03_security_validation": "docs/05-security/p03-security-validation.json",
            "frontend_baseline": "docs/03-research/FRONTEND-EXCELLENCE-BASELINE.md",
        }:
            raise SecurityUxError("upstream binding drift")

        if p03.get("gate") != "G3_SECURITY_BASELINE" or p03.get("verdict") != "PASS":
            raise SecurityUxError("G3 security baseline not PASS")
        if p03.get("live_trading") != "DISABLED" or p03.get("auto_trading") != "DISABLED":
            raise SecurityUxError("P03 Live/Auto boundary drift")

        criteria = _list(p03.get("criteria"), field="p03.criteria")
        criterion_status: dict[str, str] = {}
        for index, value in enumerate(criteria):
            item = _object(value, field=f"p03.criteria[{index}]")
            cid = _text(item.get("id"), field=f"p03.criteria[{index}].id")
            status = _text(item.get("status"), field=f"p03.criteria[{index}].status")
            criterion_status[cid] = status
        for required_id in ("C06", "C15", "C20"):
            if criterion_status.get(required_id) != "PASS":
                raise SecurityUxError(f"required P03 criterion not PASS: {required_id}")

        action_types = tuple(
            _text(value, field="dangerous_action_types[]")
            for value in _list(raw.get("dangerous_action_types"), field="dangerous_action_types")
        )
        if action_types != EXPECTED_ACTION_TYPES:
            raise SecurityUxError("dangerous action taxonomy drift")

        confirmation = _object(raw.get("confirmation"), field="confirmation")
        required_fields = tuple(
            _text(value, field="confirmation.required_fields[]")
            for value in _list(confirmation.get("required_fields"), field="confirmation.required_fields")
        )
        if required_fields != EXPECTED_FIELDS:
            raise SecurityUxError("confirmation field order/coverage drift")
        for flag in (
            "exact_action_resource_environment_digest_expiry_binding",
            "explicit_confirmation_required",
            "typed_target_confirmation_required",
            "audit_friendly_text_required",
            "server_side_session_validation_required",
            "server_side_authorization_required",
        ):
            if confirmation.get(flag) is not True:
                raise SecurityUxError(f"confirmation requirement weakened: {flag}")
        if confirmation.get("client_side_authorization_forbidden") is not True:
            raise SecurityUxError("client-side authorization must be forbidden")
        if confirmation.get("expired_or_revoked_session_behavior") != "DENY":
            raise SecurityUxError("expired/revoked session must deny")

        permission_ux = _object(raw.get("permission_ux"), field="permission_ux")
        if permission_ux != {
            "permission_aware_disabled_state_required": True,
            "denied_action_hidden_as_success_forbidden": True,
            "network_location_as_authorization_forbidden": True,
        }:
            raise SecurityUxError("permission UX boundary drift")

        storage = _object(raw.get("security_storage"), field="security_storage")
        if storage != {
            "secrets_in_browser_storage": False,
            "raw_secret_rendering": False,
            "security_sensitive_state_client_only": False,
        }:
            raise SecurityUxError("security storage boundary drift")

        approvals = _object(raw.get("approval_boundaries"), field="approval_boundaries")
        expected_approvals: dict[str, object] = {
            "grants_owner_authorization": False,
            "grants_risk_approval": False,
            "grants_security_approval": False,
            "grants_execution_approval": False,
            "grants_p24_production_approval": False,
            "a5_risk_veto_bypass": False,
            "a8_security_veto_bypass": False,
            "emergency_access_can_enable_live": False,
        }
        if approvals != expected_approvals:
            raise SecurityUxError("approval authority boundary drift")

        safety = _object(raw.get("safety"), field="safety")
        expected_safety: dict[str, object] = {
            "credential_access": False,
            "permission_mutation": False,
            "network_mutation": False,
            "execution_authority_mutation": False,
            "external_order_authority": False,
            "runtime_state_mutation": False,
            "remediation_authority": False,
            "production_activation": False,
            "p24_state": "NOT_STARTED",
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        if safety != expected_safety:
            raise SecurityUxError("P23-H safety boundary drift")

        return cls(
            action_types=action_types,
            required_fields=required_fields,
            confirmation=confirmation,
            approval_boundaries=approvals,
            safety=safety,
        )

    @property
    def policy_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()

    def payload(self) -> dict[str, object]:
        return {
            "action_types": list(self.action_types),
            "required_fields": list(self.required_fields),
            "confirmation": self.confirmation,
            "approval_boundaries": self.approval_boundaries,
            "safety": self.safety,
        }

    def confirmation_id(self, request: dict[str, str]) -> str:
        if tuple(request) != self.required_fields:
            raise SecurityUxError("confirmation fields/order must match canonical contract")
        for field in self.required_fields:
            _text(request.get(field), field=f"request.{field}")
        if request["action_type"] not in self.action_types:
            raise SecurityUxError("unknown dangerous action type")
        digest = request["requested_change_digest"]
        if not digest.startswith("sha256:") or len(digest) != 71:
            raise SecurityUxError("requested change digest must be sha256")
        return hashlib.sha256(_canonical_bytes(request)).hexdigest()
