from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Mapping, cast

from .adapter_contract import (
    AdapterBinding,
    AdapterContractPolicy,
    AdapterDescriptor,
    NormalizedOrderIntent,
)


class ForexAdapterError(ValueError):
    """P20-C deterministic Forex execution-adapter invariant failure."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ForexAdapterError(f"{field} must be non-empty text")
    return value.strip()


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ForexAdapterError(f"{field} must be a positive integer")
    return value


@dataclass(frozen=True, slots=True)
class ForexExecutionPolicy:
    allowed_environments: tuple[str, ...]
    event_types: tuple[str, ...]
    live_trading: str
    auto_trading: str

    @classmethod
    def from_path(cls, path: Path) -> "ForexExecutionPolicy":
        try:
            raw_value: object = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ForexAdapterError(f"invalid P20-C policy JSON: {exc}") from exc
        if not isinstance(raw_value, Mapping):
            raise ForexAdapterError("P20-C policy root must be an object")
        raw = cast(Mapping[str, object], raw_value)
        expected: dict[str, object] = {
            "schema_version": "1.0",
            "kind": "NEXUS_QUANT_P20C_FOREX_EXECUTION_POLICY",
            "task_id": "FIN-P20-WC-001",
            "mode": "REFERENCE_SANDBOX_FOREX_EXECUTION",
            "market": "FOREX",
            "broker_selection": "NOT_SELECTED",
            "transport_mode": "REFERENCE_SANDBOX_ONLY",
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
                raise ForexAdapterError(f"P20-C policy mismatch: {key}")
        env_value = raw.get("allowed_environments")
        event_value = raw.get("event_types")
        if not isinstance(env_value, list) or not isinstance(event_value, list):
            raise ForexAdapterError("P20-C environment/event taxonomies must be lists")
        environments = tuple(
            _text(item, field="allowed_environments")
            for item in cast(list[object], env_value)
        )
        events = tuple(
            _text(item, field="event_types")
            for item in cast(list[object], event_value)
        )
        if environments != ("SIMULATED", "SANDBOX"):
            raise ForexAdapterError("P20-C cannot enable LIVE environment")
        if events != ("ACK", "REJECT", "CANCEL_ACK"):
            raise ForexAdapterError("invalid P20-C event taxonomy")
        return cls(environments, events, "DISABLED", "DISABLED")

    @property
    def policy_id(self) -> str:
        return hashlib.sha256(
            _canonical_bytes(
                {
                    "allowed_environments": list(self.allowed_environments),
                    "event_types": list(self.event_types),
                    "broker_selection": "NOT_SELECTED",
                    "credential_mode": "NONE",
                    "network_mode": "DISABLED",
                    "external_order_submission": False,
                    "live_execution_authority": False,
                    "live_trading": self.live_trading,
                    "auto_trading": self.auto_trading,
                }
            )
        ).hexdigest()


@dataclass(frozen=True, slots=True)
class ForexSymbolRule:
    asset_id: str
    broker_symbol: str
    quantity_scale: int
    quantity_step_scaled: int
    min_quantity_scaled: int
    price_scale: int
    price_tick_scaled: int
    pip_size_scaled: int

    def validate(self) -> None:
        _text(self.asset_id, field="asset_id")
        _text(self.broker_symbol, field="broker_symbol")
        _positive_int(self.quantity_scale, field="quantity_scale")
        _positive_int(self.quantity_step_scaled, field="quantity_step_scaled")
        _positive_int(self.min_quantity_scaled, field="min_quantity_scaled")
        _positive_int(self.price_scale, field="price_scale")
        _positive_int(self.price_tick_scaled, field="price_tick_scaled")
        _positive_int(self.pip_size_scaled, field="pip_size_scaled")
        if self.min_quantity_scaled % self.quantity_step_scaled != 0:
            raise ForexAdapterError("minimum quantity must align to quantity step")
        if self.pip_size_scaled % self.price_tick_scaled != 0:
            raise ForexAdapterError("pip size must align to price tick")


@dataclass(frozen=True, slots=True)
class ForexSubmitEnvelope:
    forex_policy_id: str
    adapter_contract_id: str
    binding_id: str
    intent_hash: str
    client_order_id: str
    idempotency_key: str
    asset_id: str
    broker_symbol: str
    side: str
    order_type: str
    quantity_scaled: int
    quantity_scale: int
    time_in_force: str
    limit_price_scaled: int | None
    stop_price_scaled: int | None
    price_scale: int | None
    environment: str
    transport_mode: str = "REFERENCE_SANDBOX_ONLY"
    credential_mode: str = "NONE"
    network_mode: str = "DISABLED"
    external_order_submission: bool = False
    live_execution_authority: bool = False

    def payload(self) -> dict[str, object]:
        return {
            "forex_policy_id": self.forex_policy_id,
            "adapter_contract_id": self.adapter_contract_id,
            "binding_id": self.binding_id,
            "intent_hash": self.intent_hash,
            "client_order_id": self.client_order_id,
            "idempotency_key": self.idempotency_key,
            "asset_id": self.asset_id,
            "broker_symbol": self.broker_symbol,
            "side": self.side,
            "order_type": self.order_type,
            "quantity_scaled": self.quantity_scaled,
            "quantity_scale": self.quantity_scale,
            "time_in_force": self.time_in_force,
            "limit_price_scaled": self.limit_price_scaled,
            "stop_price_scaled": self.stop_price_scaled,
            "price_scale": self.price_scale,
            "environment": self.environment,
            "transport_mode": self.transport_mode,
            "credential_mode": self.credential_mode,
            "network_mode": self.network_mode,
            "external_order_submission": self.external_order_submission,
            "live_execution_authority": self.live_execution_authority,
        }

    @property
    def request_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class ForexCancelEnvelope:
    forex_policy_id: str
    adapter_contract_id: str
    client_order_id: str
    broker_order_id: str
    broker_symbol: str
    environment: str
    transport_mode: str = "REFERENCE_SANDBOX_ONLY"
    credential_mode: str = "NONE"
    network_mode: str = "DISABLED"
    external_order_submission: bool = False
    live_execution_authority: bool = False

    def payload(self) -> dict[str, object]:
        return {
            "forex_policy_id": self.forex_policy_id,
            "adapter_contract_id": self.adapter_contract_id,
            "client_order_id": self.client_order_id,
            "broker_order_id": self.broker_order_id,
            "broker_symbol": self.broker_symbol,
            "environment": self.environment,
            "transport_mode": self.transport_mode,
            "credential_mode": self.credential_mode,
            "network_mode": self.network_mode,
            "external_order_submission": self.external_order_submission,
            "live_execution_authority": self.live_execution_authority,
        }

    @property
    def request_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


@dataclass(frozen=True, slots=True)
class ForexSandboxEvent:
    event_type: str
    request_id: str
    client_order_id: str
    broker_order_id: str | None = None
    reject_code: str | None = None

    def validate(self, policy: ForexExecutionPolicy) -> None:
        if self.event_type not in policy.event_types:
            raise ForexAdapterError("unsupported sandbox event type")
        _text(self.request_id, field="request_id")
        _text(self.client_order_id, field="client_order_id")
        if self.event_type in ("ACK", "CANCEL_ACK"):
            _text(self.broker_order_id, field="broker_order_id")
            if self.reject_code is not None:
                raise ForexAdapterError("ack event cannot carry reject_code")
        if self.event_type == "REJECT":
            _text(self.reject_code, field="reject_code")


@dataclass(frozen=True, slots=True)
class ForexAdapterResult:
    event_type: str
    disposition: str
    request_id: str
    client_order_id: str
    broker_order_id: str | None
    reject_code: str | None
    source: str = "REFERENCE_SANDBOX_EVENT"
    oms_state_authority: bool = False
    retry_authority: bool = False
    reconciliation_authority: bool = False
    live_execution_authority: bool = False

    def payload(self) -> dict[str, object]:
        return {
            "event_type": self.event_type,
            "disposition": self.disposition,
            "request_id": self.request_id,
            "client_order_id": self.client_order_id,
            "broker_order_id": self.broker_order_id,
            "reject_code": self.reject_code,
            "source": self.source,
            "oms_state_authority": self.oms_state_authority,
            "retry_authority": self.retry_authority,
            "reconciliation_authority": self.reconciliation_authority,
            "live_execution_authority": self.live_execution_authority,
        }

    @property
    def result_id(self) -> str:
        return hashlib.sha256(_canonical_bytes(self.payload())).hexdigest()


class ForexExecutionAdapter:
    def __init__(
        self,
        *,
        adapter_policy: AdapterContractPolicy,
        forex_policy: ForexExecutionPolicy,
        descriptor: AdapterDescriptor,
    ) -> None:
        descriptor.validate(adapter_policy)
        if descriptor.market != "FOREX":
            raise ForexAdapterError("P20-C requires a FOREX adapter descriptor")
        if descriptor.environment not in forex_policy.allowed_environments:
            raise ForexAdapterError("descriptor environment is outside P20-C policy")
        self._adapter_policy = adapter_policy
        self._forex_policy = forex_policy
        self._descriptor = descriptor

    @staticmethod
    def _intent_hash(intent: NormalizedOrderIntent) -> str:
        return hashlib.sha256(_canonical_bytes(intent.payload())).hexdigest()

    def build_submit(
        self,
        *,
        intent: NormalizedOrderIntent,
        binding: AdapterBinding,
        symbol_rule: ForexSymbolRule,
        client_order_id: str,
        idempotency_key: str,
    ) -> ForexSubmitEnvelope:
        intent.validate(self._adapter_policy)
        symbol_rule.validate()
        _text(client_order_id, field="client_order_id")
        _text(idempotency_key, field="idempotency_key")
        if intent.market != "FOREX" or binding.market != "FOREX":
            raise ForexAdapterError("P20-C accepts FOREX intent/binding only")
        if intent.asset_id != symbol_rule.asset_id:
            raise ForexAdapterError("intent asset does not match symbol rule")
        if binding.adapter_contract_id != self._descriptor.adapter_contract_id:
            raise ForexAdapterError("adapter contract lineage mismatch")
        intent_hash = self._intent_hash(intent)
        if binding.intent_hash != intent_hash:
            raise ForexAdapterError("binding intent lineage mismatch")
        if binding.environment != self._descriptor.environment:
            raise ForexAdapterError("binding environment mismatch")
        if binding.external_order_submission or binding.live_execution_authority:
            raise ForexAdapterError("P20-A binding cannot grant execution authority")
        if intent.order_type not in self._descriptor.supported_order_types:
            raise ForexAdapterError("adapter does not support requested order type")
        if intent.time_in_force not in self._descriptor.supported_time_in_force:
            raise ForexAdapterError("adapter does not support requested time-in-force")
        if intent.quantity_scale != symbol_rule.quantity_scale:
            raise ForexAdapterError("quantity scale mismatch")
        if intent.quantity_scaled < symbol_rule.min_quantity_scaled:
            raise ForexAdapterError("quantity below minimum")
        if intent.quantity_scaled % symbol_rule.quantity_step_scaled != 0:
            raise ForexAdapterError("quantity does not align to step")
        if intent.price_scale is not None and intent.price_scale != symbol_rule.price_scale:
            raise ForexAdapterError("price scale mismatch")
        for value in (intent.limit_price_scaled, intent.stop_price_scaled):
            if value is not None and value % symbol_rule.price_tick_scaled != 0:
                raise ForexAdapterError("price does not align to tick")
        return ForexSubmitEnvelope(
            forex_policy_id=self._forex_policy.policy_id,
            adapter_contract_id=self._descriptor.adapter_contract_id,
            binding_id=binding.binding_id,
            intent_hash=intent_hash,
            client_order_id=client_order_id,
            idempotency_key=idempotency_key,
            asset_id=intent.asset_id,
            broker_symbol=symbol_rule.broker_symbol,
            side=intent.side,
            order_type=intent.order_type,
            quantity_scaled=intent.quantity_scaled,
            quantity_scale=intent.quantity_scale,
            time_in_force=intent.time_in_force,
            limit_price_scaled=intent.limit_price_scaled,
            stop_price_scaled=intent.stop_price_scaled,
            price_scale=intent.price_scale,
            environment=self._descriptor.environment,
        )

    def build_cancel(
        self,
        *,
        client_order_id: str,
        broker_order_id: str,
        symbol_rule: ForexSymbolRule,
    ) -> ForexCancelEnvelope:
        if not self._descriptor.cancel_supported:
            raise ForexAdapterError("adapter does not support cancel")
        symbol_rule.validate()
        _text(client_order_id, field="client_order_id")
        _text(broker_order_id, field="broker_order_id")
        return ForexCancelEnvelope(
            forex_policy_id=self._forex_policy.policy_id,
            adapter_contract_id=self._descriptor.adapter_contract_id,
            client_order_id=client_order_id,
            broker_order_id=broker_order_id,
            broker_symbol=symbol_rule.broker_symbol,
            environment=self._descriptor.environment,
        )

    def parse_event(
        self,
        event: ForexSandboxEvent,
        *,
        expected_request_id: str,
        expected_client_order_id: str,
    ) -> ForexAdapterResult:
        event.validate(self._forex_policy)
        if event.request_id != expected_request_id:
            raise ForexAdapterError("sandbox event request lineage mismatch")
        if event.client_order_id != expected_client_order_id:
            raise ForexAdapterError("sandbox event client-order lineage mismatch")
        dispositions = {
            "ACK": "ACKNOWLEDGED",
            "REJECT": "REJECTED",
            "CANCEL_ACK": "CANCEL_ACKNOWLEDGED",
        }
        return ForexAdapterResult(
            event_type=event.event_type,
            disposition=dispositions[event.event_type],
            request_id=event.request_id,
            client_order_id=event.client_order_id,
            broker_order_id=event.broker_order_id,
            reject_code=event.reject_code,
        )
