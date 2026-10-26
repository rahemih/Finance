from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
from typing import Mapping, cast


class ObservabilityError(ValueError):
    """P22-A deterministic observability invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ObservabilityError(f"{field} must be non-empty text")
    return value.strip()


def _hex_id(value: object, *, field: str, length: int) -> str:
    text = _text(value, field=field).lower()
    if len(text) != length or any(ch not in "0123456789abcdef" for ch in text):
        raise ObservabilityError(f"{field} must be {length} lowercase hex characters")
    return text


def _epoch_ns(value: object, *, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ObservabilityError(f"{field} must be a non-negative integer epoch-ns value")
    return value


def _decimal_text(value: object, *, field: str) -> str:
    if isinstance(value, bool):
        raise ObservabilityError(f"{field} must be finite numeric data")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ObservabilityError(f"{field} must be finite numeric data") from exc
    if not number.is_finite():
        raise ObservabilityError(f"{field} must be finite numeric data")
    normalized = format(number.normalize(), "f")
    return "0" if normalized in {"-0", ""} else normalized


@dataclass(frozen=True, slots=True)
class ObservabilityPolicy:
    metric_prefix: str
    allowed_metric_kinds: tuple[str, ...]
    allowed_log_levels: tuple[str, ...]
    allowed_trace_status: tuple[str, ...]
    allowed_attribute_keys: tuple[str, ...]
    max_attribute_count: int
    max_attribute_key_length: int
    max_attribute_value_length: int
    max_log_message_length: int
    correlation_id_hex_length: int
    trace_id_hex_length: int
    span_id_hex_length: int
    forbidden_key_fragments: tuple[str, ...]
    forbidden_message_fragments: tuple[str, ...]

    @classmethod
    def from_path(cls, path: Path) -> "ObservabilityPolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ObservabilityError(f"invalid P22-A policy JSON: {exc}") from exc
        if not isinstance(raw_value, Mapping):
            raise ObservabilityError("P22-A policy root must be an object")
        raw = cast(Mapping[str, object], raw_value)
        expected: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P22A_OBSERVABILITY_POLICY",
            "task_id": "FIN-P22-WA-001",
            "mode": "DETERMINISTIC_REFERENCE_OBSERVABILITY",
            "metric_prefix": "nexus_quant.",
            "allowed_metric_kinds": ["COUNTER", "GAUGE", "HISTOGRAM"],
            "allowed_log_levels": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            "allowed_trace_status": ["OK", "ERROR"],
            "allowed_attribute_keys": ["component", "phase", "workstream", "operation", "market", "instrument_class", "outcome", "reason_code"],
            "max_attribute_count": 8,
            "max_attribute_key_length": 64,
            "max_attribute_value_length": 128,
            "max_log_message_length": 512,
            "correlation_id_hex_length": 32,
            "trace_id_hex_length": 32,
            "span_id_hex_length": 16,
            "forbidden_key_fragments": ["authorization", "api_key", "apikey", "password", "secret", "token", "cookie", "credential"],
            "forbidden_message_fragments": ["bearer ", "sk-", "password=", "api_key=", "apikey=", "authorization:"],
            "network_mode": "DISABLED",
            "credential_mode": "NONE",
            "vendor_export": False,
            "automatic_system_state_mutation": False,
            "automatic_risk_policy_relaxation": False,
            "live_execution_authority": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        for key, expected_value in expected.items():
            if raw.get(key) != expected_value:
                raise ObservabilityError(f"P22-A policy mismatch: {key}")
        return cls(
            metric_prefix="nexus_quant.",
            allowed_metric_kinds=("COUNTER", "GAUGE", "HISTOGRAM"),
            allowed_log_levels=("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
            allowed_trace_status=("OK", "ERROR"),
            allowed_attribute_keys=("component", "phase", "workstream", "operation", "market", "instrument_class", "outcome", "reason_code"),
            max_attribute_count=8,
            max_attribute_key_length=64,
            max_attribute_value_length=128,
            max_log_message_length=512,
            correlation_id_hex_length=32,
            trace_id_hex_length=32,
            span_id_hex_length=16,
            forbidden_key_fragments=("authorization", "api_key", "apikey", "password", "secret", "token", "cookie", "credential"),
            forbidden_message_fragments=("bearer ", "sk-", "password=", "api_key=", "apikey=", "authorization:"),
        )

    @property
    def policy_id(self) -> str:
        return hashlib.sha256(_canonical_bytes({
            "metric_prefix": self.metric_prefix,
            "allowed_metric_kinds": self.allowed_metric_kinds,
            "allowed_log_levels": self.allowed_log_levels,
            "allowed_trace_status": self.allowed_trace_status,
            "allowed_attribute_keys": self.allowed_attribute_keys,
            "max_attribute_count": self.max_attribute_count,
            "max_attribute_key_length": self.max_attribute_key_length,
            "max_attribute_value_length": self.max_attribute_value_length,
            "max_log_message_length": self.max_log_message_length,
            "correlation_id_hex_length": self.correlation_id_hex_length,
            "trace_id_hex_length": self.trace_id_hex_length,
            "span_id_hex_length": self.span_id_hex_length,
            "forbidden_key_fragments": self.forbidden_key_fragments,
            "forbidden_message_fragments": self.forbidden_message_fragments,
            "network_mode": "DISABLED",
            "credential_mode": "NONE",
            "vendor_export": False,
            "automatic_system_state_mutation": False,
            "automatic_risk_policy_relaxation": False,
            "live_execution_authority": False,
        })).hexdigest()


def _attributes(policy: ObservabilityPolicy, attributes: Mapping[str, object] | None) -> tuple[tuple[str, str], ...]:
    if attributes is None:
        return ()
    if len(attributes) > policy.max_attribute_count:
        raise ObservabilityError("attribute count exceeds bounded-cardinality policy")
    pairs: list[tuple[str, str]] = []
    for key, raw_value in attributes.items():
        if not isinstance(key, str):
            raise ObservabilityError("attribute keys must be text")
        normalized_key = key.strip()
        if not normalized_key or len(normalized_key) > policy.max_attribute_key_length:
            raise ObservabilityError("invalid attribute key length")
        lower_key = normalized_key.lower()
        if any(fragment in lower_key for fragment in policy.forbidden_key_fragments):
            raise ObservabilityError("secret-bearing attribute key is forbidden")
        if normalized_key not in policy.allowed_attribute_keys:
            raise ObservabilityError(f"attribute key not allowed by bounded-cardinality policy: {normalized_key}")
        value = _text(raw_value, field=f"attribute.{normalized_key}")
        if len(value) > policy.max_attribute_value_length:
            raise ObservabilityError(f"attribute value too long: {normalized_key}")
        pairs.append((normalized_key, value))
    pairs.sort()
    return tuple(pairs)


def _record_id(kind: str, payload: Mapping[str, object]) -> str:
    return hashlib.sha256(_canonical_bytes({"kind": kind, "payload": payload})).hexdigest()


@dataclass(frozen=True, slots=True)
class MetricRecord:
    record_id: str
    policy_id: str
    name: str
    metric_kind: str
    value: str
    unit: str
    observed_at_ns: int
    correlation_id: str
    attributes: tuple[tuple[str, str], ...]

    def payload(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "metric_kind": self.metric_kind,
            "value": self.value,
            "unit": self.unit,
            "observed_at_ns": self.observed_at_ns,
            "correlation_id": self.correlation_id,
            "attributes": dict(self.attributes),
        }


@dataclass(frozen=True, slots=True)
class LogRecord:
    record_id: str
    policy_id: str
    level: str
    message: str
    observed_at_ns: int
    correlation_id: str
    trace_id: str | None
    span_id: str | None
    attributes: tuple[tuple[str, str], ...]

    def payload(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "level": self.level,
            "message": self.message,
            "observed_at_ns": self.observed_at_ns,
            "correlation_id": self.correlation_id,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "attributes": dict(self.attributes),
        }


@dataclass(frozen=True, slots=True)
class TraceRecord:
    record_id: str
    policy_id: str
    trace_id: str
    span_id: str
    parent_span_id: str | None
    operation: str
    status: str
    started_at_ns: int
    ended_at_ns: int
    correlation_id: str
    attributes: tuple[tuple[str, str], ...]

    def payload(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "operation": self.operation,
            "status": self.status,
            "started_at_ns": self.started_at_ns,
            "ended_at_ns": self.ended_at_ns,
            "correlation_id": self.correlation_id,
            "attributes": dict(self.attributes),
        }


def build_metric(
    policy: ObservabilityPolicy,
    *,
    name: str,
    metric_kind: str,
    value: object,
    unit: str,
    observed_at_ns: int,
    correlation_id: str,
    attributes: Mapping[str, object] | None = None,
) -> MetricRecord:
    metric_name = _text(name, field="name")
    if not metric_name.startswith(policy.metric_prefix) or len(metric_name) > 128:
        raise ObservabilityError("metric name violates namespace policy")
    kind = _text(metric_kind, field="metric_kind").upper()
    if kind not in policy.allowed_metric_kinds:
        raise ObservabilityError("unsupported metric kind")
    unit_value = _text(unit, field="unit")
    if len(unit_value) > 32:
        raise ObservabilityError("unit is too long")
    value_text = _decimal_text(value, field="value")
    timestamp = _epoch_ns(observed_at_ns, field="observed_at_ns")
    corr = _hex_id(correlation_id, field="correlation_id", length=policy.correlation_id_hex_length)
    attrs = _attributes(policy, attributes)
    payload: dict[str, object] = {
        "policy_id": policy.policy_id,
        "name": metric_name,
        "metric_kind": kind,
        "value": value_text,
        "unit": unit_value,
        "observed_at_ns": timestamp,
        "correlation_id": corr,
        "attributes": dict(attrs),
    }
    return MetricRecord(_record_id("METRIC", payload), policy.policy_id, metric_name, kind, value_text, unit_value, timestamp, corr, attrs)


def build_log(
    policy: ObservabilityPolicy,
    *,
    level: str,
    message: str,
    observed_at_ns: int,
    correlation_id: str,
    trace_id: str | None = None,
    span_id: str | None = None,
    attributes: Mapping[str, object] | None = None,
) -> LogRecord:
    normalized_level = _text(level, field="level").upper()
    if normalized_level not in policy.allowed_log_levels:
        raise ObservabilityError("unsupported log level")
    normalized_message = _text(message, field="message")
    if len(normalized_message) > policy.max_log_message_length:
        raise ObservabilityError("log message too long")
    lower_message = normalized_message.lower()
    if any(fragment in lower_message for fragment in policy.forbidden_message_fragments):
        raise ObservabilityError("potential secret material in log message")
    timestamp = _epoch_ns(observed_at_ns, field="observed_at_ns")
    corr = _hex_id(correlation_id, field="correlation_id", length=policy.correlation_id_hex_length)
    normalized_trace = None if trace_id is None else _hex_id(trace_id, field="trace_id", length=policy.trace_id_hex_length)
    normalized_span = None if span_id is None else _hex_id(span_id, field="span_id", length=policy.span_id_hex_length)
    if (normalized_trace is None) != (normalized_span is None):
        raise ObservabilityError("trace_id and span_id must be provided together")
    attrs = _attributes(policy, attributes)
    payload: dict[str, object] = {
        "policy_id": policy.policy_id,
        "level": normalized_level,
        "message": normalized_message,
        "observed_at_ns": timestamp,
        "correlation_id": corr,
        "trace_id": normalized_trace,
        "span_id": normalized_span,
        "attributes": dict(attrs),
    }
    return LogRecord(_record_id("LOG", payload), policy.policy_id, normalized_level, normalized_message, timestamp, corr, normalized_trace, normalized_span, attrs)


def build_trace(
    policy: ObservabilityPolicy,
    *,
    trace_id: str,
    span_id: str,
    parent_span_id: str | None,
    operation: str,
    status: str,
    started_at_ns: int,
    ended_at_ns: int,
    correlation_id: str,
    attributes: Mapping[str, object] | None = None,
) -> TraceRecord:
    normalized_trace = _hex_id(trace_id, field="trace_id", length=policy.trace_id_hex_length)
    normalized_span = _hex_id(span_id, field="span_id", length=policy.span_id_hex_length)
    parent = None if parent_span_id is None else _hex_id(parent_span_id, field="parent_span_id", length=policy.span_id_hex_length)
    if parent == normalized_span:
        raise ObservabilityError("span cannot parent itself")
    operation_value = _text(operation, field="operation")
    if len(operation_value) > 128:
        raise ObservabilityError("operation is too long")
    status_value = _text(status, field="status").upper()
    if status_value not in policy.allowed_trace_status:
        raise ObservabilityError("unsupported trace status")
    started = _epoch_ns(started_at_ns, field="started_at_ns")
    ended = _epoch_ns(ended_at_ns, field="ended_at_ns")
    if ended < started:
        raise ObservabilityError("trace end precedes trace start")
    corr = _hex_id(correlation_id, field="correlation_id", length=policy.correlation_id_hex_length)
    attrs = _attributes(policy, attributes)
    payload: dict[str, object] = {
        "policy_id": policy.policy_id,
        "trace_id": normalized_trace,
        "span_id": normalized_span,
        "parent_span_id": parent,
        "operation": operation_value,
        "status": status_value,
        "started_at_ns": started,
        "ended_at_ns": ended,
        "correlation_id": corr,
        "attributes": dict(attrs),
    }
    return TraceRecord(_record_id("TRACE", payload), policy.policy_id, normalized_trace, normalized_span, parent, operation_value, status_value, started, ended, corr, attrs)
