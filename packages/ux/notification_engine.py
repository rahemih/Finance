from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import cast


class NotificationEngineError(ValueError):
    """P23-F notification-engine invariant failure."""


EXPECTED_SEVERITIES = ("INFORMATIONAL", "IMPORTANT", "CRITICAL", "SUPPRESSED")
EXPECTED_CHANNELS = ("IN_APP",)
EXPECTED_REQUIRED_FIELDS = (
    "source_event_id",
    "severity",
    "title_fa",
    "body_fa",
    "created_at",
    "provenance_ref",
)


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _object(value: object, *, field: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise NotificationEngineError(f"{field} must be an object")
    raw = cast(dict[object, object], value)
    result: dict[str, object] = {}
    for key, item in raw.items():
        if not isinstance(key, str):
            raise NotificationEngineError(f"{field} keys must be strings")
        result[key] = item
    return result


def _list(value: object, *, field: str) -> list[object]:
    if not isinstance(value, list):
        raise NotificationEngineError(f"{field} must be a list")
    return cast(list[object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise NotificationEngineError(f"{field} must be non-empty text")
    return value


@dataclass(frozen=True, slots=True)
class NotificationRoute:
    action: str
    channel: str | None
    escalation_target: str | None
    notification_id: str
    dedup_key: str


@dataclass(frozen=True, slots=True)
class NotificationPolicy:
    severities: tuple[str, ...]
    channels: tuple[str, ...]
    defer_severities: tuple[str, ...]
    bypass_severities: tuple[str, ...]
    never_deliver_severities: tuple[str, ...]
    required_fields: tuple[str, ...]
    critical_target: str
    dedup_window_seconds: int
    safety: dict[str, object]

    @classmethod
    def from_paths(cls, policy_path: Path, alerting_policy_path: Path) -> "NotificationPolicy":
        try:
            raw_value: object = json.loads(policy_path.read_text(encoding="utf-8"))
            alert_value: object = json.loads(alerting_policy_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise NotificationEngineError(f"invalid notification policy JSON: {exc}") from exc

        raw = _object(raw_value, field="root")
        alert = _object(alert_value, field="alerting_policy")
        expected_static: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P23F_NOTIFICATION_ENGINE",
            "task_id": "FIN-P23-WF-001",
            "phase": "P23",
            "workstream": "P23-F",
            "authority": "NOTIFICATION_ROUTING_ONLY",
        }
        for key, expected in expected_static.items():
            if raw.get(key) != expected:
                raise NotificationEngineError(f"P23-F policy mismatch: {key}")

        upstream = _object(raw.get("upstream"), field="upstream")
        if upstream != {
            "alerting_policy": "config/news-sentiment/alerting-narrative-policy.json",
            "team_collaboration": "config/ux/team-collaboration.json",
        }:
            raise NotificationEngineError("upstream binding drift")

        severities = tuple(
            _text(item, field="severities[]")
            for item in _list(raw.get("severities"), field="severities")
        )
        if severities != EXPECTED_SEVERITIES:
            raise NotificationEngineError("notification severity order/coverage drift")
        upstream_severities = tuple(
            _text(item, field="alerting.severities[]")
            for item in _list(alert.get("severities"), field="alerting.severities")
        )
        if upstream_severities != severities:
            raise NotificationEngineError("P11-G severity binding drift")
        if alert.get("channel_delivery_enabled") is not False:
            raise NotificationEngineError("P11-G channel-delivery boundary drift")

        channels = tuple(
            _text(item, field="channels[]")
            for item in _list(raw.get("channels"), field="channels")
        )
        if channels != EXPECTED_CHANNELS:
            raise NotificationEngineError("channel contract drift")

        quiet = _object(raw.get("quiet_hours"), field="quiet_hours")
        if quiet.get("timezone_required") is not True:
            raise NotificationEngineError("quiet-hours timezone must be explicit")
        defer = tuple(
            _text(item, field="quiet_hours.defer_severities[]")
            for item in _list(quiet.get("defer_severities"), field="quiet_hours.defer_severities")
        )
        bypass = tuple(
            _text(item, field="quiet_hours.bypass_severities[]")
            for item in _list(quiet.get("bypass_severities"), field="quiet_hours.bypass_severities")
        )
        never = tuple(
            _text(item, field="quiet_hours.never_deliver_severities[]")
            for item in _list(
                quiet.get("never_deliver_severities"),
                field="quiet_hours.never_deliver_severities",
            )
        )
        if defer != ("INFORMATIONAL", "IMPORTANT"):
            raise NotificationEngineError("quiet-hours defer contract drift")
        if bypass != ("CRITICAL",):
            raise NotificationEngineError("quiet-hours bypass contract drift")
        if never != ("SUPPRESSED",):
            raise NotificationEngineError("suppressed delivery contract drift")

        escalation = _object(raw.get("escalation"), field="escalation")
        critical_target = _text(escalation.get("critical_target"), field="escalation.critical_target")
        if critical_target != "ON_CALL_QUEUE":
            raise NotificationEngineError("critical escalation target drift")
        for flag in (
            "grants_owner_authorization",
            "grants_risk_approval",
            "grants_execution_approval",
            "grants_p24_production_approval",
        ):
            if escalation.get(flag) is not False:
                raise NotificationEngineError(f"forbidden escalation authority: {flag}")

        identity = _object(raw.get("identity"), field="identity")
        if identity.get("deterministic_notification_id") is not True:
            raise NotificationEngineError("deterministic notification identity required")
        if identity.get("deterministic_dedup_key") is not True:
            raise NotificationEngineError("deterministic dedup identity required")
        window = identity.get("dedup_window_seconds")
        if not isinstance(window, int) or isinstance(window, bool) or window != 300:
            raise NotificationEngineError("dedup window contract drift")

        required = tuple(
            _text(item, field="required_fields[]")
            for item in _list(raw.get("required_fields"), field="required_fields")
        )
        if required != EXPECTED_REQUIRED_FIELDS:
            raise NotificationEngineError("required field order/coverage drift")

        delivery = _object(raw.get("delivery"), field="delivery")
        if delivery != {
            "external_delivery_enabled": False,
            "credential_access": False,
            "provider": "NOT_SELECTED",
        }:
            raise NotificationEngineError("external delivery boundary drift")

        safety = _object(raw.get("safety"), field="safety")
        expected_safety: dict[str, object] = {
            "permission_mutation": False,
            "external_order_authority": False,
            "runtime_state_mutation": False,
            "remediation_authority": False,
            "production_activation": False,
            "p24_state": "NOT_STARTED",
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        if safety != expected_safety:
            raise NotificationEngineError("P23-F safety boundary drift")

        return cls(
            severities=severities,
            channels=channels,
            defer_severities=defer,
            bypass_severities=bypass,
            never_deliver_severities=never,
            required_fields=required,
            critical_target=critical_target,
            dedup_window_seconds=window,
            safety=safety,
        )

    @property
    def policy_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()

    def payload(self) -> dict[str, object]:
        return {
            "severities": list(self.severities),
            "channels": list(self.channels),
            "defer_severities": list(self.defer_severities),
            "bypass_severities": list(self.bypass_severities),
            "never_deliver_severities": list(self.never_deliver_severities),
            "required_fields": list(self.required_fields),
            "critical_target": self.critical_target,
            "dedup_window_seconds": self.dedup_window_seconds,
            "safety": self.safety,
        }

    def route(self, event: dict[str, str], *, in_quiet_hours: bool) -> NotificationRoute:
        if tuple(event) != self.required_fields:
            raise NotificationEngineError("notification event fields/order must match canonical contract")
        for field in self.required_fields:
            _text(event.get(field), field=f"event.{field}")
        severity = event["severity"]
        if severity not in self.severities:
            raise NotificationEngineError("unknown notification severity")

        identity_payload = {
            "source_event_id": event["source_event_id"],
            "severity": severity,
            "created_at": event["created_at"],
            "provenance_ref": event["provenance_ref"],
        }
        notification_id = hashlib.sha256(_canonical_bytes(identity_payload)).hexdigest()
        dedup_payload = {
            "source_event_id": event["source_event_id"],
            "severity": severity,
            "window_seconds": self.dedup_window_seconds,
        }
        dedup_key = hashlib.sha256(_canonical_bytes(dedup_payload)).hexdigest()

        if severity in self.never_deliver_severities:
            return NotificationRoute("SUPPRESS", None, None, notification_id, dedup_key)
        if in_quiet_hours and severity in self.defer_severities:
            return NotificationRoute("DEFER_IN_APP", "IN_APP", None, notification_id, dedup_key)
        if severity == "CRITICAL":
            return NotificationRoute(
                "DELIVER_IN_APP",
                "IN_APP",
                self.critical_target,
                notification_id,
                dedup_key,
            )
        return NotificationRoute("DELIVER_IN_APP", "IN_APP", None, notification_id, dedup_key)
