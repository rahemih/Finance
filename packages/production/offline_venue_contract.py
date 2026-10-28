"""Deterministic synthetic-only venue guard for P24 readiness research.

No sockets, venue SDKs, credentials, accounts, real orders, or live authority.
This module is *not* a production adapter and cannot certify a broker.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import cast


class OfflineVenueError(ValueError):
    """Fail-closed mock venue validation failure."""


EXPECTED_POLICY: dict[str, object] = {
    "schema_version": "1.0",
    "kind": "NEXUS_QUANT_P24_WR_OFFLINE_VENUE_REFERENCE",
    "task_id": "FIN-P24-WR-001",
    "claim_scope": "RESEARCH_SIMULATOR_ONLY",
    "environment": "SIMULATED",
    "venues": [
        {
            "id": "FIBO_CTRADER_DEMO_REFERENCE",
            "market": "FOREX",
            "transport": "OFFLINE_MOCK_ONLY",
            "supports_leverage": False,
        },
        {
            "id": "TABDEAL_SPOT_MOCK_REFERENCE",
            "market": "CRYPTO",
            "transport": "OFFLINE_MOCK_ONLY",
            "supports_leverage": False,
        },
    ],
    "credential_mode": "NONE",
    "network_mode": "DISABLED",
    "external_order_submission": False,
    "live_execution_authority": False,
    "first_live_owner_approval": "NOT_GRANTED",
    "g13": "NOT_STARTED",
    "live_trading": "DISABLED",
    "auto_trading": "DISABLED",
    "production_provider_selected": False,
    "production_venue_selected": False,
}
VENUE_MARKETS = {
    "FIBO_CTRADER_DEMO_REFERENCE": "FOREX",
    "TABDEAL_SPOT_MOCK_REFERENCE": "CRYPTO",
}


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")


@dataclass(frozen=True, slots=True)
class SyntheticIntent:
    venue_id: str
    market: str
    action: str
    side: str
    client_order_id: str
    quantity_scaled: int
    quantity_step_scaled: int
    price_scaled: int
    price_tick_scaled: int
    feed_sequence: int
    previous_sequence: int = 0
    filled_quantity_scaled: int = 0
    native_order_id: str | None = None
    known_order: bool = False
    feed_fresh: bool = True
    idempotency_seen: bool = False
    risk_veto: bool = False
    leveraged: bool = False
    environment: str = "SIMULATED"
    permission: str = "SYNTHETIC_ONLY"
    credential_mode: str = "NONE"
    network_mode: str = "DISABLED"
    external_order_submission: bool = False
    live_execution_authority: bool = False


@dataclass(frozen=True, slots=True)
class OfflineDecision:
    status: str
    decision_id: str
    venue_id: str
    execution_authority: bool = False
    external_order_submission: bool = False
    network_mode: str = "DISABLED"


@dataclass(frozen=True, slots=True)
class OfflineVenueReference:
    policy_id: str

    @classmethod
    def from_path(cls, path: Path) -> "OfflineVenueReference":
        try:
            parsed: object = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise OfflineVenueError("invalid reference policy") from exc
        if parsed != EXPECTED_POLICY:
            raise OfflineVenueError("reference policy drift or authority escalation")
        return cls(hashlib.sha256(canonical_bytes(parsed)).hexdigest())

    def evaluate(self, order: SyntheticIntent) -> OfflineDecision:
        if not isinstance(order, SyntheticIntent):
            raise OfflineVenueError("synthetic order required")
        if VENUE_MARKETS.get(order.venue_id) != order.market:
            raise OfflineVenueError("unapproved venue or market mismatch")
        if order.environment != "SIMULATED":
            raise OfflineVenueError("only SIMULATED environment permitted")
        if (
            order.permission != "SYNTHETIC_ONLY"
            or order.credential_mode != "NONE"
            or order.network_mode != "DISABLED"
            or order.external_order_submission is not False
            or order.live_execution_authority is not False
        ):
            raise OfflineVenueError("external authority or credentials forbidden")
        if order.leveraged:
            raise OfflineVenueError("leveraged orders forbidden in offline scope")
        if order.action not in ("SUBMIT_MOCK", "CANCEL_MOCK"):
            raise OfflineVenueError("unsupported simulated order operation")
        if order.side not in ("BUY", "SELL") or not order.client_order_id.strip():
            raise OfflineVenueError("invalid side or client order identity")
        integers = (
            order.quantity_scaled,
            order.quantity_step_scaled,
            order.price_scaled,
            order.price_tick_scaled,
            order.feed_sequence,
            order.previous_sequence,
            order.filled_quantity_scaled,
        )
        if any(type(value) is not int for value in integers):
            raise OfflineVenueError("integer scaled units required")
        if (
            order.quantity_scaled <= 0
            or order.quantity_step_scaled <= 0
            or order.price_scaled <= 0
            or order.price_tick_scaled <= 0
        ):
            raise OfflineVenueError("quantity and price must be positive")
        if (
            order.quantity_scaled % order.quantity_step_scaled != 0
            or order.price_scaled % order.price_tick_scaled != 0
        ):
            raise OfflineVenueError("quantity or price precision drift")
        if order.feed_sequence <= order.previous_sequence or order.previous_sequence < 0:
            raise OfflineVenueError("stale or regressed feed sequence")
        if order.feed_fresh is not True:
            raise OfflineVenueError("missing fresh market evidence")
        if order.idempotency_seen is not False:
            raise OfflineVenueError("duplicate client order intent")
        if order.risk_veto is not False:
            raise OfflineVenueError("A5 risk veto")
        if not 0 <= order.filled_quantity_scaled <= order.quantity_scaled:
            raise OfflineVenueError("fill quantity outside order bounds")
        if (
            order.action == "CANCEL_MOCK"
            or order.filled_quantity_scaled > 0
        ) and (not order.known_order or not order.native_order_id):
            raise OfflineVenueError("order reconciliation identity missing")
        payload: dict[str, object] = {
            "policy_id": self.policy_id,
            "venue_id": order.venue_id,
            "market": order.market,
            "action": order.action,
            "side": order.side,
            "client_order_id": order.client_order_id,
            "quantity_scaled": order.quantity_scaled,
            "price_scaled": order.price_scaled,
            "feed_sequence": order.feed_sequence,
            "native_order_id": order.native_order_id,
            "filled_quantity_scaled": order.filled_quantity_scaled,
        }
        return OfflineDecision(
            status="VALIDATED_OFFLINE_ONLY",
            decision_id=hashlib.sha256(canonical_bytes(payload)).hexdigest(),
            venue_id=order.venue_id,
        )
