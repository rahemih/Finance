from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Mapping, cast


class AdapterContractError(ValueError):
    """P20-A deterministic execution-adapter contract invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise AdapterContractError(f"{field} must be an object")
    return cast(Mapping[str, object], value)


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AdapterContractError(f"{field} must be non-empty text")
    return value.strip()


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise AdapterContractError(f"{field} must be a positive integer")
    return value


def _tuple_of_text(value: object, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise AdapterContractError(f"{field} must be a non-empty list")
    items = cast(list[object], value)
    parsed = tuple(_text(item, field=field) for item in items)
    if len(set(parsed)) != len(parsed):
        raise AdapterContractError(f"{field} cannot contain duplicates")
    return parsed


@dataclass(frozen=True, slots=True)
class AdapterContractPolicy:
    markets: tuple[str, ...]
    environments: tuple[str, ...]
    sides: tuple[str, ...]
    order_types: tuple[str, ...]
    time_in_force: tuple[str, ...]
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "AdapterContractPolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise AdapterContractError(f"invalid P20-A policy JSON: {exc}") from exc
        raw = _mapping(raw_value, field="policy root")
        expected = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P20A_EXECUTION_ADAPTER_CONTRACT_POLICY",
            "task_id": "FIN-P20-WA-001",
            "mode": "DETERMINISTIC_ADAPTER_CONTRACT",
            "credential_mode": "NONE",
            "network_mode": "DISABLED",
            "external_order_submission": False,
            "live_execution_authority": False,
            "automatic_live_promotion": False,
            "live_trading": "DISABLED",
            "auto_trading": "DISABLED",
        }
        for key, value in expected.items():
            if raw.get(key) != value:
                raise AdapterContractError(f"P20-A policy mismatch: {key}")

        markets = _tuple_of_text(raw.get("markets"), field="markets")
        environments = _tuple_of_text(raw.get("environments"), field="environments")
        sides = _tuple_of_text(raw.get("sides"), field="sides")
        order_types = _tuple_of_text(raw.get("order_types"), field="order_types")
        time_in_force = _tuple_of_text(raw.get("time_in_force"), field="time_in_force")
        if markets != ("CRYPTO", "FOREX"):
            raise AdapterContractError("invalid P20-A market taxonomy")
        if environments != ("SIMULATED", "SANDBOX"):
            raise AdapterContractError("P20-A cannot enable LIVE environment")
        if sides != ("BUY", "SELL"):
            raise AdapterContractError("invalid P20-A side taxonomy")
        if order_types != ("MARKET", "LIMIT", "STOP"):
            raise AdapterContractError("invalid P20-A order-type taxonomy")
        if time_in_force != ("GTC", "IOC", "FOK", "DAY"):
            raise AdapterContractError("invalid P20-A time-in-force taxonomy")
        return cls(
            markets=markets,
            environments=environments,
            sides=sides,
            order_types=order_types,
            time_in_force=time_in_force,
            live_trading="DISABLED",
            auto_trading="DISABLED",
        )

    @property
    def policy_id(self) -> str:
        return hashlib.sha256(
            _canonical_bytes(
                {
                    "markets": list(self.markets),
                    "environments": list(self.environments),
                    "sides": list(self.sides),
                    "order_types": list(self.order_types),
                    "time_in_force": list(self.time_in_force),
                    "credential_mode": "NONE",
                    "network_mode": "DISABLED",
                    "live_execution_authority": False,
                    "live_trading": self.live_trading,
                    "auto_trading": self.auto_trading,
                }
            )
        ).hexdigest()


@dataclass(frozen=True, slots=True)
class AdapterDescriptor:
    adapter_name: str
    venue_id: str
    market: str
    environment: str
    api_version: str
    supported_order_types: tuple[str, ...]
    supported_time_in_force: tuple[str, ...]
    client_order_id_required: bool
    idempotency_key_required: bool
    cancel_supported: bool
    amend_supported: bool
    reconciliation_supported: bool

    def validate(self, policy: AdapterContractPolicy) -> None:
        for field in ("adapter_name", "venue_id", "api_version"):
            _text(getattr(self, field), field=field)
        if self.market not in policy.markets:
            raise AdapterContractError("adapter market is outside P20-A contract")
        if self.environment not in policy.environments:
            raise AdapterContractError("adapter environment is not authorized")
        if not self.supported_order_types:
            raise AdapterContractError("adapter must support at least one order type")
        if any(item not in policy.order_types for item in self.supported_order_types):
            raise AdapterContractError("adapter declares unsupported order type")
        if len(set(self.supported_order_types)) != len(self.supported_order_types):
            raise AdapterContractError("adapter order types cannot contain duplicates")
        if not self.supported_time_in_force:
            raise AdapterContractError("adapter must support at least one time-in-force")
        if any(item not in policy.time_in_force for item in self.supported_time_in_force):
            raise AdapterContractError("adapter declares unsupported time-in-force")
        if len(set(self.supported_time_in_force)) != len(self.supported_time_in_force):
            raise AdapterContractError("adapter time-in-force cannot contain duplicates")
        if not self.client_order_id_required:
            raise AdapterContractError("client_order_id must be mandatory")
        if not self.idempotency_key_required:
            raise AdapterContractError("idempotency key must be mandatory")
        if not self.reconciliation_supported:
            raise AdapterContractError("reconciliation capability is mandatory")

    def payload(self) -> dict[str, object]:
        return {
            "adapter_name": self.adapter_name,
            "venue_id": self.venue_id,
            "market": self.market,
            "environment": self.environment,
            "api_version": self.api_version,
            "supported_order_types": list(self.supported_order_types),
            "supported_time_in_force": list(self.supported_time_in_force),
            "client_order_id_required": self.client_order_id_required,
            "idempotency_key_required": self.idempotency_key_required,
            "cancel_supported": self.cancel_supported,
            "amend_supported": self.amend_supported,
            "reconciliation_supported": self.reconciliation_supported,
        }

    @property
    def adapter_contract_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class NormalizedOrderIntent:
    intent_id: str
    asset_id: str
    market: str
    side: str
    order_type: str
    quantity_scaled: int
    quantity_scale: int
    time_in_force: str
    limit_price_scaled: int | None = None
    stop_price_scaled: int | None = None
    price_scale: int | None = None

    def validate(self, policy: AdapterContractPolicy) -> None:
        _text(self.intent_id, field="intent_id")
        _text(self.asset_id, field="asset_id")
        if self.market not in policy.markets:
            raise AdapterContractError("intent market is outside P20-A contract")
        if self.side not in policy.sides:
            raise AdapterContractError("unsupported intent side")
        if self.order_type not in policy.order_types:
            raise AdapterContractError("unsupported intent order type")
        if self.time_in_force not in policy.time_in_force:
            raise AdapterContractError("unsupported intent time-in-force")
        _positive_int(self.quantity_scaled, field="quantity_scaled")
        _positive_int(self.quantity_scale, field="quantity_scale")
        if self.order_type == "MARKET":
            if any(
                value is not None
                for value in (
                    self.limit_price_scaled,
                    self.stop_price_scaled,
                    self.price_scale,
                )
            ):
                raise AdapterContractError("MARKET intent cannot carry price triggers")
        elif self.order_type == "LIMIT":
            _positive_int(self.limit_price_scaled, field="limit_price_scaled")
            _positive_int(self.price_scale, field="price_scale")
            if self.stop_price_scaled is not None:
                raise AdapterContractError("LIMIT intent cannot carry stop_price_scaled")
        elif self.order_type == "STOP":
            _positive_int(self.stop_price_scaled, field="stop_price_scaled")
            _positive_int(self.price_scale, field="price_scale")
            if self.limit_price_scaled is not None:
                raise AdapterContractError("STOP intent cannot carry limit_price_scaled")

    def payload(self) -> dict[str, object]:
        return {
            "intent_id": self.intent_id,
            "asset_id": self.asset_id,
            "market": self.market,
            "side": self.side,
            "order_type": self.order_type,
            "quantity_scaled": self.quantity_scaled,
            "quantity_scale": self.quantity_scale,
            "time_in_force": self.time_in_force,
            "limit_price_scaled": self.limit_price_scaled,
            "stop_price_scaled": self.stop_price_scaled,
            "price_scale": self.price_scale,
        }


@dataclass(frozen=True, slots=True)
class AdapterBinding:
    policy_id: str
    adapter_contract_id: str
    intent_hash: str
    market: str
    environment: str
    routing_mode: str = "CONTRACT_ONLY"
    credential_mode: str = "NONE"
    network_mode: str = "DISABLED"
    external_order_submission: bool = False
    live_execution_authority: bool = False

    @property
    def binding_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()

    def payload(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "adapter_contract_id": self.adapter_contract_id,
            "intent_hash": self.intent_hash,
            "market": self.market,
            "environment": self.environment,
            "routing_mode": self.routing_mode,
            "credential_mode": self.credential_mode,
            "network_mode": self.network_mode,
            "external_order_submission": self.external_order_submission,
            "live_execution_authority": self.live_execution_authority,
        }


class AdapterContractRegistry:
    def __init__(self, policy: AdapterContractPolicy) -> None:
        self._policy = policy
        self._by_name: dict[str, AdapterDescriptor] = {}
        self._venue_environment: set[tuple[str, str, str]] = set()

    def register(self, descriptor: AdapterDescriptor) -> str:
        descriptor.validate(self._policy)
        if descriptor.adapter_name in self._by_name:
            raise AdapterContractError("duplicate adapter_name")
        venue_key = (descriptor.venue_id, descriptor.market, descriptor.environment)
        if venue_key in self._venue_environment:
            raise AdapterContractError("duplicate venue/market/environment binding")
        self._by_name[descriptor.adapter_name] = descriptor
        self._venue_environment.add(venue_key)
        return descriptor.adapter_contract_id

    def bind(self, adapter_name: str, intent: NormalizedOrderIntent) -> AdapterBinding:
        intent.validate(self._policy)
        try:
            descriptor = self._by_name[adapter_name]
        except KeyError as exc:
            raise AdapterContractError("unknown adapter_name") from exc
        if descriptor.market != intent.market:
            raise AdapterContractError("adapter/intent market mismatch")
        if intent.order_type not in descriptor.supported_order_types:
            raise AdapterContractError("adapter does not support requested order type")
        if intent.time_in_force not in descriptor.supported_time_in_force:
            raise AdapterContractError("adapter does not support requested time-in-force")
        intent_hash = hashlib.sha256(_canonical_bytes(intent.payload())).hexdigest()
        return AdapterBinding(
            policy_id=self._policy.policy_id,
            adapter_contract_id=descriptor.adapter_contract_id,
            intent_hash=intent_hash,
            market=descriptor.market,
            environment=descriptor.environment,
        )

    def snapshot(self) -> dict[str, object]:
        adapters = [self._by_name[name].payload() for name in sorted(self._by_name)]
        payload = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P20A_ADAPTER_CONTRACT_REGISTRY",
            "task_id": "FIN-P20-WA-001",
            "policy_id": self._policy.policy_id,
            "adapters": adapters,
            "authority": {
                "routing_mode": "CONTRACT_ONLY",
                "credential_mode": "NONE",
                "network_mode": "DISABLED",
                "external_order_submission": False,
                "live_execution_authority": False,
                "live_trading": self._policy.live_trading,
                "auto_trading": self._policy.auto_trading,
            },
        }
        return {
            **payload,
            "snapshot_id": hashlib.sha256(_canonical_bytes(payload)).hexdigest(),
        }
