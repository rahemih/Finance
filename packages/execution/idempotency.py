from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import string
from typing import Mapping, cast


class IdempotencyError(ValueError):
    """P20-E deterministic idempotency / duplicate-prevention invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise IdempotencyError(f"{field} must be non-empty text")
    return value.strip()


def _tuple_of_text(value: object, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise IdempotencyError(f"{field} must be a non-empty list")
    items = cast(list[object], value)
    parsed = tuple(_text(item, field=field) for item in items)
    if len(set(parsed)) != len(parsed):
        raise IdempotencyError(f"{field} cannot contain duplicates")
    return parsed


def _sha256_hex(value: object, *, field: str) -> str:
    text = _text(value, field=field).lower()
    if len(text) != 64 or any(ch not in string.hexdigits for ch in text):
        raise IdempotencyError(f"{field} must be a sha256 hex digest")
    return text


@dataclass(frozen=True, slots=True)
class IdempotencyPolicy:
    markets: tuple[str, ...]
    operations: tuple[str, ...]
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "IdempotencyPolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise IdempotencyError(f"invalid P20-E policy JSON: {exc}") from exc
        if not isinstance(raw_value, Mapping):
            raise IdempotencyError("P20-E policy root must be an object")
        raw = cast(Mapping[str, object], raw_value)
        expected: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P20E_IDEMPOTENCY_POLICY",
            "task_id": "FIN-P20-WE-001",
            "mode": "DETERMINISTIC_FAIL_CLOSED_IDEMPOTENCY",
            "exact_replay": "REPLAY_EXISTING",
            "conflicting_key_reuse": "REJECT",
            "duplicate_client_order_id": "REJECT",
            "duplicate_request_fingerprint": "REJECT",
            "duplicate_operation_order": "REJECT",
            "retry_owner": "P20-F",
            "reconciliation_owner": "P20-G",
            "execution_quality_owner": "P20-H",
            "simulation_gate_owner": "P20-I",
            "position_management_owner": "P21",
            "credential_mode": "NONE",
            "network_mode": "DISABLED",
            "external_order_submission": False,
            "live_execution_authority": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        for key, expected_value in expected.items():
            if raw.get(key) != expected_value:
                raise IdempotencyError(f"P20-E policy mismatch: {key}")
        markets = _tuple_of_text(raw.get("markets"), field="markets")
        operations = _tuple_of_text(raw.get("operations"), field="operations")
        if markets != ("CRYPTO", "FOREX"):
            raise IdempotencyError("invalid P20-E market taxonomy")
        if operations != ("ORDER_SUBMIT", "ORDER_CANCEL"):
            raise IdempotencyError("invalid P20-E operation taxonomy")
        return cls(markets=markets, operations=operations, live_trading="DISABLED", auto_trading="DISABLED")

    @property
    def policy_id(self) -> str:
        payload: dict[str, object] = {
            "markets": list(self.markets),
            "operations": list(self.operations),
            "exact_replay": "REPLAY_EXISTING",
            "retry_owner": "P20-F",
            "reconciliation_owner": "P20-G",
            "credential_mode": "NONE",
            "network_mode": "DISABLED",
            "external_order_submission": False,
            "live_execution_authority": False,
            "live_trading": self.live_trading,
            "auto_trading": self.auto_trading,
        }
        return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


@dataclass(frozen=True, slots=True)
class IdempotencyRequest:
    market: str
    operation: str
    order_id: str
    client_order_id: str
    idempotency_key: str
    request_fingerprint: str

    def validate(self, policy: IdempotencyPolicy) -> None:
        if self.market not in policy.markets:
            raise IdempotencyError("request market is outside P20-E policy")
        if self.operation not in policy.operations:
            raise IdempotencyError("request operation is outside P20-E policy")
        _text(self.order_id, field="order_id")
        _text(self.client_order_id, field="client_order_id")
        _text(self.idempotency_key, field="idempotency_key")
        _sha256_hex(self.request_fingerprint, field="request_fingerprint")

    def payload(self) -> dict[str, object]:
        return {
            "market": self.market,
            "operation": self.operation,
            "order_id": self.order_id,
            "client_order_id": self.client_order_id,
            "idempotency_key": self.idempotency_key,
            "request_fingerprint": self.request_fingerprint.lower(),
        }

    @property
    def request_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class IdempotencyClaim:
    policy_id: str
    market: str
    operation: str
    order_id: str
    client_order_id: str
    idempotency_key: str
    request_fingerprint: str
    request_id: str
    credential_mode: str = "NONE"
    network_mode: str = "DISABLED"
    external_order_submission: bool = False
    retry_authority: bool = False
    reconciliation_authority: bool = False
    live_execution_authority: bool = False

    def payload(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "market": self.market,
            "operation": self.operation,
            "order_id": self.order_id,
            "client_order_id": self.client_order_id,
            "idempotency_key": self.idempotency_key,
            "request_fingerprint": self.request_fingerprint,
            "request_id": self.request_id,
            "credential_mode": self.credential_mode,
            "network_mode": self.network_mode,
            "external_order_submission": self.external_order_submission,
            "retry_authority": self.retry_authority,
            "reconciliation_authority": self.reconciliation_authority,
            "live_execution_authority": self.live_execution_authority,
        }

    @property
    def claim_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class IdempotencyDecision:
    disposition: str
    claim_id: str
    request_id: str
    idempotency_key: str
    replay_existing: bool
    new_claim: bool
    retry_authority: bool = False
    reconciliation_authority: bool = False
    live_execution_authority: bool = False

    def payload(self) -> dict[str, object]:
        return {
            "disposition": self.disposition,
            "claim_id": self.claim_id,
            "request_id": self.request_id,
            "idempotency_key": self.idempotency_key,
            "replay_existing": self.replay_existing,
            "new_claim": self.new_claim,
            "retry_authority": self.retry_authority,
            "reconciliation_authority": self.reconciliation_authority,
            "live_execution_authority": self.live_execution_authority,
        }

    @property
    def decision_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


class IdempotencyLedger:
    def __init__(self, policy: IdempotencyPolicy) -> None:
        self._policy = policy
        self._by_key: dict[str, IdempotencyClaim] = {}
        self._client_key: dict[tuple[str, str], str] = {}
        self._fingerprint_key: dict[tuple[str, str, str], str] = {}
        self._operation_order_key: dict[tuple[str, str, str], str] = {}

    def admit(self, request: IdempotencyRequest) -> IdempotencyDecision:
        request.validate(self._policy)
        existing = self._by_key.get(request.idempotency_key)
        if existing is not None:
            if (
                existing.market == request.market
                and existing.operation == request.operation
                and existing.order_id == request.order_id
                and existing.client_order_id == request.client_order_id
                and existing.request_fingerprint == request.request_fingerprint.lower()
                and existing.request_id == request.request_id
            ):
                return IdempotencyDecision(
                    disposition="REPLAY_EXISTING",
                    claim_id=existing.claim_id,
                    request_id=request.request_id,
                    idempotency_key=request.idempotency_key,
                    replay_existing=True,
                    new_claim=False,
                )
            raise IdempotencyError("conflicting reuse of idempotency_key")

        client_scope = (request.market, request.client_order_id)
        claimed_client_key = self._client_key.get(client_scope)
        if claimed_client_key is not None:
            raise IdempotencyError("duplicate client_order_id under another idempotency key")

        fingerprint_scope = (
            request.market,
            request.operation,
            request.request_fingerprint.lower(),
        )
        claimed_fingerprint_key = self._fingerprint_key.get(fingerprint_scope)
        if claimed_fingerprint_key is not None:
            raise IdempotencyError("duplicate request fingerprint under another idempotency key")

        operation_order_scope = (request.market, request.operation, request.order_id)
        claimed_operation_order_key = self._operation_order_key.get(operation_order_scope)
        if claimed_operation_order_key is not None:
            raise IdempotencyError("duplicate operation/order claim under another idempotency key")

        claim = IdempotencyClaim(
            policy_id=self._policy.policy_id,
            market=request.market,
            operation=request.operation,
            order_id=request.order_id,
            client_order_id=request.client_order_id,
            idempotency_key=request.idempotency_key,
            request_fingerprint=request.request_fingerprint.lower(),
            request_id=request.request_id,
        )
        self._by_key[request.idempotency_key] = claim
        self._client_key[client_scope] = request.idempotency_key
        self._fingerprint_key[fingerprint_scope] = request.idempotency_key
        self._operation_order_key[operation_order_scope] = request.idempotency_key
        return IdempotencyDecision(
            disposition="ADMIT_NEW",
            claim_id=claim.claim_id,
            request_id=request.request_id,
            idempotency_key=request.idempotency_key,
            replay_existing=False,
            new_claim=True,
        )

    def claim(self, idempotency_key: str) -> IdempotencyClaim:
        try:
            return self._by_key[idempotency_key]
        except KeyError as exc:
            raise IdempotencyError("unknown idempotency key") from exc

    def snapshot(self) -> dict[str, object]:
        claims: list[dict[str, object]] = []
        for key in sorted(self._by_key):
            claim_payload: dict[str, object] = dict(self._by_key[key].payload())
            claim_payload["claim_id"] = self._by_key[key].claim_id
            claims.append(claim_payload)
        payload: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P20E_IDEMPOTENCY_SNAPSHOT",
            "task_id": "FIN-P20-WE-001",
            "policy_id": self._policy.policy_id,
            "claims": claims,
            "authority": {
                "retry_owner": "P20-F",
                "reconciliation_owner": "P20-G",
                "execution_quality_owner": "P20-H",
                "simulation_gate_owner": "P20-I",
                "position_management_owner": "P21",
                "credential_mode": "NONE",
                "network_mode": "DISABLED",
                "external_order_submission": False,
                "retry_authority": False,
                "reconciliation_authority": False,
                "live_execution_authority": False,
                "live_trading": self._policy.live_trading,
                "auto_trading": self._policy.auto_trading,
            },
        }
        snapshot: dict[str, object] = dict(payload)
        snapshot["snapshot_id"] = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
        return snapshot
