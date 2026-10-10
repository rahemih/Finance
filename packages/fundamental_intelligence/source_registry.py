from __future__ import annotations

from dataclasses import dataclass, fields, replace
import hashlib
import json
from pathlib import Path
from typing import Mapping, cast
from urllib.parse import urlparse


class OfficialSourceRegistryError(ValueError):
    """Raised when P10-A official-source registry invariants fail closed."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise OfficialSourceRegistryError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _object_list(value: object, *, field: str) -> list[object]:
    if not isinstance(value, list):
        raise OfficialSourceRegistryError(f"{field} must be a list")
    return cast(list[object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OfficialSourceRegistryError(f"{field} must be non-empty text")
    return value.strip()


def _boolean(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise OfficialSourceRegistryError(f"{field} must be boolean")
    return value


def _text_tuple(value: object, *, field: str) -> tuple[str, ...]:
    return tuple(_text(item, field=field) for item in _object_list(value, field=field))


def _https_url(value: object, *, field: str) -> str:
    text = _text(value, field=field)
    parsed = urlparse(text)
    if parsed.scheme != "https" or not parsed.hostname:
        raise OfficialSourceRegistryError(f"{field} must be an absolute HTTPS URL")
    if parsed.username or parsed.password:
        raise OfficialSourceRegistryError(f"{field} must not contain credentials")
    return text


def _host(value: str) -> str:
    host = urlparse(value).hostname
    if host is None:
        raise OfficialSourceRegistryError("URL must contain hostname")
    return host.lower()


def validate_secret_handle(value: object) -> str:
    text = _text(value, field="secret_handle")
    if not text.startswith("secret://") or len(text) <= len("secret://"):
        raise OfficialSourceRegistryError("credential references must use non-empty secret:// handles")
    lowered = text.lower()
    if any(marker in lowered for marker in ("api_key=", "apikey=", "token=", "password=")):
        raise OfficialSourceRegistryError("secret handle must not embed raw credential material")
    return text


@dataclass(frozen=True, slots=True)
class OfficialSourcePolicy:
    required_source_ids: tuple[str, ...]
    allowed_access_kinds: tuple[str, ...]
    allowed_auth_modes: tuple[str, ...]
    allowed_revision_modes: tuple[str, ...]
    official_first_required: bool
    https_required: bool
    secret_handle_prefix: str
    raw_secret_allowed: bool
    production_source_selection: str
    canonical_tests_network_required: bool
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "OfficialSourcePolicy":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        raw = _mapping(raw_value, field="policy root")
        if raw.get("schema_version") != "1.0":
            raise OfficialSourceRegistryError("unsupported policy schema_version")
        required = _text_tuple(raw.get("required_source_ids"), field="required_source_ids")
        access = _text_tuple(raw.get("allowed_access_kinds"), field="allowed_access_kinds")
        auth = _text_tuple(raw.get("allowed_auth_modes"), field="allowed_auth_modes")
        revision = _text_tuple(raw.get("allowed_revision_modes"), field="allowed_revision_modes")
        if len(set(required)) != len(required):
            raise OfficialSourceRegistryError("required_source_ids must be unique")
        if not required or not access or not auth or not revision:
            raise OfficialSourceRegistryError("policy enumerations must be non-empty")

        official_first = _boolean(raw.get("official_first_required"), field="official_first_required")
        https_required = _boolean(raw.get("https_required"), field="https_required")
        raw_secret = _boolean(raw.get("raw_secret_allowed"), field="raw_secret_allowed")
        network = _boolean(
            raw.get("canonical_tests_network_required"),
            field="canonical_tests_network_required",
        )
        prefix = _text(raw.get("secret_handle_prefix"), field="secret_handle_prefix")
        production = _text(raw.get("production_source_selection"), field="production_source_selection")
        live = _text(raw.get("live_trading"), field="live_trading")
        auto = _text(raw.get("auto_trading"), field="auto_trading")

        if not official_first:
            raise OfficialSourceRegistryError("P10-A requires official-first policy")
        if not https_required:
            raise OfficialSourceRegistryError("P10-A requires HTTPS")
        if prefix != "secret://":
            raise OfficialSourceRegistryError("P10-A secret handle prefix must be secret://")
        if raw_secret:
            raise OfficialSourceRegistryError("P10-A forbids raw secrets")
        if network:
            raise OfficialSourceRegistryError("P10-A canonical tests must remain offline")
        if production != "NOT_SELECTED":
            raise OfficialSourceRegistryError("P10-A cannot select a production source")
        if live != "DISABLED" or auto != "DISABLED":
            raise OfficialSourceRegistryError("P10-A cannot enable trading")

        return cls(
            required_source_ids=required,
            allowed_access_kinds=access,
            allowed_auth_modes=auth,
            allowed_revision_modes=revision,
            official_first_required=official_first,
            https_required=https_required,
            secret_handle_prefix=prefix,
            raw_secret_allowed=raw_secret,
            production_source_selection=production,
            canonical_tests_network_required=network,
            live_trading=live,
            auto_trading=auto,
        )


@dataclass(frozen=True, slots=True)
class OfficialSourceDescriptor:
    source_id: str
    institution: str
    access_kind: str
    auth_mode: str
    revision_mode: str
    base_url: str
    official_docs_url: str
    official_hosts: tuple[str, ...]
    capabilities: tuple[str, ...]
    transport_state: str
    license_state: str
    verified_on: str
    notes: str

    @classmethod
    def from_mapping(cls, raw: Mapping[str, object]) -> "OfficialSourceDescriptor":
        hosts = tuple(host.lower() for host in _text_tuple(raw.get("official_hosts"), field="official_hosts"))
        capabilities = _text_tuple(raw.get("capabilities"), field="capabilities")
        if len(set(hosts)) != len(hosts) or not hosts:
            raise OfficialSourceRegistryError("official_hosts must be non-empty and unique")
        if len(set(capabilities)) != len(capabilities) or not capabilities:
            raise OfficialSourceRegistryError("capabilities must be non-empty and unique")

        descriptor = cls(
            source_id=_text(raw.get("source_id"), field="source_id"),
            institution=_text(raw.get("institution"), field="institution"),
            access_kind=_text(raw.get("access_kind"), field="access_kind"),
            auth_mode=_text(raw.get("auth_mode"), field="auth_mode"),
            revision_mode=_text(raw.get("revision_mode"), field="revision_mode"),
            base_url=_https_url(raw.get("base_url"), field="base_url"),
            official_docs_url=_https_url(raw.get("official_docs_url"), field="official_docs_url"),
            official_hosts=hosts,
            capabilities=capabilities,
            transport_state=_text(raw.get("transport_state"), field="transport_state"),
            license_state=_text(raw.get("license_state"), field="license_state"),
            verified_on=_text(raw.get("verified_on"), field="verified_on"),
            notes=_text(raw.get("notes"), field="notes"),
        )
        for url_field, url in (
            ("base_url", descriptor.base_url),
            ("official_docs_url", descriptor.official_docs_url),
        ):
            if _host(url) not in descriptor.official_hosts:
                raise OfficialSourceRegistryError(
                    f"{descriptor.source_id} {url_field} host is outside official_hosts"
                )
        return descriptor

    def payload(self) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "institution": self.institution,
            "access_kind": self.access_kind,
            "auth_mode": self.auth_mode,
            "revision_mode": self.revision_mode,
            "base_url": self.base_url,
            "official_docs_url": self.official_docs_url,
            "official_hosts": list(self.official_hosts),
            "capabilities": list(self.capabilities),
            "transport_state": self.transport_state,
            "license_state": self.license_state,
            "verified_on": self.verified_on,
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class OfficialSourceRegistry:
    verified_on: str
    sources: tuple[OfficialSourceDescriptor, ...]

    @classmethod
    def from_path(
        cls,
        path: Path,
        *,
        policy: OfficialSourcePolicy,
    ) -> "OfficialSourceRegistry":
        raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        raw = _mapping(raw_value, field="registry root")
        if raw.get("schema_version") != "1.0":
            raise OfficialSourceRegistryError("unsupported registry schema_version")
        verified_on = _text(raw.get("verified_on"), field="verified_on")
        source_values = _object_list(raw.get("sources"), field="sources")
        sources = tuple(
            OfficialSourceDescriptor.from_mapping(_mapping(item, field="source descriptor"))
            for item in source_values
        )
        registry = cls(verified_on=verified_on, sources=sources)
        validate_registry(registry, policy=policy)
        return registry

    def payload(self) -> dict[str, object]:
        return {
            "schema_version": "1.0",
            "verified_on": self.verified_on,
            "sources": [source.payload() for source in sorted(self.sources, key=lambda item: item.source_id)],
        }

    @property
    def registry_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()

    def get(self, source_id: str) -> OfficialSourceDescriptor:
        for source in self.sources:
            if source.source_id == source_id:
                return source
        raise OfficialSourceRegistryError(f"unknown official source: {source_id}")


@dataclass(frozen=True, slots=True)
class OfficialSourceRequestSpec:
    source_id: str
    method: str
    url: str
    secret_handle: str | None
    intended_use: str

    def payload(self) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "method": self.method,
            "url": self.url,
            "secret_handle": self.secret_handle,
            "intended_use": self.intended_use,
        }


def validate_registry(
    registry: OfficialSourceRegistry,
    *,
    policy: OfficialSourcePolicy,
) -> None:
    ids = [source.source_id for source in registry.sources]
    if len(ids) != len(set(ids)):
        raise OfficialSourceRegistryError("source IDs must be unique")
    if set(ids) != set(policy.required_source_ids):
        raise OfficialSourceRegistryError("registry source set must exactly match policy required_source_ids")

    for source in registry.sources:
        if source.access_kind not in policy.allowed_access_kinds:
            raise OfficialSourceRegistryError(f"{source.source_id} access_kind is not allowed")
        if source.auth_mode not in policy.allowed_auth_modes:
            raise OfficialSourceRegistryError(f"{source.source_id} auth_mode is not allowed")
        if source.revision_mode not in policy.allowed_revision_modes:
            raise OfficialSourceRegistryError(f"{source.source_id} revision_mode is not allowed")
        if source.verified_on != registry.verified_on:
            raise OfficialSourceRegistryError(f"{source.source_id} verification date drift")
        if source.transport_state == "PRODUCTION_ACTIVE":
            raise OfficialSourceRegistryError("P10-A cannot activate production transport")

    expected = {
        "FRED_ALFRED": ("API_KEY_REQUIRED", "NATIVE_VINTAGE"),
        "ECB": ("NONE", "HISTORY_QUERY"),
        "EUROSTAT": ("NONE", "LATEST_ONLY"),
        "WORLD_BANK": ("NONE", "LATEST_WITH_REVISIONS_NO_NATIVE_VINTAGE"),
        "EIA": ("API_KEY_REQUIRED", "LATEST_WITH_REVISIONS_NO_NATIVE_VINTAGE"),
        "IEA": ("LICENSE_REVIEW_REQUIRED", "LICENSED_HISTORY"),
        "LBMA": ("LICENSE_REVIEW_REQUIRED", "LICENSED_HISTORY"),
    }
    by_id = {source.source_id: source for source in registry.sources}
    for source_id, (auth_mode, revision_mode) in expected.items():
        source = by_id[source_id]
        if source.auth_mode != auth_mode or source.revision_mode != revision_mode:
            raise OfficialSourceRegistryError(f"{source_id} critical semantics drift")

    if "INCLUDE_HISTORY" not in by_id["ECB"].capabilities:
        raise OfficialSourceRegistryError("ECB history capability missing")
    if "VINTAGE_DATES" not in by_id["FRED_ALFRED"].capabilities:
        raise OfficialSourceRegistryError("FRED/ALFRED vintage capability missing")


def build_offline_request_spec(
    source: OfficialSourceDescriptor,
    *,
    relative_path: str,
    method: str = "GET",
    secret_handle: str | None = None,
) -> OfficialSourceRequestSpec:
    if source.transport_state not in {"OFFLINE_REQUEST_SPEC_ALLOWED", "PUBLIC_DOWNLOAD_ONLY"}:
        raise OfficialSourceRegistryError(
            f"{source.source_id} transport requires revalidation/licence before request specs"
        )
    clean_path = relative_path.strip()
    if not clean_path or "://" in clean_path or clean_path.startswith("//"):
        raise OfficialSourceRegistryError("relative_path must be a non-empty relative path")
    normalized_method = method.strip().upper()
    if normalized_method not in {"GET", "POST"}:
        raise OfficialSourceRegistryError("only GET/POST request specs are allowed")

    if source.auth_mode == "API_KEY_REQUIRED":
        if secret_handle is None:
            raise OfficialSourceRegistryError(f"{source.source_id} requires secret handle")
        credential_ref = validate_secret_handle(secret_handle)
    else:
        credential_ref = validate_secret_handle(secret_handle) if secret_handle is not None else None

    url = source.base_url.rstrip("/") + "/" + clean_path.lstrip("/")
    if _host(url) not in source.official_hosts:
        raise OfficialSourceRegistryError("request URL escaped official source host")

    return OfficialSourceRequestSpec(
        source_id=source.source_id,
        method=normalized_method,
        url=url,
        secret_handle=credential_ref,
        intended_use="OFFLINE_REQUEST_SPEC_ONLY_NO_NETWORK",
    )


def assert_no_source_registry_trade_authority_fields() -> None:
    forbidden = {
        "order",
        "quantity",
        "leverage",
        "stop_loss",
        "take_profit",
        "recommendation",
        "probability",
        "entry",
        "exit",
        "risk_approval",
    }
    contract_fields = (
        {field.name for field in fields(OfficialSourceDescriptor)}
        | {field.name for field in fields(OfficialSourceRegistry)}
        | {field.name for field in fields(OfficialSourceRequestSpec)}
    )
    if forbidden & contract_fields:
        raise OfficialSourceRegistryError("official-source contracts expose trade authority fields")


def registry_with_replaced_source(
    registry: OfficialSourceRegistry,
    *,
    source_id: str,
    **changes: object,
) -> OfficialSourceRegistry:
    updated: list[OfficialSourceDescriptor] = []
    found = False
    for source in registry.sources:
        if source.source_id == source_id:
            updated.append(replace(source, **changes))
            found = True
        else:
            updated.append(source)
    if not found:
        raise OfficialSourceRegistryError(f"unknown official source: {source_id}")
    return OfficialSourceRegistry(verified_on=registry.verified_on, sources=tuple(updated))
